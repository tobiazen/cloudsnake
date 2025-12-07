"""Unit tests for utils.helpers module"""
import unittest
import pygame
from utils.helpers import (
    get_unicode_font, get_resource_path,
    draw_bullet_icon, draw_bomb_icon,
    draw_text_with_shadow, draw_gradient_rect
)


class TestHelpers(unittest.TestCase):
    """Test utility helper functions"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize pygame once for all tests"""
        pygame.init()
    
    @classmethod
    def tearDownClass(cls):
        """Quit pygame after all tests"""
        pygame.quit()
    
    def test_get_unicode_font(self):
        """Test get_unicode_font function"""
        font = get_unicode_font(16)
        self.assertIsInstance(font, pygame.font.Font)
        # Font height may vary slightly based on the font file
        self.assertGreater(font.get_height(), 0)
    
    def test_get_resource_path(self):
        """Test get_resource_path function"""
        path = get_resource_path('test.txt')
        self.assertIsInstance(path, str)
        self.assertIn('test.txt', path)
    
    def test_draw_bullet_icon(self):
        """Test draw_bullet_icon function"""
        screen = pygame.Surface((100, 100))
        # Should not raise any exceptions
        draw_bullet_icon(screen, 50, 50, 10)
        self.assertIsNotNone(screen)
    
    def test_draw_bomb_icon(self):
        """Test draw_bomb_icon function"""
        screen = pygame.Surface((100, 100))
        # Should not raise any exceptions
        draw_bomb_icon(screen, 50, 50, 10)
        self.assertIsNotNone(screen)
    
    def test_draw_text_with_shadow(self):
        """Test draw_text_with_shadow function"""
        screen = pygame.Surface((200, 100))
        font = get_unicode_font(16)
        # Should not raise any exceptions
        draw_text_with_shadow(screen, "Test", font, 100, 50, (255, 255, 255))
        self.assertIsNotNone(screen)
    
    def test_draw_gradient_rect(self):
        """Test draw_gradient_rect function"""
        screen = pygame.Surface((200, 100))
        # Should not raise any exceptions
        draw_gradient_rect(screen, 10, 10, 100, 50, (0, 0, 255), (0, 0, 128))
        self.assertIsNotNone(screen)


if __name__ == '__main__':
    unittest.main()
