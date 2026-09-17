# Elemental RPS

A six-element duel built with pygame. The classic rock-paper-scissors triangle
is extended with three natural elements — fire, water and earth — into a
meaningful cycle. Face an adaptive AI that learns your patterns, manage your
energy, chain combos and grab power-ups. First side to run out of HP loses.

## Rules

Every element beats exactly two others, loses to two and ties with one:

| Element  | Beats            | Loses to        | Ties with |
| -------- | ---------------- | --------------- | --------- |
| Rock     | Scissors, Earth  | Paper, Water    | Fire      |
| Paper    | Rock, Water      | Scissors, Fire  | Earth     |
| Scissors | Paper, Earth     | Rock, Fire      | Water     |
| Fire     | Paper, Scissors  | Water, Earth    | Rock      |
| Water    | Rock, Fire       | Paper, Earth    | Scissors  |
| Earth    | Fire, Water      | Rock, Scissors  | Paper      |

The natural logic: earth smothers fire, fire boils water away, water erodes
rock, rock dulls scissors, scissors cut earth, paper covers rock — and every
other pair follows a similar physical story (shown in the in-game help screen).

## Features

- **Adaptive AI** — frequency counting plus a simple Markov chain over your
  last 15 picks; it plays its prediction 60% of the time and stays random
  otherwise so it cannot be gamed.
- **Best-of-3 / 5 / 7** matches, chosen before the fight.
- **HP + energy systems** — elemental choices hit harder but cost more energy;
  broke choices are greyed out until you can afford them.
- **Combo multiplier** — consecutive wins add up to +50% damage.
- **Random power-ups** — double damage, a hint at the AI's next category,
  full energy refill or a one-shot shield.
- **Juice** — countdown, choices colliding in the center, element-themed
  particles, screen shake, winner glow and smooth state transitions.

## Controls

- **Mouse** — click choice buttons and power-ups, navigate menus.
- **Keyboard** — `1`-`6` pick an element, `H` open help, `Esc` go back,
  `M` mute.

## Run

```bash
pip install pygame
python main.py
```

Python 3.10+ recommended. The only dependency is pygame.

## Configuration

Every tunable value — window size, palette, balance numbers, AI behaviour,
power-up pacing, animation timing — lives in `config.py`.

## Development

```bash
pip install ruff pytest
ruff check .
ruff format --check .
pytest
```

## Project layout

```
main.py              # entry point and main loop
config.py            # all tunable values in one place
game_logic.py        # rules table, winner resolution, HP/energy/combo
ai_opponent.py       # adaptive AI opponent (frequency + Markov)
power_ups.py         # power-up spawning and activation
particle_system.py   # particle effects
ui.py                # buttons, HP/energy bars, shared widgets
states.py            # game state machine (menu, game, result, help)
assets/              # fonts/sounds (procedural audio needs no files)
tests/               # pytest suite for the game logic and AI
```
