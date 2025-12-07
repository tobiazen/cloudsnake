"""Unit tests for network.game_client module"""
import unittest
from network.game_client import GameClient


class TestGameClient(unittest.TestCase):
    """Test GameClient class"""
    
    def setUp(self):
        """Create a GameClient instance for testing"""
        self.client = GameClient("127.0.0.1", 50000, "TestPlayer")
    
    def tearDown(self):
        """Clean up after each test"""
        if self.client.connected:
            self.client.disconnect()
    
    def test_initialization(self):
        """Test GameClient initialization"""
        self.assertEqual(self.client.server_ip, "127.0.0.1")
        self.assertEqual(self.client.server_port, 50000)
        self.assertEqual(self.client.player_name, "TestPlayer")
        self.assertFalse(self.client.connected)
        self.assertFalse(self.client.running)
    
    def test_has_required_attributes(self):
        """Test that GameClient has all required attributes"""
        required_attrs = [
            'server_ip', 'server_port', 'player_name',
            'connected', 'running', 'game_state'
        ]
        for attr in required_attrs:
            self.assertTrue(hasattr(self.client, attr),
                          f"GameClient should have {attr} attribute")
    
    def test_has_required_methods(self):
        """Test that GameClient has all required methods"""
        required_methods = [
            'connect', 'disconnect', 'send_to_server',
            'receive_messages', 'shoot', 'throw_bomb', 'respawn',
            'handle_server_message'
        ]
        for method in required_methods:
            self.assertTrue(hasattr(self.client, method),
                          f"GameClient should have {method} method")
            self.assertTrue(callable(getattr(self.client, method)),
                          f"GameClient.{method} should be callable")
    
    def test_game_state_initialization(self):
        """Test that game_state is properly initialized"""
        # game_state is None until connected, which is expected
        self.assertIsNone(self.client.game_state)
    
    def test_no_pygame_dependency(self):
        """Test that GameClient doesn't import pygame"""
        import inspect
        source = inspect.getsource(GameClient)
        self.assertNotIn('import pygame', source,
                        "GameClient should not import pygame")
        self.assertNotIn('from pygame', source,
                        "GameClient should not import from pygame")


if __name__ == '__main__':
    unittest.main()
