"""Unit tests for the adaptive AI opponent."""

import random

import config
from ai_opponent import AIOpponent, counter_moves, element_category
from game_logic import resolve_round


class ScriptedRng:
    """Deterministic RNG stand-in: ``random()`` forces the prediction branch."""

    def __init__(self, choice_index: int = 0, random_value: float = 0.0) -> None:
        self.choice_index = choice_index
        self.random_value = random_value

    def random(self) -> float:
        return self.random_value

    def choice(self, sequence):
        return sequence[self.choice_index % len(sequence)]


def feed(ai: AIOpponent, choices) -> None:
    """Convenience helper to record a sequence of player choices."""
    for choice in choices:
        ai.observe(choice)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def test_element_category_splits_groups():
    assert element_category("fire") == "elemental"
    assert element_category("earth") == "elemental"
    assert element_category("water") == "elemental"
    assert element_category("rock") == "classic"
    assert element_category("paper") == "classic"
    assert element_category("scissors") == "classic"


def test_counter_moves_match_rules_table():
    assert counter_moves("rock") == ("paper", "water")
    assert counter_moves("fire") == ("water", "earth")
    assert counter_moves("scissors") == ("rock", "fire")
    for target in config.ELEMENTS:
        for counter in counter_moves(target):
            assert resolve_round(counter, target) == "win"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_empty_affordable_raises():
    ai = AIOpponent(random.Random(0))
    try:
        ai.choose([])
    except ValueError:
        pass
    else:
        raise AssertionError("empty affordable list must raise ValueError")


def test_unknown_choice_rejected():
    ai = AIOpponent(random.Random(0))
    try:
        ai.choose(["dragon"])
    except ValueError:
        pass
    else:
        raise AssertionError("unknown element must raise ValueError")


# ---------------------------------------------------------------------------
# Prediction: frequency, Markov and the sliding window
# ---------------------------------------------------------------------------


def test_predict_next_is_none_without_data():
    ai = AIOpponent(random.Random(0))
    assert ai.predict_next() is None


def test_frequency_prediction():
    ai = AIOpponent(random.Random(0))
    feed(ai, ["rock", "rock", "rock"])
    assert ai.predict_next() == "rock"


def test_markov_overrides_global_frequency():
    """A specific recent pattern beats the globally most frequent element."""
    ai = AIOpponent(random.Random(0))
    feed(ai, ["rock"] * 8)  # global frequency favourite
    feed(ai, ["paper", "fire"] * 4)  # recent repeating pattern
    # The last two choices ("paper", "fire") were always followed by "paper".
    assert ai.predict_next() == "paper"


def test_frequency_fallback_is_deterministic_on_ties():
    ai = AIOpponent(random.Random(0))
    feed(ai, ["rock", "paper"])  # no Markov context exists yet
    # Ties resolve to the first-seen element in the window.
    assert ai.predict_next() == "rock"


def test_history_window_trims_to_config():
    ai = AIOpponent(random.Random(0))
    feed(ai, ["rock"] * 40)
    assert len(ai.history) == config.AI_HISTORY_WINDOW


def test_windowed_learning_forgets_old_patterns():
    """Only the last N choices influence prediction, so strategy shifts register."""
    ai = AIOpponent(random.Random(0))
    feed(ai, ["rock"] * 14)
    feed(ai, ["water"] * 15)  # pushes every rock out of the window
    assert set(ai.history) == {"water"}
    assert ai.predict_next() == "water"


def test_reset_clears_memory():
    ai = AIOpponent(random.Random(0))
    feed(ai, ["rock"] * 20)
    ai.reset()
    assert ai.history == ()
    assert ai.predict_next() is None


# ---------------------------------------------------------------------------
# Decision making
# ---------------------------------------------------------------------------


def test_cold_start_picks_from_affordable():
    ai = AIOpponent(ScriptedRng(choice_index=0))
    assert ai.choose(["water", "fire"]) == "water"


def test_prediction_branch_picks_a_counter():
    """With a forced prediction branch, the AI plays a beater of the prediction."""
    ai = AIOpponent(ScriptedRng(choice_index=0))
    feed(ai, ["scissors"] * 3)  # prediction: scissors
    # Both remaining options are counters here; the first in canonical order is rock.
    assert ai.choose(["rock", "paper"]) == "rock"


def test_prediction_branch_counter_ordering():
    ai = AIOpponent(ScriptedRng(choice_index=1))
    feed(ai, ["rock"] * 3)  # prediction: rock; beaters: paper, water
    assert ai.choose(["paper", "water"]) == "water"


def test_random_branch_skips_counter_picking():
    """A high random() value must fall through to the uniform branch."""
    ai = AIOpponent(ScriptedRng(choice_index=1, random_value=0.99))
    feed(ai, ["scissors"] * 3)  # prediction exists, counter is rock
    assert ai.choose(["rock", "paper"]) == "paper"


def test_falls_back_when_no_counter_is_affordable():
    ai = AIOpponent(ScriptedRng(choice_index=0))
    feed(ai, ["rock"] * 3)  # prediction: rock; beaters: paper, water
    # Neither beater is affordable, so the AI picks randomly among the rest.
    assert ai.choose(["scissors", "fire"]) == "scissors"


def test_choice_always_within_affordable():
    rng = random.Random(7)
    for _ in range(300):
        ai = AIOpponent(rng)
        feed(ai, [rng.choice(config.ELEMENTS) for _ in range(rng.randint(0, 20))])
        allowed = rng.sample(config.ELEMENTS, rng.randint(1, 6))
        assert ai.choose(allowed) in allowed


def test_choice_respects_energy_constrained_subsets():
    """Simulates the game loop: AI only ever picks what its energy allows."""
    rng = random.Random(11)
    ai = AIOpponent(rng)
    for _ in range(200):
        feed(ai, [rng.choice(config.ELEMENTS)])
        # Late-match budgets often exclude expensive elementals.
        assert ai.choose(config.CLASSIC_ELEMENTS) in config.CLASSIC_ELEMENTS
