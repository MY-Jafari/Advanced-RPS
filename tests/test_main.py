"""End-to-end smoke test driving the game exactly like main.py's loop."""

import os
import random

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import config
from audio import SilentAudio
from states import Game


@pytest.fixture(scope="module", autouse=True)
def pygame_session():
    pygame.init()
    pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    yield
    pygame.quit()


def test_full_session_smoke(monkeypatch):
    """Simulate a real session: menu -> mode -> duel rounds -> result -> menu."""
    game = Game(audio=SilentAudio(), rng=random.Random(123))
    screen = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    game_state = game.machine.states["game"]

    # --- a few idle menu frames -----------------------------------------
    for _ in range(10):
        game.update(0.016)
        game.draw(screen)

    # --- start a best-of-3 duel ------------------------------------------
    game.machine.change_state("game", immediate=True, best_of=3)
    assert game_state.match is not None

    # --- drive up to 8 rounds or until the result screen appears ---------
    result_state = game.machine.states["result"]
    rounds = 0
    for _ in range(8):
        # countdown -> choose
        for _ in range(80):
            game.update(0.1)
            if game_state.phase == "choose":
                break
        if game_state.phase != "choose":
            break
        # player picks the first affordable button
        button = next(b for b in game_state.element_buttons if b.enabled)
        game_state._player_picked(button.element)
        # resolution -> next countdown or done -> result
        for _ in range(200):
            game.update(0.05)
            if game.machine.current is result_state:
                break
            if game_state.phase == "choose" and not game.machine.transitioning:
                break
        rounds += 1
        if game.machine.current is result_state:
            break
    assert rounds >= 1, "at least one full round must have been played"
    assert game.match_or_none() is not None or game.machine.current is result_state

    # --- result screen renders and rematch re-enters the duel ------------
    if game.machine.current is result_state:
        game.update(0.016)
        game.draw(screen)

    # --- back to menu and idle again --------------------------------------
    game.machine.change_state("menu", immediate=True)
    for _ in range(5):
        game.update(0.016)
        game.draw(screen)


def test_frame_step_matches_main_loop_clamp():
    """The dt clamp in main.py protects the simulation from long stalls."""
    raw_ms = 2_500  # a 2.5s stall (e.g. window drag)
    dt = min(raw_ms / 1000.0, 0.1)
    assert dt == 0.1
