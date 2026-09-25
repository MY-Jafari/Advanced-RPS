import pygame
import math
from theme import get_font, BG_PANEL, BG_PANEL_HOVER, TEXT_LIGHT, TEXT_MUTED, ACCENT_PRIMARY, ELEMENT_THEMES
from image_manager import get_element_image, are_images_loaded

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

def ease_in_out_quad(t):
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2

def draw_gradient_rect(surface, rect, color_top, color_bottom, radius=0):
    """Draws a vertical gradient rectangle with optional rounded corners."""
    x, y, w, h = rect
    if w < 1 or h < 1:
        return

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(h):
        t = i / max(1, (h - 1))
        r = int(color_top[0] * (1 - t) + color_bottom[0] * t)
        g = int(color_top[1] * (1 - t) + color_bottom[1] * t)
        b = int(color_top[2] * (1 - t) + color_bottom[2] * t)
        pygame.draw.line(surf, (r, g, b), (0, i), (w, i))

    if radius > 0:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

    surface.blit(surf, (x, y))

def draw_glow_circle(surface, center, radius, color, intensity=3):
    """Draws a glowing aura circle."""
    cx, cy = center
    for i in range(intensity, 0, -1):
        r = radius + i * 5
        alpha = int(35 / i)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (color[0], color[1], color[2], alpha), (r, r), r)
        surface.blit(s, (cx - r, cy - r))

