import random
import math
import pygame
from theme import ELEMENT_THEMES

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 6.28)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.05)
        self.size = random.randint(3, 7)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        self.size = max(0, self.size - 0.1)

    def draw(self, surface):
        if self.life > 0 and self.size > 0:
            alpha_color = (
                int(self.color[0]),
                int(self.color[1]),
                int(self.color[2])
            )
            pygame.draw.circle(surface, alpha_color, (int(self.x), int(self.y)), int(self.size))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, element, count=25):
        theme = ELEMENT_THEMES.get(element, {"primary": (255, 255, 255)})
        color = theme["primary"]
        for _ in range(count):
            self.particles.append(Particle(x, y, color))

    def update(self):
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)
