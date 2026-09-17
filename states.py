"""State machine and screens for Elemental RPS.

Every screen is a :class:`AppState`: menu, mode select, help, the duel
itself and the result screen. A :class:`StateMachine` swaps states behind a
short fade transition; a shared :class:`Game` context owns cross-screen
resources (fonts, particles, floating text, screen shake, background tint
and an optional audio hook).

The duel state runs each round as a phase pipeline::

    countdown -> choose -> resolve (travel -> impact -> reveal) -> next round
                                                                 or -> result

The AI commits its choice the moment the choose phase begins, which is what
lets the hint power-up honestly reveal the category of the choice the AI
has already locked in.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from typing import Any

import pygame

import config
from ai_opponent import AIOpponent, element_category
from game_logic import Match, affordable_choices
from particle_system import ParticleSystem
from power_ups import POWERUP_TITLES, PowerUpManager
from ui import (
    Bar,
    Button,
    Countdown,
    ElementButton,
    FloatingTextManager,
    build_element_buttons,
    draw_rules_help,
    draw_text,
    lerp,
    lerp_color,
    load_fonts,
)


def ease_in_quad(t: float) -> float:
    """Accelerating ease used for the choice-impact collision."""
    return t * t


class AppState:
    """Base class for one screen.

    Attributes:
        game: Shared context (fonts, particles, shake, audio, machine).
    """

    def __init__(self, game: Game) -> None:
        """Attach the state to its shared game context."""
        self.game = game

    def enter(self, **params: Any) -> None:
        """Called right after the state becomes current; params vary per state."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process one pygame event."""

    def update(self, dt: float) -> None:
        """Advance the state by ``dt`` seconds."""

    def draw(self, surface: pygame.Surface, offset: tuple[float, float]) -> None:
        """Draw the screen; ``offset`` is the screen-shake shift for world items."""


# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------


