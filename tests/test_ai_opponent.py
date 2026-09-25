import pytest
from ai_opponent import AIOpponent
from config import ELEMENTS

def test_ai_opponent_recording():
    ai = AIOpponent()
    ai.record_player_choice("rock")
    ai.record_player_choice("paper")
    assert len(ai.history) == 2
    assert ai.element_counts["rock"] == 1
    assert ai.element_counts["paper"] == 1

def test_ai_choose_move():
    ai = AIOpponent()
    move = ai.choose_move(100)
    assert move in ELEMENTS
