"""Core rules and state for Elemental RPS.

Single source of truth for the six-element rules table, round resolution,
damage, energy and combo handling. The module deliberately imports nothing
but ``config`` (and the standard library) so the entire rule set can be
unit-tested headlessly without pygame or a display.

The rules table is stored as an explicit, hand-written dictionary — never
derived from rotational formulas — exactly matching the design document.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import config

# A game element, identified by its canonical lowercase name in config.ELEMENTS.
Element = str
# Round outcome from the player's perspective.
Outcome = Literal["win", "lose", "tie"]
# Who won a finished match.
MatchWinner = Literal["player", "ai", "draw"]

# ---------------------------------------------------------------------------
# Rules table — explicit and hand-written, mirroring the design document.
# ---------------------------------------------------------------------------

# Each element beats exactly the two elements listed here.
BEATS: dict[Element, tuple[Element, Element]] = {
    "rock": ("scissors", "earth"),
    "paper": ("rock", "water"),
    "scissors": ("paper", "earth"),
    "fire": ("paper", "scissors"),
    "water": ("rock", "fire"),
    "earth": ("fire", "water"),
}

# Each element ties with exactly one other element.
TIES: dict[Element, Element] = {
    "rock": "fire",
    "paper": "earth",
    "scissors": "water",
    "fire": "rock",
    "water": "scissors",
    "earth": "paper",
}

# Short thematic explanation for every winning pair, shown on the help
# screen. Keys are (winner, loser) pairs.
JUSTIFICATIONS: dict[tuple[Element, Element], str] = {
    ("rock", "scissors"): "Rock dulls the scissors' blades.",
    ("rock", "earth"): "Solid rock crushes loose earth.",
    ("paper", "rock"): "Paper wraps around and covers rock.",
    ("paper", "water"): "Paper soaks up and holds water.",
    ("scissors", "paper"): "Scissors slice straight through paper.",
    ("scissors", "earth"): "Scissors carve furrows into soft earth.",
    ("fire", "paper"): "Fire burns paper to ash.",
    ("fire", "scissors"): "Fire softens the scissors' steel.",
    ("water", "rock"): "Water erodes rock, grain by grain.",
    ("water", "fire"): "Water quenches fire in a burst of steam.",
    ("earth", "fire"): "Earth smothers fire's air supply.",
    ("earth", "water"): "Earth dams and absorbs the water.",
}


def _build_outcomes(
    beats: dict[Element, tuple[Element, Element]], ties: dict[Element, Element]
) -> dict[tuple[Element, Element], Outcome]:
    """Materialize the explicit tables into a fast lookup matrix.

    ``OUTCOMES[(a, b)]`` is ``"win"`` when ``a`` beats ``b``, ``"lose"`` when
    ``a`` loses to ``b`` and ``"tie"`` when the two draw. Same-element pairs
    are not stored; ``resolve_round`` treats them as a tie directly.
    """
    outcomes: dict[tuple[Element, Element], Outcome] = {}
    for attacker, beaten in beats.items():
        for defender in beaten:
            outcomes[(attacker, defender)] = "win"
            outcomes[(defender, attacker)] = "lose"
    for a, b in ties.items():
        outcomes[(a, b)] = "tie"
        outcomes[(b, a)] = "tie"
    return outcomes


OUTCOMES: dict[tuple[Element, Element], Outcome] = _build_outcomes(BEATS, TIES)


def validate_rules(
    beats: dict[Element, tuple[Element, Element]] | None = None,
    ties: dict[Element, Element] | None = None,
) -> None:
    """Sanity-check a rules table for completeness and consistency.

    Verifies that every element beats exactly two others, loses to exactly
    two, ties with exactly one, and that the win/lose relations are mutually
    consistent. Raises ``ValueError`` with a human-readable message on the
    first inconsistency found.

    Args:
        beats: Win table to check; defaults to the module table.
        ties: Tie table to check; defaults to the module table.
    """
    beats = BEATS if beats is None else beats
    ties = TIES if ties is None else ties

    unknown = (set(beats) | set(ties)) - set(config.ELEMENTS)
    if unknown:
        raise ValueError(f"unknown elements in rules table: {sorted(unknown)}")

    outcomes = _build_outcomes(beats, ties)
    for element in config.ELEMENTS:
        wins = sum(1 for other in config.ELEMENTS if other != element and outcomes.get((element, other)) == "win")
        losses = sum(1 for other in config.ELEMENTS if other != element and outcomes.get((element, other)) == "lose")
        draw_pairs = sum(1 for other in config.ELEMENTS if other != element and outcomes.get((element, other)) == "tie")
        if wins != 2 or losses != 2 or draw_pairs != 1:
            raise ValueError(f"{element}: expected 2 wins / 2 losses / 1 tie, got {wins}/{losses}/{draw_pairs}")
        if ties.get(element, element) == element or ties.get(ties[element]) != element:
            raise ValueError(f"{element}: tie relation must be mutual")
        for beaten in beats[element]:
            if outcomes[(beaten, element)] != "lose":
                raise ValueError(f"{element} beats {beaten} but the reverse entry disagrees")


def resolve_round(player_choice: Element, ai_choice: Element) -> Outcome:
    """Resolve one round and return the outcome from the player's perspective.

    Args:
        player_choice: The player's element.
        ai_choice: The opponent's element.

    Returns:
        ``"win"`` if the player's choice beats the AI's, ``"lose"`` if it is
        beaten, and ``"tie"`` for equal choices or a declared tie pair.

    Example:
        >>> resolve_round("water", "fire")
        'win'
        >>> resolve_round("rock", "paper")
        'lose'
        >>> resolve_round("scissors", "water")
        'tie'
    """
    if player_choice == ai_choice:
        return "tie"
    outcome = OUTCOMES.get((player_choice, ai_choice))
    if outcome is None:  # Defensive: unknown pair means the table is broken.
        raise ValueError(f"no rule for pair ({player_choice!r}, {ai_choice!r})")
    return outcome


def choice_cost(choice: Element) -> int:
    """Energy cost of a choice: classics are cheap, elementals expensive."""
    return config.COST_CLASSIC if choice in config.CLASSIC_ELEMENTS else config.COST_ELEMENTAL


def base_damage(winner_choice: Element) -> int:
    """Base HP damage dealt by the winner's choice type.

    Losing to an elemental hurts more than losing to a classic choice.
    """
    if winner_choice in config.ELEMENTAL_ELEMENTS:
        return config.DAMAGE_FROM_ELEMENTAL
    return config.DAMAGE_FROM_CLASSIC


def scaled_damage(base: int, bonus_percent: int) -> int:
    """Apply a percentage damage bonus with deterministic integer math.

    Integer flooring is used instead of float rounding so damage values are
    stable and easy to reason about (and to test).
    """
    return base * (100 + bonus_percent) // 100


def affordable_choices(player: Player) -> tuple[Element, ...]:
    """Elements the given player can currently pay for (UI greys out the rest)."""
    return tuple(element for element in config.ELEMENTS if player.can_afford(element))


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


class Player:
    """One side of a match: HP, energy, combo streak and shield charges.

    Attributes:
        name: Display name shown in the UI.
        max_hp: Maximum (and starting) HP.
        hp: Current HP; the match ends for a side when it reaches zero.
        energy: Current energy, spent on choices and regenerated each round.
        combo: Current streak of consecutive round wins.
        shields: One-shot loss cancellations granted by power-ups.
    """

    def __init__(
        self,
        name: str,
        max_hp: int = config.MAX_HP,
        energy: int = config.STARTING_ENERGY,
    ) -> None:
        """Initialize a player with full HP and the starting energy pool."""
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.energy = energy
        self.combo = 0
        self.shields = 0

    def can_afford(self, choice: Element) -> bool:
        """Return whether this player has enough energy for the choice."""
        return self.energy >= choice_cost(choice)

    def spend_energy(self, choice: Element) -> None:
        """Pay a choice's energy cost; the caller must check ``can_afford`` first."""
        self.energy = max(0, self.energy - choice_cost(choice))

    def regenerate_energy(self) -> None:
        """Restore the per-round energy amount, capped at the maximum."""
        self.energy = min(config.MAX_ENERGY, self.energy + config.ENERGY_REGEN_PER_ROUND)

    def combo_bonus_percent(self) -> int:
        """Damage bonus (in percent) the *next* consecutive win would deal."""
        return min(self.combo * config.COMBO_STEP_BONUS_PERCENT, config.COMBO_MAX_BONUS_PERCENT)

    def take_damage(self, amount: int) -> None:
        """Reduce HP by ``amount``, clamped at zero."""
        self.hp = max(0, self.hp - max(0, amount))

    def gain_shield(self) -> None:
        """Add one one-shot shield charge (cancels the damage of one loss)."""
        self.shields += 1

    def use_shield(self) -> bool:
        """Consume one shield charge if available; return whether one was used."""
        if self.shields > 0:
            self.shields -= 1
            return True
        return False

    def is_defeated(self) -> bool:
        """Return whether this player is out of HP."""
        return self.hp <= 0

    def reset(self) -> None:
        """Restore starting HP/energy and clear combo and shields."""
        self.hp = self.max_hp
        self.energy = config.STARTING_ENERGY
        self.combo = 0
        self.shields = 0