class Game:
    """Shared context threaded through every state.

    Owns the fonts, particle system, floating text manager, screen shake,
    background tint, the state machine itself and an optional audio hook
    exposing ``play(name)`` (headless tests pass ``None``).
    """

    def __init__(
        self,
        fonts: dict[str, Any] | None = None,
        audio: Any | None = None,
        rng: random.Random | None = None,
    ) -> None:
        """Create the context; ``fonts`` loads lazily when omitted."""
        self.fonts = fonts if fonts is not None else load_fonts()
        self.audio = audio
        self.rng = rng if rng is not None else random.Random()
        self.particles = ParticleSystem(self.rng)
        self.floating = FloatingTextManager(self.fonts["h2"])
        self.machine = StateMachine(self)

        # Screen shake state.
        self.shake_time_left = 0.0
        self.shake_duration = 0.0
        self.shake_magnitude = 0.0
        self.shake_offset: tuple[float, float] = (0.0, 0.0)

        # Background tint follows the dominant element of recent rounds.
        self.tint_color: tuple[float, float, float] = tuple(config.BACKGROUND)

        # Register the screens.
        self.machine.register("menu", MenuState(self))
        self.machine.register("mode", ModeSelectState(self))
        self.machine.register("help", HelpState(self))
        self.machine.register("game", GameState(self))
        self.machine.register("result", ResultState(self))
        self.machine.change_state("menu", immediate=True)

    # -- Effects -------------------------------------------------------------

    def shake(self, duration: float, magnitude: float) -> None:
        """Start (or re-arm) a screen shake."""
        self.shake_time_left = duration
        self.shake_duration = duration
        self.shake_magnitude = magnitude

    def tint_toward(self, element: str | None) -> None:
        """Retarget the background tint at an element's identity color."""
        if element is None:
            self._tint_target = tuple(config.BACKGROUND)
        else:
            self._tint_target = lerp_color(
                config.BACKGROUND, config.ELEMENT_COLORS[element], config.BACKGROUND_TINT_STRENGTH
            )

    _tint_target: tuple[float, float, float] = tuple(config.BACKGROUND)

    def play_sound(self, name: str) -> None:
        """Play a named sound if an audio hook is installed."""
        if self.audio is not None:
            self.audio.play(name)

    # -- Frame drivers -------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Forward events to the current state."""
        self.machine.current.handle_event(event)

    def update(self, dt: float) -> None:
        """Advance shake, tint, particles, floating text and the current state."""
        if self.shake_time_left > 0.0:
            self.shake_time_left = max(0.0, self.shake_time_left - dt)
            remaining = self.shake_time_left / max(self.shake_duration, 0.0001)
            magnitude = self.shake_magnitude * remaining
            self.shake_offset = (
                self.rng.uniform(-magnitude, magnitude),
                self.rng.uniform(-magnitude, magnitude),
            )
        else:
            self.shake_offset = (0.0, 0.0)
        self.tint_color = tuple(
            lerp(current, target, min(1.0, config.BAR_LERP_SPEED * dt))
            for current, target in zip(self.tint_color, self._tint_target, strict=True)
        )
        self.machine.update(dt)
        self.particles.update(dt)
        self.floating.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Render the tinted background, the current state and top effects."""
        background = tuple(int(channel) for channel in self.tint_color)
        surface.fill(background)
        self.machine.current.draw(surface, self.shake_offset)
        self.particles.draw(surface, self.shake_offset)
        self.floating.draw(surface)
        self.machine.draw_transition(surface)


# ---------------------------------------------------------------------------
# State machine with fade transitions
# ---------------------------------------------------------------------------


class StateMachine:
    """Swaps between states behind a short fade-to-dark transition."""

    def __init__(self, game: Game) -> None:
        """Create the machine; states register themselves by name."""
        self.game = game
        self.states: dict[str, AppState] = {}
        self.current: AppState | None = None
        self._pending: str | None = None
        self._pending_params: dict[str, Any] = {}
        self._fade_phase: str | None = None  # "out" | "in" | None
        self._fade_t = 0.0

    def register(self, name: str, state: AppState) -> None:
        """Add a state under ``name``."""
        self.states[name] = state

    def change_state(self, name: str, immediate: bool = False, **params: Any) -> None:
        """Request a state change.

        Args:
            name: Registered state name.
            immediate: Skip the fade (used for the initial state).
            **params: Forwarded to the new state's ``enter``.
        """
        self._pending = name
        self._pending_params = params
        if immediate:
            self._commit_change()
            self._fade_phase = None
            self._fade_t = 0.0
        else:
            self._fade_phase = "out"
            self._fade_t = 0.0

    def _commit_change(self) -> None:
        """Swap in the pending state and call its ``enter``."""
        assert self._pending is not None
        self.current = self.states[self._pending]
        self.current.enter(**self._pending_params)
        self._pending = None
        self._pending_params = {}

    @property
    def transitioning(self) -> bool:
        """Whether a fade is currently running."""
        return self._fade_phase is not None

    def update(self, dt: float) -> None:
        """Advance the fade and the current state.

        Input is intentionally not blocked for long: the fade is brief
        (``config.TRANSITION_SECONDS`` per phase) and state logic keeps
        running during it.
        """
        if self._fade_phase == "out":
            self._fade_t += dt
            if self._fade_t >= config.TRANSITION_SECONDS:
                self._commit_change()
                self._fade_phase = "in"
                self._fade_t = 0.0
        elif self._fade_phase == "in":
            self._fade_t += dt
            if self._fade_t >= config.TRANSITION_SECONDS:
                self._fade_phase = None
                self._fade_t = 0.0
        if self.current is not None:
            self.current.update(dt)

    def draw_transition(self, surface: pygame.Surface) -> None:
        """Draw the fade overlay for the current phase."""
        if self._fade_phase is None:
            return
        progress = min(1.0, self._fade_t / config.TRANSITION_SECONDS)
        alpha = int(255 * (progress if self._fade_phase == "out" else 1.0 - progress))
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*config.BACKGROUND_ALT, alpha))
        surface.blit(overlay, (0, 0))


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------


class MenuState(AppState):
    """Title screen with Play, How to Play and Quit."""

    def __init__(self, game: Game) -> None:
        """Build the menu buttons from the shared fonts."""
        super().__init__(game)
        self.time = 0.0
        center_x = config.WINDOW_WIDTH / 2
        button_width, button_height = 320, config.BUTTON_HEIGHT
        self.play_button = Button(
            pygame.Rect(0, 0, button_width, button_height),
            "Play",
            self.game.fonts["h2"],
        )
        self.help_button = Button(
            pygame.Rect(0, 0, button_width, button_height),
            "How to Play",
            self.game.fonts["h2"],
        )
        self.quit_button = Button(
            pygame.Rect(0, 0, button_width, button_height),
            "Quit",
            self.game.fonts["h2"],
        )
        y = config.WINDOW_HEIGHT * 0.52
        for button in (self.play_button, self.help_button, self.quit_button):
            button.rect.center = (center_x, y)
            y += button_height + 18

    def handle_event(self, event: pygame.event.Event) -> None:
        """Commit menu choices on click."""
        if self.play_button.handle_event(event):
            self.game.play_sound("click")
            self.game.machine.change_state("mode")
        elif self.help_button.handle_event(event):
            self.game.play_sound("click")
            self.game.machine.change_state("help", return_to="menu")
        elif self.quit_button.handle_event(event):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt: float) -> None:
        """Advance the title pulse and button hover states."""
        self.time += dt
        for button in (self.play_button, self.help_button, self.quit_button):
            button.update(dt)

    def draw(self, surface: pygame.Surface, offset: tuple[float, float]) -> None:
        """Render the pulsing title and menu buttons."""
        pulse = 1.0 + 0.03 * math.sin(self.time * 2.0)
        title = self.game.fonts["title"].render("ELEMENTAL RPS", True, config.TEXT)
        size = (int(title.get_width() * pulse), int(title.get_height() * pulse))
        scaled = pygame.transform.smoothscale(title, size)
        surface.blit(scaled, scaled.get_rect(center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.22)))
        draw_text(
            surface,
            "Rock - Paper - Scissors - Fire - Water - Earth",
            self.game.fonts["body"],
            config.TEXT_DIM,
            center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.36),
        )
        for button in (self.play_button, self.help_button, self.quit_button):
            button.draw(surface)


# ---------------------------------------------------------------------------
# Mode select
# ---------------------------------------------------------------------------


class ModeSelectState(AppState):
    """Choose Best-of-3 / 5 / 7 before entering the duel."""

    def __init__(self, game: Game) -> None:
        """Build one button per configured best-of option plus Back."""
        super().__init__(game)
        self.buttons: list[tuple[int, Button]] = []
        button_width = 260
        spacing = 40
        total = len(config.BEST_OF_OPTIONS) * button_width + (len(config.BEST_OF_OPTIONS) - 1) * spacing
        x = (config.WINDOW_WIDTH - total) / 2 + button_width / 2
        for option in config.BEST_OF_OPTIONS:
            button = Button(
                pygame.Rect(0, 0, button_width, config.BUTTON_HEIGHT + 14),
                f"Best of {option}",
                self.game.fonts["h2"],
            )
            button.rect.center = (x, config.WINDOW_HEIGHT * 0.5)
            self.buttons.append((option, button))
            x += button_width + spacing
        self.back_button = Button(pygame.Rect(0, 0, 180, config.BUTTON_HEIGHT), "Back", self.game.fonts["body"])
        self.back_button.rect.center = (config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.78)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Start a match of the chosen length, or go back."""
        for option, button in self.buttons:
            if button.handle_event(event):
                self.game.play_sound("click")
                self.game.machine.change_state("game", best_of=option)
                return
        if self.back_button.handle_event(event):
            self.game.play_sound("click")
            self.game.machine.change_state("menu")

    def update(self, dt: float) -> None:
        """Refresh hover states."""
        for _, button in self.buttons:
            button.update(dt)
        self.back_button.update(dt)

    def draw(self, surface: pygame.Surface, offset: tuple[float, float]) -> None:
        """Render the prompt and the option buttons."""
        draw_text(
            surface,
            "Choose your battle",
            self.game.fonts["h1"],
            config.TEXT,
            center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.28),
        )
        draw_text(
            surface,
            "First side to run out of HP loses - higher HP wins if rounds run out.",
            self.game.fonts["small"],
            config.TEXT_DIM,
            center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.38),
        )
        for _, button in self.buttons:
            button.draw(surface)
        self.back_button.draw(surface)


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class HelpState(AppState):
    """The full rules table; returns to wherever it was opened from."""

    def __init__(self, game: Game) -> None:
        """Create the back button; ``return_to`` defaults to the menu."""
        super().__init__(game)
        self.return_to = "menu"
        self.back_button = Button(pygame.Rect(0, 0, 180, config.BUTTON_HEIGHT), "Back", self.game.fonts["body"])
        self.back_button.rect.center = (config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT - 38)

    def enter(self, return_to: str = "menu", **_: Any) -> None:
        """Remember which screen to return to."""
        self.return_to = return_to

    def handle_event(self, event: pygame.event.Event) -> None:
        """Back on click, Esc or H."""
        if self.back_button.handle_event(event):
            self.game.play_sound("click")
            self.game.machine.change_state(self.return_to)
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_h):
            self.game.machine.change_state(self.return_to)

    def update(self, dt: float) -> None:
        """Refresh hover state."""
        self.back_button.update(dt)

    def draw(self, surface: pygame.Surface, offset: tuple[float, float]) -> None:
        """Render the rules table and back button."""
        draw_rules_help(surface, self.game.fonts)
        self.back_button.draw(surface)


