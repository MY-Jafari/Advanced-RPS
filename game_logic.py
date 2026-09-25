from config import RULES, DEFAULT_HP, MAX_ENERGY, COMBO_MULTIPLIER_STEP

def validate_rules_symmetry():
    """Verify that every win has a corresponding loss on the other side."""
    for elem, data in RULES.items():
        for opponent in data["beats"]:
            assert elem in RULES[opponent]["loses_to"], f"Symmetry violation: {elem} beats {opponent}, but {opponent} does not list {elem} in loses_to"
        for opponent in data["loses_to"]:
            assert elem in RULES[opponent]["beats"], f"Symmetry violation: {elem} loses to {opponent}, but {opponent} does not list {elem} in beats"

# Run rule validation on import
validate_rules_symmetry()

def determine_round_winner(player_choice, ai_choice):
    """
    Determine winner between player_choice and ai_choice.
    Returns: 'win', 'lose', or 'tie'
    """
    if player_choice == ai_choice:
        return 'tie'
    if ai_choice in RULES[player_choice]["beats"]:
        return 'win'
    elif ai_choice in RULES[player_choice]["loses_to"]:
        return 'lose'
    return 'tie'

class GameSession:
    """Manages game state, HP, energy, combos, and round resolution."""
    def __init__(self, best_of=3):
        self.best_of = best_of
        self.player_hp = DEFAULT_HP
        self.ai_hp = DEFAULT_HP
        self.player_energy = MAX_ENERGY
        self.ai_energy = MAX_ENERGY

        self.player_combo = 0
        self.ai_combo = 0

        self.player_wins = 0
        self.ai_wins = 0

        self.max_wins = (best_of // 2) + 1
        self.shield_active = False
        self.double_damage_next = False
        self.ai_hint_type = None

    def can_afford(self, choice):
        cost = RULES[choice]["energy_cost"]
        return self.player_energy >= cost

    def apply_energy_cost(self, choice, is_player=True):
        cost = RULES[choice]["energy_cost"]
        if is_player:
            self.player_energy = max(0, self.player_energy - cost)
        else:
            self.ai_energy = max(0, self.ai_energy - cost)

    def regenerate_energy(self, regen_amount):
        self.player_energy = min(MAX_ENERGY, self.player_energy + regen_amount)
        self.ai_energy = min(MAX_ENERGY, self.ai_energy + regen_amount)

    def calculate_damage(self, winner_choice, combo_count, is_double_damage=False):
        base = RULES[winner_choice]["base_damage"]
        combo_bonus = 1.0 + (combo_count * COMBO_MULTIPLIER_STEP)
        dmg = base * combo_bonus
        if is_double_damage:
            dmg *= 2
        return int(dmg)

    def process_round(self, player_choice, ai_choice, power_up_effects=None):
        """
        Processes a round and updates HP, combos, and scores.
        power_up_effects: dict containing active buffs (e.g., {'shield': bool, 'double_damage': bool})
        """
        if power_up_effects is None:
            power_up_effects = {}

        p_cost = RULES[player_choice]["energy_cost"]
        ai_cost = RULES[ai_choice]["energy_cost"]

        self.player_energy = max(0, self.player_energy - p_cost)
        self.ai_energy = max(0, self.ai_energy - ai_cost)

        result = determine_round_winner(player_choice, ai_choice)

        player_dmg_dealt = 0
        ai_dmg_dealt = 0

        if result == 'win':
            self.player_combo += 1
            self.ai_combo = 0
            dd = power_up_effects.get('player_double_damage', False)
            player_dmg_dealt = self.calculate_damage(player_choice, self.player_combo, dd)
            self.ai_hp = max(0, self.ai_hp - player_dmg_dealt)

        elif result == 'lose':
            self.ai_combo += 1
            self.player_combo = 0
            if power_up_effects.get('player_shield', False):
                # Shield absorbs the damage
                ai_dmg_dealt = 0
                shield_used = True
            else:
                shield_used = False
                ai_dmg_dealt = self.calculate_damage(ai_choice, self.ai_combo)
                self.player_hp = max(0, self.player_hp - ai_dmg_dealt)
        else:
            # Tie
            self.player_combo = 0
            self.ai_combo = 0
            shield_used = False

        return {
            "result": result,
            "player_dmg": player_dmg_dealt,
            "ai_dmg": ai_dmg_dealt,
            "shield_used": power_up_effects.get('player_shield', False) and result == 'lose'
        }

    def is_match_over(self):
        if self.player_hp <= 0 or self.ai_hp <= 0:
            return True
        if self.player_wins >= self.max_wins or self.ai_wins >= self.max_wins:
            return True
        return False

    def get_match_winner(self):
        if self.player_hp <= 0 or self.ai_wins < self.player_wins and (self.player_wins >= self.max_wins or self.ai_hp <= 0):
            if self.player_hp <= 0 and self.ai_hp > 0:
                return "ai"
            if self.ai_hp <= 0 and self.player_hp > 0:
                return "player"
        if self.player_wins > self.ai_wins:
            return "player"
        elif self.ai_wins > self.player_wins:
            return "ai"
        if self.player_hp > self.ai_hp:
            return "player"
        elif self.ai_hp > self.player_hp:
            return "ai"
        return "tie"
