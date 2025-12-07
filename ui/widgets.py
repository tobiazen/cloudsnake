"""UI Widgets for CloudSnake client - InputBox and Button components"""
import pygame
from typing import Any, Tuple
from config.constants import BORDER_COLOR, CYAN, PANEL_BG, TEXT_COLOR, WHITE, BLUE
from utils.helpers import get_unicode_font


class InputBox:
    """Simple input box for text entry"""
    
    def __init__(self, x: int, y: int, w: int, h: int, text: str = '') -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.color = BORDER_COLOR
        self.text = text
        self.font = get_unicode_font(23)
        self.active = False
        
    def handle_event(self, event: Any) -> bool:
        """Handle input events. Returns True if Enter was pressed."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = CYAN if self.active else BORDER_COLOR
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return False
    
    def draw(self, screen: Any) -> None:
        """Draw the input box on screen"""
        # Draw box background
        pygame.draw.rect(screen, PANEL_BG, self.rect)
        # Draw border
        border_color = CYAN if self.active else self.color
        pygame.draw.rect(screen, border_color, self.rect, 2)
        # Draw text
        txt_surface = self.font.render(self.text, True, TEXT_COLOR)
        screen.blit(txt_surface, (self.rect.x + 5, self.rect.y + 5))


class Button:
    """Simple button widget with hover effect"""
    
    def __init__(self, x: int, y: int, w: int, h: int, text: str, color: Tuple[int, int, int] = BLUE) -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = (min(color[0] + 30, 255), min(color[1] + 30, 255), min(color[2] + 30, 255))
        self.font = get_unicode_font(23)
        self.hovered = False
        
    def handle_event(self, event: Any) -> bool:
        """Handle mouse events. Returns True if button was clicked."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False
    
    def draw(self, screen: Any) -> None:
        """Draw the button on screen with shadow effect"""
        color = self.hover_color if self.hovered else self.color
        # Draw button with shadow effect
        shadow_rect = pygame.Rect(self.rect.x + 2, self.rect.y + 2, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, (0, 0, 0, 50), shadow_rect)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BORDER_COLOR, self.rect, 2)
        
        txt_surface = self.font.render(self.text, True, WHITE)
        txt_rect = txt_surface.get_rect(center=self.rect.center)
        screen.blit(txt_surface, txt_rect)
