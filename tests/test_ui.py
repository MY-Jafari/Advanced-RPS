"""Headless unit tests for the UI widget layer."""

import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import config
from ui import (
    Bar,
    Button,
    Countdown,
    FloatingTextManager,
    build_element_buttons,
    darken,
    draw_rules_help,
    lerp,
    lerp_color,
    load_fonts,
)


@pytest.fixture(scope="module", autouse=True)
def pygame_session():
    """One pygame init for the module; surfaces need it."""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture()
def surface():
    """A fresh headless surface per test."""
    return pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))


@pytest.fixture()
def fonts():
    return load_fonts()


def click_down(position):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": position, "button": 1})


def click_up(position):
    return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": position, "button": 1})


# ---------------------------------------------------------------------------
# Color and interpolation helpers
# ---------------------------------------------------------------------------


def test_lerp_basics():
    assert lerp(0.0, 10.0, 0.5) == 5.0
    assert lerp(0.0, 10.0, 1.5) == 10.0  # clamped
    assert lerp(0.0, 10.0, -1.0) == 0.0  # clamped


def test_lerp_color_channels():
    assert lerp_color((0, 0, 0), (100, 200, 60), 0.5) == (50, 100, 30)


def test_darken_scales_channels():
    assert darken((200, 100, 50), 0.5) == (100, 50, 25)


# ---------------------------------------------------------------------------
# Button interaction contract
# ---------------------------------------------------------------------------


class TestButton:
    def make_button(self):
        return Button(pygame.Rect(100, 100, 120, 40), "Play", pygame.font.Font(None, 24))

    def test_commit_only_on_release_inside(self):
        button = self.make_button()
        assert button.handle_event(click_down((150, 120))) is False
        assert button.handle_event(click_up((150, 120))) is True

    def test_drag_away_cancels(self):
        button = self.make_button()
        button.handle_event(click_down((150, 120)))
        assert button.handle_event(click_up((500, 120))) is False  # released outside

    def test_disabled_ignores_clicks(self):
        button = self.make_button()
        button.enabled = False
        assert button.handle_event(click_down((150, 120))) is False
        assert button.handle_event(click_up((150, 120))) is False

    def test_release_without_press_is_ignored(self):
        button = self.make_button()
        assert button.handle_event(click_up((150, 120))) is False

    def test_hover_and_draw(self, surface):
        button = self.make_button()
        button.update(0.016)  # mouse is elsewhere
        assert button.hovered is False
        button.draw(surface)


# ---------------------------------------------------------------------------
# Element buttons and grid layout
# ---------------------------------------------------------------------------


class TestElementButtons:
    def test_grid_layout(self):
        buttons = build_element_buttons(pygame.font.Font(None, 24), pygame.font.Font(None, 18))
        assert [button.element for button in buttons] == list(config.ELEMENTS)
        for button in buttons:
            assert button.rect.left >= config.WINDOW_WIDTH * 0
            assert button.rect.right <= config.WINDOW_WIDTH
            assert button.rect.bottom <= config.WINDOW_HEIGHT
        # Classics sit above the elemental row.
        classic_bottoms = {button.rect.top for button in buttons[:3]}
        elemental_tops = {button.rect.top for button in buttons[3:]}
        assert max(classic_bottoms) < min(elemental_tops)

    def test_affordable_toggles_enabled(self):
        buttons = build_element_buttons(pygame.font.Font(None, 24), pygame.font.Font(None, 18))
        for button in buttons:
            button.set_affordable(False)
            assert button.enabled is False
            button.set_affordable(True)
            assert button.enabled is True

    def test_draw_states(self, surface, fonts):
        buttons = build_element_buttons(fonts["body"], fonts["small"])
        buttons[0].set_affordable(False)  # disabled path
        buttons[1].pressed = True  # pressed path
        buttons[2].hovered = True  # hover path
        for button in buttons:
            button.draw(surface)


# ---------------------------------------------------------------------------
# Animated bars
# ---------------------------------------------------------------------------


class TestBar:
    def test_bar_chases_target(self):
        bar = Bar(pygame.Rect(0, 0, 200, 20), max_value=100, fill_color=(255, 0, 0))
        bar.set_target(50)
        bar.update(0.1)
        assert 50 < bar.display < 100  # moving toward target
        for _ in range(120):
            bar.update(0.05)
        assert bar.display == pytest.approx(50, abs=0.5)

    def test_bar_clamps_target(self):
        bar = Bar(pygame.Rect(0, 0, 200, 20), max_value=100, fill_color=(255, 0, 0))
        bar.set_target(150)
        assert bar.target == 100
        bar.set_target(-10)
        assert bar.target == 0

    def test_bar_draw(self, surface, fonts):
        bar = Bar(
            pygame.Rect(100, 100, 260, 22),
            max_value=100,
            fill_color=config.PLAYER_COLOR,
            label="HP",
            font=fonts["small"],
        )
        bar.set_target(35)
        for _ in range(60):
            bar.update(0.05)
        bar.draw(surface)


# ---------------------------------------------------------------------------
# Countdown
# ---------------------------------------------------------------------------


class TestCountdown:
    def test_countdown_sequence(self):
        countdown = Countdown(pygame.font.Font(None, 72), (400, 200))
        labels = []
        for _ in range(45):
            countdown.update(config.COUNTDOWN_STEP_SECONDS / 10)
            labels.append(countdown.label())
        assert labels[0] == "3"
        assert "2" in labels and "1" in labels and "GO!" in labels
        assert countdown.finished is True
        assert countdown.label() is None

    def test_restart_resets(self):
        countdown = Countdown(pygame.font.Font(None, 72), (400, 200))
        for _ in range(60):
            countdown.update(config.COUNTDOWN_STEP_SECONDS / 5)
        assert countdown.finished
        countdown.restart()
        assert not countdown.finished
        assert countdown.label() == "3"

    def test_draw_across_steps(self, surface, fonts):
        countdown = Countdown(fonts["h1"], (400, 200))
        for _ in range(30):
            countdown.draw(surface)
            countdown.update(config.COUNTDOWN_STEP_SECONDS / 6)


# ---------------------------------------------------------------------------
# Floating text
# ---------------------------------------------------------------------------


class TestFloatingText:
    def test_spawn_and_expire(self):
        manager = FloatingTextManager(pygame.font.Font(None, 24))
        manager.spawn("+16", (100, 100), config.SUCCESS, lifetime=0.5)
        assert len(manager.items) == 1
        for _ in range(20):
            manager.update(0.05)
        assert len(manager.items) == 0

    def test_clear(self):
        manager = FloatingTextManager(pygame.font.Font(None, 24))
        for i in range(5):
            manager.spawn(f"x{i}", (100, 100 + i * 20), config.TEXT)
        manager.clear()
        assert manager.items == []

    def test_draw(self, surface, fonts):
        manager = FloatingTextManager(fonts["body"])
        manager.spawn("COMBO x2", (300, 300), config.WARNING)
        manager.update(0.1)
        manager.draw(surface)


# ---------------------------------------------------------------------------
# Rules help render
# ---------------------------------------------------------------------------


def test_draw_rules_help_renders(surface, fonts):
    """The full help table draws without errors for all six elements."""
    draw_rules_help(surface, fonts)
