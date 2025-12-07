"""Unit tests for ui.widgets module"""
import unittest
import pygame
from ui.widgets import InputBox, Button
from config.constants import BLUE


class TestInputBox(unittest.TestCase):
    """Test InputBox widget"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize pygame once for all tests"""
        pygame.init()
    
    @classmethod
    def tearDownClass(cls):
        """Quit pygame after all tests"""
        pygame.quit()
    
    def test_initialization(self):
        """Test InputBox initialization"""
        input_box = InputBox(100, 100, 200, 40, "test text")
        self.assertEqual(input_box.text, "test text")
        self.assertFalse(input_box.active)
    
    def test_has_required_attributes(self):
        """Test that InputBox has all required attributes"""
        input_box = InputBox(100, 100, 200, 40, "")
        required_attrs = ['rect', 'text', 'color', 'font', 'active']
        for attr in required_attrs:
            self.assertTrue(hasattr(input_box, attr),
                          f"InputBox should have {attr} attribute")
    
    def test_has_required_methods(self):
        """Test that InputBox has all required methods"""
        input_box = InputBox(100, 100, 200, 40, "")
        required_methods = ['handle_event', 'draw']
        for method in required_methods:
            self.assertTrue(hasattr(input_box, method),
                          f"InputBox should have {method} method")
            self.assertTrue(callable(getattr(input_box, method)),
                          f"InputBox.{method} should be callable")
    
    def test_draw_method(self):
        """Test InputBox draw method"""
        input_box = InputBox(100, 100, 200, 40, "test")
        screen = pygame.Surface((400, 300))
        # Should not raise any exceptions
        input_box.draw(screen)
        self.assertIsNotNone(screen)


class TestButton(unittest.TestCase):
    """Test Button widget"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize pygame once for all tests"""
        pygame.init()
    
    @classmethod
    def tearDownClass(cls):
        """Quit pygame after all tests"""
        pygame.quit()
    
    def test_initialization(self):
        """Test Button initialization"""
        button = Button(100, 100, 150, 50, "Click Me", BLUE)
        self.assertEqual(button.text, "Click Me")
        self.assertEqual(button.color, BLUE)
        self.assertFalse(button.hovered)
    
    def test_has_required_attributes(self):
        """Test that Button has all required attributes"""
        button = Button(100, 100, 150, 50, "Test", BLUE)
        required_attrs = ['rect', 'text', 'color', 'hover_color', 'font', 'hovered']
        for attr in required_attrs:
            self.assertTrue(hasattr(button, attr),
                          f"Button should have {attr} attribute")
    
    def test_has_required_methods(self):
        """Test that Button has all required methods"""
        button = Button(100, 100, 150, 50, "Test", BLUE)
        required_methods = ['handle_event', 'draw']
        for method in required_methods:
            self.assertTrue(hasattr(button, method),
                          f"Button should have {method} method")
            self.assertTrue(callable(getattr(button, method)),
                          f"Button.{method} should be callable")
    
    def test_draw_method(self):
        """Test Button draw method"""
        button = Button(100, 100, 150, 50, "Test", BLUE)
        screen = pygame.Surface((400, 300))
        # Should not raise any exceptions
        button.draw(screen)
        self.assertIsNotNone(screen)


if __name__ == '__main__':
    unittest.main()