# ---------------------------------------------------------------------------
# Match orchestration
# ---------------------------------------------------------------------------


@dataclass
class RoundResult:
    """Everything the UI needs to present one resolved round.

    Attributes:
        round_number: 1-based index of the resolved round.
        player_choice: The player's element.
        ai_choice: The opponent's element.
        outcome: Round outcome from the player's perspective.
        player_damage_dealt: HP actually removed from the AI this round.
        ai_damage_dealt: HP actually removed from the player this round.
        player_energy_spent: Energy the player paid for their choice.
        ai_energy_spent: Energy the AI paid for its choice.
        player_combo: The player's consecutive-win streak after the round.
        ai_combo: The AI's consecutive-win streak after the round.
        player_shield_used: Whether the player's shield cancelled their loss.
        ai_shield_used: Whether the AI's shield cancelled its loss.
    """

    round_number: int
    player_choice: Element
    ai_choice: Element
    outcome: Outcome
    player_damage_dealt: int
    ai_damage_dealt: int
    player_energy_spent: int
    ai_energy_spent: int
    player_combo: int
    ai_combo: int
    player_shield_used: bool
    ai_shield_used: bool


class Match:
    """A best-of-N match between a human player and the AI.

    Owns both ``Player`` objects, tracks round progress and applies the full
    round pipeline: energy spending, outcome resolution, combo-scaled damage
    and shield interception. Ending conditions: either side's HP reaches zero,
    or ``best_of`` rounds have been played (higher HP then wins; equal HP is
    a draw).
    """

    def __init__(self, best_of: int = config.DEFAULT_BEST_OF) -> None:
        """Create a match; ``best_of`` must be one of ``config.BEST_OF_OPTIONS``."""
        if best_of not in config.BEST_OF_OPTIONS:
            raise ValueError(f"best_of must be one of {config.BEST_OF_OPTIONS}, got {best_of}")
        self.best_of = best_of
        self.round_number = 1  # 1-based number of the round being played
        self.rounds_played = 0
        self.player = Player("Player")
        self.opponent = Player("AI")
        self._regenerated_through = 0  # rounds_played count already regenerated for

    def start_round(self) -> None:
        """Prepare the current round, regenerating energy exactly once.

        Round 1 keeps its fixed starting energy; every later round restores
        ``config.ENERGY_REGEN_PER_ROUND`` to both sides first.
        """
        while self._regenerated_through < self.rounds_played:
            self.player.regenerate_energy()
            self.opponent.regenerate_energy()
            self._regenerated_through += 1

    def play_round(self, player_choice: Element, ai_choice: Element) -> RoundResult:
        """Play one round end-to-end and return its full result.

        Args:
            player_choice: The player's element; must be affordable.
            ai_choice: The AI's element; must be affordable.

        Returns:
            A ``RoundResult`` describing damage, energy and combo state.

        Raises:
            ValueError: If either choice is unaffordable (the UI disables
                unaffordable buttons and the AI only picks affordable moves,
                so this indicates a caller bug).
        """
        if not self.player.can_afford(player_choice):
            raise ValueError(f"player cannot afford {player_choice!r}")
        if not self.opponent.can_afford(ai_choice):
            raise ValueError(f"AI cannot afford {ai_choice!r}")

        self.player.spend_energy(player_choice)
        self.opponent.spend_energy(ai_choice)
        outcome = resolve_round(player_choice, ai_choice)

        player_dealt = 0
        ai_dealt = 0
        player_shield_used = False
        ai_shield_used = False

        if outcome == "win":
            # Combo bonus is based on the streak *before* this win: the first
            # consecutive win deals base damage, the second +10%, and so on.
            bonus = self.player.combo_bonus_percent()
            self.player.combo += 1
            self.opponent.combo = 0
            player_dealt = scaled_damage(base_damage(player_choice), bonus)
            if self.opponent.use_shield():
                ai_shield_used = True
                player_dealt = 0
            else:
                self.opponent.take_damage(player_dealt)
        elif outcome == "lose":
            bonus = self.opponent.combo_bonus_percent()
            self.opponent.combo += 1
            self.player.combo = 0
            ai_dealt = scaled_damage(base_damage(ai_choice), bonus)
            if self.player.use_shield():
                player_shield_used = True
                ai_dealt = 0
            else:
                self.player.take_damage(ai_dealt)
        else:  # tie: no damage, both streaks break
            self.player.combo = 0
            self.opponent.combo = 0
            player_dealt = ai_dealt = config.DRAW_DAMAGE
            self.player.take_damage(player_dealt)
            self.opponent.take_damage(ai_dealt)

        result = RoundResult(
            round_number=self.round_number,
            player_choice=player_choice,
            ai_choice=ai_choice,
            outcome=outcome,
            player_damage_dealt=player_dealt,
            ai_damage_dealt=ai_dealt,
            player_energy_spent=choice_cost(player_choice),
            ai_energy_spent=choice_cost(ai_choice),
            player_combo=self.player.combo,
            ai_combo=self.opponent.combo,
            player_shield_used=player_shield_used,
            ai_shield_used=ai_shield_used,
        )
        self.rounds_played += 1
        self.round_number += 1
        return result

    def is_over(self) -> bool:
        """Return whether the match has ended (knockout or rounds exhausted)."""
        return self.player.is_defeated() or self.opponent.is_defeated() or self.rounds_played >= self.best_of

    def winner(self) -> MatchWinner | None:
        """Return the match winner, or ``None`` while the match is running.

        On a rounds-exhausted finish the higher HP wins; equal HP is a draw.
        """
        if not self.is_over():
            return None
        if self.opponent.is_defeated() and not self.player.is_defeated():
            return "player"
        if self.player.is_defeated() and not self.opponent.is_defeated():
            return "ai"
        if self.player.hp > self.opponent.hp:
            return "player"
        if self.opponent.hp > self.player.hp:
            return "ai"
        return "draw"
