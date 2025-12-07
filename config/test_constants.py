"""Unit tests for config.constants module"""
import unittest
from config.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    WHITE, BLACK, GRAY, DARK_GRAY, LIGHT_GRAY,
    GREEN, DARK_GREEN, RED, DARK_RED,
    BLUE, DARK_BLUE, YELLOW, DARK_YELLOW,
    ORANGE, PURPLE, CYAN,
    BG_COLOR, PANEL_BG, BORDER_COLOR, HIGHLIGHT_COLOR,
    TEXT_COLOR, TEXT_SHADOW
)


class TestConstants(unittest.TestCase):
    """Test configuration constants"""
    
    def test_screen_dimensions(self):
        """Test screen dimension constants"""
        self.assertEqual(SCREEN_WIDTH, 1000)
        self.assertEqual(SCREEN_HEIGHT, 750)
        self.assertEqual(FPS, 60)
    
    def test_colors_are_tuples(self):
        """Test that colors are RGB tuples"""
        colors = [WHITE, BLACK, GRAY, DARK_GRAY, LIGHT_GRAY,
                  GREEN, DARK_GREEN, RED, DARK_RED,
                  BLUE, DARK_BLUE, YELLOW, DARK_YELLOW,
                  ORANGE, PURPLE, CYAN,
                  BG_COLOR, PANEL_BG, BORDER_COLOR, HIGHLIGHT_COLOR,
                  TEXT_COLOR, TEXT_SHADOW]
        
        for color in colors:
            self.assertIsInstance(color, tuple)
            self.assertEqual(len(color), 3)
            for value in color:
                self.assertIsInstance(value, int)
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 255)
    
    def test_basic_colors(self):
        """Test basic color values"""
        self.assertEqual(WHITE, (255, 255, 255))
        self.assertEqual(BLACK, (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
