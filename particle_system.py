"""Particle effects for Elemental RPS.

A small, allocation-friendly particle engine driving the element-themed
bursts (sparks for fire, droplets for water, rubble for earth, fluttering
slips for paper and so on) plus generic clash and pickup bursts.

Motion is integrated with plain floats and a delta-time step; rendering
fades each particle toward black (which reads as fading out on the dark
theme) and shrinks it over its lifetime, so no per-particle alpha surfaces
are needed and drawing hundreds of particles stays cheap.

Particle construction reads its recipe from ``config.PARTICLE_PRESETS`` /
``config.IMPACT_PRESET``; only ``pygame.draw`` is touched at render time,
so the whole system is testable without a display.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

import pygame

import config

Position = tuple[float, float]


class Particle:
    """One moving, aging and fading particle.

    Attributes:
        x, y: Current position in screen pixels.
        vx, vy: Velocity in px/s.
        age: Seconds lived so far.
        lifetime: Total seconds before the particle expires.
        size: Starting radius (circles) or half-width (squares/flakes) in px.
        color: Base RGB color; fading multiplies it by remaining life.
        shape: ``"circle"``, ``"square"`` or ``"flake"`` (render style).
        gravity_scale: Multiplier on ``config.PARTICLE_GRAVITY``.
        drag: Fraction of velocity removed per second (exponential); 0 = none.
        sway: Horizontal flutter amplitude in px/s^2 (0 disables it).
        sway_phase: Phase of the flutter sinusoid in radians.
    """

    __slots__ = (
        "x",
        "y",
        "vx",
        "vy",
        "age",
        "lifetime",
        "size",
        "color",
        "shape",
        "gravity_scale",
        "drag",
        "sway",
        "sway_phase",
    )

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        lifetime: float,
        size: float,
        color: tuple[int, int, int],
        shape: str = "circle",
        gravity_scale: float = 1.0,
        drag: float = 0.0,
        sway: float = 0.0,
        sway_phase: float = 0.0,
    ) -> None:
        """Store the particle's motion, appearance and physics parameters."""
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.age = 0.0
        self.lifetime = max(lifetime, 0.001)
        self.size = size
        self.color = color
        self.shape = shape
        self.gravity_scale = gravity_scale
        self.drag = drag
        self.sway = sway
        self.sway_phase = sway_phase

    @property
    def life_fraction(self) -> float:
        """Remaining life as a 1.0 -> 0.0 fraction (used for fade and shrink)."""
        return max(0.0, 1.0 - self.age / self.lifetime)

    def update(self, dt: float) -> bool:
        """Advance the particle by ``dt`` seconds.

        Applies gravity, exponential air drag and (optionally) a sinusoidal
        horizontal flutter, then integrates the position.

        Args:
            dt: Elapsed seconds since the previous frame.

        Returns:
            ``True`` while the particle is alive, ``False`` once expired.
        """
        self.age += dt
        if self.age >= self.lifetime:
            return False
        self.vy += config.PARTICLE_GRAVITY * self.gravity_scale * dt
        if self.sway:
            self.sway_phase += config.PARTICLE_SWAY_SPEED * dt
            self.vx += math.sin(self.sway_phase) * self.sway * dt
        drag_factor = max(0.0, 1.0 - self.drag * dt)
        self.vx *= drag_factor
        self.vy *= drag_factor
        self.x += self.vx * dt
        self.y += self.vy * dt
        return True

    def draw(self, surface: pygame.Surface, offset: Position = (0.0, 0.0)) -> None:
        """Render the particle, fading toward black and shrinking as it dies."""
        fraction = self.life_fraction
        color = tuple(int(channel * fraction) for channel in self.color)
        radius = max(1, int(self.size * fraction))
        x = int(self.x + offset[0])
        y = int(self.y + offset[1])
        if self.shape == "circle":
            pygame.draw.circle(surface, color, (x, y), radius)
        else:  # square or flake: both render as little rectangles
            rect = pygame.Rect(0, 0, radius * 2, radius * 2)
            rect.center = (x, y)
            pygame.draw.rect(surface, color, rect)