def draw_element_icon(surface, element, center, size, is_enabled=True):
    """Draws element icon using loaded PNG images. Falls back to procedural drawing if images not loaded."""
    if are_images_loaded():
        image = get_element_image(element, size)
        if image:
            rect = image.get_rect(center=center)
            surface.blit(image, rect)

            if not is_enabled:
                # Apply a dimming overlay if the element is disabled
                overlay = pygame.Surface(image.get_size(), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150)) # Black, semi-transparent
                surface.blit(overlay, rect)
            return

    # Fallback: Procedural drawing for when images are not loaded
    cx, cy = center
    theme = ELEMENT_THEMES.get(element, {"primary": (255, 255, 255), "glow": (200, 200, 200)})
    primary = theme["primary"] if is_enabled else (theme["primary"][0]//3, theme["primary"][1]//3, theme["primary"][2]//3)
    glow_color = theme["glow"] if is_enabled else (theme["glow"][0]//3, theme["glow"][1]//3, theme["glow"][2]//3)
    detail_color = (40, 40, 40) if is_enabled else (20, 20, 20)

    if element == "rock":
        points = [
            (cx - size * 0.5, cy + size * 0.4),
            (cx - size * 0.7, cy - size * 0.1),
            (cx - size * 0.2, cy - size * 0.6),
            (cx + size * 0.4, cy - size * 0.5),
            (cx + size * 0.7, cy + size * 0.1),
            (cx + size * 0.3, cy + size * 0.6)
        ]
        pygame.draw.polygon(surface, primary, points)
        pygame.draw.polygon(surface, glow_color, points, width=int(size * 0.08))
        pygame.draw.line(surface, detail_color, (cx - size * 0.2, cy - size * 0.2), (cx + size * 0.1, cy + size * 0.1), int(size * 0.08))

    elif element == "paper":
        rect_outline = pygame.Rect(cx - size * 0.45, cy - size * 0.55, size * 0.9, size * 1.1)
        draw_gradient_rect(surface, rect_outline, primary, (max(0, primary[0]-20), max(0, primary[1]-20), max(0, primary[2]-20)), radius=4)
        pygame.draw.rect(surface, glow_color, rect_outline, width=int(size * 0.08), border_radius=4)
        fold_pts = [
            (cx + size * 0.45, cy - size * 0.3),
            (cx + size * 0.15, cy - size * 0.55),
            (cx + size * 0.45, cy - size * 0.55)
        ]
        pygame.draw.polygon(surface, (200, 200, 200) if is_enabled else (100,100,100), fold_pts)
        pygame.draw.line(surface, detail_color, (cx - size * 0.25, cy - size * 0.2), (cx + size * 0.25, cy - size * 0.2), int(size * 0.05))
        pygame.draw.line(surface, detail_color, (cx - size * 0.25, cy), (cx + size * 0.25, cy), int(size * 0.05))

    elif element == "scissors":
        blade_color = (200, 200, 200) if is_enabled else (100, 100, 100)
        handle_color_a = (50, 150, 200) if is_enabled else (25, 75, 100)
        handle_color_b = (200, 100, 50) if is_enabled else (100, 50, 25)

        pygame.draw.line(surface, blade_color, (cx - size * 0.3, cy + size * 0.3), (cx + size * 0.3, cy - size * 0.5), int(size * 0.1))
        pygame.draw.line(surface, blade_color, (cx + size * 0.3, cy + size * 0.3), (cx - size * 0.3, cy - size * 0.5), int(size * 0.1))
        pygame.draw.circle(surface, (100, 100, 100), (cx, cy - size * 0.1), int(size * 0.1))
        pygame.draw.circle(surface, handle_color_a, (cx - size * 0.4, cy + size * 0.4), int(size * 0.2), width=int(size * 0.08))
        pygame.draw.circle(surface, handle_color_b, (cx + size * 0.4, cy + size * 0.4), int(size * 0.2), width=int(size * 0.08))

    elif element == "fire":
        flame_color_outer = primary
        flame_color_inner = (255, 200, 100) if is_enabled else (120, 100, 50)

        points_outer = [
            (cx, cy - size * 0.6),
            (cx - size * 0.4, cy + size * 0.2),
            (cx, cy + size * 0.5),
            (cx + size * 0.4, cy + size * 0.2)
        ]
        pygame.draw.polygon(surface, flame_color_outer, points_outer)

        points_inner = [
            (cx, cy - size * 0.3),
            (cx - size * 0.2, cy + size * 0.2),
            (cx + size * 0.2, cy + size * 0.2)
        ]
        pygame.draw.polygon(surface, flame_color_inner, points_inner)
        draw_glow_circle(surface, center, size * 0.4, glow_color, intensity=2)

    elif element == "water":
        drop_color = primary
        highlight_color = (200, 240, 255) if is_enabled else (100, 120, 128)
        outline_color = (max(0, primary[0]-40), max(0, primary[1]-40), max(0, primary[2]-40))

        points = [
            (cx, cy - size * 0.6),
            (cx - size * 0.4, cy),
            (cx, cy + size * 0.6),
            (cx + size * 0.4, cy)
        ]
        pygame.draw.polygon(surface, drop_color, points)
        pygame.draw.polygon(surface, outline_color, points, width=int(size * 0.08))
        pygame.draw.circle(surface, highlight_color, (cx - size * 0.1, cy - size * 0.3), int(size * 0.15))
        draw_glow_circle(surface, center, size * 0.5, glow_color, intensity=2)

    elif element == "earth":
        globe_color = primary
        pygame.draw.circle(surface, globe_color, (cx, cy), size * 0.5)
        pygame.draw.circle(surface, glow_color, (cx, cy), size * 0.5, width=int(size * 0.08))
        pygame.draw.ellipse(surface, detail_color, (cx - size * 0.3, cy - size * 0.2, size * 0.6, size * 0.4), 0)
        pygame.draw.ellipse(surface, detail_color, (cx - size * 0.2, cy + size * 0.1, size * 0.4, size * 0.3), 0)

def draw_shockwave_ring(surface, center, current_radius, max_radius, color, thickness, alpha):
    """Draws an expanding shockwave ring."""
    s = pygame.Surface((max_radius * 2, max_radius * 2), pygame.SRCALPHA)
    alpha_color = (color[0], color[1], color[2], alpha)
    pygame.draw.circle(s, alpha_color, (max_radius, max_radius), current_radius, thickness)
    surface.blit(s, (center[0] - max_radius, center[1] - max_radius))


class Button:
    def __init__(self, x, y, w, h, text, font=None, bg_color=BG_PANEL, hover_color=BG_PANEL_HOVER, text_color=TEXT_LIGHT):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font or get_font(20, bold=True)
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.hovered = False

    def update(self, mouse_pos, mouse_clicked):
        self.hovered = self.rect.collidepoint(mouse_pos)
        return self.hovered and mouse_clicked

    def draw(self, surface):
        current_bg = self.hover_color if self.hovered else self.bg_color
        draw_gradient_rect(surface, self.rect, current_bg, (max(0, current_bg[0]-15), max(0, current_bg[1]-15), max(0, current_bg[2]-15)), radius=14)

        border_col = ACCENT_PRIMARY if self.hovered else (71, 85, 105)
        pygame.draw.rect(surface, border_col, self.rect, width=2, border_radius=14)

        txt_surf = self.font.render(self.text, True, self.text_color)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

class Bar:
    """Animated status bar (HP / Energy)."""
    def __init__(self, x, y, w, h, max_val, color, bg_color=(20, 27, 43)):
        self.rect = pygame.Rect(x, y, w, h)
        self.max_val = max_val
        self.current_val = float(max_val)
        self.target_val = float(max_val)
        self.color = color
        self.bg_color = bg_color

    def set_value(self, val):
        self.target_val = max(0, min(self.max_val, val))

    def update(self):
        diff = self.target_val - self.current_val
        self.current_val += diff * 0.15

    def draw(self, surface, label=""):
        # Background
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=10)
        pygame.draw.rect(surface, (51, 65, 85), self.rect, width=1, border_radius=10)

        # Fill
        fill_w = int(self.rect.width * (self.current_val / self.max_val))
        if fill_w > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
            draw_gradient_rect(surface, fill_rect, self.color, (max(0, self.color[0]-50), max(0, self.color[1]-50), max(0, self.color[2]-50)), radius=10)

        # Label & Text
        if label:
            font = get_font(15, bold=True)
            txt = font.render(f"{label}: {int(self.current_val)} / {self.max_val}", True, TEXT_LIGHT)
            surface.blit(txt, (self.rect.x + 12, self.rect.y + (self.rect.height - txt.get_height()) // 2))
