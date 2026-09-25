import pygame
import random
import math
from config import ELEMENTS, RULES, WIDTH, HEIGHT, ENERGY_REGEN, POWER_UP_SPAWN_INTERVAL
from theme import get_font, ELEMENT_THEMES, BG_DARK, BG_PANEL, BG_PANEL_HOVER, TEXT_LIGHT, TEXT_MUTED, ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_SUCCESS, ACCENT_DANGER, ACCENT_WARNING
from ui import Button, Bar, draw_gradient_rect, draw_glow_circle, draw_element_icon, ease_out_cubic
from game_logic import GameSession
from ai_opponent import AIOpponent
from power_ups import PowerUp
from particle_system import ParticleSystem

class BackgroundParticle:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.uniform(1, 3)
        self.speed = random.uniform(0.2, 1.0)
        self.alpha = random.randint(50, 180)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):
        s = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, self.alpha), (int(self.size), int(self.size)), int(self.size))
        surface.blit(s, (self.x, self.y))


class StateMachine:
    def __init__(self):
        self.states = {}
        self.current_state = None

    def add_state(self, name, state):
        self.states[name] = state

    def change_state(self, name, **kwargs):
        if self.current_state:
            self.current_state.exit()
        self.current_state = self.states.get(name)
        if self.current_state:
            # Ensure enter method is called with kwargs
            self.current_state.enter(**kwargs)

    def handle_event(self, event):
        if self.current_state:
            self.current_state.handle_event(event)

    def update(self):
        if self.current_state:
            self.current_state.update()

    def draw(self, surface):
        if self.current_state:
            self.current_state.draw(surface)


class BaseState:
    def __init__(self, machine):
        self.machine = machine
        self.bg_particles = [BackgroundParticle() for _ in range(60)]

    def enter(self, **kwargs):
        """Called when the state is entered."""
        pass

    def exit(self):
        """Called when the state is exited."""
        pass

    def update(self):
        """Updates the state logic."""
        pass

    def handle_event(self, event):
        """Handles pygame events."""
        pass

    def draw(self, surface):
        """Draws the state to the surface."""
        pass

    def update_bg(self):
        for p in self.bg_particles:
            p.update()

    def draw_bg(self, surface):
        surface.fill(BG_DARK)
        for p in self.bg_particles:
            p.draw(surface)