class ParticleSystem:
    """Owns all live particles and spawns themed bursts.

    The system keeps at most ``config.MAX_PARTICLES`` particles; when a new
    burst exceeds the cap the oldest particles are evicted first so fresh
    effects always stay visible.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        """Create an empty system; ``rng`` is injectable for deterministic tests."""
        self._rng = rng if rng is not None else random.Random()
        self._particles: list[Particle] = []

    def __len__(self) -> int:
        """Number of currently alive particles."""
        return len(self._particles)

    def clear(self) -> None:
        """Remove every particle instantly (used on state changes)."""
        self._particles.clear()

    # -- Spawning -----------------------------------------------------------

    def _spawn_with_recipe(
        self,
        recipe: dict,
        position: Position,
        direction: Position | None,
    ) -> None:
        """Emit one burst from a preset recipe, evicting old particles if needed.

        Args:
            recipe: A ``config.PARTICLE_PRESETS``-style dictionary.
            position: Burst origin in screen pixels.
            direction: Optional unit-ish bias vector; when given, launches
                are blended 60% toward it and 40% uniform (so damage bursts
                can fly toward the loser while still scattering).
        """
        count = self._rng.randint(*recipe["count"])
        colors: Sequence[tuple[int, int, int]] = recipe["colors"]
        while count > 0:
            while len(self._particles) >= config.MAX_PARTICLES:
                self._particles.pop(0)
            angle = self._rng.uniform(0.0, math.tau)
            speed = self._rng.uniform(*recipe["speed"])
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            if direction is not None:
                vx = vx * 0.4 + direction[0] * speed * 0.6
                vy = vy * 0.4 + direction[1] * speed * 0.6
            self._particles.append(
                Particle(
                    x=position[0],
                    y=position[1],
                    vx=vx,
                    vy=vy,
                    lifetime=self._rng.uniform(*recipe["lifetime"]),
                    size=self._rng.uniform(*recipe["size"]),
                    color=colors[self._rng.randrange(len(colors))],
                    shape=recipe["shape"],
                    gravity_scale=recipe["gravity_scale"],
                    drag=recipe["drag"],
                    sway=recipe["sway"],
                    sway_phase=self._rng.uniform(0.0, math.tau),
                )
            )
            count -= 1

    def burst_for_element(self, element: str, position: Position, direction: Position | None = None) -> None:
        """Spawn an element-themed burst (sparks, droplets, rubble, ...).

        Args:
            element: One of ``config.ELEMENTS``.
            position: Burst origin in screen pixels.
            direction: Optional launch bias toward the loser of the round.
        """
        self._spawn_with_recipe(config.PARTICLE_PRESETS[element], position, direction)

    def impact_burst(self, position: Position, direction: Position | None = None) -> None:
        """Spawn the white-hot clash burst used at the center on impact."""
        self._spawn_with_recipe(config.IMPACT_PRESET, position, direction)

    def pickup_burst(self, position: Position, color: tuple[int, int, int]) -> None:
        """Spawn a short celebratory burst when a power-up is claimed."""
        recipe = dict(config.IMPACT_PRESET)
        recipe["colors"] = (color, tuple(min(255, channel + 40) for channel in color))
        recipe["count"] = (14, 20)
        self._spawn_with_recipe(recipe, position, None)

    # -- Simulation and rendering --------------------------------------------

    def update(self, dt: float) -> None:
        """Advance every particle and drop the expired ones.

        Args:
            dt: Elapsed seconds since the previous frame.
        """
        self._particles = [particle for particle in self._particles if particle.update(dt)]

    def draw(self, surface: pygame.Surface, offset: Position = (0.0, 0.0)) -> None:
        """Draw all particles onto ``surface``, shifted by ``offset`` (screen shake)."""
        for particle in self._particles:
            particle.draw(surface, offset)
