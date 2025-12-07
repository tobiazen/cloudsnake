"""Unit tests for game.game_state module"""
import unittest
from game.game_state import GameStateManager, PlayerInfo


class TestGameStateManager(unittest.TestCase):
    """Test GameStateManager class"""
    
    def setUp(self):
        """Set up test game state"""
        self.game_state = {
            'players': {
                'player1': {
                    'player_name': 'Alice',
                    'score': 500,
                    'snake': [[10, 10], [10, 11], [10, 12]],
                    'color': [255, 0, 0],
                    'bullets': 3,
                    'bombs': 2,
                    'alive': True,
                    'in_game': True
                },
                'player2': {
                    'player_name': 'Bob',
                    'score': 300,
                    'snake': [[5, 5]],
                    'color': [0, 255, 0],
                    'bullets': 0,
                    'bombs': 1,
                    'alive': False,
                    'in_game': True
                }
            },
            'bricks': [[15, 15], [20, 20]],
            'bullet_bricks': [[25, 25]],
            'bomb_bricks': [[30, 30]],
            'bullets': [{'pos': [12, 12], 'direction': 'up'}],
            'bombs': [{'pos': [18, 18], 'timer': 2.5}],
            'explosions': [{'pos': [22, 22], 'timer': 0.5}],
            'leaderboard': [
                {'player_name': 'Alice', 'highscore': 500},
                {'player_name': 'Bob', 'highscore': 300}
            ],
            'all_time_highscore': 1000,
            'all_time_highscore_player': 'Charlie'
        }
        self.manager = GameStateManager(self.game_state)
    
    def test_initialization(self):
        """Test manager initialization"""
        # With game state
        self.assertTrue(self.manager.is_valid)
        
        # Without game state
        empty_manager = GameStateManager()
        self.assertFalse(empty_manager.is_valid)
    
    def test_update(self):
        """Test updating game state"""
        new_state = {'players': {'player3': {'player_name': 'Carol'}}}
        self.manager.update(new_state)
        self.assertEqual(len(self.manager.get_players()), 1)
    
    def test_get_players(self):
        """Test getting all players"""
        players = self.manager.get_players()
        self.assertEqual(len(players), 2)
        self.assertIn('player1', players)
        self.assertIn('player2', players)
    
    def test_get_player_data(self):
        """Test getting individual player data"""
        data = self.manager.get_player_data('player1')
        self.assertEqual(data['player_name'], 'Alice')
        self.assertEqual(data['score'], 500)
        
        # Non-existent player
        empty_data = self.manager.get_player_data('nonexistent')
        self.assertEqual(empty_data, {})
    
    def test_get_player_name(self):
        """Test getting player name"""
        self.assertEqual(self.manager.get_player_name('player1'), 'Alice')
        self.assertEqual(self.manager.get_player_name('nonexistent'), 'Unknown')
    
    def test_get_player_score(self):
        """Test getting player score"""
        self.assertEqual(self.manager.get_player_score('player1'), 500)
        self.assertEqual(self.manager.get_player_score('player2'), 300)
        self.assertEqual(self.manager.get_player_score('nonexistent'), 0)
    
    def test_get_player_snake(self):
        """Test getting player snake"""
        snake = self.manager.get_player_snake('player1')
        self.assertEqual(len(snake), 3)
        self.assertEqual(snake[0], (10, 10))
        self.assertEqual(snake[1], (10, 11))
    
    def test_get_player_color(self):
        """Test getting player color"""
        color = self.manager.get_player_color('player1')
        self.assertEqual(color, (255, 0, 0))
    
    def test_get_player_bullets_and_bombs(self):
        """Test getting player bullets and bombs"""
        self.assertEqual(self.manager.get_player_bullets('player1'), 3)
        self.assertEqual(self.manager.get_player_bombs('player1'), 2)
        self.assertEqual(self.manager.get_player_bullets('player2'), 0)
    
    def test_is_player_alive(self):
        """Test checking if player is alive"""
        self.assertTrue(self.manager.is_player_alive('player1'))
        self.assertFalse(self.manager.is_player_alive('player2'))
        self.assertTrue(self.manager.is_player_alive('nonexistent'))  # Default True
    
    def test_is_player_in_game(self):
        """Test checking if player is in game"""
        self.assertTrue(self.manager.is_player_in_game('player1'))
        self.assertTrue(self.manager.is_player_in_game('player2'))
        self.assertFalse(self.manager.is_player_in_game('nonexistent'))  # Default False
    
    def test_get_sorted_players(self):
        """Test getting sorted players"""
        sorted_players = self.manager.get_sorted_players()
        self.assertEqual(len(sorted_players), 2)
        self.assertEqual(sorted_players[0][0], 'player1')  # Alice has higher score
        self.assertEqual(sorted_players[1][0], 'player2')
        
        # Test with limit
        limited = self.manager.get_sorted_players(limit=1)
        self.assertEqual(len(limited), 1)
        self.assertEqual(limited[0][0], 'player1')
    
    def test_get_bricks(self):
        """Test getting bricks"""
        bricks = self.manager.get_bricks()
        self.assertEqual(len(bricks), 2)
        self.assertIn((15, 15), bricks)
        self.assertIn((20, 20), bricks)
    
    def test_get_bullet_bricks(self):
        """Test getting bullet bricks"""
        bullet_bricks = self.manager.get_bullet_bricks()
        self.assertEqual(len(bullet_bricks), 1)
        self.assertEqual(bullet_bricks[0], (25, 25))
    
    def test_get_bomb_bricks(self):
        """Test getting bomb bricks"""
        bomb_bricks = self.manager.get_bomb_bricks()
        self.assertEqual(len(bomb_bricks), 1)
        self.assertEqual(bomb_bricks[0], (30, 30))
    
    def test_get_bullets(self):
        """Test getting bullets"""
        bullets = self.manager.get_bullets()
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0]['pos'], [12, 12])
    
    def test_get_bombs(self):
        """Test getting bombs"""
        bombs = self.manager.get_bombs()
        self.assertEqual(len(bombs), 1)
        self.assertEqual(bombs[0]['pos'], [18, 18])
    
    def test_get_explosions(self):
        """Test getting explosions"""
        explosions = self.manager.get_explosions()
        self.assertEqual(len(explosions), 1)
        self.assertEqual(explosions[0]['pos'], [22, 22])
    
    def test_get_leaderboard(self):
        """Test getting leaderboard"""
        leaderboard = self.manager.get_leaderboard()
        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0]['player_name'], 'Alice')
    
    def test_get_all_time_highscore(self):
        """Test getting all-time high score"""
        self.assertEqual(self.manager.get_all_time_highscore(), 1000)
        self.assertEqual(self.manager.get_all_time_highscore_player(), 'Charlie')


