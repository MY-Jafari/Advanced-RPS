"""Elemental RPS — a six-element rock-paper-scissors duel against an adaptive AI.

Run with::

    python main.py

This module owns pygame initialization, the fixed-timestep-friendly main
loop, global mute handling and clean shutdown. Everything else lives in the
dedicated modules (config, game_logic, ai_opponent, power_ups,
particle_system, ui, states, audio).
"""

from __future__ import annotations

import pygame

import config
from audio import build_audio_hook
from states import Game


def main() -> None:
    """Initialize pygame, run the main loop and shut down cleanly."""
    pygame.init()
    pygame.display.set_caption(config.WINDOW_TITLE)
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    audio = build_audio_hook()
    game = Game(audio=audio)
    running = True
    while running:
        # dt in seconds, clamped so pauses/resize stalls cannot teleport animations.
        dt = min(clock.tick(config.FPS) / 1000.0, 0.1)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                muted = audio.toggle_mute()
                game.floating.spawn(
                    "SOUND OFF" if muted else "SOUND ON", (config.WINDOW_WIDTH / 2 - 60, 12), config.TEXT_DIM
                )
            else:
                game.handle_event(event)
        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
