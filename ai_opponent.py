"""Adaptive AI opponent for Elemental RPS.

The opponent combines two pattern detectors over the player's recent
choices — a frequency table and an order-N Markov chain — and plays a
counter to its prediction with a fixed probability, spending the rest of
its decisions on randomness so it cannot be gamed. All detectors are
recomputed from a sliding window of the player's last
``config.AI_HISTORY_WINDOW`` choices, so the AI adapts when the player
changes strategy instead of clinging to stale habits.

The module only depends on ``config`` and ``game_logic`` so it stays fully
unit-testable without pygame or a display.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict, deque
from collections.abc import Sequence

import config
from game_logic import Element, resolve_round

# Thematic group of a choice, as revealed by the hint power-up.
Category = str  # "classic" or "elemental"


def element_category(choice: Element) -> Category:
    """Return the thematic group of a choice: ``"elemental"`` or ``"classic"``.

    The hint power-up uses this to reveal only the group of the AI's next
    choice, never the exact element.

    Example:
        >>> element_category("fire")
        'elemental'
        >>> element_category("rock")
        'classic'
    """
    return "elemental" if choice in config.ELEMENTAL_ELEMENTS else "classic"


def counter_moves(target: Element) -> tuple[Element, ...]:
    """All elements that beat ``target``, in canonical order.

    Example:
        >>> counter_moves("rock")
        ('paper', 'water')
    """
    return tuple(element for element in config.ELEMENTS if resolve_round(element, target) == "win")


class AIOpponent:
    """Adaptive opponent mixing frequency counting, Markov chains and noise.

    Decision policy for each round:

    1. Predict the player's next choice: try the highest configured Markov
       order first, fall back to shorter contexts, then to the raw frequency
       table (see ``predict_next``).
    2. With probability ``config.AI_PREDICT_PROBABILITY`` play a counter to
       that prediction (any element that beats it).
    3. Otherwise — or whenever no prediction or no affordable counter
       exists — pick uniformly at random among the affordable choices.

    The RNG is injectable so tests can be fully deterministic.

    Attributes:
        history: The sliding window of observed player choices, oldest first.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        """Create an opponent; ``rng`` defaults to a fresh seeded-from-OS generator."""
        self._rng = rng if rng is not None else random.Random()
        if config.AI_MARKOV_ORDER < 1:
            raise ValueError("config.AI_MARKOV_ORDER must be at least 1")
        self.reset()

    def reset(self) -> None:
        """Forget every observation; called when a new match starts."""
        self._history: deque[Element] = deque(maxlen=config.AI_HISTORY_WINDOW)
        self._frequency: Counter[Element] = Counter()
        # Per-order Markov tables: order -> context tuple -> next-choice counts.
        self._transitions: dict[int, dict[tuple[Element, ...], Counter[Element]]] = {
            order: defaultdict(Counter) for order in range(1, config.AI_MARKOV_ORDER + 1)
        }

    # -- Learning -----------------------------------------------------------

    def observe(self, player_choice: Element) -> None:
        """Record one player choice and refresh all pattern detectors.

        Detectors are rebuilt from the sliding window on every observation,
        so only the most recent ``config.AI_HISTORY_WINDOW`` choices ever
        influence predictions.
        """
        self._history.append(player_choice)
        self._rebuild_detectors()

    def _rebuild_detectors(self) -> None:
        """Recompute the frequency table and Markov tables from the window."""
        items = tuple(self._history)
        self._frequency = Counter(items)
        for order, table in self._transitions.items():
            table.clear()
            for index in range(len(items) - order):
                context = items[index : index + order]
                table[context][items[index + order]] += 1

    @property
    def history(self) -> tuple[Element, ...]:
        """Copy of the analysed player history, oldest first."""
        return tuple(self._history)

    # -- Prediction ---------------------------------------------------------

    def predict_next(self) -> Element | None:
        """Best guess of the player's next choice, or ``None`` without data.

        Tries the highest Markov order first (longest context = most
        specific pattern) and falls back to shorter contexts, then to the
        overall frequency table. ``Counter.most_common`` is stable for ties,
        which keeps predictions deterministic for a given history.

        Example:
            >>> ai = AIOpponent(random.Random(0))
            >>> for choice in ("rock", "rock", "rock"):
            ...     ai.observe(choice)
            >>> ai.predict_next()
            'rock'
        """
        items = tuple(self._history)
        for order in range(config.AI_MARKOV_ORDER, 0, -1):
            if len(items) >= order:
                counter = self._transitions[order].get(items[-order:])
                if counter:
                    return counter.most_common(1)[0][0]
        if self._frequency:
            return self._frequency.most_common(1)[0][0]
        return None

    # -- Decision -----------------------------------------------------------

    def choose(self, affordable: Sequence[Element]) -> Element:
        """Pick the AI's move for the current round.

        Args:
            affordable: Choices the AI's energy can pay for. May be any
                subset of ``config.ELEMENTS`` in any order; duplicates are
                ignored.

        Returns:
            One of the affordable elements: a counter to the predicted
            player choice with ``config.AI_PREDICT_PROBABILITY`` likelihood,
            a random affordable element otherwise.

        Raises:
            ValueError: If ``affordable`` is empty or contains unknown
                elements.
        """
        options = tuple(dict.fromkeys(affordable))  # dedupe, preserve order
        unknown = [choice for choice in options if choice not in config.ELEMENTS]
        if unknown:
            raise ValueError(f"unknown choices: {unknown}")
        if not options:
            raise ValueError("the AI has no affordable choices")

        prediction = self.predict_next()
        if prediction is not None and self._rng.random() < config.AI_PREDICT_PROBABILITY:
            counters = [choice for choice in counter_moves(prediction) if choice in options]
            if counters:
                return self._rng.choice(counters)
        return self._rng.choice(options)
