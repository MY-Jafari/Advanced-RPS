import pytest
from game_logic import determine_round_winner, GameSession, validate_rules_symmetry
from config import RULES

def test_rules_symmetry():
    # Should not raise any assertion errors
    validate_rules_symmetry()

def test_determine_winner():
    # Rock beats scissors and earth
    assert determine_round_winner("rock", "scissors") == "win"
    assert determine_round_winner("rock", "earth") == "win"
    # Rock loses to paper and water
    assert determine_round_winner("rock", "paper") == "lose"
    assert determine_round_winner("rock", "water") == "lose"
    # Rock ties with rock
    assert determine_round_winner("rock", "rock") == "tie"

def test_game_session():
    session = GameSession(best_of=3)
    assert session.player_hp == 100
    assert session.ai_hp == 100
    assert session.player_energy == 100
    assert session.can_afford("rock") is True
