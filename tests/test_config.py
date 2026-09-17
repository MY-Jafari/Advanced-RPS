"""Consistency checks for the central configuration values."""

import config


def test_elements_registry_is_complete():
    """The element registry matches the intended six-element set and grouping."""
    assert len(config.ELEMENTS) == 6
    assert set(config.ELEMENTS) == {"rock", "paper", "scissors", "fire", "water", "earth"}
    assert set(config.CLASSIC_ELEMENTS) | set(config.ELEMENTAL_ELEMENTS) == set(config.ELEMENTS)
    assert not set(config.CLASSIC_ELEMENTS) & set(config.ELEMENTAL_ELEMENTS)


def test_every_element_has_a_color():
    """Each element carries a UI color so per-element theming never KeyErrors."""
    for element in config.ELEMENTS:
        assert element in config.ELEMENT_COLORS


def test_energy_and_hp_bounds_are_sane():
    """Balance numbers stay inside their logical bounds."""
    assert 0 < config.STARTING_ENERGY <= config.MAX_ENERGY
    assert config.DAMAGE_FROM_CLASSIC < config.DAMAGE_FROM_ELEMENTAL
    assert config.COST_CLASSIC < config.COST_ELEMENTAL
    assert config.ENERGY_REGEN_PER_ROUND <= config.MAX_ENERGY
    assert 0 <= config.COMBO_STEP_BONUS <= 1.0
