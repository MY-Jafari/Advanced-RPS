"""Reusable UI widgets for Elemental RPS.

Everything visual that more than one screen needs lives here: font
loading, text helpers, buttons (with press feedback and disabled states),
animated HP/energy bars, the round countdown, floating combat text and the
rules-help table layout.

The module follows the fluid-feedback rules: interactive widgets respond
visually on mouse-down, commit on mouse-up, and every animated value moves
smoothly toward its target instead of snapping. Only ``pygame`` is used;
no asset files are required.
"""

from __future__ import annotations

import math
from typing import Any

import pygame

import config
from game_logic import (
    BEATS,
    JUSTIFICATIONS,
    TIE_JUSTIFICATIONS,
    TIES,
    Element,
)

# Unicode glyphs that render in the stock Arial font; used as element icons.
ELEMENT_GLYPHS: dict[Element, str] = {
    "rock": "\u25cf",  # ●
    "paper": "\u25af",  # ▯
    "scissors": "\u00d7",  # ×
    "fire": "\u25b2",  # ▲
    "water": "\u25bc",  # ▼
    "earth": "\u25a0",  # ■
}


# ---------------------------------------------------------------------------
# Fonts and small drawing helpers
# ---------------------------------------------------------------------------


def load_fonts() -> dict[str, pygame.font.Font]:
    """Load the UI font set, trying config candidates before falling back.

    Requires ``pygame.font.init()`` (done by ``pygame.init()``).

    Returns:
        Mapping of ``config.FONT_SIZES`` keys to ready-to-use fonts.
    """
    for candidate in config.FONT_CANDIDATES:
        try:
            return {name: pygame.font.Font(candidate, size) for name, size in config.FONT_SIZES.items()}
        except (OSError, pygame.error):
            continue
    return {name: pygame.font.Font(None, size) for name, size in config.FONT_SIZES.items()}


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    center: tuple[float, float] | None = None,
    topleft: tuple[float, float] | None = None,
) -> pygame.Rect:
    """Render one line of text anchored at ``center`` or ``topleft``.

    Returns:
        The blit rectangle (handy for hit tests and layout math).
    """
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center is not None:
        rect.center = (int(center[0]), int(center[1]))
    elif topleft is not None:
        rect.topleft = (int(topleft[0]), int(topleft[1]))
    surface.blit(rendered, rect)
    return rect


def lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation clamped to ``t`` in ``[0, 1]``."""
    t = min(1.0, max(0.0, t))
    return start + (end - start) * t


def lerp_color(start: tuple[int, int, int], end: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Per-channel linear interpolation between two colors."""
    return tuple(int(lerp(s, e, t)) for s, e in zip(start, end, strict=True))  # type: ignore[return-value]


