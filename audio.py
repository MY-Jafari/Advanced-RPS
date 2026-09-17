"""Procedural sound effects for Elemental RPS.

Every effect is synthesized at startup with plain numpy math (sine sweeps,
noise, envelopes) and converted to pygame ``Sound`` objects in memory, so
the game ships with no audio files yet still has feedback for clicks,
countdown ticks, throws, clashes, wins, losses, ties and pickups.

The module degrades gracefully: if audio hardware or numpy is unavailable,
``create_sounds`` returns an empty hook and the game simply runs silent
(see ``main.py``).
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
import pygame

import config


class AudioHook(Protocol):
    """Anything that exposes ``play(name)`` (the real mixer hook, or a stub)."""

    def play(self, name: str) -> None: ...


def _envelope(samples: np.ndarray, attack: float = 0.005) -> np.ndarray:
    """Apply a fast attack and exponential decay to a waveform."""
    count = len(samples)
    envelope = np.exp(-np.linspace(0.0, 6.0, count))
    attack_count = max(1, int(attack * config.AUDIO_SAMPLE_RATE))
    envelope[:attack_count] *= np.linspace(0.0, 1.0, attack_count)
    return samples * envelope


def _sine_sweep(start_freq: float, end_freq: float, duration: float) -> np.ndarray:
    """Render a sine wave whose frequency glides from start to end."""
    times = np.linspace(0.0, duration, int(config.AUDIO_SAMPLE_RATE * duration), endpoint=False)
    frequencies = np.linspace(start_freq, end_freq, len(times))
    phases = 2.0 * np.pi * np.cumsum(frequencies) / config.AUDIO_SAMPLE_RATE
    return _envelope(np.sin(phases))


def _noise_burst(duration: float, lowpass: float = 0.5) -> np.ndarray:
    """Render decaying white noise smoothed by a one-pole low-pass filter.

    A plain recursion loop is used (a closed form overflows to NaN here);
    the run is a few thousand iterations once at startup, so it is fast.
    """
    count = int(config.AUDIO_SAMPLE_RATE * duration)
    rng = np.random.default_rng(7)
    noise = rng.uniform(-1.0, 1.0, count)
    alpha = min(1.0, lowpass)
    smoothed = np.empty_like(noise)
    accumulator = 0.0
    for index in range(count):
        accumulator += alpha * (noise[index] - accumulator)
        smoothed[index] = accumulator
    return _envelope(smoothed)


def _mix(*layers: np.ndarray) -> np.ndarray:
    """Sum waveforms of different lengths by zero-padding to the longest."""
    total = max(len(layer) for layer in layers)
    mixed = np.zeros(total)
    for layer in layers:
        mixed[: len(layer)] += layer
    return mixed


def _to_sound(samples: np.ndarray, volume: float = 1.0) -> pygame.mixer.Sound:
    """Convert float samples in ``[-1, 1]`` to a mono pygame Sound."""
    scaled = np.clip(samples * volume * config.AUDIO_MASTER_VOLUME, -1.0, 1.0)
    array = (scaled * 32767.0).astype(np.int16)
    channels = 1 if pygame.mixer.get_init()[2] == 1 else 2
    if channels == 2:
        array = np.column_stack((array, array))  # duplicate onto both channels
    return pygame.mixer.Sound(array=array)


class MixerAudio:
    """Audio hook playing named effects through the pygame mixer."""

    def __init__(self, sounds: dict[str, pygame.mixer.Sound]) -> None:
        """Wrap a name -> Sound table built by ``create_sounds``."""
        self.sounds = sounds
        self.muted = False

    def play(self, name: str) -> None:
        """Play one named effect; unknown names and mute are no-ops."""
        if self.muted:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def toggle_mute(self) -> bool:
        """Flip mute state and return the new value."""
        self.muted = not self.muted
        return self.muted


class SilentAudio:
    """Stand-in hook used when audio is unavailable; every call is a no-op."""

    def __init__(self) -> None:
        """Start unmuted so toggling keeps consistent semantics."""
        self.muted = False

    def play(self, name: str) -> None:
        """No-op."""

    def toggle_mute(self) -> bool:
        """Flip the flag for UI consistency; there is nothing to silence."""
        self.muted = not self.muted
        return self.muted


def create_sounds() -> dict[str, pygame.mixer.Sound]:
    """Synthesize every named effect the game plays.

    Requires ``pygame.mixer.init()`` (with pre_init from ``main.py``) and
    numpy; callers should fall back to ``SilentAudio`` on any exception.
    """
    return {
        # UI: a short, soft blip.
        "click": _to_sound(_sine_sweep(880.0, 660.0, 0.08), 0.5),
        # Countdown ticks rise in pitch; "go" resolves upward.
        "tick": _to_sound(_sine_sweep(600.0, 620.0, 0.09), 0.45),
        "go": _to_sound(_sine_sweep(520.0, 1040.0, 0.22), 0.55),
        # Choices flying out.
        "throw": _to_sound(_sine_sweep(300.0, 900.0, 0.16), 0.45),
        # The mid-air collision: filtered noise plus a low thump.
        "clash": _to_sound(_mix(_noise_burst(0.28, 0.35), 0.6 * _sine_sweep(180.0, 60.0, 0.28)), 0.8),
        # Verdicts.
        "win": _to_sound(_mix(_sine_sweep(660.0, 1320.0, 0.3), 0.4 * _sine_sweep(990.0, 1980.0, 0.3)), 0.6),
        "lose": _to_sound(_sine_sweep(440.0, 180.0, 0.42), 0.6),
        "tie": _to_sound(_sine_sweep(500.0, 500.0, 0.18), 0.4),
        # Power-up claim: a quick two-step chime.
        "powerup": _to_sound(_mix(_sine_sweep(700.0, 1400.0, 0.12), 0.5 * _sine_sweep(1050.0, 2100.0, 0.18)), 0.55),
    }


def build_audio_hook() -> AudioHook:
    """Try to build the real mixer hook; fall back to silence gracefully."""
    try:
        pygame.mixer.pre_init(config.AUDIO_SAMPLE_RATE, size=-16, channels=1, buffer=512)
        pygame.mixer.init()
        return MixerAudio(create_sounds())
    except (pygame.error, ImportError, OSError, ValueError):
        return SilentAudio()
