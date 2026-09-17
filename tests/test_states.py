"""Headless tests for the state machine and game states."""

import os
import random

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import config
from states import Game, GameState, HelpState, ModeSelectState, ResultState


@pytest.fixture(scope="module", autouse=True)
def pygame_session():
    pygame.init()
    pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    yield
    pygame.quit()


@pytest.fixture()
def game():
    """A Game context with deterministic RNG and silent audio."""
    return Game(audio=None, rng=random.Random(42))


@pytest.fixture()
def surface():
    """A fresh headless drawing surface per test."""
    return pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))


def key_down(key):
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


def click_at(position):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (int(position[0]), int(position[1])), "button": 1})


def release_at(position):
    return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (int(position[0]), int(position[1])), "button": 1})


# ---------------------------------------------------------------------------
# State machine mechanics
# ---------------------------------------------------------------------------


class TestStateMachine:
    def test_immediate_change_enters_state(self, game):
        assert game.machine.current is game.machine.states["menu"]
        game.machine.change_state("mode", immediate=True)
        assert game.machine.current is game.machine.states["mode"]

    def test_transition_fades_out_then_in(self, game):
        game.machine.change_state("help", return_to="menu")
        assert game.machine.transitioning is True
        assert game.machine.current is game.machine.states["menu"]  # swap pending
        game.machine.update(config.TRANSITION_SECONDS + 0.01)  # finish fade-out
        assert game.machine.current is game.machine.states["help"]  # swapped
        assert game.machine.transitioning is True  # now fading in
        game.machine.update(config.TRANSITION_SECONDS + 0.01)
        assert game.machine.transitioning is False

    def test_enter_params_forwarded(self, game):
        game.machine.change_state("help", immediate=True, return_to="game")
        help_state = game.machine.states["help"]
        assert isinstance(help_state, HelpState)
        assert help_state.return_to == "game"


# ---------------------------------------------------------------------------
# Menu and mode select
# ---------------------------------------------------------------------------


class TestMenuFlow:
    def test_play_button_leads_to_mode_select(self, game):
        play = game.machine.states["menu"].play_button
        game.machine.states["menu"].handle_event(click_at(play.rect.center))
        game.machine.states["menu"].handle_event(release_at(play.rect.center))
        assert game.machine._pending == "mode"

    def test_quit_posts_pygame_quit(self, game):
        quit_button = game.machine.states["menu"].quit_button
        game.machine.states["menu"].handle_event(click_at(quit_button.rect.center))
        game.machine.states["menu"].handle_event(release_at(quit_button.rect.center))
        assert any(event.type == pygame.QUIT for event in pygame.event.get())

    def test_mode_select_starts_best_of(self, game):
        state = game.machine.states["mode"]
        assert isinstance(state, ModeSelectState)
        option, button = state.buttons[1]  # Best of 5
        state.handle_event(click_at(button.rect.center))
        state.handle_event(release_at(button.rect.center))
        assert state.game.machine._pending == "game"
        assert state.game.machine._pending_params["best_of"] == option


# ---------------------------------------------------------------------------
# Full duel flow
# ---------------------------------------------------------------------------


def settle_transition(game, cycles=4):
    """Run the fade cycle to completion."""
    for _ in range(cycles):
        game.machine.update(config.TRANSITION_SECONDS + 0.01)


def play_rounds_until(game, predicate, max_rounds=15):
    """Play rounds by picking affordable classic choices until predicate holds."""
    state: GameState = game.machine.states["game"]
    result_state = game.machine.states["result"]
    for _ in range(max_rounds):
        state._begin_choose_phase()
        # AI choice is committed by _begin_choose_phase.
        for button in state.element_buttons:
            if button.element in config.CLASSIC_ELEMENTS:
                state._player_picked(button.element)
                break
        # Drive resolution (and any pending state swap) to completion.
        for _ in range(120):
            game.update(0.05)
            if game.machine.current is result_state:
                break
            if state.phase == "choose" and not game.machine.transitioning:
                break
        if predicate(state):
            return state
    raise AssertionError("condition never reached")


