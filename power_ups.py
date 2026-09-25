import random
import math
import pygame
from config import WIDTH, HEIGHT

class PowerUp:
    def __init__(self):
        self.types = ["double_damage", "hint", "full_energy", "shield"]
        self.type = random.choice(self.types)

        # Position randomly in the arena area (avoiding top/bottom UI bars)
        self.x = random.randint(200, WIDTH - 200)
        self.y = random.randint(220, HEIGHT - 220)

        self.radius = 28
        self.spawn_time = pygame.time.get_ticks()
        self.duration = 8000  # disappears after 8 seconds if not collected
        self.float_offset = 0.0

    def update(self):
        elapsed = pygame.time.get_ticks() - self.spawn_time
        self.float_offset = math.sin(pygame.time.get_ticks() * 0.005) * 6
        return elapsed < self.duration

    def is_clicked(self, mouse_pos):
        mx, my = mouse_pos
        current_y = self.y + self.float_offset
        dist = math.hypot(mx - self.x, my - current_y)
        return dist <= self.radius

    def get_display_info(self):
        info = {
            "double_damage": {"name": "دو برابر آسیب", "color": (239, 68, 68), "symbol": "2X"},
            "hint": {"name": "سرنخ هوش مصنوعی", "color": (234, 179, 8), "symbol": "?"},
            "full_energy": {"name": "انرژی کامل", "color": (34, 197, 94), "symbol": "⚡"},
            "shield": {"name": "شیلد دفاعی", "color": (59, 130, 246), "symbol": "🛡️"}
        }
        return info.get(self.type, {"name": "پاورآپ", "color": (255, 255, 255), "symbol": "★"})
