"""
Unit tests for bomb functionality.

Tests verify that:
1. Bomb bricks spawn with 2% probability
2. Players collect bombs from bomb bricks
3. Bombs are thrown 2-5 cells left or right
4. Bombs explode after 2-4 seconds
5. Explosions hit snakes in a 3x3 area around the bomb
6. Snakes hit in the head die
7. Snakes hit in the body lose their tail from the point of impact
8. Bomb count resets on death, respawn, and game leave
"""

import unittest
import time
from typing import Dict, Any, Tuple
from unittest.mock import patch, MagicMock
from server import GameServer


class TestBombFeature(unittest.TestCase):
    """Test cases for bomb functionality"""

    def setUp(self):
        """Set up a game server instance for testing"""
        # Mock socket before creating server to prevent binding
        with patch('socket.socket'):
            self.server = GameServer(port=50002)  # Use different port for testing
        
        self.server.running = True
        
        # Add test players
        self.player1_addr = ("127.0.0.1", 10001)
        self.player2_addr = ("127.0.0.1", 10002)
        self.player3_addr = ("127.0.0.1", 10003)
        
        # Initialize player 1 (thrower)
        self.server.clients[self.player1_addr] = {
            'player_name': 'BombThrower',
            'snake': [(20, 15), (20, 16), (20, 17)],
            'snake_set': {(20, 15), (20, 16), (20, 17)},
            'direction': 'UP',
            'score': 500,
            'alive': True,
            'bullets': 0,
            'bombs': 3,  # Player has 3 bombs
            'in_game': True,
            'last_seen': 0,
            'color': (255, 0, 0)
        }
        
        # Initialize player 2 (victim - will be in explosion range)
        self.server.clients[self.player2_addr] = {
            'player_name': 'VictimPlayer',
            'snake': [(25, 15), (25, 16), (25, 17), (25, 18), (25, 19)],
            'snake_set': {(25, 15), (25, 16), (25, 17), (25, 18), (25, 19)},
            'direction': 'DOWN',
            'score': 300,
            'alive': True,
            'bullets': 0,
            'bombs': 0,
            'in_game': True,
            'last_seen': 0,
            'color': (0, 255, 0)
        }
        
        # Initialize player 3 (safe distance - outside explosion range)
        self.server.clients[self.player3_addr] = {
            'player_name': 'SafePlayer',
            'snake': [(30, 15), (30, 16), (30, 17)],
            'snake_set': {(30, 15), (30, 16), (30, 17)},
            'direction': 'DOWN',
            'score': 200,
            'alive': True,
            'bullets': 0,
            'bombs': 1,
            'in_game': True,
            'last_seen': 0,
            'color': (0, 0, 255)
        }
        
        # Update occupied cells
        self.server.occupied_cells = (
            {(20, 15), (20, 16), (20, 17)} |
            {(25, 15), (25, 16), (25, 17), (25, 18), (25, 19)} |
            {(30, 15), (30, 16), (30, 17)}
        )

    def tearDown(self):
        """Clean up after tests"""
        self.server.running = False

    @patch('random.random')
    def test_bomb_brick_spawn_probability(self, mock_random: MagicMock) -> None:
        """Test that bomb bricks spawn with 2% probability"""
        # Mock random to return 0.01 (< 0.02, should spawn bomb brick)
        mock_random.return_value = 0.01
        
        initial_bomb_bricks = len(self.server.bomb_bricks)
        
        # Spawn a brick
        result = self.server.spawn_brick()
        
        # Verify bomb brick was spawned
        self.assertTrue(result)
        self.assertEqual(len(self.server.bomb_bricks), initial_bomb_bricks + 1)
        
        # Mock random to return 0.03 (>= 0.02 but < 0.07, should spawn bullet brick)
        mock_random.return_value = 0.03
        initial_bullet_bricks = len(self.server.bullet_bricks)
        
        result = self.server.spawn_brick()
        
        self.assertTrue(result)
        self.assertEqual(len(self.server.bullet_bricks), initial_bullet_bricks + 1)
        
        # Mock random to return 0.10 (>= 0.07, should spawn regular brick)
        mock_random.return_value = 0.10
        initial_bricks = len(self.server.bricks)
        
        result = self.server.spawn_brick()
        
        self.assertTrue(result)
        self.assertEqual(len(self.server.bricks), initial_bricks + 1)

    def test_collect_bomb_brick(self):
        """Test that collecting a bomb brick increases bomb count by 1"""
        initial_bombs = self.server.clients[self.player1_addr]['bombs']
        
        # Place a bomb brick at player's head position
        player_head = self.server.clients[self.player1_addr]['snake'][0]
        self.server.bomb_bricks.append([player_head[0], player_head[1]])
        self.server.bomb_bricks_set.add(player_head)
        
        # Check brick collection
        snake = self.server.clients[self.player1_addr]['snake']
        result = self.server.check_brick_collection(self.player1_addr, snake)
        
        # Verify bomb count increased by 1
        self.assertEqual(result, 'bomb')
        self.assertEqual(self.server.clients[self.player1_addr]['bombs'], initial_bombs + 1)
        
        # Verify bomb brick was removed
        self.assertNotIn(player_head, self.server.bomb_bricks_set)

    @patch('random.choice')
    @patch('random.randint')
    @patch('random.uniform')
    def test_throw_bomb_mechanics(self, mock_uniform: MagicMock, 
                                  mock_randint: MagicMock, 
                                  mock_choice: MagicMock) -> None:
        """Test that bombs are thrown with correct mechanics"""
        # Mock throw direction (RIGHT) and distance (3 cells)
        mock_choice.return_value = 'RIGHT'
        mock_randint.return_value = 3
        mock_uniform.return_value = 2.5  # 2.5 seconds until explosion
        
        initial_bombs = self.server.clients[self.player1_addr]['bombs']
        
        # Throw bomb
        self.server.handle_throw_bomb(self.player1_addr)
        
        # Verify bomb count decreased
        self.assertEqual(self.server.clients[self.player1_addr]['bombs'], initial_bombs - 1)
        
        # Verify bomb was created
        self.assertEqual(len(self.server.bombs), 1)
        
        bomb = self.server.bombs[0]
        player_head = self.server.clients[self.player1_addr]['snake'][0]
        
        # Verify bomb position (should be 3 cells to the RIGHT of head)
        expected_pos = [player_head[0] + 3, player_head[1]]
        self.assertEqual(bomb['pos'], expected_pos)
        
        # Verify bomb has correct metadata
        self.assertIn('explode_time', bomb)
        self.assertEqual(bomb['owner'], str(self.player1_addr))
        self.assertEqual(bomb['thrower_name'], 'BombThrower')

    @patch('random.choice')
    @patch('random.randint')
    @patch('random.uniform')
    def test_throw_bomb_to_left(self, mock_uniform: MagicMock,
                                mock_randint: MagicMock,
                                mock_choice: MagicMock) -> None:
        """Test that bombs can be thrown to the left"""
        mock_choice.return_value = 'LEFT'
        mock_randint.return_value = 4  # 4 cells away
        mock_uniform.return_value = 3.0
        
        player_head = self.server.clients[self.player1_addr]['snake'][0]
        
        # Throw bomb
        self.server.handle_throw_bomb(self.player1_addr)
        
        bomb = self.server.bombs[0]
        
        # Verify bomb position (should be 4 cells to the LEFT of head)
        expected_pos = [player_head[0] - 4, player_head[1]]
        self.assertEqual(bomb['pos'], expected_pos)

    def test_cannot_throw_bomb_without_bombs(self):
        """Test that players cannot throw bombs when they have none"""
        # Set player bombs to 0
        self.server.clients[self.player1_addr]['bombs'] = 0
        
        # Try to throw bomb
        self.server.handle_throw_bomb(self.player1_addr)
        
        # Verify no bomb was created
        self.assertEqual(len(self.server.bombs), 0)

    def test_cannot_throw_bomb_when_dead(self):
        """Test that dead players cannot throw bombs"""
        # Kill player
        self.server.clients[self.player1_addr]['alive'] = False
        
        # Try to throw bomb
        self.server.handle_throw_bomb(self.player1_addr)
        
        # Verify no bomb was created
        self.assertEqual(len(self.server.bombs), 0)

    def test_explosion_3x3_area_headshot(self):
        """Test that explosions hit all snakes in 3x3 area and headshot kills"""
        # Place bomb at position (24, 15) which is 1 cell to the left of player2's head
        # Player2 head is at (25, 15)
        bomb_pos = [24, 15]
        explode_time = time.time() - 0.1  # Already expired
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        # Player 2's head at (25, 15) is within 3x3 explosion area centered at (24, 15)
        # 3x3 area: (23,14) to (25,16)
        # (25, 15) is inside this area
        
        # Process bomb explosions
        self.server.update_bombs()
        
        # Verify player 2 is dead (headshot)
        self.assertFalse(self.server.clients[self.player2_addr]['alive'],
                        "Player hit in head should be dead")
        self.assertEqual(self.server.clients[self.player2_addr]['bombs'], 0,
                        "Bombs should be reset to 0 after death")
        
        # Verify bomb was removed
        self.assertEqual(len(self.server.bombs), 0)

    def test_explosion_3x3_area_body_hit(self):
        """Test that body hits truncate snake from point of impact"""
        # Place bomb at position (24, 17) which hits player2's body (not head)
        # Player2 snake: [(25, 15), (25, 16), (25, 17), (25, 18), (25, 19)]
        # 3x3 area around (24, 17): x in [23,24,25], y in [16,17,18]
        # Snake segments in explosion: (25,16) at idx 1, (25,17) at idx 2, (25,18) at idx 3
        # The explosion will hit the FIRST segment found (lowest index), which is (25, 16) at index 1
        # This truncates the snake at index 1, leaving snake[:1] = [(25, 15)]
        
        bomb_pos = [24, 17]
        explode_time = time.time() - 0.1
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        initial_score = self.server.clients[self.player2_addr]['score']
        
        # Process bomb explosions
        self.server.update_bombs()
        
        # Verify player 2 is still alive (body hit, not head)
        self.assertTrue(self.server.clients[self.player2_addr]['alive'],
                       "Player hit in body should stay alive")
        
        # Verify snake was truncated at the first hit position (index 1)
        # After truncation at index 1: snake[:1] = [(25, 15)]
        remaining_snake = self.server.clients[self.player2_addr]['snake']
        self.assertEqual(len(remaining_snake), 1,
                        "Snake should be truncated to 1 segment")
        self.assertEqual(remaining_snake, [(25, 15)])
        
        # Verify score was deducted (50 points per removed segment)
        # 4 segments removed: (25, 16), (25, 17), (25, 18), (25, 19)
        expected_score = initial_score - (4 * 50)
        self.assertEqual(self.server.clients[self.player2_addr]['score'], expected_score)

    def test_explosion_doesnt_hit_outside_3x3_area(self):
        """Test that explosions don't hit snakes outside the 3x3 area"""
        # Place bomb at position (24, 15)
        # Player3 is at (30, 15) which is 6 cells away, outside 3x3 range
        
        bomb_pos = [24, 15]
        explode_time = time.time() - 0.1
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        initial_snake_length = len(self.server.clients[self.player3_addr]['snake'])
        
        # Process bomb explosions
        self.server.update_bombs()
        
        # Verify player 3 is unaffected
        self.assertTrue(self.server.clients[self.player3_addr]['alive'])
        self.assertEqual(len(self.server.clients[self.player3_addr]['snake']), 
                        initial_snake_length,
                        "Snake outside explosion range should be unaffected")

    def test_explosion_multiple_snakes_in_range(self):
        """Test that explosion hits multiple snakes if they're in range"""
        # Add player 2 and another snake within explosion range
        # Bomb at (24, 15), 3x3 area: (23,14) to (25,16)
        
        # Position player2's head at (25, 15) - inside range
        self.server.clients[self.player2_addr]['snake'] = [(25, 15), (25, 16)]
        self.server.clients[self.player2_addr]['snake_set'] = {(25, 15), (25, 16)}
        
        # Position player3's head at (23, 15) - also inside range
        self.server.clients[self.player3_addr]['snake'] = [(23, 15), (23, 16)]
        self.server.clients[self.player3_addr]['snake_set'] = {(23, 15), (23, 16)}
        
        bomb_pos = [24, 15]
        explode_time = time.time() - 0.1
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        # Process bomb explosions
        self.server.update_bombs()
        
        # Both players should be dead (headshots)
        self.assertFalse(self.server.clients[self.player2_addr]['alive'])
        self.assertFalse(self.server.clients[self.player3_addr]['alive'])

    def test_bomb_timer_not_expired(self):
        """Test that bombs don't explode before timer expires"""
        # Create bomb with future explosion time
        bomb_pos = [24, 15]
        explode_time = time.time() + 10.0  # 10 seconds in the future
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        # Process bomb explosions
        self.server.update_bombs()
        
        # Bomb should still exist (not exploded yet)
        self.assertEqual(len(self.server.bombs), 1)
        
        # Players should be unaffected
        self.assertTrue(self.server.clients[self.player2_addr]['alive'])
        self.assertTrue(self.server.clients[self.player3_addr]['alive'])

    def test_bomb_explosion_at_grid_edges(self):
        """Test that explosion area is properly bounded at grid edges"""
        # Place bomb at top-left corner
        bomb_pos = [0, 0]
        explode_time = time.time() - 0.1
        
        # Place a snake at (1, 1) which is within range
        self.server.clients[self.player2_addr]['snake'] = [(1, 1), (1, 2)]
        self.server.clients[self.player2_addr]['snake_set'] = {(1, 1), (1, 2)}
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        # Should not crash even though some explosion positions are out of bounds
        try:
            self.server.update_bombs()
            success = True
        except Exception:
            success = False
        
        self.assertTrue(success, "Explosion at grid edge should not crash")
        
        # Snake at (1,1) should be hit (it's within the 3x3 area)
        self.assertFalse(self.server.clients[self.player2_addr]['alive'])

    @patch('random.randint')
    def test_bombs_reset_on_respawn(self, mock_randint: MagicMock) -> None:
        """Test that bombs are reset to 0 when player respawns"""
        # Mock random position for respawn
        mock_randint.side_effect = [15, 15]
        
        # Kill player with bombs
        self.server.clients[self.player1_addr]['alive'] = False
        self.server.clients[self.player1_addr]['bombs'] = 5
        
        # Send respawn request
        respawn_message: Dict[str, Any] = {
            'type': 'update',
            'data': {'respawn': True}
        }
        
        self.server.handle_player_update(self.player1_addr, respawn_message)
        
        # Verify bombs are reset to 0
        self.assertTrue(self.server.clients[self.player1_addr]['alive'])
        self.assertEqual(self.server.clients[self.player1_addr]['bombs'], 0)

    def test_bombs_reset_on_death(self):
        """Test that bombs are reset to 0 when player dies"""
        # Player has bombs
        self.server.clients[self.player2_addr]['bombs'] = 4
        
        # Create headshot scenario
        bomb_pos = [25, 15]  # Player2's head position
        explode_time = time.time() - 0.1
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        # Process explosion
        self.server.update_bombs()
        
        # Verify bombs are reset
        self.assertFalse(self.server.clients[self.player2_addr]['alive'])
        self.assertEqual(self.server.clients[self.player2_addr]['bombs'], 0)

    def test_bombs_reset_on_leave_game(self):
        """Test that bombs are reset to 0 when player leaves game"""
        # Player has bombs
        self.server.clients[self.player1_addr]['bombs'] = 3
        
        # Leave game
        self.server.handle_leave_game(self.player1_addr)
        
        # Verify bombs are reset
        self.assertFalse(self.server.clients[self.player1_addr]['in_game'])
        self.assertEqual(self.server.clients[self.player1_addr]['bombs'], 0)

    def test_bombs_reset_on_start_game(self):
        """Test that bombs are reset to 0 when player starts game"""
        # Set player as not in game with some bombs
        self.server.clients[self.player1_addr]['in_game'] = False
        self.server.clients[self.player1_addr]['bombs'] = 5
        
        # Start game
        self.server.handle_start_game(self.player1_addr)
        
        # Verify bombs are reset
        self.assertTrue(self.server.clients[self.player1_addr]['in_game'])
        self.assertEqual(self.server.clients[self.player1_addr]['bombs'], 0)

    def test_explosion_snake_set_consistency(self):
        """Test that snake_set is properly updated after explosion truncation"""
        # Setup: Player2 with snake at specific positions
        self.server.clients[self.player2_addr]['snake'] = [
            (25, 15), (25, 16), (25, 17), (25, 18), (25, 19)
        ]
        self.server.clients[self.player2_addr]['snake_set'] = {
            (25, 15), (25, 16), (25, 17), (25, 18), (25, 19)
        }
        
        # Add these to occupied cells
        self.server.occupied_cells.update({(25, 15), (25, 16), (25, 17), (25, 18), (25, 19)})
        
        # Bomb at (25, 17) will have 3x3 area: x in [24,25,26], y in [16,17,18]
        # Snake segments in explosion: (25,16) at idx 1, (25,17) at idx 2, (25,18) at idx 3
        # First hit at index 1 truncates to snake[:1] = [(25, 15)]
        bomb_pos = [25, 17]
        explode_time = time.time() - 0.1
        
        bomb: Dict[str, Any] = {
            'pos': bomb_pos,
            'explode_time': explode_time,
            'owner': str(self.player1_addr),
            'thrower_name': 'BombThrower'
        }
        self.server.bombs.append(bomb)
        
        # Process explosion
        self.server.update_bombs()
        
        # Verify snake_set matches actual snake
        actual_snake = self.server.clients[self.player2_addr]['snake']
        snake_set = self.server.clients[self.player2_addr]['snake_set']
        
        # After explosion at first hit (index 1), snake should be [(25, 15)]
        self.assertEqual(len(actual_snake), 1)
        self.assertEqual(len(snake_set), 1)
        
        # Verify removed segments are not in snake_set
        self.assertNotIn((25, 16), snake_set)
        self.assertNotIn((25, 17), snake_set)
        self.assertNotIn((25, 18), snake_set)
        self.assertNotIn((25, 19), snake_set)
        
        # Verify remaining segment is in snake_set
        self.assertIn((25, 15), snake_set)
        
        # Verify removed segments are not in occupied_cells
        self.assertNotIn((25, 16), self.server.occupied_cells)
        self.assertNotIn((25, 17), self.server.occupied_cells)
        self.assertNotIn((25, 18), self.server.occupied_cells)
        self.assertNotIn((25, 19), self.server.occupied_cells)


if __name__ == '__main__':
    unittest.main()
