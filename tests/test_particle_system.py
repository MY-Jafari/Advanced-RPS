"""Unit tests for the particle engine (no pygame display required)."""

import os
import random

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # headless-safe rendering

import config
from particle_system import Particle, ParticleSystem


@pytest.fixture()
def surface():
    """A real (but headless) pygame surface for draw-call smoke tests."""
    pygame.init()
    yield pygame.Surface((320, 240))
    pygame.quit()


# ---------------------------------------------------------------------------
# Single particle physics
# ---------------------------------------------------------------------------


class TestParticlePhysics:
    """Integration of the delta-time step: aging, gravity, drag, sway."""

    def test_particle_expires_after_lifetime(self):
        particle = Particle(0, 0, 0, 0, lifetime=0.5, size=3, color=(255, 255, 255))
        assert particle.update(0.2) is True
        assert particle.update(0.2) is True
        assert particle.update(0.2) is False  # 0.6s > 0.5s lifetime

    def test_life_fraction_decays(self):
        particle = Particle(0, 0, 0, 0, lifetime=1.0, size=3, color=(255, 255, 255))
        assert particle.life_fraction == pytest.approx(1.0)
        particle.update(0.25)
        assert particle.life_fraction == pytest.approx(0.75)

    def test_gravity_pulls_down(self):
        particle = Particle(0, 0, 0, 0, lifetime=5.0, size=3, color=(255, 255, 255), gravity_scale=1.0)
        particle.update(0.5)
        assert particle.vy == pytest.approx(config.PARTICLE_GRAVITY * 0.5)

    def test_negative_gravity_scale_floats_up(self):
        particle = Particle(0, 0, 0, 0, lifetime=5.0, size=3, color=(255, 255, 255), gravity_scale=-1.0)
        particle.update(0.5)
        assert particle.vy < 0

    def test_drag_slows_motion(self):
        particle = Particle(0, 0, 100, 0, lifetime=5.0, size=3, color=(255, 255, 255), drag=2.0)
        particle.update(0.1)
        assert particle.vx < 100

    def test_sway_pushes_horizontally(self):
        particle = Particle(0, 0, 0, 0, lifetime=5.0, size=3, color=(255, 255, 255), sway=20.0)
        particle.update(0.1)  # sin(phase) > 0 shortly after phase 0
        assert particle.vx > 0

    def test_zero_sway_never_pushes(self):
        particle = Particle(0, 0, 0, 0, lifetime=5.0, size=3, color=(255, 255, 255))
        particle.update(0.1)
        assert particle.vx == 0

    def test_position_integrates_velocity(self):
        """Semi-implicit Euler: velocity updates first, then position uses it."""
        particle = Particle(0, 0, 50, -20, lifetime=5.0, size=3, color=(255, 255, 255))
        particle.update(0.2)
        assert particle.x == pytest.approx(10.0)
        assert particle.y == pytest.approx((-20 + config.PARTICLE_GRAVITY * 0.2) * 0.2)


# ---------------------------------------------------------------------------
# Rendering smoke tests (headless surface)
# ---------------------------------------------------------------------------


class TestParticleRendering:
    """Draw calls must survive on a real surface without a display."""

    def test_draw_circle_and_square_shapes(self, surface):
        for shape in ("circle", "square", "flake"):
            particle = Particle(50, 50, 0, 0, lifetime=1.0, size=4, color=(200, 100, 50), shape=shape)
            particle.draw(surface)
        particle = Particle(50, 50, 0, 0, lifetime=1.0, size=4, color=(200, 100, 50))
        particle.draw(surface, offset=(10, -5))  # shake offset path

    def test_draw_with_dead_fraction_clamps(self, surface):
        particle = Particle(50, 50, 0, 0, lifetime=0.001, size=4, color=(200, 100, 50))
        particle.update(1.0)  # expired; life_fraction clamps to 0
        particle.draw(surface)  # must not raise on radius < 1


# ---------------------------------------------------------------------------
# System spawning and lifecycle
# ---------------------------------------------------------------------------


class TestParticleSystem:
    """Bursts, presets, cap eviction and updates."""

    def test_burst_spawns_within_recipe_range(self):
        system = ParticleSystem(random.Random(1))
        recipe = config.PARTICLE_PRESETS["fire"]
        system.burst_for_element("fire", (100, 100))
        assert recipe["count"][0] <= len(system) <= recipe["count"][1]

    def test_every_element_has_a_working_preset(self):
        for element in config.ELEMENTS:
            system = ParticleSystem(random.Random(2))
            system.burst_for_element(element, (100, 100))
            assert len(system) > 0
            system.clear()

    def test_direction_biases_velocities(self):
        system = ParticleSystem(random.Random(3))
        system.burst_for_element("rock", (100, 100), direction=(1.0, 0.0))
        rightward = sum(1 for particle in system._particles if particle.vx > 0)
        assert rightward > len(system) / 2  # bias launches toward +x

    def test_impact_and_pickup_bursts_spawn(self):
        system = ParticleSystem(random.Random(4))
        system.impact_burst((100, 100))
        assert len(system) > 0
        system.clear()
        system.pickup_burst((100, 100), (90, 160, 255))
        assert len(system) > 0

    def test_particle_cap_evicts_oldest(self):
        system = ParticleSystem(random.Random(5))
        for _ in range(30):  # far more than MAX_PARTICLES at once
            system.impact_burst((100, 100))
        assert len(system) == config.MAX_PARTICLES

    def test_update_removes_expired_particles(self):
        system = ParticleSystem(random.Random(6))
        system.impact_burst((100, 100))
        assert len(system) > 0
        system.update(30.0)  # longer than any preset lifetime
        assert len(system) == 0

    def test_clear_empties_immediately(self):
        system = ParticleSystem(random.Random(7))
        system.impact_burst((100, 100))
        system.clear()
        assert len(system) == 0

    def test_draw_all_particles(self, surface):
        system = ParticleSystem(random.Random(8))
        system.burst_for_element("water", (100, 100))
        system.impact_burst((100, 100))
        system.draw(surface, offset=(3, 3))