def darken(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Scale a color toward black by ``factor`` (1.0 = unchanged)."""
    return tuple(int(channel * factor) for channel in color)  # type: ignore[return-value]


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int], radius: int = 10) -> None:
    """Draw a filled rounded rectangle used as a card/panel background."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, darken(color, 0.7), rect, width=1, border_radius=radius)


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------


class Button:
    """A clickable rounded-rect button with hover and press feedback.

    Feedback follows the press, not the release: the fill darkens the
    instant the mouse goes down inside the button, and the click only
    commits on release inside it (so users can cancel by dragging away).

    Attributes:
        rect: Hit box and draw area.
        label: Text shown centered on the button.
        enabled: Disabled buttons ignore clicks and render dimmed.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        enabled: bool = True,
        accent: tuple[int, int, int] = config.ACCENT,
    ) -> None:
        """Create a button; styling colors come from the config palette."""
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.enabled = enabled
        self.accent = accent
        self.pressed = False
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process a pygame event; return ``True`` exactly on a committed click."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.enabled and self.rect.collidepoint(event.pos):
                self.pressed = True
                return False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.enabled and self.rect.collidepoint(event.pos):
                return True
        return False

    def update(self, dt: float) -> None:
        """Refresh hover state from the current mouse position."""
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, surface: pygame.Surface) -> None:
        """Render the button with its current state colors."""
        if not self.enabled:
            fill, border, text_color = config.PANEL, config.PANEL, config.TEXT_DISABLED
        elif self.pressed:
            fill, border, text_color = darken(self.accent, 0.45), self.accent, config.TEXT
        elif self.hovered:
            fill, border, text_color = config.PANEL_LIGHT, self.accent, config.TEXT
        else:
            fill, border, text_color = config.PANEL, darken(self.accent, 0.75), config.TEXT
        draw_panel(surface, self.rect, fill)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=config.BUTTON_RADIUS)
        draw_text(surface, self.label, self.font, text_color, center=self.rect.center)


class ElementButton(Button):
    """A choice button for one element: icon, name, cost and hotkey badge.

    Disabled state doubles as the energy system: choices the player cannot
    afford render grey and ignore clicks.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        element: Element,
        font_body: pygame.font.Font,
        font_small: pygame.font.Font,
        affordable: bool = True,
        hotkey: str = "",
    ) -> None:
        """Create an element button; ``hotkey`` renders as a corner badge."""
        super().__init__(rect, label=element.capitalize(), font=font_body, enabled=affordable)
        self.element = element
        self.font_small = font_small
        self.hotkey = hotkey

    def set_affordable(self, affordable: bool) -> None:
        """Enable or disable the button from the player's energy budget."""
        self.enabled = affordable

    def draw(self, surface: pygame.Surface) -> None:
        """Render icon, name, cost and hotkey in the element's color."""
        if not self.enabled:
            border = config.PANEL_LIGHT
        elif self.pressed or self.hovered:
            border = config.ELEMENT_COLORS[self.element]
        else:
            border = darken(config.ELEMENT_COLORS[self.element], 0.7)
        draw_panel(surface, self.rect, config.PANEL)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=config.BUTTON_RADIUS)

        icon_color = config.ELEMENT_COLORS[self.element] if self.enabled else config.TEXT_DISABLED
        cx = self.rect.centerx
        glyph = ELEMENT_GLYPHS[self.element]
        icon_rect = draw_text(surface, glyph, self.font, icon_color, center=(cx - 58, self.rect.centery))
        draw_text(
            surface,
            self.label,
            self.font,
            config.TEXT if self.enabled else config.TEXT_DISABLED,
            topleft=(icon_rect.right + 8, self.rect.centery - 14),
        )
        cost = config.COST_ELEMENTAL if self.element in config.ELEMENTAL_ELEMENTS else config.COST_CLASSIC
        draw_text(
            surface,
            f"EN {cost}",
            self.font_small,
            config.TEXT_DIM if self.enabled else config.TEXT_DISABLED,
            topleft=(icon_rect.right + 8, self.rect.centery + 2),
        )
        if self.hotkey:
            badge = pygame.Rect(0, 0, 22, 22)
            badge.bottomright = (self.rect.right - 6, self.rect.bottom - 6)
            pygame.draw.rect(surface, darken(config.PANEL_LIGHT, 0.9), badge, border_radius=6)
            draw_text(surface, self.hotkey, self.font_small, config.TEXT_DIM, center=badge.center)


def build_element_buttons(font_body: pygame.font.Font, font_small: pygame.font.Font) -> list[ElementButton]:
    """Lay out the 3x2 element choice grid above the bottom edge.

    Row one holds the classic choices, row two the elemental ones; hotkeys
    follow ``config.ELEMENTS`` order (``1``-``6``).

    Returns:
        Fully positioned buttons ready for the game state.
    """
    cell_width, cell_height, gap, bottom_margin = 208, 72, 16, 28
    total_width = 3 * cell_width + 2 * gap
    x0 = (config.WINDOW_WIDTH - total_width) // 2
    y_row2 = config.WINDOW_HEIGHT - bottom_margin - cell_height
    y_row1 = y_row2 - cell_height - gap
    buttons: list[ElementButton] = []
    for index, element in enumerate(config.ELEMENTS):
        row, col = divmod(index, 3)
        rect = pygame.Rect(x0 + col * (cell_width + gap), y_row1 if row == 0 else y_row2, cell_width, cell_height)
        buttons.append(ElementButton(rect, element, font_body, font_small, affordable=True, hotkey=str(index + 1)))
    return buttons


# ---------------------------------------------------------------------------
# Animated bars
# ---------------------------------------------------------------------------