# ---------------------------------------------------------------------------
# The duel
# ---------------------------------------------------------------------------


class GameState(AppState):
    """The duel itself: countdown, choosing, resolution and round flow."""

    def __init__(self, game: Game) -> None:
        """Pre-build bars, buttons and helpers; ``start_match`` initializes a match."""
        super().__init__(game)
        self.best_of = config.DEFAULT_BEST_OF
        self.match: Match | None = None
        self.ai = AIOpponent(self.game.rng)
        self.powerups: PowerUpManager | None = None

        self.phase = "countdown"
        self._resolve_t = 0.0
        self._reveal_started = False
        self._impact_done = False
        self._done_t = 0.0
        self._result_requested = False
        self.result: Any | None = None
        self.ai_choice: str | None = None
        self._countdown_step_seen: str | None = None
        self.player_max_combo = 0

        self.countdown = Countdown(self.game.fonts["h1"], (config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.30))

        # Bars: HP on top, energy underneath, mirrored for both sides.
        bar_width, bar_height = 380, 24
        self.player_hp_bar = Bar(
            pygame.Rect(48, 34, bar_width, bar_height),
            config.MAX_HP,
            config.PLAYER_COLOR,
            label="HP",
            font=self.game.fonts["small"],
        )
        self.player_energy_bar = Bar(
            pygame.Rect(48, 66, bar_width - 40, 14),
            config.MAX_ENERGY,
            config.ACCENT,
            label="EN",
            font=self.game.fonts["small"],
            start_value=config.STARTING_ENERGY,
        )
        self.ai_hp_bar = Bar(
            pygame.Rect(config.WINDOW_WIDTH - 48 - bar_width, 34, bar_width, bar_height),
            config.MAX_HP,
            config.AI_COLOR,
            label="HP",
            font=self.game.fonts["small"],
        )
        self.ai_energy_bar = Bar(
            pygame.Rect(config.WINDOW_WIDTH - 48 - (bar_width - 40), 66, bar_width - 40, 14),
            config.MAX_ENERGY,
            config.WARNING,
            label="EN",
            font=self.game.fonts["small"],
            start_value=config.STARTING_ENERGY,
        )

        self.element_buttons: list[ElementButton] = build_element_buttons(
            self.game.fonts["body"], self.game.fonts["small"]
        )
        self._hotkeys = {str(index + 1): button.element for index, button in enumerate(self.element_buttons)}

        # Choice tokens flying toward the center during resolution.
        self._token_travel = config.CHOICE_TRAVEL_SECONDS
        self._player_token_pos = (90.0, config.WINDOW_HEIGHT * 0.42)
        self._ai_token_pos = (config.WINDOW_WIDTH - 90.0, config.WINDOW_HEIGHT * 0.42)
        self._center = (config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.40)

    # -- Lifecycle -----------------------------------------------------------

    def enter(self, best_of: int | None = None, **_: Any) -> None:
        """Start (or restart) a match of ``best_of`` rounds."""
        self.start_match(best_of if best_of is not None else self.best_of)

    def start_match(self, best_of: int) -> None:
        """Reset every piece of match state for a fresh duel."""
        self.best_of = best_of
        self.match = Match(best_of)
        self.ai.reset()
        self.powerups = PowerUpManager(self.match, self._ai_category_provider, self.game.rng)
        self.phase = "countdown"
        self.countdown.restart()
        self.result = None
        self.ai_choice = None
        self._resolve_t = 0.0
        self._reveal_started = False
        self._impact_done = False
        self._done_t = 0.0
        self._result_requested = False
        self.player_max_combo = 0
        self.game.particles.clear()
        self.game.floating.clear()
        self.game.tint_toward(None)
        for bar, value in (
            (self.player_hp_bar, config.MAX_HP),
            (self.player_energy_bar, config.STARTING_ENERGY),
            (self.ai_hp_bar, config.MAX_HP),
            (self.ai_energy_bar, config.STARTING_ENERGY),
        ):
            bar.display = float(value)
            bar.set_target(value)

    def _ai_category_provider(self) -> str:
        """Category of the AI's committed choice; used by the hint power-up."""
        return element_category(self.ai_choice) if self.ai_choice is not None else "classic"

    # -- Input ---------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route clicks/keys to buttons, power-ups and choices."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.machine.change_state("menu")
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            self.game.machine.change_state("help", return_to="game")
            return
        if self.match is None:
            return

        if self.powerups is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.powerups.try_claim(event.pos):
                    self.game.play_sound("powerup")
                    if self.powerups.last_pickup is not None:
                        self.game.floating.spawn(
                            self.powerups.last_pickup,
                            (config.WINDOW_WIDTH / 2 - 80, config.WINDOW_HEIGHT * 0.20),
                            config.SUCCESS,
                        )
                    return
            # "E" activates whichever power-up is on screen; the digits
            # 1-6 stay reserved for element choices.
            elif event.type == pygame.KEYDOWN and event.unicode.lower() == "e" and self.powerups.claim_by_hotkey():
                self.game.play_sound("powerup")
                return

        if self.phase == "choose":
            for button in self.element_buttons:
                if button.handle_event(event):
                    self._player_picked(button.element)
                    return
            if event.type == pygame.KEYDOWN and event.unicode in self._hotkeys:
                self._player_picked(self._hotkeys[event.unicode])

    def _player_picked(self, element: str) -> None:
        """Commit the player's choice and start the resolution pipeline."""
        assert self.match is not None and self.ai_choice is not None
        self.result = self.match.play_round(element, self.ai_choice)
        self.ai.observe(element)
        self.phase = "resolve"
        self._resolve_t = 0.0
        self._reveal_started = False
        self._impact_done = False
        self.game.play_sound("throw")

    # -- Simulation ----------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the phase pipeline and every animated widget."""
        if self.match is None:
            return
        match = self.match

        # Bars always chase the true values.
        self.player_hp_bar.set_target(match.player.hp)
        self.player_energy_bar.set_target(match.player.energy)
        self.ai_hp_bar.set_target(match.opponent.hp)
        self.ai_energy_bar.set_target(match.opponent.energy)
        for button in self.element_buttons:
            button.update(dt)
        self.player_hp_bar.update(dt)
        self.player_energy_bar.update(dt)
        self.ai_hp_bar.update(dt)
        self.ai_energy_bar.update(dt)
        self.player_max_combo = max(self.player_max_combo, match.player.combo)

        # Energy gating lives in update (not draw) so it stays testable:
        # unaffordable choices grey out while the player may act.
        if self.phase == "choose":
            affordable = set(affordable_choices(match.player))
            for button in self.element_buttons:
                button.set_affordable(button.element in affordable)
        else:
            for button in self.element_buttons:
                button.enabled = True

        if self.phase == "countdown":
            self.countdown.update(dt)
            label = self.countdown.label()
            if label != self._countdown_step_seen:
                self._countdown_step_seen = label
                if label is not None:
                    self.game.play_sound("tick")
            if self.countdown.finished:
                self._begin_choose_phase()
        elif self.phase == "choose":
            pass  # wait for input; buttons handle their own hover
        elif self.phase == "resolve":
            self._update_resolve(dt)
        elif self.phase == "done":
            self._done_t += dt
            if self._done_t >= config.TRANSITION_SECONDS and not self._result_requested:
                self._result_requested = True  # request the swap exactly once
                winner = match.winner()
                self.game.machine.change_state(
                    "result",
                    winner=winner,
                    rounds=match.rounds_played,
                    best_of=self.best_of,
                    max_combo=self.player_max_combo,
                    player_hp=match.player.hp,
                    ai_hp=match.opponent.hp,
                )

    def _begin_choose_phase(self) -> None:
        """Open the choosing window: regen, power-up pacing, AI commitment."""
        assert self.match is not None and self.powerups is not None
        self.match.start_round()
        self.powerups.on_round_started()
        self.phase = "choose"
        # The AI locks its move now, so the hint power-up stays honest.
        self.ai_choice = self.ai.choose(tuple(affordable_choices(self.match.opponent)))
        self._countdown_step_seen = None

    def _update_resolve(self, dt: float) -> None:
        """Run travel -> impact -> reveal for the current round result."""
        assert self.match is not None and self.result is not None
        self._resolve_t += dt
        impact_time = self._token_travel
        reveal_time = impact_time + config.IMPACT_PAUSE_SECONDS

        if not self._impact_done and self._resolve_t >= impact_time:
            self._impact_done = True
            self.game.particles.impact_burst(self._center)
            self.game.shake(0.18, 5.0)
            self.game.play_sound("clash")
            self.game.tint_toward(self.result.player_choice if self.result.outcome != "lose" else self.result.ai_choice)
        if self._reveal_started:
            if self._resolve_t >= reveal_time + config.RESULT_DISPLAY_SECONDS:
                if self.match.is_over():
                    self.phase = "done"
                    self._done_t = 0.0
                else:
                    self.phase = "countdown"
                    self.countdown.restart()
            return
        if self._resolve_t >= reveal_time:
            self._reveal_started = True
            self._spawn_reveal_effects()

    def _spawn_reveal_effects(self) -> None:
        """Floating damage/combo text, themed bursts, shake and sounds."""
        assert self.result is not None
        result = self.result
        if result.outcome != "tie":
            loser_element = result.ai_choice if result.outcome == "win" else result.player_choice
            burst_pos = self._ai_token_pos if result.outcome == "win" else self._player_token_pos
            self.game.particles.burst_for_element(loser_element, burst_pos)
        if result.outcome == "win":
            self.game.play_sound("win")
            if result.ai_damage_dealt > 0:
                self.game.floating.spawn(
                    f"-{result.ai_damage_dealt}", (self._center[0] + 40, self._center[1] - 30), config.SUCCESS
                )
            if result.player_combo >= 2:
                self.game.floating.spawn(
                    f"COMBO x{result.player_combo}", (self._center[0] - 160, self._center[1] - 70), config.WARNING
                )
        elif result.outcome == "lose":
            self.game.play_sound("lose")
            self.game.shake(config.SHAKE_DURATION_SECONDS, config.SHAKE_MAGNITUDE_PX)
            if result.ai_damage_dealt > 0:
                self.game.floating.spawn(
                    f"-{result.ai_damage_dealt}", (self._center[0] - 120, self._center[1] - 30), config.DANGER
                )
        else:
            self.game.play_sound("tie")
            self.game.floating.spawn("TIE", (self._center[0] - 30, self._center[1] - 40), config.TEXT_DIM)

    # -- Rendering -----------------------------------------------------------

    def _draw_token(
        self, surface: pygame.Surface, element: str, position: tuple[float, float], offset: tuple[float, float]
    ) -> None:
        """Draw one flying choice token as an element-colored disc with a glyph."""
        radius = 46
        center = (int(position[0] + offset[0]), int(position[1] + offset[1]))
        color = config.ELEMENT_COLORS[element]
        pygame.draw.circle(surface, color, center, radius)
        pygame.draw.circle(surface, darken_for_token(color), center, radius, width=3)
        glyph = self.game.fonts["h1"].render(GLYPHS[element], True, config.BACKGROUND)
        surface.blit(glyph, glyph.get_rect(center=center))

    def draw(self, surface: pygame.Surface, offset: tuple[float, float]) -> None:
        """Render the whole duel screen for the current phase."""
        if self.match is None:
            return
        match = self.match
        fonts = self.game.fonts

        # Top HUD: names, bars, round counter.
        draw_text(surface, "YOU", fonts["h2"], config.PLAYER_COLOR, topleft=(48, 4))
        draw_text(surface, "AI", fonts["h2"], config.AI_COLOR, topright=(config.WINDOW_WIDTH - 48, 4))
        self.player_hp_bar.draw(surface)
        self.player_energy_bar.draw(surface)
        self.ai_hp_bar.draw(surface)
        self.ai_energy_bar.draw(surface)
        draw_text(
            surface,
            f"Round {min(match.round_number, self.best_of)} / {self.best_of}",
            fonts["body"],
            config.TEXT,
            center=(config.WINDOW_WIDTH / 2, 40),
        )

        # Combo tracker under the player bars.
        if match.player.combo >= 2:
            draw_text(surface, f"COMBO x{match.player.combo}", fonts["body"], config.WARNING, topleft=(48, 92))

        # Active power-up bubble.
        if self.powerups is not None and self.powerups.active is not None:
            power_up = self.powerups.active
            center = (int(power_up.position[0]), int(power_up.position[1]))
            pulse = 1.0 + 0.08 * math.sin(pygame.time.get_ticks() / 180.0)
            radius = int(config.POWERUP_RADIUS * pulse)
            pygame.draw.circle(surface, config.WARNING, center, radius)
            pygame.draw.circle(surface, darken_for_token(config.WARNING), center, radius, width=3)
            draw_text(
                surface,
                POWERUP_TITLES[power_up.kind],
                fonts["small"],
                config.BACKGROUND,
                center=(center[0], center[1] - 8),
            )
            draw_text(
                surface,
                f"[{power_up.hotkey}] {power_up.description()}",
                fonts["tiny"],
                config.BACKGROUND,
                center=(center[0], center[1] + 14),
            )

        # Flying tokens and the winner glow during resolution.
        if self.phase == "resolve" and self.result is not None:
            result = self.result
            progress = ease_in_quad(min(1.0, self._resolve_t / self._token_travel))
            player_pos = (
                lerp(self._player_token_pos[0], self._center[0], progress),
                lerp(self._player_token_pos[1], self._center[1], progress),
            )
            ai_pos = (
                lerp(self._ai_token_pos[0], self._center[0], progress),
                lerp(self._ai_token_pos[1], self._center[1], progress),
            )
            self._draw_token(surface, result.player_choice, player_pos, offset)
            self._draw_token(surface, result.ai_choice, ai_pos, offset)
            if self._reveal_started and result.outcome != "tie":
                glow_element = result.player_choice if result.outcome == "win" else result.ai_choice
                glow_pos = player_pos if result.outcome == "win" else ai_pos
                glow_radius = 46 + 6 * math.sin(pygame.time.get_ticks() / 1000.0 * config.GLOW_PULSE_SPEED)
                pygame.draw.circle(
                    surface,
                    config.ELEMENT_COLORS[glow_element],
                    (int(glow_pos[0] + offset[0]), int(glow_pos[1] + offset[1])),
                    int(glow_radius),
                    width=4,
                )
            if self._reveal_started:
                banner, color = OUTCOME_BANNERS[result.outcome]
                draw_text(
                    surface, banner, fonts["h1"], color, center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.62)
                )
        elif self.phase == "choose":
            draw_text(
                surface,
                "Choose your element!",
                fonts["body"],
                config.TEXT_DIM,
                center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.42),
            )

        if self.phase == "countdown":
            self.countdown.draw(surface)
        for button in self.element_buttons:
            button.draw(surface)


