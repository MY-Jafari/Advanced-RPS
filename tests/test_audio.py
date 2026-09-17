"""Tests for the procedural audio module (skipped without an audio device)."""

import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import config
from audio import MixerAudio, SilentAudio, _noise_burst, _sine_sweep

pytest.importorskip("numpy")

try:
    pygame.mixer.init(config.AUDIO_SAMPLE_RATE, size=-16, channels=1, buffer=512)
    MIXER_AVAILABLE = True
except pygame.error:  # no audio backend on this machine
    MIXER_AVAILABLE = False

if MIXER_AVAILABLE:
    from audio import create_sounds


@pytest.fixture(scope="module")
def sounds():
    return create_sounds()


@pytest.mark.skipif(not MIXER_AVAILABLE, reason="pygame mixer unavailable")
def test_all_named_effects_exist(sounds):
    expected = {"click", "tick", "go", "throw", "clash", "win", "lose", "tie", "powerup"}
    assert expected == set(sounds)


@pytest.mark.skipif(not MIXER_AVAILABLE, reason="pygame mixer unavailable")
def test_sounds_have_positive_length(sounds):
    for name, sound in sounds.items():
        assert sound.get_length() > 0.01, name


@pytest.mark.skipif(not MIXER_AVAILABLE, reason="pygame mixer unavailable")
def test_play_unknown_name_is_noop(sounds):
    hook = MixerAudio(sounds)
    hook.play("does_not_exist")  # must not raise


@pytest.mark.skipif(not MIXER_AVAILABLE, reason="pygame mixer unavailable")
def test_mute_blocks_and_unblocks(sounds):
    hook = MixerAudio(sounds)
    assert hook.toggle_mute() is True
    hook.play("click")  # silently dropped
    assert hook.toggle_mute() is False


def test_silent_hook_mirrors_interface():
    hook = SilentAudio()
    hook.play("anything")
    assert hook.toggle_mute() is True
    assert hook.toggle_mute() is False


def test_sine_sweep_shape_and_bounds():
    samples = _sine_sweep(440.0, 880.0, 0.05)
    assert len(samples) == int(config.AUDIO_SAMPLE_RATE * 0.05)
    assert float(samples.max()) <= 1.0
    assert float(samples.min()) >= -1.0


def test_noise_burst_bounds():
    samples = _noise_burst(0.05, lowpass=0.4)
    assert len(samples) == int(config.AUDIO_SAMPLE_RATE * 0.05)
    assert float(abs(samples).max()) <= 1.0
