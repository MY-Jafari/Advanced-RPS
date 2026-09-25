# 🌟 Elemental RPS: Arena

**The Ultimate Rock-Paper-Scissors Experience** — A modern, visually stunning 6-element battle arena built with Python and Pygame.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.5%2B-green?logo=pygame&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 🎮 Game Overview

**Elemental RPS: Arena** elevates the classic Rock-Paper-Scissors into a strategic, visually rich battle system with **6 unique elements**, **adaptive AI**, **resource management**, **combo mechanics**, and **power-ups**.

| Classic Elements | Natural Elements |
|:----------------:|:----------------:|
| 🪨 **Rock** | 🔥 **Fire** |
| 📄 **Paper** | 💧 **Water** |
| ✂️ **Scissors** | 🌍 **Earth** |

---

## ✨ Features

### 🎯 **Balanced 6-Element System**
Each element has **exactly 2 wins, 2 losses, and 1 tie** — perfectly balanced with thematic justifications:
- **Rock** crushes Scissors & shatters Earth
- **Paper** covers Rock & absorbs Water  
- **Scissors** cuts Paper & pierces Earth
- **Fire** burns Paper & melts Scissors
- **Water** erodes Rock & extinguishes Fire
- **Earth** smothers Fire & absorbs Water

### 🤖 **Adaptive AI Opponent**
- **Markov Chain Prediction** — Learns your patterns from the last 10-15 moves
- **Frequency Analysis** — Falls back to global playstyle when pattern data is insufficient
- **Configurable Intelligence** — 60% prediction-based counter, 40% randomness (tunable)
- **Category Hints** — Power-up reveals only "Classic" or "Natural" — never the exact move

### ⚡ **Deep Gameplay Systems**
| System | Description |
|--------|-------------|
| **Energy** | 0-100 pool. Classic moves cost 10, Natural moves cost 22. Regenerates 18/round |
| **HP Bars** | 100 HP each. Natural elements deal higher base damage (25 vs 15) |
| **Combo Streaks** | Consecutive wins increase damage +10% per stack (capped) |
| **Power-Ups** | Spawn randomly: 2× Damage, AI Hint, Full Energy, One-time Shield |

### 🎨 **Modern Visual Design**
- **Procedural Vector Icons** — Crisp, resolution-independent element icons (no emoji rendering issues)
- **PNG Asset Support** — Optional high-res custom artwork loading
- **Dynamic Background** — Living starfield with floating particles
- **Smooth Animations** — Easing functions (cubic, quadratic) for all transitions
- **Clash Effects** — Shockwave rings, particle explosions, winner/loser scaling
- **Dark Theme UI** — Gradient panels, glow effects, responsive hover states

### 🏗️ **Clean Architecture**
```
elemental_rps/
├── main.py              # Game loop & state management
├── config.py            # All gameplay constants & rules
├── theme.py             # Colors, gradients, fonts, easing
├── game_logic.py        # Pure logic: damage, HP, energy, combos
├── ai_opponent.py       # Markov chain AI with prediction
├── power_ups.py         # Power-up types & manager
├── particle_system.py   # Visual effects engine
├── ui.py                # Reusable UI components & drawing
├── image_manager.py     # PNG asset loading & fallback
├── states.py            # State machine: Menu → Battle → GameOver
├── assets/
│   ├── images/          # Custom PNG icons (optional)
│   └── README.md
├── tests/               # Unit tests for logic & AI
└── pyproject.toml       # Project metadata & dependencies
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**
- **pip** (package manager)

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/elemental-rps.git
cd elemental-rps

# Install dependencies (only Pygame required)
pip install -r requirements.txt
# OR simply:
pip install pygame
```

### Run the Game
```bash
python main.py
```

---

## 🎯 How to Play

1. **Launch** → `python main.py`
2. **Select Mode** → Best of 3 or Best of 5
3. **Choose Element** → Click one of 6 element cards at bottom
   - 🟢 **Green border** = Affordable
   - 🔴 **Red/Locked** = Not enough energy
4. **Watch the Clash** → Elements animate to center, shockwave triggers, result displays
5. **Collect Power-Ups** → Click floating orbs before they disappear
6. **Win** → Reduce enemy HP to 0 OR win majority of rounds

### Element Costs & Damage
| Element | Category | Energy Cost | Base Damage |
|---------|----------|-------------|-------------|
| Rock | Classic | 10 | 15 |
| Paper | Classic | 10 | 15 |
| Scissors | Classic | 10 | 15 |
| Fire | Natural | 22 | 25 |
| Water | Natural | 22 | 25 |
| Earth | Natural | 22 | 25 |

---

## ⚙️ Configuration

All gameplay values live in **`config.py`** — tweak without touching logic:

```python
# Gameplay defaults
DEFAULT_HP = 100
MAX_ENERGY = 100
ENERGY_REGEN = 18
AI_PREDICTION_PROB = 0.60      # 60% smart, 40% random
COMBO_MULTIPLIER_STEP = 0.10   # +10% per combo
POWER_UP_SPAWN_INTERVAL = 3    # Every 3 rounds
```

---

## 🧪 Testing

```bash
# Run all unit tests
pytest

# Run with coverage
pytest --cov=.

# Check syntax on all files
python -m py_compile *.py tests/*.py
```

---

## 🎨 Custom Assets (Optional)

To use your own PNG icons instead of procedural vector art:

1. Place 6 PNG files in `assets/images/`:
   - `rock.png`, `paper.png`, `scissors.png`
   - `fire.png`, `water.png`, `earth.png`
2. Recommended: **256×256px** with transparency
3. Restart the game — assets auto-load after window initialization

---

## 📁 Project Structure

```
elemental-rps/
├── .gitignore
├── .gitattributes
├── pyproject.toml
├── README.md
├── LICENSE
├── main.py
├── config.py
├── theme.py
├── game_logic.py
├── ai_opponent.py
├── power_ups.py
├── particle_system.py
├── ui.py
├── image_manager.py
├── states.py
├── assets/
│   ├── images/
│   │   ├── rock.png
│   │   ├── paper.png
│   │   ├── scissors.png
│   │   ├── fire.png
│   │   ├── water.png
│   │   └── earth.png
│   └── README.md
└── tests/
    ├── __init__.py
    ├── test_game_logic.py
    └── test_ai_opponent.py
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ |
| Graphics | Pygame 2.5+ (SDL2) |
| Architecture | State Machine, MVC-inspired separation |
| AI | 1st-Order Markov Chain + Frequency Analysis |
| Testing | pytest |
| Build | setuptools / pyproject.toml |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 🙏 Acknowledgments

- **Pygame Community** — For the excellent SDL2 wrapper
- **Game Design Inspiration** — Classic RPS, Pokémon type charts, fighting game mechanics
- **Visual Design** — Modern dark UI trends, procedural generation techniques

---

<div align="center">

**Made with ❤️ and Python**

*Elemental RPS: Arena — Where strategy meets spectacle*

</div>