"""Random power-ups for Elemental RPS.

Every few rounds (random gap between ``config.POWERUP_MIN_GAP_ROUNDS`` and
``config.POWERUP_MAX_GAP_ROUNDS``) one power-up appears on screen. The
player claims it by clicking it (or pressing its hotkey) before it expires
after ``config.POWERUP_LIFETIME_ROUNDS`` rounds.

Kinds (from the design document):

- ``double_damage``: the player's damage next round is doubled.
- ``hint``: reveals the *category* ("classic" / "elemental") of the AI's
  next choice, never the exact element.
- ``full_energy``: refills the player's energy to maximum immediately.
- ``shield``: grants a one-shot charge that cancels the damage of the
  player's next lost round.

The manager is deliberately display-agnostic: it owns state and pacing
only, and the UI layer decides where to draw the active power-up and its
hotkey bubble.
"""

from __future__ import annotations

import random
from collections.abc import Callable

import config
from ai_opponent import Category
from game_logic import Match

__all__ = ["PowerUp", "PowerUpManager", "POWERUP_KINDS"]

# Canonical kind order; the UI uses indices as hotkeys (1-4).
POWERUP_KINDS = ("double_damage", "hint", "full_energy", "shield")


class PowerUp:
    """One collectible power-up sitting on screen.

    Attributes:
        kind: One of ``POWERUP_KINDS``.
        position: Screen center position in pixels (x, y).
        hotkey: Keyboard key name shown on the bubble (e.g. ``"1"``).
        rounds_left: How many more full rounds it stays collectible.
        claimed: Whether the player has already taken it.
    """

    __slots__ = ("kind", "position", "hotkey", "rounds_left", "claimed")

    def __init__(self, kind: str, position: tuple[float, float], hotkey: str, lifetime: int) -> None:
        """Create a live, unclaimed power-up with its full round budget."""
        self.kind = kind
        self.position = position
        self.hotkey = hotkey
        self.rounds_left = lifetime
        self.claimed = False

    def title(self) -> str:
        """Human-readable name used on the bubble and pickup feed."""
        return POWERUP_TITLES[self.kind]

    def description(self) -> str:
        """One-line effect explanation, shown on the help screen and pickup feed."""
        return POWERUP_DESCRIPTIONS[self.kind]


# Display strings kept beside the kinds for easy editing.
POWERUP_TITLES = {
    "double_damage": "Double Damage",
    "hint": "Hint",
    "full_energy": "Full Energy",
    "shield": "Shield",
}

POWERUP_DESCRIPTIONS = {
    "double_damage": "Double your damage next round",
    "hint": "Reveal the AI's next category (classic/elemental)",
    "full_energy": "Refill your energy instantly",
    "shield": "Cancel the damage of your next loss",
}


class PowerUpManager:
    """Spawns, tracks and applies power-ups across a match.

    The manager drives itself from round boundaries: call ``on_round_started``
    when a new round begins (it counts down expiries and rolls for spawns)
    and ``try_claim`` from input handlers. Effects are applied through the
    ``Match`` object; the hint effect instead asks the injected
    ``category_provider`` for the AI's committed next category.

    Args:
        match: The owning match (effects mutate its player/multiplier).
        category_provider: Callable returning the category the AI will play
            in the current round; only consulted when the hint is claimed.
        rng: Injectable RNG for deterministic tests.
    """

    def __init__(
        self,
        match: Match,
        category_provider: Callable[[], Category],
        rng: random.Random | None = None,
    ) -> None:
        """Wire the manager to a match and its AI's category source."""
        self._match = match
        self._category_provider = category_provider
        self._rng = rng if rng is not None else random.Random()
        self.active: PowerUp | None = None
        self._rounds_until_spawn = self._roll_spawn_gap()
        self.last_pickup: str | None = None  # title of the most recently claimed power-up
        self.pending_hint: Category | None = None  # revealed category, consumed by the UI

    # -- Pacing -------------------------------------------------------------

    def _roll_spawn_gap(self) -> int:
        """Random rounds until the next spawn, within the configured gap."""
        return self._rng.randint(config.POWERUP_MIN_GAP_ROUNDS, config.POWERUP_MAX_GAP_ROUNDS)

    def on_round_started(self) -> None:
        """Advance spawn/expiry bookkeeping at a round boundary.

        Call once when a new round begins. A currently active power-up that
        has outlived its lifetime quietly disappears.
        """
        if self.active is not None:
            self.active.rounds_left -= 1
            if self.active.rounds_left <= 0 or self.active.claimed:
                self.active = None
        if self.active is None:
            self._rounds_until_spawn -= 1
            if self._rounds_until_spawn <= 0:
                self._spawn()
                self._rounds_until_spawn = self._roll_spawn_gap()
        self.last_pickup = None
        self.pending_hint = None

    def _spawn(self) -> None:
        """Place a new random power-up on screen with its activation key.

        Every power-up shares the single activation key "E" (digits 1-6 are
        reserved for element choices); only one is ever active at a time.
        """
        kind = self._rng.choice(POWERUP_KINDS)
        x = self._rng.uniform(config.WINDOW_WIDTH * 0.3, config.WINDOW_WIDTH * 0.7)
        y = self._rng.uniform(config.WINDOW_HEIGHT * 0.28, config.WINDOW_HEIGHT * 0.5)
        self.active = PowerUp(
            kind=kind,
            position=(x, y),
            hotkey="E",
            lifetime=config.POWERUP_LIFETIME_ROUNDS,
        )

    # -- Claiming -----------------------------------------------------------

    def try_claim(self, point: tuple[float, float]) -> bool:
        """Claim the active power-up by mouse click, if it was hit.

        Args:
            point: Click position in screen pixels.

        Returns:
            ``True`` when the click claimed a power-up this frame.
        """
        if self.active is None or self.active.claimed:
            return False
        dx = point[0] - self.active.position[0]
        dy = point[1] - self.active.position[1]
        if dx * dx + dy * dy > config.POWERUP_RADIUS * config.POWERUP_RADIUS:
            return False
        return self.claim_active()

    def claim_by_hotkey(self) -> bool:
        """Claim the active power-up via its keyboard hotkey.

        Every kind maps to its own key (its index in ``POWERUP_KINDS``), but
        since only one power-up is ever active, any hotkey press simply
        claims whatever is on screen.

        Returns:
            ``True`` when a power-up was claimed.
        """
        if self.active is None or self.active.claimed:
            return False
        return self.claim_active()

    def claim_active(self) -> bool:
        """Apply and consume the active power-up.

        Returns:
            ``True`` when a power-up was claimed, ``False`` when none was
            available.
        """
        if self.active is None or self.active.claimed:
            return False
        power_up = self.active
        power_up.claimed = True
        self._apply(power_up)
        self.last_pickup = power_up.title()
        self.active = None
        return True

    def _apply(self, power_up: PowerUp) -> None:
        """Apply a claimed power-up's effect to the match."""
        player = self._match.player
        if power_up.kind == "double_damage":
            self._match.player_damage_multiplier = 2.0
        elif power_up.kind == "hint":
            self.pending_hint = self._next_ai_category()
        elif power_up.kind == "full_energy":
            player.energy = config.MAX_ENERGY
        elif power_up.kind == "shield":
            player.gain_shield()
        else:  # pragma: no cover - guarded by POWERUP_KINDS
            raise ValueError(f"unknown power-up kind: {power_up.kind}")

    def _next_ai_category(self) -> Category:
        """Ask the injected provider for the AI's committed category this round."""
        return self._category_provider()