class TestDuelFlow:
    def test_start_match_resets_everything(self, game):
        game.machine.change_state("game", immediate=True, best_of=5)
        state: GameState = game.machine.states["game"]
        assert state.match is not None
        assert state.best_of == 5
        assert state.match.best_of == 5
        assert state.phase == "countdown"
        assert state.player_hp_bar.target == config.MAX_HP

    def test_countdown_then_choose(self, game):
        game.machine.change_state("game", immediate=True, best_of=3)
        state: GameState = game.machine.states["game"]
        for _ in range(60):
            state.update(0.1)
            if state.phase != "countdown":
                break
        assert state.phase == "choose"
        assert state.ai_choice in config.ELEMENTS

    def test_full_round_produces_result_and_damage(self, game):
        game.machine.change_state("game", immediate=True, best_of=7)
        state: GameState = game.machine.states["game"]
        for _ in range(60):
            state.update(0.1)
            if state.phase == "choose":
                break
        before = state.match.opponent.hp
        for button in state.element_buttons:
            if button.element == "rock":
                state._player_picked(button.element)
                break
        for _ in range(60):
            state.update(0.05)
            if state.phase != "resolve":
                break
        assert state.result is not None
        assert state.result.round_number == 1
        hp_change = before - state.match.opponent.hp
        assert hp_change == state.result.player_damage_dealt  # consistent damage
        assert state.phase in ("countdown", "done")

    def test_match_reaches_result_state(self, game):
        game.machine.change_state("game", immediate=True, best_of=3)
        settle_transition(game)
        play_rounds_until(game, lambda s: game.machine.current is game.machine.states["result"])
        assert game.machine.current is game.machine.states["result"]

    def test_hotkey_choice_works(self, game):
        game.machine.change_state("game", immediate=True, best_of=3)
        state: GameState = game.machine.states["game"]
        for _ in range(60):
            state.update(0.1)
            if state.phase == "choose":
                break
        state.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_1, "unicode": "1"}))
        assert state.phase == "resolve"
        assert state.result is not None
        assert state.result.player_choice == "rock"

    def test_escape_leaves_duel(self, game):
        game.machine.change_state("game", immediate=True, best_of=3)
        state: GameState = game.machine.states["game"]
        state.handle_event(key_down(pygame.K_ESCAPE))
        assert game.machine._pending == "menu"

    def test_help_roundtrip_from_game(self, game):
        game.machine.change_state("game", immediate=True, best_of=3)
        state: GameState = game.machine.states["game"]
        state.handle_event(key_down(pygame.K_h))
        settle_transition(game)
        assert game.machine.current is game.machine.states["help"]
        game.machine.states["help"].handle_event(key_down(pygame.K_ESCAPE))
        settle_transition(game)
        assert game.machine.current is game.machine.states["game"]

    def test_unaffordable_choices_grey_out(self, game):
        game.machine.change_state("game", immediate=True, best_of=3)
        state: GameState = game.machine.states["game"]
        state._begin_choose_phase()
        state.match.player.energy = config.COST_CLASSIC + 1
        state.update(0.016)  # affordability refresh happens in update
        affordable = {button.element for button in state.element_buttons if button.enabled}
        assert affordable == set(config.CLASSIC_ELEMENTS)


# ---------------------------------------------------------------------------
# Result screen
# ---------------------------------------------------------------------------


class TestResultScreen:
    def test_rematch_returns_to_game(self, game):
        result_state: ResultState = game.machine.states["result"]
        result_state.enter(winner="player", rounds=3, best_of=3, max_combo=2, player_hp=80, ai_hp=0)
        result_state.rematch_button.update(0.016)
        result_state.handle_event(click_at(result_state.rematch_button.rect.center))
        result_state.handle_event(release_at(result_state.rematch_button.rect.center))
        assert game.machine._pending == "game"
        assert game.machine._pending_params["best_of"] == 3

    def test_draw_result(self, game, surface):
        result_state: ResultState = game.machine.states["result"]
        result_state.enter(winner="draw", rounds=3, best_of=3, max_combo=0, player_hp=55, ai_hp=55)
        result_state.draw(surface, (0.0, 0.0))  # renders the draw banner


# ---------------------------------------------------------------------------
# Shared context effects
# ---------------------------------------------------------------------------


class TestGameEffects:
    def test_shake_decays_to_zero(self, game):
        game.shake(0.2, 8.0)
        game.update(0.02)  # mid-shake: offset wanders off zero
        assert game.shake_offset != (0.0, 0.0)
        for _ in range(40):
            game.update(0.05)
        assert game.shake_offset == (0.0, 0.0)
        assert game.shake_time_left == 0.0

    def test_tint_follows_element_and_neutral(self, game):
        game.tint_toward("fire")
        for _ in range(60):
            game.update(0.05)
        target = tuple(
            int(c * (1 - config.BACKGROUND_TINT_STRENGTH) + e * config.BACKGROUND_TINT_STRENGTH)
            for c, e in zip(config.BACKGROUND, config.ELEMENT_COLORS["fire"], strict=True)
        )
        assert all(abs(a - b) <= 2 for a, b in zip(game.tint_color, target, strict=True))
        game.tint_toward(None)
        for _ in range(60):
            game.update(0.05)
        assert game.tint_color == tuple(float(channel) for channel in config.BACKGROUND)

    def test_audio_hook_receives_named_sounds(self, game):
        played = []

        class Audio:
            def play(self, name):
                played.append(name)

        game.audio = Audio()
        game.play_sound("clash")
        game.play_sound("win")
        assert played == ["clash", "win"]

    def test_draw_full_frame(self, game, surface):
        """A full frame renders for every state without errors."""
        for name in ("menu", "mode", "help", "game", "result"):
            game.machine.change_state(name, immediate=True, return_to="menu")
            game.update(0.016)
            game.draw(surface)


# ---------------------------------------------------------------------------
# AI commitment honesty (hint power-up)
# ---------------------------------------------------------------------------


def test_hint_provider_reports_committed_choice(game):
    game.machine.change_state("game", immediate=True, best_of=3)
    state: GameState = game.machine.states["game"]
    for _ in range(60):
        state.update(0.1)
        if state.phase == "choose":
            break
    provider_category = state._ai_category_provider()
    assert provider_category == ("elemental" if state.ai_choice in config.ELEMENTAL_ELEMENTS else "classic")
