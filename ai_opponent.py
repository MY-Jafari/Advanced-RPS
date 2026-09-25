import random
from collections import defaultdict
from config import ELEMENTS, RULES, AI_PREDICTION_PROB

class AIOpponent:
    """Adaptive AI using 1st order Markov chain and frequency analysis."""
    def __init__(self):
        self.history = []
        self.transition_counts = defaultdict(lambda: defaultdict(int))
        self.element_counts = defaultdict(int)

    def record_player_choice(self, choice):
        if choice not in ELEMENTS:
            return
        if self.history:
            prev = self.history[-1]
            self.transition_counts[prev][choice] += 1
        self.element_counts[choice] += 1
        self.history.append(choice)

    def predict_next_choice(self):
        if not self.history:
            return random.choice(ELEMENTS)

        # 60% chance to use adaptive prediction if enough history
        if random.random() < AI_PREDICTION_PROB:
            last_choice = self.history[-1]
            transitions = self.transition_counts[last_choice]

            if transitions:
                # Pick the most frequent next choice after last_choice
                predicted = max(transitions, key=transitions.get)
                return predicted
            elif self.element_counts:
                # Fallback to most frequent overall choice
                predicted = max(self.element_counts, key=self.element_counts.get)
                return predicted

        # Otherwise random
        return random.choice(ELEMENTS)

    def choose_move(self, available_energy=100):
        """
        Predict player's move, then choose a counter move that beats or ties it,
        respecting energy constraints if possible.
        """
        predicted_player = self.predict_next_choice()

        # Find elements that beat predicted_player
        winning_moves = [e for e, r in RULES.items() if predicted_player in r["beats"]]

        if winning_moves and random.random() < 0.75:
            # 75% chance to pick a winning counter
            candidate = random.choice(winning_moves)
            if RULES[candidate]["energy_cost"] <= available_energy:
                return candidate

        # Fallback to random valid move
        affordable = [e for e in ELEMENTS if RULES[e]["energy_cost"] <= available_energy]
        if affordable:
            return random.choice(affordable)
        return random.choice(ELEMENTS)

    def get_hint(self):
        """Returns category hint ('classic' or 'natural') for the next prediction."""
        next_pred = self.predict_next_choice()
        return RULES[next_pred]["category"]
