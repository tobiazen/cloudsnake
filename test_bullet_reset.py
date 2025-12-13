"""
Unit tests for bullet reset functionality when players die or respawn.

Tests verify that:
1. Bullet count is reset to 0 when a player dies (headshot, wall collision, self-collision)
2. Bullet count is reset to 0 when a player respawns
3. Bullet count doesn't leak between players
"""

import unittest
from typing import Dict, Any
from unittest.mock import patch, MagicMock
from server import GameServer


class TestBulletReset(unittest.TestCase):
    """Test cases for bullet count reset on death and respawn"""

    def setUp(self):
        """Set up a game server instance for testing"""
        # Mock socket before creating server to prevent binding
        with patch('socket.socket'):
            self.server = GameServer(port=50001)  # Use different port for testing
        
        self.server.running = True
        
        # Add two test players
        self.player1_addr = ("127.0.0.1", 10001)
        self.player2_addr = ("127.0.0.1", 10002)
        
        # Initialize player 1
        self.server.clients[self.player1_addr] = {
            'player_name': 'TestPlayer1',
            'snake': [(10, 10), (10, 11), (10, 12)],
            'snake_set': {(10, 10), (10, 11), (10, 12)},
            'direction': 'UP',
            'score': 500,
            'alive': True,
            'bullets': 5,  # Player has 5 bullets
            'bombs': 0,
            'in_game': True,  # Player is in active game
            'last_seen': 0
        }
        
        # Initialize player 2
        self.server.clients[self.player2_addr] = {
            'player_name': 'TestPlayer2',
            'snake': [(20, 20), (20, 21), (20, 22)],
            'snake_set': {(20, 20), (20, 21), (20, 22)},
            'direction': 'DOWN',
            'score': 300,
            'alive': True,
            'bullets': 3,  # Player has 3 bullets
            'bombs': 0,
            'in_game': True,  # Player is in active game
            'last_seen': 0
        }
        
        # Update occupied cells
        self.server.occupied_cells = {(10, 10), (10, 11), (10, 12), (20, 20), (20, 21), (20, 22)}

    def tearDown(self):
        """Clean up after tests"""
        self.server.running = False

    def test_bullets_reset_on_headshot_death(self):
        """Test that bullets are reset to 0 when player dies from headshot"""
        # Player 1 has 5 bullets before death
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 5)
        self.assertTrue(self.server.clients[self.player1_addr]['alive'])
        
        # Record player 2's initial score
        initial_score_player2 = self.server.clients[self.player2_addr]['score']
        
        # Create a bullet that will hit player 1's head
        # Bullet is owned by player 2 and positioned at player 1's head
        bullet: Dict[str, Any] = {
            'pos': [9, 10],  # One position to the left, will move right to (10, 10)
            'direction': 'RIGHT',
            'owner': str(self.player2_addr),
            'shooter_name': 'TestPlayer2'
        }
        self.server.bullets = [bullet]
        
        # Process bullet collisions
        self.server.update_bullets()
        
        # Verify player 1 is dead and bullets are reset
        self.assertFalse(self.server.clients[self.player1_addr]['alive'], 
                        "Player should be dead after headshot")
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 0,
                        "Bullets should be reset to 0 after death")
        
        # Verify player 2 got 250 points for the kill
        self.assertEqual(self.server.clients[self.player2_addr]['score'], initial_score_player2 + 250,
                        "Killer should receive 250 points for the kill")
        
        # Verify snake is removed from occupied cells
        player1_snake_set = self.server.clients[self.player1_addr].get('snake_set', set())
        self.assertEqual(len(player1_snake_set), 0,
                        "Dead snake's snake_set should be empty")
        # Verify no player 1 segments remain in occupied_cells
        for segment in [(10, 10), (10, 11), (10, 12)]:
            self.assertNotIn(segment, self.server.occupied_cells,
                           f"Dead snake segment {segment} should be removed from occupied_cells")

    def test_bullets_reset_on_wall_collision(self):
        """Test that bullets are reset to 0 when player hits a wall"""
        # Player 1 has 5 bullets before collision
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 5)
        self.assertTrue(self.server.clients[self.player1_addr]['alive'])
        
        # Move player 1 towards the top wall
        self.server.clients[self.player1_addr]['snake'] = [(0, 0)]  # At edge
        self.server.clients[self.player1_addr]['snake_set'] = {(0, 0)}
        self.server.clients[self.player1_addr]['direction'] = 'UP'  # Moving towards wall
        
        # Update occupied cells to include player's snake
        self.server.occupied_cells.add((0, 0))
        
        # Process game logic (will detect wall collision)
        self.server.update_game_logic()
        
        # Verify player 1 is dead and bullets are reset
        self.assertFalse(self.server.clients[self.player1_addr]['alive'])
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 0)

    def test_bullets_reset_on_self_collision(self):
        """Test that bullets are reset to 0 when player hits themselves"""
        # Player 1 has 5 bullets before collision
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 5)
        self.assertTrue(self.server.clients[self.player1_addr]['alive'])
        
        # Create a snake that will collide with itself on next move
        # Snake at (5,5) moving RIGHT will hit (6,5) which is in the body
        self.server.clients[self.player1_addr]['snake'] = [(5, 5), (4, 5), (3, 5), (3, 6), (4, 6), (5, 6), (6, 6), (6, 5)]
        self.server.clients[self.player1_addr]['snake_set'] = {(5, 5), (4, 5), (3, 5), (3, 6), (4, 6), (5, 6), (6, 6), (6, 5)}
        self.server.clients[self.player1_addr]['direction'] = 'RIGHT'  # Will hit (6, 5) which is in snake_set
        
        # Update occupied cells
        self.server.occupied_cells.update(self.server.clients[self.player1_addr]['snake_set'])
        
        # Process game logic (will detect self-collision)
        self.server.update_game_logic()
        
        # Verify player 1 is dead and bullets are reset
        self.assertFalse(self.server.clients[self.player1_addr]['alive'])
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 0)

    @patch('random.randint')
    def test_bullets_reset_on_respawn(self, mock_randint: MagicMock) -> None:
        """Test that bullets are reset to 0 when player respawns"""
        # Mock random position for respawn
        mock_randint.side_effect = [15, 15]  # x, y coordinates
        
        # Kill player 1 first
        self.server.clients[self.player1_addr]['alive'] = False
        self.server.clients[self.player1_addr]['bullets'] = 5  # Still has bullets after death
        
        # Send respawn request
        respawn_message: Dict[str, Any] = {
            'type': 'player_update',
            'data': {
                'respawn': True
            }
        }
        
        self.server.handle_player_update(self.player1_addr, respawn_message)
        
        # Verify player is alive and bullets are reset to 0
        self.assertTrue(self.server.clients[self.player1_addr]['alive'])
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 0)
        self.assertEqual(self.server.clients[self.player1_addr]['score'], 250)  # Half of 500

    def test_bullets_dont_swap_between_players(self):
        """Test that bullet counts remain independent between players"""
        # Initial state
        player1_bullets = self.server.clients[self.player1_addr]['bullets']
        player2_bullets = self.server.clients[self.player2_addr]['bullets']
        
        self.assertEqual(player1_bullets, 5)
        self.assertEqual(player2_bullets, 3)
        
        # Kill player 1
        self.server.clients[self.player1_addr]['alive'] = False
        self.server.clients[self.player1_addr]['bullets'] = 0
        
        # Verify player 2's bullets are unchanged
        self.assertEqual(self.server.clients[self.player2_addr]['bullets'], 3)
        
        # Respawn player 1
        with patch('random.randint', side_effect=[15, 15]):
            respawn_message: Dict[str, Any] = {
                'type': 'player_update',
                'data': {'respawn': True}
            }
            self.server.handle_player_update(self.player1_addr, respawn_message)
        
        # Verify player 1 has 0 bullets and player 2 still has 3
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 0)
        self.assertEqual(self.server.clients[self.player2_addr]['bullets'], 3)

    def test_bullet_count_after_collecting_bullet_brick(self):
        """Test that collecting bullet brick increases bullet count by 1"""
        # Set up player with 2 bullets
        initial_bullets = 2
        self.server.clients[self.player1_addr]['bullets'] = initial_bullets
        
        # Create a bullet brick at player's head position
        player_head = self.server.clients[self.player1_addr]['snake'][0]
        self.server.bullet_bricks.append([player_head[0], player_head[1]])  # bullet_bricks is a list
        self.server.bullet_bricks_set.add(player_head)
        
        # Check brick collection
        snake = self.server.clients[self.player1_addr]['snake']
        result = self.server.check_brick_collection(self.player1_addr, snake)
        
        # Verify bullet count increased by 1
        self.assertEqual(result, 'bullet')
        self.assertEqual(self.server.clients[self.player1_addr]['bullets'], initial_bullets + 1)

    def test_multiple_death_and_respawn_cycles(self):
        """Test that bullets reset correctly through multiple death/respawn cycles"""
        with patch('random.randint') as mock_randint:
            for cycle in range(3):
                # Set up position for respawn
                mock_randint.side_effect = [10 + cycle, 10 + cycle]
                
                # Give player some bullets
                self.server.clients[self.player1_addr]['bullets'] = 5
                
                # Kill player
                self.server.clients[self.player1_addr]['alive'] = False
                self.server.clients[self.player1_addr]['bullets'] = 0
                
                # Respawn
                respawn_message: Dict[str, Any] = {
                    'type': 'player_update',
                    'data': {'respawn': True}
                }
                self.server.handle_player_update(self.player1_addr, respawn_message)
                
                # Verify bullets are 0 after each respawn
                self.assertEqual(self.server.clients[self.player1_addr]['bullets'], 0,
                               f"Bullets not reset to 0 in cycle {cycle + 1}")
                self.assertTrue(self.server.clients[self.player1_addr]['alive'],
                              f"Player not alive after respawn in cycle {cycle + 1}")


if __name__ == '__main__':
    unittest.main()