class Bar:
    """A smoothly animated horizontal value bar (HP, energy).

    The drawn fill chases its target value exponentially each frame, so
    damage and regeneration visibly drain/refill instead of jumping.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        max_value: float,
        fill_color: tuple[int, int, int],
        label: str = "",
        font: pygame.font.Font | None = None,
        start_value: float | None = None,
    ) -> None:
        """Create a bar starting full (or at ``start_value``) and already settled."""
        self.rect = pygame.Rect(rect)
        self.max_value = max(1.0, float(max_value))
        self.fill_color = fill_color
        self.label = label
        self.font = font
        self.target = float(max_value if start_value is None else start_value)
        self.display = self.target

    def set_target(self, value: float) -> None:
        """Set the value the fill should animate toward."""
        self.target = min(self.max_value, max(0.0, float(value)))

    def update(self, dt: float) -> None:
        """Move the displayed value toward the target (frame-rate independent).

        Uses exponential smoothing ``1 - e^(-speed*dt)`` so the fill moves
        fast while far from the target and settles gently, at any frame rate.
        """
        difference = self.target - self.display
        if abs(difference) < 0.05:
            self.display = self.target
            return
        self.display += difference * (1.0 - math.exp(-config.BAR_LERP_SPEED * dt))

    def draw(self, surface: pygame.Surface) -> None:
        """Render track, animated fill and optional right-side label."""
        draw_panel(surface, self.rect, darken(config.PANEL, 0.8))
        inner = self.rect.inflate(-8, -8)
        fraction = self.display / self.max_value
        if fraction > 0:
            fill_width = max(6, int(inner.width * fraction))
            fill_rect = pygame.Rect(0, 0, fill_width, inner.height)
            fill_rect.topleft = inner.topleft
            color = self.fill_color
            if fraction < 0.3:  # low-value warning blend
                color = lerp_color(config.DANGER, self.fill_color, fraction / 0.3)
            pygame.draw.rect(surface, color, fill_rect, border_radius=8)
        if self.label and self.font is not None:
            draw_text(surface, self.label, self.font, config.TEXT_DIM, center=(self.rect.right + 42, self.rect.centery))


# ---------------------------------------------------------------------------
# Countdown, floating text
# ---------------------------------------------------------------------------


class Countdown:
    """The 3-2-1-Go! pre-round countdown with a scale pulse per step."""

    def __init__(self, font: pygame.font.Font, position: tuple[float, float]) -> None:
        """Create a countdown starting fresh from the first number."""
        self.font = font
        self.position = position
        self.elapsed = 0.0
        self.total = (config.COUNTDOWN_STEPS + 1) * config.COUNTDOWN_STEP_SECONDS

    def restart(self) -> None:
        """Reset the countdown to its first step."""
        self.elapsed = 0.0

    @property
    def finished(self) -> bool:
        """Whether the full 3-2-1-Go! sequence has played out."""
        return self.elapsed >= self.total

    def label(self) -> str | None:
        """Current display text, or ``None`` once finished."""
        if self.finished:
            return None
        step_index = int(self.elapsed // config.COUNTDOWN_STEP_SECONDS)
        if step_index < config.COUNTDOWN_STEPS:
            return str(config.COUNTDOWN_STEPS - step_index)
        return "GO!"

    def update(self, dt: float) -> None:
        """Advance the countdown clock."""
        self.elapsed += dt

    def draw(self, surface: pygame.Surface) -> None:
        """Render the current label, pulsing and fading within each step."""
        label = self.label()
        if label is None:
            return
        step_progress = (self.elapsed % config.COUNTDOWN_STEP_SECONDS) / config.COUNTDOWN_STEP_SECONDS
        scale = 0.85 + 0.45 * step_progress
        rendered = self.font.render(label, True, config.TEXT if label != "GO!" else config.SUCCESS)
        size = (max(1, int(rendered.get_width() * scale)), max(1, int(rendered.get_height() * scale)))
        scaled = pygame.transform.smoothscale(rendered, size)
        scaled.set_alpha(int(255 * (1.0 - 0.55 * step_progress)))
        rect = scaled.get_rect(center=(int(self.position[0]), int(self.position[1])))
        surface.blit(scaled, rect)


class FloatingText:
    """One rising, fading text snippet (combo counters, pickups, damage)."""

    __slots__ = ("text", "x", "y", "color", "age", "lifetime")

    def __init__(
        self, text: str, position: tuple[float, float], color: tuple[int, int, int], lifetime: float = 1.2
    ) -> None:
        """Create a floating text with its rise duration."""
        self.text = text
        self.x, self.y = position
        self.color = color
        self.age = 0.0
        self.lifetime = lifetime

    def update(self, dt: float) -> bool:
        """Rise the text and return ``False`` once its time is up."""
        self.age += dt
        self.y -= 42.0 * dt
        return self.age < self.lifetime

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Render with a fade driven by remaining life."""
        fraction = max(0.0, 1.0 - self.age / self.lifetime)
        rendered = font.render(self.text, True, self.color)
        rendered.set_alpha(int(255 * fraction))
        surface.blit(rendered, (int(self.x), int(self.y)))