GLYPHS: dict[str, str] = {
    "rock": "\u25cf",
    "paper": "\u25af",
    "scissors": "\u00d7",
    "fire": "\u25b2",
    "water": "\u25bc",
    "earth": "\u25a0",
}

OUTCOME_BANNERS: dict[str, tuple[str, tuple[int, int, int]]] = {
    "win": ("YOU WIN THE ROUND", config.SUCCESS),
    "lose": ("YOU LOSE THE ROUND", config.DANGER),
    "tie": ("TIE", config.TEXT_DIM),
}


def darken_for_token(color: tuple[int, int, int]) -> tuple[int, int, int]:
    """Border color for tokens: a moderately darkened element color."""
    return tuple(int(channel * 0.55) for channel in color)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


class ResultState(AppState):
    """Match outcome screen with rematch / mode / menu options."""

    def __init__(self, game: Game) -> None:
        """Create the three outcome buttons."""
        super().__init__(game)
        self.winner: str | None = None
        self.stats: dict[str, Any] = {}
        button_width = 260
        self.rematch_button = Button(
            pygame.Rect(0, 0, button_width, config.BUTTON_HEIGHT), "Rematch", self.game.fonts["h2"]
        )
        self.mode_button = Button(
            pygame.Rect(0, 0, button_width, config.BUTTON_HEIGHT), "Change Mode", self.game.fonts["h2"]
        )
        self.menu_button = Button(
            pygame.Rect(0, 0, button_width, config.BUTTON_HEIGHT), "Main Menu", self.game.fonts["h2"]
        )
        x = config.WINDOW_WIDTH / 2 - button_width - 20
        for button in (self.rematch_button, self.mode_button, self.menu_button):
            button.rect.center = (x, config.WINDOW_HEIGHT * 0.72)
            x += button_width + 40

    def enter(
        self,
        winner: str | None = None,
        rounds: int = 0,
        best_of: int = 3,
        max_combo: int = 0,
        player_hp: int = 0,
        ai_hp: int = 0,
        **_: Any,
    ) -> None:
        """Store the outcome and summary stats for drawing."""
        self.winner = winner
        self.stats = {
            "rounds": rounds,
            "best_of": best_of,
            "max_combo": max_combo,
            "player_hp": player_hp,
            "ai_hp": ai_hp,
        }

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route the three buttons; Esc returns to the menu."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.machine.change_state("menu")
            return
        if self.rematch_button.handle_event(event):
            self.game.play_sound("click")
            self.game.machine.change_state("game", best_of=self.stats["best_of"])
        elif self.mode_button.handle_event(event):
            self.game.play_sound("click")
            self.game.machine.change_state("mode")
        elif self.menu_button.handle_event(event):
            self.game.play_sound("click")
            self.game.machine.change_state("menu")

    def update(self, dt: float) -> None:
        """Refresh hover states."""
        for button in (self.rematch_button, self.mode_button, self.menu_button):
            button.update(dt)

    def draw(self, surface: pygame.Surface, offset: tuple[float, float]) -> None:
        """Render the outcome banner, stats and buttons."""
        titles = {
            "player": ("VICTORY!", config.SUCCESS),
            "ai": ("DEFEAT", config.DANGER),
            "draw": ("DRAW", config.TEXT_DIM),
        }
        title, color = titles.get(self.winner or "draw", ("DRAW", config.TEXT_DIM))
        draw_text(
            surface,
            title,
            self.game.fonts["title"],
            color,
            center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.30),
        )
        draw_text(
            surface,
            f"Rounds played: {self.stats['rounds']} / {self.stats['best_of']}   -   Best combo: x{self.stats['max_combo']}   -   Final HP  You {self.stats['player_hp']} : AI {self.stats['ai_hp']}",
            self.game.fonts["body"],
            config.TEXT,
            center=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT * 0.46),
        )
        for button in (self.rematch_button, self.mode_button, self.menu_button):
            button.draw(surface)


# A module-level type alias used by type checkers; Callable comes from
# collections.abc and is re-exported for providers configured by embedders.
ProviderFactory = Callable[[], str]
