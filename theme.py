import pygame

# Premium Dark Theme Color Palette
BG_DARK = (10, 14, 23)
BG_PANEL = (20, 27, 45)
BG_PANEL_HOVER = (30, 41, 69)
TEXT_LIGHT = (248, 250, 252)
TEXT_MUTED = (148, 163, 184)
ACCENT_PRIMARY = (99, 102, 241)    # Indigo
ACCENT_SECONDARY = (236, 72, 153)  # Pink
ACCENT_SUCCESS = (34, 197, 94)     # Emerald Green
ACCENT_WARNING = (245, 158, 11)    # Amber
ACCENT_DANGER = (239, 68, 68)      # Crimson Red

# Element visual identities (Primary, Gradient Bottom, Glow, Accent)
ELEMENT_THEMES = {
    "rock": {
        "primary": (113, 113, 122),
        "gradient": (63, 63, 70),
        "glow": (161, 161, 170),
        "accent": (228, 228, 231)
    },
    "paper": {
        "primary": (226, 232, 240),
        "gradient": (148, 163, 184),
        "glow": (248, 250, 252),
        "accent": (255, 255, 255)
    },
    "scissors": {
        "primary": (245, 158, 11),
        "gradient": (180, 83, 9),
        "glow": (251, 191, 36),
        "accent": (254, 243, 199)
    },
    "fire": {
        "primary": (239, 68, 68),
        "gradient": (185, 28, 28),
        "glow": (248, 113, 113),
        "accent": (254, 202, 202)
    },
    "water": {
        "primary": (59, 130, 246),
        "gradient": (29, 78, 216),
        "glow": (96, 165, 250),
        "accent": (191, 219, 254)
    },
    "earth": {
        "primary": (34, 197, 94),
        "gradient": (21, 128, 61),
        "glow": (74, 222, 128),
        "accent": (187, 247, 208)
    }
}

def get_font(size, bold=False):
    """Get a clean system font."""
    try:
        return pygame.font.SysFont("Segoe UI", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)
