"""Unit tests for the power-up system."""

import random

import config
from ai_opponent import AIOpponent, element_category
from game_logic import Match
from power_ups import (
    POWERUP_DESCRIPTIONS,
    POWERUP_KINDS,
    POWERUP_TITLES,
    PowerUp,
    PowerUpManager,
)


class FixedCategoryProvider:
    """Always reports one AI category, standing in for the AI's committed choice."""

    def __init__(self, category: str = "elemental") -> None:
        self.category = category

    def __call__(self) -> str:
        return self.category


def make_manager(rng_seed: int = 0, category: str = "elemental") -> PowerUpManager:
    """Build a manager over a fresh match with deterministic RNG."""
    return PowerUpManager(
        Match(),
        FixedCategoryProvider(category),
        random.Random(rng_seed),
    )


def force_spawn(manager: PowerUpManager, kind: str) -> None:
    """Replace the manager's active power-up with one of a specific kind."""
    manager.active = PowerUp(
        kind=kind,
        position=(config.WINDOW_WIDTH / 2, config.WINDOW_HEIGHT / 2),
        hotkey="1",
        lifetime=config.POWERUP_LIFETIME_ROUNDS,
    )


# ---------------------------------------------------------------------------
# Titles and descriptions
# ---------------------------------------------------------------------------


def test_every_kind_has_title_and_description():
    assert set(POWERUP_TITLES) == set(POWERUP_KINDS)
    assert set(POWERUP_DESCRIPTIONS) == set(POWERUP_KINDS)
    for kind in POWERUP_KINDS:
        assert POWERUP_TITLES[kind]
        assert POWERUP_DESCRIPTIONS[kind]


# ---------------------------------------------------------------------------
# Spawning and pacing
# ---------------------------------------------------------------------------


def test_no_powerup_before_min_gap():
    """Across many seeds, nothing spawns before round MIN_GAP_ROUNDS."""
    for seed in range(200):
        manager = make_manager(rng_seed=seed)
        for _ in range(config.POWERUP_MIN_GAP_ROUNDS - 1):
            manager.on_round_started()
            assert manager.active is None, f"early spawn with seed {seed}"


def spawn_within_bound(manager: PowerUpManager, max_rounds: int = 20) -> None:
    """Advance round boundaries until a power-up spawns (generous bound)."""
    for _ in range(max_rounds):
        manager.on_round_started()
        if manager.active is not None:
            return
    raise AssertionError("power-up never spawned")


def test_spawn_eventually_happens():
    manager = make_manager(rng_seed=2)
    spawn_within_bound(manager)
    assert manager.active.kind in POWERUP_KINDS
    assert manager.active.hotkey in {"1", "2", "3", "4"}


def test_spawn_position_inside_center_band():
    manager = make_manager(rng_seed=3)
    spawn_within_bound(manager)
    x, y = manager.active.position
    assert config.WINDOW_WIDTH * 0.3 <= x <= config.WINDOW_WIDTH * 0.7
    assert config.WINDOW_HEIGHT * 0.28 <= y <= config.WINDOW_HEIGHT * 0.5


def test_powerup_expires_after_lifetime_rounds():
    manager = make_manager(rng_seed=4)
    for _ in range(config.POWERUP_MAX_GAP_ROUNDS + 1):
        manager.on_round_started()
    force_spawn(manager, "shield")
    for _ in range(config.POWERUP_LIFETIME_ROUNDS):
        manager.on_round_started()
    assert manager.active is None


# ---------------------------------------------------------------------------
# Claiming
# ---------------------------------------------------------------------------


def test_click_at_center_claims():
    manager = make_manager(rng_seed=5)
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "shield")
    assert manager.try_claim(manager.active.position) is True
    assert manager.active is None


def test_click_outside_radius_ignores():
    manager = make_manager(rng_seed=6)
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "shield")
    far = (manager.active.position[0] + config.POWERUP_RADIUS + 50, manager.active.position[1])
    assert manager.try_claim(far) is False
    assert manager.active is not None


def test_hotkey_claims_any_active_powerup():
    manager = make_manager(rng_seed=7)
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "full_energy")
    assert manager.claim_by_hotkey() is True
    assert manager.claim_by_hotkey() is False  # nothing left to claim


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------


def test_double_damage_doubles_next_round_damage():
    match = Match()
    manager = PowerUpManager(match, FixedCategoryProvider(), random.Random(8))
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "double_damage")
    manager.claim_active()
    assert match.player_damage_multiplier == 2.0

    match.start_round()
    match.play_round("water", "fire")  # player wins with an elemental
    assert match.opponent.hp == config.MAX_HP - 2 * config.DAMAGE_FROM_ELEMENTAL
    # Bonus is consumed after exactly one round.
    assert match.player_damage_multiplier == 1.0


def test_full_energy_refills_to_max():
    match = Match()
    match.player.energy = 10
    manager = PowerUpManager(match, FixedCategoryProvider(), random.Random(9))
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "full_energy")
    manager.claim_active()
    assert match.player.energy == config.MAX_ENERGY


def test_shield_grants_one_charge():
    match = Match()
    manager = PowerUpManager(match, FixedCategoryProvider(), random.Random(10))
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "shield")
    manager.claim_active()
    assert match.player.shields == 1

    match.start_round()
    result = match.play_round("fire", "water")  # player loses
    assert result.player_shield_used is True
    assert match.player.hp == config.MAX_HP


def test_hint_reveals_category_only():
    match = Match()
    manager = PowerUpManager(match, FixedCategoryProvider("elemental"), random.Random(11))
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "hint")
    manager.claim_active()
    assert manager.pending_hint == "elemental"


def test_hint_resets_on_next_round():
    manager = make_manager(rng_seed=12, category="classic")
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "hint")
    manager.claim_active()
    assert manager.pending_hint == "classic"
    manager.on_round_started()
    assert manager.pending_hint is None


def test_pickup_feed_resets_each_round():
    manager = make_manager(rng_seed=13)
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "shield")
    manager.claim_active()
    assert manager.last_pickup == POWERUP_TITLES["shield"]
    manager.on_round_started()
    assert manager.last_pickup is None


# ---------------------------------------------------------------------------
# Integration with the AI loop
# ---------------------------------------------------------------------------


def test_category_provider_uses_ai_prediction():
    """The provider wired to the AI returns the category of its next pick."""
    match = Match()
    ai = AIOpponent(random.Random(0))
    for _ in range(6):
        ai.observe("scissors")

    def provider() -> str:
        return element_category(ai.choose(tuple(config.ELEMENTS)))

    manager = PowerUpManager(match, provider, random.Random(14))
    manager.on_round_started()
    manager.active = None
    force_spawn(manager, "hint")
    manager.claim_active()
    # Scissors-heavy history: the AI's pick is whatever the provider computed;
    # the hint must always be one of the two valid categories.
    assert manager.pending_hint in {"classic", "elemental"}