class FloatingTextManager:
    """Keeps a small list of active floating texts alive and drawn."""

    def __init__(self, font: pygame.font.Font) -> None:
        """Create a manager rendering with the given font."""
        self.font = font
        self.items: list[FloatingText] = []

    def spawn(
        self, text: str, position: tuple[float, float], color: tuple[int, int, int], lifetime: float = 1.2
    ) -> None:
        """Add a new floating text."""
        self.items.append(FloatingText(text, position, color, lifetime))

    def update(self, dt: float) -> None:
        """Advance and retire floating texts."""
        self.items = [item for item in self.items if item.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        """Draw every active floating text."""
        for item in self.items:
            item.draw(surface, self.font)

    def clear(self) -> None:
        """Remove all floating texts (state changes)."""
        self.items.clear()


# ---------------------------------------------------------------------------
# Rules help table
# ---------------------------------------------------------------------------


def draw_rules_help(surface: pygame.Surface, fonts: dict[str, Any]) -> None:
    """Render the full six-element relationship table onto a clean surface.

    One row per element: icon, name, what it beats (with the thematic
    reasons), what it loses to and its tie partner (with the tie's reason).
    Layout assumes the configured window size.
    """
    title_rect = draw_text(
        surface, "The Cycle of Elements", fonts["h1"], config.TEXT, center=(config.WINDOW_WIDTH / 2, 52)
    )
    draw_text(
        surface,
        "Every element beats two, loses to two and ties with one.",
        fonts["body"],
        config.TEXT_DIM,
        center=(config.WINDOW_WIDTH / 2, title_rect.bottom + 24),
    )

    row_height, row_width = 88, 1140
    x0 = (config.WINDOW_WIDTH - row_width) // 2
    y0 = title_rect.bottom + 56
    for index, element in enumerate(config.ELEMENTS):
        row_y = y0 + index * row_height
        color = config.ELEMENT_COLORS[element]
        card = pygame.Rect(x0, row_y, row_width, row_height - 8)
        draw_panel(surface, card, config.PANEL)

        icon_center = (x0 + 36, row_y + (row_height - 8) / 2)
        draw_text(surface, ELEMENT_GLYPHS[element], fonts["h1"], color, center=icon_center)
        draw_text(surface, element.capitalize(), fonts["h2"], config.TEXT, topleft=(x0 + 76, row_y + 12))

        beats = BEATS[element]
        loses = [other for other in config.ELEMENTS if other != element and element in BEATS[other]]
        reasons = f"{JUSTIFICATIONS[(element, beats[0])]} {JUSTIFICATIONS[(element, beats[1])]}"
        draw_text(
            surface,
            f"Beats {beats[0].capitalize()} & {beats[1].capitalize()}  -  {reasons}",
            fonts["small"],
            config.TEXT_DIM,
            topleft=(x0 + 260, row_y + 10),
        )
        lose_text = ", ".join(loses)
        tie = TIES[element]
        tie_reason = TIE_JUSTIFICATIONS[frozenset((element, tie))]
        draw_text(
            surface,
            f"Loses to {lose_text.capitalize()}  -  Ties {tie.capitalize()}: {tie_reason}",
            fonts["small"],
            config.TEXT_DIM,
            topleft=(x0 + 260, row_y + 38),
        )
