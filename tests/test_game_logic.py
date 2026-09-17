"""Unit tests for the rules table, round resolution and match pipeline."""

import pytest

import config
from game_logic import (
    BEATS,
    OUTCOMES,
    TIES,
    Match,
    Player,
    base_damage,
    choice_cost,
    resolve_round,
    scaled_damage,
    validate_rules,
)

# ---------------------------------------------------------------------------
# Rules table integrity
# ---------------------------------------------------------------------------


class TestRulesTable:
    """The explicit 6x6 table must be complete, consistent and balanced."""

    def test_validate_builtin_table_passes(self):
        """The built-in table passes its own integrity validation."""
        validate_rules()

    def test_validate_catches_broken_tables(self):
        """Corrupting the table raises ValueError instead of failing silently."""
        with pytest.raises(ValueError):
            validate_rules(beats=dict.fromkeys(config.ELEMENTS, ("rock", "paper")))
        broken_ties = dict(TIES)
        broken_ties["rock"] = "paper"
        with pytest.raises(ValueError):
            validate_rules(ties=broken_ties)

    def test_every_element_beats_exactly_two(self):
        for element in config.ELEMENTS:
            beaten = BEATS[element]
            assert len(beaten) == 2
            for loser in beaten:
                assert OUTCOMES[(element, loser)] == "win"
                assert OUTCOMES[(loser, element)] == "lose"

    def test_every_element_ties_with_exactly_one(self):
        for element, partner in TIES.items():
            assert TIES[partner] == element  # mutual
            assert OUTCOMES[(element, partner)] == "tie"

    def test_design_document_wins(self):
        """Spot-checks straight from the design document's table."""
        expected_wins = {
            "rock": ("scissors", "earth"),
            "paper": ("rock", "water"),
            "scissors": ("paper", "earth"),
            "fire": ("paper", "scissors"),
            "water": ("rock", "fire"),
            "earth": ("fire", "water"),
        }
        assert expected_wins == BEATS

    def test_design_document_ties(self):
        assert TIES == {
            "rock": "fire",
            "paper": "earth",
            "scissors": "water",
            "fire": "rock",
            "water": "scissors",
            "earth": "paper",
        }

    def test_matrix_is_symmetric(self):
        """For every distinct pair, both directions exist and disagree."""
        for (a, b), outcome in OUTCOMES.items():
            if a == b:
                continue
            reverse = OUTCOMES[(b, a)]
            if outcome == "tie":
                assert reverse == "tie"
            else:
                assert {outcome, reverse} == {"win", "lose"}

    def test_every_non_equal_pair_has_a_rule(self):
        for a in config.ELEMENTS:
            for b in config.ELEMENTS:
                if a == b:
                    assert resolve_round(a, b) == "tie"
                else:
                    assert (a, b) in OUTCOMES

    def test_justifications_cover_all_winning_pairs(self):
        """Every winning (winner, loser) pair has a thematic explanation."""
        from game_logic import JUSTIFICATIONS

        for winner, losers in BEATS.items():
            for loser in losers:
                assert (winner, loser) in JUSTIFICATIONS


# ---------------------------------------------------------------------------
# Round resolution and balance math
# ---------------------------------------------------------------------------


class TestResolution:
    """resolve_round and the damage/energy helpers."""

    def test_sample_rounds(self):
        assert resolve_round("water", "fire") == "win"
        assert resolve_round("rock", "paper") == "lose"
        assert resolve_round("scissors", "water") == "tie"
        assert resolve_round("earth", "earth") == "tie"

    def test_costs_by_group(self):
        for element in config.CLASSIC_ELEMENTS:
            assert choice_cost(element) == config.COST_CLASSIC
        for element in config.ELEMENTAL_ELEMENTS:
            assert choice_cost(element) == config.COST_ELEMENTAL

    def test_base_damage_by_group(self):
        assert base_damage("rock") == config.DAMAGE_FROM_CLASSIC
        assert base_damage("fire") == config.DAMAGE_FROM_ELEMENTAL

    def test_scaled_damage_integer_math(self):
        assert scaled_damage(15, 0) == 15
        assert scaled_damage(15, 10) == 16  # 16.5 floors to 16
        assert scaled_damage(15, 50) == 22  # 22.5 floors to 22
        assert scaled_damage(22, 50) == 33

    def test_scaled_damage_caps_apply(self):
        player = Player("P")
        player.combo = 99
        assert player.combo_bonus_percent() == config.COMBO_MAX_BONUS_PERCENT


# ---------------------------------------------------------------------------
# Player mechanics
# ---------------------------------------------------------------------------


