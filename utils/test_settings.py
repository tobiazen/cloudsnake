"""Unit tests for utils.settings module"""
import unittest
import os
import tempfile
from utils.settings import load_settings, save_settings, add_player_name


class TestSettings(unittest.TestCase):
    """Test settings management functions"""
    
    def setUp(self):
        """Create a temporary file for each test"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up temporary file after each test"""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)
    
    def test_load_settings_nonexistent_file(self):
        """Test loading settings from non-existent file returns defaults"""
        settings = load_settings('nonexistent_file.json')
        self.assertIn('player_names', settings)
        self.assertIn('last_player_name', settings)
        self.assertIn('server_ip', settings)
        self.assertEqual(settings['player_names'], [])
    
    def test_save_and_load_settings(self):
        """Test saving and loading settings"""
        test_settings = {
            'player_names': ['Player1', 'Player2'],
            'last_player_name': 'Player1',
            'server_ip': '127.0.0.1'
        }
        save_settings(test_settings, self.temp_file.name)
        
        loaded_settings = load_settings(self.temp_file.name)
        self.assertEqual(loaded_settings['player_names'], ['Player1', 'Player2'])
        self.assertEqual(loaded_settings['last_player_name'], 'Player1')
        self.assertEqual(loaded_settings['server_ip'], '127.0.0.1')
    
    def test_add_player_name_new(self):
        """Test adding a new player name"""
        settings = {'player_names': [], 'last_player_name': '', 'server_ip': '127.0.0.1'}
        add_player_name(settings, 'Player1', self.temp_file.name)
        
        self.assertEqual(settings['player_names'][0], 'Player1')
        self.assertEqual(settings['last_player_name'], 'Player1')
    
    def test_add_player_name_duplicate(self):
        """Test adding a duplicate player name moves it to front"""
        settings = {
            'player_names': ['Player2', 'Player1'],
            'last_player_name': 'Player2',
            'server_ip': '127.0.0.1'
        }
        add_player_name(settings, 'Player1', self.temp_file.name)
        
        self.assertEqual(settings['player_names'][0], 'Player1')
        self.assertEqual(settings['player_names'][1], 'Player2')
        self.assertEqual(len(settings['player_names']), 2)
    
    def test_add_player_name_max_limit(self):
        """Test that player names list is limited to 10 entries"""
        settings = {
            'player_names': [f'Player{i}' for i in range(10)],
            'last_player_name': 'Player0',
            'server_ip': '127.0.0.1'
        }
        add_player_name(settings, 'NewPlayer', self.temp_file.name)
        
        self.assertEqual(settings['player_names'][0], 'NewPlayer')
        self.assertEqual(len(settings['player_names']), 10)
        self.assertNotIn('Player9', settings['player_names'])


if __name__ == '__main__':
    unittest.main()