class TestPlayerInfo(unittest.TestCase):
    """Test PlayerInfo class"""
    
    def setUp(self):
        """Set up test player data"""
        self.player_data = {
            'player_name': 'TestPlayer',
            'score': 750,
            'snake': [[5, 5], [5, 6], [5, 7]],
            'color': [0, 0, 255],
            'bullets': 4,
            'bombs': 3,
            'alive': True,
            'in_game': True
        }
        self.player_info = PlayerInfo('test_id', self.player_data)
    
    def test_properties(self):
        """Test basic properties"""
        self.assertEqual(self.player_info.player_id, 'test_id')
        self.assertEqual(self.player_info.name, 'TestPlayer')
        self.assertEqual(self.player_info.score, 750)
        self.assertEqual(self.player_info.bullets, 4)
        self.assertEqual(self.player_info.bombs, 3)
        self.assertTrue(self.player_info.is_alive)
        self.assertTrue(self.player_info.in_game)
    
    def test_snake_property(self):
        """Test snake property"""
        snake = self.player_info.snake
        self.assertEqual(len(snake), 3)
        self.assertEqual(snake[0], (5, 5))
    
    def test_color_property(self):
        """Test color property"""
        color = self.player_info.color
        self.assertEqual(color, (0, 0, 255))
    
    def test_head_position(self):
        """Test head position property"""
        head = self.player_info.head_position
        self.assertEqual(head, (5, 5))
        
        # Test with empty snake
        empty_player = PlayerInfo('empty', {'snake': []})
        self.assertIsNone(empty_player.head_position)
    
    def test_body_color(self):
        """Test body color property"""
        body_color = self.player_info.body_color
        # Should be 70% of (0, 0, 255) = (0, 0, 178)
        self.assertEqual(body_color[0], 0)
        self.assertEqual(body_color[1], 0)
        self.assertAlmostEqual(body_color[2], 178, delta=1)
    
    def test_get_truncated_name(self):
        """Test name truncation"""
        # Short name
        short = self.player_info.get_truncated_name(20)
        self.assertEqual(short, 'TestPlayer')
        
        # Long name needs truncation
        long_player = PlayerInfo('long', {'player_name': 'VeryLongPlayerName'})
        truncated = long_player.get_truncated_name(10)
        self.assertEqual(truncated, 'VeryLongPl..')
        self.assertEqual(len(truncated), 12)  # 10 chars + ".."


if __name__ == '__main__':
    unittest.main()