class MenuState(BaseState):
    def __init__(self, machine):
        super().__init__(machine)
        self.title_font = get_font(64, bold=True)
        self.subtitle_font = get_font(24)
        self.play_btn = Button(WIDTH // 2 - 150, HEIGHT // 2 - 20, 300, 70, "Start Game", font=get_font(28, bold=True))
        self.help_btn = Button(WIDTH // 2 - 150, HEIGHT // 2 + 70, 300, 70, "How to Play", font=get_font(28, bold=True))
        self.quit_btn = Button(WIDTH // 2 - 150, HEIGHT // 2 + 160, 300, 70, "Exit Game", font=get_font(28, bold=True))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.play_btn.update(pos, True):
                self.machine.change_state("mode_select")
            elif self.help_btn.update(pos, True):
                self.machine.change_state("help")
            elif self.quit_btn.update(pos, True):
                pygame.quit()
                import sys
                sys.exit(0)

    def update(self):
        self.update_bg()
        pos = pygame.mouse.get_pos()
        self.play_btn.update(pos, False)
        self.help_btn.update(pos, False)
        self.quit_btn.update(pos, False)

    def draw(self, surface):
        self.draw_bg(surface)

        draw_glow_circle(surface, (WIDTH // 2 + 100, HEIGHT // 2 - 200), 180, ACCENT_PRIMARY, intensity=5)
        draw_glow_circle(surface, (WIDTH // 2 - 200, HEIGHT // 2 + 180), 140, ACCENT_SECONDARY, intensity=4)

        title = self.title_font.render("Elemental Arena", True, TEXT_LIGHT)
        subtitle = self.subtitle_font.render("The Ultimate RPS Experience", True, TEXT_MUTED)

        surface.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 140)))
        surface.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 90)))

        self.play_btn.draw(surface)
        self.help_btn.draw(surface)
        self.quit_btn.draw(surface)


class ModeSelectState(BaseState):
    def __init__(self, machine):
        super().__init__(machine)
        self.font = get_font(38, bold=True)
        self.btn_bo3 = Button(WIDTH // 2 - 200, HEIGHT // 2 - 60, 400, 70, "Best of 3 Rounds", font=get_font(28, bold=True))
        self.btn_bo5 = Button(WIDTH // 2 - 200, HEIGHT // 2 + 30, 400, 70, "Best of 5 Rounds", font=get_font(28, bold=True))
        self.btn_back = Button(WIDTH // 2 - 200, HEIGHT // 2 + 150, 400, 60, "Back to Menu", font=get_font(24, bold=True))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.btn_bo3.update(pos, True):
                self.machine.change_state("battle", best_of=3)
            elif self.btn_bo5.update(pos, True):
                self.machine.change_state("battle", best_of=5)
            elif self.btn_back.update(pos, True):
                self.machine.change_state("menu")

    def update(self):
        self.update_bg()
        pos = pygame.mouse.get_pos()
        self.btn_bo3.update(pos, False)
        self.btn_bo5.update(pos, False)
        self.btn_back.update(pos, False)

    def draw(self, surface):
        self.draw_bg(surface)
        title = self.font.render("Select Match Mode", True, TEXT_LIGHT)
        surface.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150)))

        self.btn_bo3.draw(surface)
        self.btn_bo5.draw(surface)
        self.btn_back.draw(surface)


class HelpState(BaseState):
    def __init__(self, machine):
        super().__init__(machine)
        self.title_font = get_font(40, bold=True)
        self.element_name_font = get_font(24, bold=True)
        self.rule_text_font = get_font(16)
        self.back_btn = Button(WIDTH // 2 - 180, HEIGHT - 80, 360, 60, "Back to Menu", font=get_font(24, bold=True))

        self.element_cards = []
        card_w, card_h = 280, 180
        start_x = (WIDTH - (3 * (card_w + 30))) // 2
        start_y = 120
        for i, elem in enumerate(ELEMENTS):
            x = start_x + (i % 3) * (card_w + 30)
            y = start_y + (i // 3) * (card_h + 30)
            self.element_cards.append({"element": elem, "rect": pygame.Rect(x, y, card_w, card_h), "hovered": False})

        self.hover_element = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn.update(event.pos, True):
                self.machine.change_state("menu")

    def update(self):
        self.update_bg()
        mouse_pos = pygame.mouse.get_pos()
        self.back_btn.update(mouse_pos, False)

        self.hover_element = None
        for card in self.element_cards:
            card["hovered"] = card["rect"].collidepoint(mouse_pos)
            if card["hovered"]:
                self.hover_element = card["element"]

    def draw(self, surface):
        self.draw_bg(surface)
        title = self.title_font.render("Elemental Rules & Guide", True, TEXT_LIGHT)
        surface.blit(title, title.get_rect(center=(WIDTH // 2, 50)))

        for card_data in self.element_cards:
            elem = card_data["element"]
            rect = card_data["rect"]
            is_hovered = card_data["hovered"]

            theme = ELEMENT_THEMES[elem]
            bg_top = theme["primary"]
            bg_bot = theme["gradient"]

            draw_gradient_rect(surface, rect, bg_top, bg_bot, radius=15)
            border_color = theme["glow"] if is_hovered else (71, 85, 105)
            pygame.draw.rect(surface, border_color, rect, width=2, border_radius=15)

            name_surf = self.element_name_font.render(RULES[elem]["name"], True, TEXT_LIGHT)
            surface.blit(name_surf, name_surf.get_rect(center=(rect.centerx, rect.y + 35)))
            draw_element_icon(surface, elem, (rect.centerx, rect.y + 85), 35, is_enabled=True)

            if self.hover_element == elem:
                beats = ", ".join([RULES[b]["name"] for b in RULES[elem]["beats"]])
                loses = ", ".join([RULES[l]["name"] for l in RULES[elem]["loses_to"]])

                beats_surf = self.rule_text_font.render(f"BEATS: {beats}", True, ACCENT_SUCCESS)
                loses_surf = self.rule_text_font.render(f"LOSES: {loses}", True, ACCENT_DANGER)

                surface.blit(beats_surf, beats_surf.get_rect(center=(rect.centerx, rect.y + 130)))
                surface.blit(loses_surf, loses_surf.get_rect(center=(rect.centerx, rect.y + 155)))

        self.back_btn.draw(surface)


class BattleState(BaseState):
    def __init__(self, machine):
        super().__init__(machine)
        self.session = None
        self.ai = AIOpponent()
        self.particles = ParticleSystem()
        self.power_ups = []
        self.active_power_up_buffs = {}
        self.round_count = 0

        self.p_hp_bar = Bar(50, 30, 350, 28, 100, ACCENT_SUCCESS, bg_color=(20, 27, 45))
        self.ai_hp_bar = Bar(WIDTH - 400, 30, 350, 28, 100, ACCENT_DANGER, bg_color=(20, 27, 45))
        self.p_energy_bar = Bar(50, 70, 350, 20, 100, ACCENT_PRIMARY, bg_color=(20, 27, 45))
        self.ai_energy_bar = Bar(WIDTH - 400, 70, 350, 20, 100, ACCENT_WARNING, bg_color=(20, 27, 45))

        self.selected_choice = None
        self.ai_choice_display = None
        self.result_display_text = ""
        self.result_color = TEXT_LIGHT
        self.result_timer = 0
        self.hint_text = ""

        self.clash_animation_start_time = 0
        self.clash_duration = 900  # ms

    def enter(self, best_of=3):
        self.session = GameSession(best_of=best_of)
        self.ai = AIOpponent()
        self.particles = ParticleSystem()
        self.power_ups = []
        self.active_power_up_buffs = {}
        self.selected_choice = None
        self.ai_choice_display = None
        self.result_display_text = ""
        self.hint_text = ""
        self.round_count = 0

        self.p_hp_bar.set_value(self.session.player_hp)
        self.ai_hp_bar.set_value(self.session.ai_hp)
        self.p_energy_bar.set_value(self.session.player_energy)
        self.ai_energy_bar.set_value(self.session.ai_energy)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            for pu in self.power_ups[:]:
                if pu.is_clicked(pos):
                    self.apply_power_up(pu.type)
                    self.power_ups.remove(pu)
                    return

            if self.result_display_text != "":
                return

            card_w, card_h = 150, 160
            start_x = (WIDTH - (6 * 165)) // 2
            y = HEIGHT - 190

            for i, elem in enumerate(ELEMENTS):
                cx = start_x + i * 165
                rect = pygame.Rect(cx, y, card_w, card_h)
                if rect.collidepoint(pos):
                    if self.session.can_afford(elem):
                        self.execute_round(elem)
                    else:
                        self.hint_text = "Not enough energy for this element!"
                    break

    def apply_power_up(self, pu_type):
        if pu_type == "double_damage":
            self.active_power_up_buffs['player_double_damage'] = True
            self.hint_text = "Power-up Activated: Double Damage next round!"
        elif pu_type == "full_energy":
            self.session.player_energy = 100
            self.hint_text = "Power-up Activated: Full Energy Restored!"
        elif pu_type == "shield":
            self.active_power_up_buffs['player_shield'] = True
            self.hint_text = "Power-up Activated: One-time Shield!"
        elif pu_type == "hint":
            h = self.ai.get_hint()
            self.hint_text = f"AI Hint: Next move is a {h.upper()} element."

    def execute_round(self, player_choice):
        self.round_count += 1
        self.selected_choice = player_choice
        ai_choice = self.ai.choose_move(self.session.ai_energy)
        self.ai.record_player_choice(player_choice)

        res = self.session.process_round(player_choice, ai_choice, self.active_power_up_buffs)
        self.ai_choice_display = ai_choice

        if res["result"] == 'win':
            self.result_display_text = f"VICTORY! +{res['player_dmg']} DMG"
            self.result_color = ACCENT_SUCCESS
            self.session.player_wins += 1
            self.particles.emit(WIDTH // 2, HEIGHT // 2, player_choice, count=40)
        elif res["result"] == 'lose':
            if res["shield_used"]:
                self.result_display_text = "SHIELD BLOCKED DAMAGE!"
                self.result_color = ACCENT_PRIMARY
            else:
                self.result_display_text = f"DEFEAT! -{res['ai_dmg']} DMG"
                self.result_color = ACCENT_DANGER
            self.session.ai_wins += 1
            self.particles.emit(WIDTH // 2, HEIGHT // 2, ai_choice, count=40)
        else:
            self.result_display_text = "ROUND TIE!"
            self.result_color = ACCENT_WARNING
            self.particles.emit(WIDTH // 2, HEIGHT // 2, "paper", count=20) # Neutral particles for tie

        if self.active_power_up_buffs.get('player_double_damage'):
            self.active_power_up_buffs['player_double_damage'] = False
        if res.get('shield_used'):
            self.active_power_up_buffs['player_shield'] = False

        self.clash_animation_start_time = pygame.time.get_ticks()
        self.result_timer = pygame.time.get_ticks() + 2500

        self.session.regenerate_energy(ENERGY_REGEN)

        if self.round_count % POWER_UP_SPAWN_INTERVAL == 0 and random.random() < 0.6 and len(self.power_ups) < 2:
            self.power_ups.append(PowerUp())

    def update(self):
        self.update_bg()
        self.p_hp_bar.set_value(self.session.player_hp)
        self.ai_hp_bar.set_value(self.session.ai_hp)
        self.p_energy_bar.set_value(self.session.player_energy)
        self.ai_energy_bar.set_value(self.session.ai_energy)

        self.p_hp_bar.update()
        self.ai_hp_bar.update()
        self.p_energy_bar.update()
        self.ai_energy_bar.update()
        self.particles.update()

        for pu in self.power_ups[:]:
            if not pu.update():
                self.power_ups.remove(pu)

        if self.result_display_text != "" and pygame.time.get_ticks() > self.result_timer:
            self.result_display_text = ""
            self.selected_choice = None
            self.ai_choice_display = None
            self.hint_text = ""
            if self.session.is_match_over():
                winner = self.session.get_match_winner()
                self.machine.change_state("game_over", winner=winner, session=self.session)

    def draw(self, surface):
        self.draw_bg(surface)

        # Header HUD
        self.p_hp_bar.draw(surface, "Your HP")
        self.ai_hp_bar.draw(surface, "AI HP")
        self.p_energy_bar.draw(surface, "Energy")
        self.ai_energy_bar.draw(surface, "AI Energy")

        # Score display
        score_font = get_font(28, bold=True)
        score_txt = score_font.render(f"Score: You {self.session.player_wins} - {self.session.ai_wins} AI", True, TEXT_LIGHT)
        surface.blit(score_txt, score_txt.get_rect(center=(WIDTH // 2, 45)))

        # Combo display
        if self.session.player_combo > 0:
            combo_font = get_font(22 + self.session.player_combo * 2, bold=True)
            combo_color = (min(255, 200 + self.session.player_combo * 10), max(0, 100 - self.session.player_combo * 10), 0)
            combo_txt = combo_font.render(f"COMBO! {self.session.player_combo}x", True, combo_color)
            combo_rect = combo_txt.get_rect(center=(WIDTH // 2, 100))
            draw_glow_circle(surface, combo_rect.center, combo_rect.width // 4, combo_color, intensity=2)
            surface.blit(combo_txt, combo_rect)

        if self.hint_text:
            hint_surf = get_font(20).render(self.hint_text, True, ACCENT_WARNING)
            surface.blit(hint_surf, hint_surf.get_rect(center=(WIDTH // 2, 140)))

        # Enhanced Arena Clash Animation
        if self.selected_choice and self.ai_choice_display:
            elapsed = pygame.time.get_ticks() - self.clash_animation_start_time
            t = min(1, elapsed / self.clash_duration)
            eased_t = ease_out_cubic(t)

            # Player Choice Movement (from left to center)
            p_start_x, p_start_y = WIDTH // 2 - 350, HEIGHT // 2
            p_end_x, p_end_y = WIDTH // 2 - 90, HEIGHT // 2
            current_p_x = p_start_x + (p_end_x - p_start_x) * eased_t
            current_p_y = p_start_y + (p_end_y - p_start_y) * eased_t

            # AI Choice Movement (from right to center)
            ai_start_x, ai_start_y = WIDTH // 2 + 350, HEIGHT // 2
            ai_end_x, ai_end_y = WIDTH // 2 + 90, HEIGHT // 2
            current_ai_x = ai_start_x + (ai_end_x - ai_start_x) * eased_t
            current_ai_y = ai_start_y + (ai_end_y - ai_start_y) * eased_t

            # Scale elements after clash
            p_scale = 1.0
            ai_scale = 1.0
            if t >= 1.0:
                if self.result_display_text.startswith("VICTORY"):
                    p_scale = 1.3
                elif self.result_display_text.startswith("DEFEAT"):
                    ai_scale = 1.3

            self.draw_clash_card(surface, self.selected_choice, (current_p_x, current_p_y), scale=p_scale)
            self.draw_clash_card(surface, self.ai_choice_display, (current_ai_x, current_ai_y), scale=ai_scale)

            # Shockwave Ring at impact point (only during clash)
            if t > 0.4 and t < 0.8:
                ring_radius = int(80 + (t - 0.4) * 200)
                ring_alpha = max(0, int(200 * (1 - (t - 0.4) / 0.4))) # Fade out
                ring_surf = pygame.Surface((ring_radius * 2, ring_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (*self.result_color, ring_alpha), (ring_radius, ring_radius), ring_radius, width=4)
                surface.blit(ring_surf, (WIDTH // 2 - ring_radius, HEIGHT // 2 - ring_radius))
                draw_glow_circle(surface, (WIDTH // 2, HEIGHT // 2), 90, self.result_color, intensity=4)

            if t >= 0.9 and self.result_display_text != "":
                res_font = get_font(46, bold=True)
                res_surf = res_font.render(self.result_display_text, True, self.result_color)
                surface.blit(res_surf, res_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 160)))

        # Draw Power-Ups
        for pu in self.power_ups:
            info = pu.get_display_info()
            current_y = pu.y + pu.float_offset
            draw_glow_circle(surface, (pu.x, int(current_y)), pu.radius, info["color"], intensity=3)
            pygame.draw.circle(surface, info["color"], (pu.x, int(current_y)), pu.radius)
            sym_font = get_font(20, bold=True)
            sym_surf = sym_font.render(info["symbol"], True, TEXT_LIGHT)
            surface.blit(sym_surf, sym_surf.get_rect(center=(pu.x, int(current_y))))

        # Element Cards at bottom
        card_w, card_h = 150, 160
        start_x = (WIDTH - (6 * 165)) // 2
        y = HEIGHT - 190
        mouse_pos = pygame.mouse.get_pos()

        for i, elem in enumerate(ELEMENTS):
            cx = start_x + i * 165
            rect = pygame.Rect(cx, y, card_w, card_h)
            hovered = rect.collidepoint(mouse_pos)
            can_afford = self.session.can_afford(elem)

            scale_factor = 1.0
            lift_offset = 0
            if hovered and can_afford and self.selected_choice is None:
                scale_factor = 1.08
                lift_offset = -10
                draw_glow_circle(surface, (rect.centerx, rect.centery + lift_offset), int(card_w * 0.6), ELEMENT_THEMES[elem]["glow"], intensity=2)

            self.draw_element_card(surface, elem, (rect.centerx, rect.centery + lift_offset),
                                   scale=scale_factor, is_selected=(self.selected_choice == elem),
                                   is_enabled=can_afford, hovered=hovered)

        self.particles.draw(surface)

    def draw_element_card(self, surface, element, center_pos, scale=1.0, is_selected=False, is_enabled=True, hovered=False):
        card_w, card_h = int(150 * scale), int(160 * scale)
        rect = pygame.Rect(0, 0, card_w, card_h)
        rect.center = center_pos

        theme = ELEMENT_THEMES[element]
        bg_top = theme["primary"]
        bg_bot = theme["gradient"]

        current_bg_top = bg_top if is_enabled else (bg_top[0]//3, bg_top[1]//3, bg_top[2]//3)
        current_bg_bot = bg_bot if is_enabled else (bg_bot[0]//3, bg_bot[1]//3, bg_bot[2]//3)

        draw_gradient_rect(surface, rect, current_bg_top, current_bg_bot, radius=14)

        border_color = theme["glow"] if hovered or is_selected else (71, 85, 105)
        if not is_enabled:
            border_color = (border_color[0]//2, border_color[1]//2, border_color[2]//2)
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=14)

        if is_selected:
            pulse_alpha = int(100 + 50 * math.sin(pygame.time.get_ticks() * 0.008))
            draw_glow_circle(surface, center_pos, rect.width // 2, theme["glow"], intensity=2)

        draw_element_icon(surface, element, (rect.centerx, rect.y + 55), int(38 * scale))

        name_font_size = int(22 * scale)
        name_font = get_font(name_font_size, bold=True)
        name_surf = name_font.render(RULES[element]["name"], True, TEXT_LIGHT if is_enabled else TEXT_MUTED)
        name_rect = name_surf.get_rect(center=(rect.centerx, rect.y + card_h - (35 * scale)))
        surface.blit(name_surf, name_rect)

        if not is_enabled:
            lock_font = get_font(int(14 * scale))
            lock_surf = lock_font.render(f"Need {RULES[element]['energy_cost']} En", True, ACCENT_DANGER)
            surface.blit(lock_surf, lock_surf.get_rect(center=(rect.centerx, rect.y + card_h - (12 * scale))))

    def draw_clash_card(self, surface, element, center_pos, scale=1.0):
        card_w, card_h = int(140 * scale), int(150 * scale)
        rect = pygame.Rect(0, 0, card_w, card_h)
        rect.center = center_pos

        theme = ELEMENT_THEMES[element]
        draw_gradient_rect(surface, rect, theme["primary"], theme["gradient"], radius=16)
        pygame.draw.rect(surface, theme["glow"], rect, width=3, border_radius=16)

        draw_element_icon(surface, element, (rect.centerx, rect.centery - 15), int(45 * scale))

        name_font = get_font(20, bold=True)
        name_surf = name_font.render(RULES[element]["name"], True, TEXT_LIGHT)
        surface.blit(name_surf, name_surf.get_rect(center=(rect.centerx, rect.y + card_h - 25)))


class GameOverState(BaseState):
    def __init__(self, machine):
        super().__init__(machine)
        self.font = get_font(52, bold=True)
        self.sub_font = get_font(28)
        self.menu_btn = Button(WIDTH // 2 - 180, HEIGHT // 2 + 100, 360, 70, "Return to Main Menu", font=get_font(28, bold=True))
        self.winner = ""
        self.session = None

    def enter(self, winner="player", session=None):
        self.winner = winner
        self.session = session

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu_btn.update(event.pos, True):
                self.machine.change_state("menu")

    def update(self):
        self.update_bg()
        self.menu_btn.update(pygame.mouse.get_pos(), False)

    def draw(self, surface):
        self.draw_bg(surface)

        msg = "VICTORY! You won the match!" if self.winner == "player" else ("DEFEAT! AI won the match." if self.winner == "ai" else "IT'S A TIE!")
        color = ACCENT_SUCCESS if self.winner == "player" else (ACCENT_DANGER if self.winner == "ai" else ACCENT_WARNING)

        t_surf = self.font.render(msg, True, color)
        surface.blit(t_surf, t_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80)))

        if self.session:
            score_txt = f"Final Score: You {self.session.player_wins} - {self.session.ai_wins} AI"
            s_surf = self.sub_font.render(score_txt, True, TEXT_LIGHT)
            surface.blit(s_surf, s_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        self.menu_btn.draw(surface)
