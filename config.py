# Game configuration and constants

WIDTH = 1280
HEIGHT = 720
FPS = 60
TITLE = "Elemental RPS: Arena"

# Elements definition
ELEMENTS = ["rock", "paper", "scissors", "fire", "water", "earth"]

# Rules dictionary: Element -> { "beats": [...], "loses_to": [...], "ties": [...] }
RULES = {
    "rock": {
        "beats": ["scissors", "earth"],
        "loses_to": ["paper", "water"],
        "ties": ["rock"],
        "category": "classic",
        "energy_cost": 10,
        "base_damage": 15,
        "name": "Rock",
        "desc": "Crushes scissors & shatters earth"
    },
    "paper": {
        "beats": ["rock", "water"],
        "loses_to": ["scissors", "fire"],
        "ties": ["paper"],
        "category": "classic",
        "energy_cost": 10,
        "base_damage": 15,
        "name": "Paper",
        "desc": "Covers rock & absorbs water"
    },
    "scissors": {
        "beats": ["paper", "earth"],
        "loses_to": ["rock", "fire"],
        "ties": ["scissors"],
        "category": "classic",
        "energy_cost": 10,
        "base_damage": 15,
        "name": "Scissors",
        "desc": "Cuts paper & pierces earth"
    },
    "fire": {
        "beats": ["paper", "scissors"],
        "loses_to": ["water", "earth"],
        "ties": ["fire"],
        "category": "natural",
        "energy_cost": 22,
        "base_damage": 25,
        "name": "Fire",
        "desc": "Burns paper & melts scissors"
    },
    "water": {
        "beats": ["rock", "fire"],
        "loses_to": ["paper", "earth"],
        "ties": ["water"],
        "category": "natural",
        "energy_cost": 22,
        "base_damage": 25,
        "name": "Water",
        "desc": "Erodes rock & extinguishes fire"
    },
    "earth": {
        "beats": ["fire", "water"],
        "loses_to": ["rock", "scissors"],
        "ties": ["earth"],
        "category": "natural",
        "energy_cost": 22,
        "base_damage": 25,
        "name": "Earth",
        "desc": "Smothers fire & absorbs water"
    }
}

# Gameplay defaults
DEFAULT_HP = 100
MAX_ENERGY = 100
ENERGY_REGEN = 18
AI_PREDICTION_PROB = 0.60
COMBO_MULTIPLIER_STEP = 0.10
POWER_UP_SPAWN_INTERVAL = 3
PERFORMANCE_OPTIMIZED = False
