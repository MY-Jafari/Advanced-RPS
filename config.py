"""Central configuration for Elemental RPS.

Every tunable value in the game lives in this module: window size, colors,
balance numbers (HP, energy, damage, combo), AI behaviour, power-up pacing,
animation timing and particle/audio settings. Gameplay code must read values
from here instead of hard-coding numbers, so the whole game can be re-balanced
or re-skinned by editing this file alone.

This module intentionally imports nothing beyond the standard library (not
even pygame) so headless unit tests can use it without a display.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Font candidates tried in order; the UI falls back to pygame's built-in font.
FONT_CANDIDATES = ("arial.ttf", "C:/Windows/Fonts/arial.ttf")

# ---------------------------------------------------------------------------
# Window and main loop
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Elemental RPS"
FPS = 60

# ---------------------------------------------------------------------------
# Match structure
# ---------------------------------------------------------------------------

BEST_OF_OPTIONS = (3, 5, 7)  # Best-of-3 / 5 / 7 selectable before a match
DEFAULT_BEST_OF = 3

# ---------------------------------------------------------------------------
# Elements (canonical order used across the whole game)
# ---------------------------------------------------------------------------

ELEMENTS = ("rock", "paper", "scissors", "fire", "water", "earth")
CLASSIC_ELEMENTS = ("rock", "paper", "scissors")
ELEMENTAL_ELEMENTS = ("fire", "water", "earth")

# ---------------------------------------------------------------------------
# Balance: HP and damage
# ---------------------------------------------------------------------------

MAX_HP = 100
DAMAGE_FROM_CLASSIC = 15  # HP lost when losing a round against a classic choice
DAMAGE_FROM_ELEMENTAL = 22  # HP lost when losing a round against an elemental choice
DRAW_DAMAGE = 0  # HP lost on a tied round

# ---------------------------------------------------------------------------
# Balance: combo multiplier
# ---------------------------------------------------------------------------

COMBO_STEP_BONUS = 0.10  # +10% damage per consecutive win
COMBO_MAX_BONUS = 0.50  # damage bonus cap after many wins in a row

# ---------------------------------------------------------------------------
# Balance: energy
# ---------------------------------------------------------------------------

MAX_ENERGY = 100
STARTING_ENERGY = 60
ENERGY_REGEN_PER_ROUND = 15
COST_CLASSIC = 10  # energy cost of a classic choice
COST_ELEMENTAL = 22  # energy cost of an elemental choice

# ---------------------------------------------------------------------------
# Adaptive AI
# ---------------------------------------------------------------------------

AI_HISTORY_WINDOW = 15  # how many recent player choices are analysed
AI_PREDICT_PROBABILITY = 0.60  # chance of playing the statistical prediction
AI_MARKOV_ORDER = 2  # primary Markov context length (order-1 is the fallback)

# ---------------------------------------------------------------------------
# Power-ups
# ---------------------------------------------------------------------------

POWERUP_MIN_GAP_ROUNDS = 3  # earliest round a new power-up can spawn
POWERUP_MAX_GAP_ROUNDS = 5  # latest round a new power-up can spawn
POWERUP_LIFETIME_ROUNDS = 3  # rounds an unclaimed power-up stays on screen
POWERUP_RADIUS = 34  # clickable radius in pixels

# ---------------------------------------------------------------------------
# UI palette
# ---------------------------------------------------------------------------

# Base surface colors (dark theme)
BACKGROUND = (16, 18, 24)
BACKGROUND_ALT = (12, 14, 19)
PANEL = (28, 32, 42)
PANEL_LIGHT = (38, 44, 58)

# Text
TEXT = (232, 236, 244)
TEXT_DIM = (150, 158, 172)
TEXT_DISABLED = (96, 102, 112)

# Semantic accents
ACCENT = (90, 160, 255)
SUCCESS = (60, 200, 120)
DANGER = (255, 90, 95)
WARNING = (255, 190, 60)

# Duel sides
PLAYER_COLOR = (90, 160, 255)
AI_COLOR = (255, 105, 110)

# Per-element identity colors (keys match ELEMENTS)
ELEMENT_COLORS = {
    "rock": (150, 150, 158),
    "paper": (235, 238, 242),
    "scissors": (170, 182, 200),
    "fire": (255, 122, 40),
    "water": (64, 150, 255),
    "earth": (172, 124, 74),
}

# How strongly the dominant element of recent rounds tints the background
# (0.0 = off, 1.0 = full element color).
BACKGROUND_TINT_STRENGTH = 0.10

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

FONT_SIZES = {
    "title": 64,
    "h1": 40,
    "h2": 28,
    "body": 22,
    "small": 17,
    "tiny": 14,
}

# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

BUTTON_HEIGHT = 56
BUTTON_PADDING_X = 28
BUTTON_RADIUS = 12

# ---------------------------------------------------------------------------
# Animation timing (all values in seconds unless noted)
# ---------------------------------------------------------------------------

COUNTDOWN_STEPS = 3  # counts 3-2-1-Go
COUNTDOWN_STEP_SECONDS = 0.70
CHOICE_TRAVEL_SECONDS = 0.55  # choices fly from both sides to the center
IMPACT_PAUSE_SECONDS = 0.30  # hold on the clash before revealing the outcome
RESULT_DISPLAY_SECONDS = 1.15  # how long the round verdict stays on screen
TRANSITION_SECONDS = 0.35  # fade/slide between game states
BAR_LERP_SPEED = 12.0  # higher = bars catch up to their target value faster
SHAKE_DURATION_SECONDS = 0.30
SHAKE_MAGNITUDE_PX = 9.0
GLOW_PULSE_SPEED = 6.0  # radians/second of the winner glow pulse

# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------

MAX_PARTICLES = 400
PARTICLE_GRAVITY = 340.0  # px/s^2 applied to most particle kinds

# ---------------------------------------------------------------------------
# Audio (procedural — no sound files required)
# ---------------------------------------------------------------------------

AUDIO_SAMPLE_RATE = 44100
AUDIO_MASTER_VOLUME = 0.5