class TestPlayer:
    """Energy, shields and HP bookkeeping."""

    def test_energy_spend_and_regen(self):
        player = Player("P")
        start = player.energy
        player.spend_energy("fire")
        assert player.energy == start - config.COST_ELEMENTAL
        player.regenerate_energy()
        assert player.energy == min(config.MAX_ENERGY, start - config.COST_ELEMENTAL + config.ENERGY_REGEN_PER_ROUND)

    def test_cannot_afford_elemental_early(self):
        player = Player("P", energy=config.COST_CLASSIC + 1)
        assert player.can_afford("rock")
        assert not player.can_afford("fire")

    def test_shield_blocks_one_loss(self):
        player = Player("P")
        player.gain_shield()
        assert player.use_shield() is True
        assert player.use_shield() is False
        assert player.shields == 0

    def test_hp_clamps_at_zero(self):
        player = Player("P")
        player.take_damage(10_000)
        assert player.hp == 0
        assert player.is_defeated()

    def test_reset_restores_everything(self):
        player = Player("P")
        player.take_damage(40)
        player.spend_energy("fire")
        player.gain_shield()
        player.reset()
        assert player.hp == player.max_hp
        assert player.energy == config.STARTING_ENERGY
        assert player.shields == 0
        assert player.combo == 0


# ---------------------------------------------------------------------------
# Match pipeline
# ---------------------------------------------------------------------------


class TestMatch:
    """Best-of-N flow: energy, combo-scaled damage, shields, endings."""

    def test_invalid_best_of_rejected(self):
        with pytest.raises(ValueError):
            Match(best_of=4)

    def test_round_one_uses_starting_energy_no_regen(self):
        match = Match()
        match.start_round()
        assert match.player.energy == config.STARTING_ENERGY
        result = match.play_round("rock", "fire")  # tie
        assert result.outcome == "tie"
        assert result.player_damage_dealt == 0
        assert match.rounds_played == 1

    def test_energy_regen_applies_once_per_round(self):
        match = Match()
        match.start_round()
        match.play_round("rock", "fire")  # round 1
        match.start_round()  # regen for round 2
        expected = min(
            config.MAX_ENERGY,
            config.STARTING_ENERGY - config.COST_CLASSIC + config.ENERGY_REGEN_PER_ROUND,
        )
        assert match.player.energy == expected
        match.start_round()  # idempotent for the same round
        assert match.player.energy == expected

    def test_win_deals_damage_and_breaks_ai_combo(self):
        match = Match()
        match.start_round()
        result = match.play_round("water", "fire")  # water beats fire
        assert result.outcome == "win"
        assert result.player_damage_dealt == config.DAMAGE_FROM_ELEMENTAL
        assert match.opponent.hp == config.MAX_HP - config.DAMAGE_FROM_ELEMENTAL
        assert result.player_combo == 1
        assert result.ai_combo == 0

    def test_combo_scales_consecutive_wins(self):
        match = Match()
        match.start_round()
        first = match.play_round("water", "fire")  # win, combo 0 -> base damage
        assert first.player_damage_dealt == config.DAMAGE_FROM_ELEMENTAL
        match.start_round()
        second = match.play_round("rock", "scissors")  # win, combo 1 -> +10%
        expected = config.DAMAGE_FROM_CLASSIC * (100 + config.COMBO_STEP_BONUS_PERCENT) // 100
        assert second.player_damage_dealt == expected
        match.start_round()
        third = match.play_round("paper", "rock")  # win, combo 2 -> +20%
        expected = config.DAMAGE_FROM_CLASSIC * (100 + 2 * config.COMBO_STEP_BONUS_PERCENT) // 100
        assert third.player_damage_dealt == expected

    def test_tie_breaks_combo(self):
        match = Match()
        match.start_round()
        match.play_round("water", "fire")
        assert match.player.combo == 1
        match.start_round()
        match.play_round("fire", "fire")
        assert match.player.combo == 0
        assert match.opponent.combo == 0

    def test_shield_cancels_player_loss(self):
        match = Match()
        match.player.gain_shield()
        match.start_round()
        result = match.play_round("fire", "water")  # water beats fire
        assert result.outcome == "lose"
        assert result.player_shield_used is True
        assert result.ai_damage_dealt == 0
        assert match.player.hp == config.MAX_HP

    def test_unaffordable_choice_rejected(self):
        match = Match()
        match.player.energy = 0
        match.start_round()
        with pytest.raises(ValueError):
            match.play_round("rock", "fire")

    def test_knockout_ends_match(self):
        match = Match()
        match.opponent.hp = 1
        match.start_round()
        match.play_round("water", "fire")  # 22 damage >= 1 HP
        assert match.is_over()
        assert match.winner() == "player"

    def test_rounds_exhausted_higher_hp_wins(self):
        match = Match(best_of=3)
        for _ in range(3):
            match.start_round()
            match.play_round("rock", "fire")  # ties keep HP equal
        assert match.is_over()
        assert match.winner() == "draw"

        match2 = Match(best_of=3)
        match2.opponent.hp = 90  # AI took chip damage earlier
        for _ in range(3):
            match2.start_round()
            match2.play_round("rock", "fire")
        assert match2.is_over()
        assert match2.winner() == "player"

    def test_winner_returns_none_while_running(self):
        match = Match()
        assert match.winner() is None
        assert not match.is_over()
