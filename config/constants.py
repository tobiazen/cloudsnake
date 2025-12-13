"""Constants for CloudSnake client - colors, dimensions, and display settings"""
from typing import Tuple

# Screen dimensions
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
FPS = 60

# Direction enums (for network optimization)
DIR_UP = 0
DIR_DOWN = 1
DIR_LEFT = 2
DIR_RIGHT = 3

# Direction mappings
DIRECTION_TO_INT = {'UP': 0, 'DOWN': 1, 'LEFT': 2, 'RIGHT': 3}
INT_TO_DIRECTION = {0: 'UP', 1: 'DOWN', 2: 'LEFT', 3: 'RIGHT'}

# Basic colors - Enhanced palette
WHITE: Tuple[int, int, int] = (255, 255, 255)
BLACK: Tuple[int, int, int] = (0, 0, 0)
GRAY: Tuple[int, int, int] = (200, 200, 200)
DARK_GRAY: Tuple[int, int, int] = (80, 80, 80)
LIGHT_GRAY: Tuple[int, int, int] = (240, 240, 240)
GREEN: Tuple[int, int, int] = (34, 177, 76)
DARK_GREEN: Tuple[int, int, int] = (25, 130, 55)
RED: Tuple[int, int, int] = (237, 41, 57)
DARK_RED: Tuple[int, int, int] = (180, 30, 43)
BLUE: Tuple[int, int, int] = (0, 120, 215)
DARK_BLUE: Tuple[int, int, int] = (0, 90, 160)
YELLOW: Tuple[int, int, int] = (255, 185, 0)
DARK_YELLOW: Tuple[int, int, int] = (200, 145, 0)
ORANGE: Tuple[int, int, int] = (255, 140, 0)
PURPLE: Tuple[int, int, int] = (136, 23, 152)
CYAN: Tuple[int, int, int] = (0, 188, 212)

# UI Colors
BG_COLOR: Tuple[int, int, int] = (15, 15, 25)
PANEL_BG: Tuple[int, int, int] = (25, 25, 40)
BORDER_COLOR: Tuple[int, int, int] = (60, 60, 80)
HIGHLIGHT_COLOR: Tuple[int, int, int] = (80, 80, 120)
TEXT_COLOR: Tuple[int, int, int] = (220, 220, 230)
TEXT_SHADOW: Tuple[int, int, int] = (10, 10, 15)
