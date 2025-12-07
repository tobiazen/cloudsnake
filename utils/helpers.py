"""Helper utilities for CloudSnake client - fonts, resources, and drawing functions"""
import os
import pygame
from typing import Any

def get_unicode_font(size: int) -> pygame.font.Font:
    """Return a pygame Font with good Unicode coverage (fallbacks to default)."""
    try:
        # Try common Unicode-capable fonts
        font_path = pygame.font.match_font('dejavusans,arial unicode ms,noto sans,liberation sans')
        if font_path:
            return pygame.font.Font(font_path, size)
    except Exception:
        pass
    # Fallback to default font
    return pygame.font.Font(None, size)


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        import sys
        base_path = sys._MEIPASS  # type: ignore
        print(f"DEBUG: Running in PyInstaller bundle, base_path: {base_path}")
    except Exception:
        base_path = os.path.abspath(".")
        print(f"DEBUG: Running in development mode, base_path: {base_path}")
    
    full_path = os.path.join(base_path, relative_path)
    
    # Debug: list what's in the assets directory
    assets_dir = os.path.join(base_path, 'assets')
    if os.path.exists(assets_dir):
        print(f"DEBUG: Contents of assets directory:")
        try:
            for item in os.listdir(assets_dir):
                print(f"  - {item}")
        except Exception as e:
            print(f"  ERROR listing directory: {e}")
    else:
        print(f"DEBUG: Assets directory does not exist at: {assets_dir}")
    
    return full_path


def draw_bullet_icon(screen: Any, x: int, y: int, size: int = 16) -> None:
    """Draw a bullet icon (simple blue/cyan projectile)"""
    center_x = x + size // 2
    center_y = y + size // 2
    
    # Draw elongated bullet shape (vertical ellipse/capsule)
    # Main body - blue
    bullet_width = size // 2
    bullet_height = size - 2
    
    # Draw rounded capsule shape
    top_y = y + 1
    bottom_y = y + bullet_height - 1
    
    # Top rounded part
    pygame.draw.circle(screen, (0, 150, 255), (center_x, top_y + bullet_width // 2), bullet_width // 2)
    # Middle rectangle
    pygame.draw.rect(screen, (0, 150, 255), (center_x - bullet_width // 2, top_y + bullet_width // 2, bullet_width, bullet_height - bullet_width))
    # Bottom flat/pointed part
    pygame.draw.polygon(screen, (0, 120, 200), [
        (center_x - bullet_width // 2, bottom_y - 2),
        (center_x + bullet_width // 2, bottom_y - 2),
        (center_x, bottom_y + 1)
    ])
    
    # Highlight shine
    pygame.draw.circle(screen, (150, 220, 255), (center_x - 1, top_y + 3), 2)


def draw_bomb_icon(screen: Any, x: int, y: int, size: int = 16) -> None:
    """Draw a bomb icon (black sphere with red fuse)"""
    center_x = x + size // 2
    center_y = y + size // 2 + 2
    
    # Bomb body (black circle with gradient effect)
    pygame.draw.circle(screen, (30, 30, 30), (center_x, center_y), size // 2 - 1)
    pygame.draw.circle(screen, (60, 60, 60), (center_x, center_y), size // 2 - 1, 1)
    
    # Shine highlight on bomb
    pygame.draw.circle(screen, (80, 80, 80), (center_x - 2, center_y - 2), size // 5)
    
    # Fuse (red sparkle line)
    fuse_start_x = center_x - size // 4
    fuse_start_y = y + 2
    pygame.draw.line(screen, (150, 150, 150), (fuse_start_x, fuse_start_y), (fuse_start_x - 2, fuse_start_y - 3), 2)
    # Red spark at fuse tip
    pygame.draw.circle(screen, (255, 50, 50), (fuse_start_x - 2, fuse_start_y - 3), 2)
    pygame.draw.circle(screen, (255, 150, 0), (fuse_start_x - 2, fuse_start_y - 3), 1)
