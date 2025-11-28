import socket
import threading
import time
import json
from typing import Dict, Tuple, Any, List, Set, Optional

# Type alias for player data dictionary
PlayerData = Dict[str, Any]
# Type alias for bullet data dictionary  
BulletData = Dict[str, Any]

class GameServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 50000) -> None:
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        
        # Store connected clients: {client_address: {player_data}}
        self.clients: Dict[Tuple[str, int], PlayerData] = {}
        
        # Game state
        self.game_state: Dict[str, Any] = {
            'players': {},
            'bricks': [],  # List of brick positions
            'bullet_bricks': [],  # List of bullet brick positions
            'bullets': [],  # List of active bullets
            'timestamp': 0,
            'game_time': 0
        }
        
        # Game settings
        self.grid_width = 40
        self.grid_height = 30
        # Active bricks in the game (list for serialization) + set for O(1) checks
        self.bricks: List[List[int]] = []
        self.bricks_set: Set[Tuple[int, int]] = set()
        # Bullet bricks (special bricks that give bullets)
        self.bullet_bricks: List[List[int]] = []
        self.bullet_bricks_set: Set[Tuple[int, int]] = set()
        # Active bullets: list of dicts with {pos: (x,y), direction: str, owner: client_address}
        self.bullets: List[BulletData] = []
        
        # Color pool for players
        self.available_colors: List[Tuple[int, int, int]] = [
            (0, 255, 0),      # Green
            (255, 0, 0),      # Red
            (0, 100, 255),    # Blue
            (255, 255, 0),    # Yellow
            (255, 0, 255),    # Magenta
            (0, 255, 255),    # Cyan
            (255, 128, 0),    # Orange
            (128, 0, 255),    # Purple
            (255, 192, 203),  # Pink
            (0, 255, 128),    # Spring Green
            (128, 255, 0),    # Chartreuse
            (255, 64, 64),    # Light Red
            (64, 64, 255),    # Light Blue
            (255, 255, 128),  # Light Yellow
            (128, 255, 255),  # Light Cyan
            (255, 128, 255),  # Light Magenta
        ]
        self.used_colors: Set[Tuple[int, int, int]] = set()  # Track colors currently in use
        self.max_players = 16  # Maximum number of players allowed
        
        self.running = False
        self.broadcast_interval = 0.5  # 2Hz = 0.5 seconds
        # Cached occupied cells for quick membership checks
        self.occupied_cells: set[Tuple[int, int]] = set()
        
    def start(self) -> None:
        """Start the server"""
        self.running = True
        
        # print(f"🎮 Game Server started on {self.host}:{self.port}")
        # print(f"📡 Broadcasting game state at 2Hz (every {self.broadcast_interval}s)")
        # print("Waiting for clients to connect...\n")
        
        # Start broadcast thread
        broadcast_thread = threading.Thread(target=self.broadcast_game_state, daemon=True)
        broadcast_thread.start()
        
        # Start listening for client messages
        self.listen()
    
    def listen(self) -> None:
        """Listen for incoming UDP messages from clients"""
        while self.running:
            try:
                data, client_address = self.socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                # Handle different message types
                self.handle_client_message(client_address, message)
                
            except json.JSONDecodeError as e:
                print(f"❌ Received invalid JSON: {e}")
            except Exception as e:
                print(f"❌ Error receiving data: {e}")
    
    def handle_client_message(self, client_address: Tuple[str, int], message: Dict[str, Any]) -> None:
        """Handle messages from clients"""
        message_type: str = message.get('type', '')
        
        if message_type == 'connect':
            self.handle_connect(client_address, message)
        elif message_type == 'disconnect':
            self.handle_disconnect(client_address)
        elif message_type == 'update':
            self.handle_player_update(client_address, message)
        elif message_type == 'ping':
            self.handle_ping(client_address)
        elif message_type == 'shoot':
            self.handle_shoot(client_address)
        else:
            pass  # print(f"⚠️  Unknown message type: {message_type} from {client_address}")
    
    def get_safe_direction(self, x: int, y: int) -> str:
        """Get a safe initial direction that won't hit walls or other players within 2 steps"""
        import random
        
        # Use cached occupied cells
        occupied: Set[Tuple[int, int]] = self.occupied_cells
        
        # Check each direction for safety (2 steps ahead)
        safe_directions: List[str] = []
        
        # UP: check y-1 and y-2
        if y >= 2 and (x, y-1) not in occupied and (x, y-2) not in occupied:
            safe_directions.append('UP')
        
        # DOWN: check y+1 and y+2
        if y < self.grid_height - 2 and (x, y+1) not in occupied and (x, y+2) not in occupied:
            safe_directions.append('DOWN')
        
        # LEFT: check x-1 and x-2
        if x >= 2 and (x-1, y) not in occupied and (x-2, y) not in occupied:
            safe_directions.append('LEFT')
        
        # RIGHT: check x+1 and x+2
        if x < self.grid_width - 2 and (x+1, y) not in occupied and (x+2, y) not in occupied:
            safe_directions.append('RIGHT')
        
        # Return a random safe direction, or fallback to any direction if none are safe
        if safe_directions:
            return random.choice(safe_directions)
        else:
            # Fallback: choose direction away from nearest wall
            directions: List[str] = []
            if y >= 2:
                directions.append('UP')
            if y < self.grid_height - 2:
                directions.append('DOWN')
            if x >= 2:
                directions.append('LEFT')
            if x < self.grid_width - 2:
                directions.append('RIGHT')
            return random.choice(directions) if directions else 'RIGHT'
    
    def handle_connect(self, client_address: Tuple[str, int], message: Dict[str, Any]) -> None:
        """Handle new client connections"""
        player_name: str = message.get('player_name', f'Player_{len(self.clients) + 1}')
        
        if client_address not in self.clients:
            # Check if server is full
            if len(self.clients) >= self.max_players:
                # print(f"⛔ Server full! Rejected connection from {player_name} at {client_address[0]}:{client_address[1]}")
                
                # Send server full message
                full_msg: Dict[str, Any] = {
                    'type': 'server_full',
                    'message': f'Server is full ({self.max_players}/{self.max_players} players). Please try again later.',
                    'max_players': self.max_players,
                    'current_players': len(self.clients)
                }
                self.send_to_client(client_address, full_msg)
                return
            
            import random
            
            # Find an available color that's not in use
            available = [c for c in self.available_colors if c not in self.used_colors]
            
            if not available:
                # If all colors are used, generate a random color
                color = (
                    random.randint(50, 255),
                    random.randint(50, 255),
                    random.randint(50, 255)
                )
                pass  # print(f"⚠️  All predefined colors in use, generated random color: RGB{color}")
            else:
                # Assign the first available color
                color = available[0]
            
            # Mark color as used
            self.used_colors.add(color)
            
            # Random starting position for snake
            start_x = random.randint(5, 35)
            start_y = random.randint(5, 25)
        
            # Get a safe initial direction
            safe_direction = self.get_safe_direction(start_x, start_y)
        
            # Normalize snake storage to tuples and maintain a per-player set
            start_pos = (start_x, start_y)
            self.clients[client_address] = {
                'player_name': player_name,
                'connected_at': time.time(),
                'last_seen': time.time(),
                'snake': [start_pos],
                'snake_set': {start_pos},
                'direction': safe_direction,
                'score': 0,
                'alive': True,
                'color': color,
                'bullets': 0  # Starting bullet count
            }
            
            # Add to game state
            self.game_state['players'][str(client_address)] = self.clients[client_address].copy()
            
            # print(f"✅ Client connected: {player_name} from {client_address[0]}:{client_address[1]}")
            # print(f"   Assigned color: RGB{color}")
            # print(f"   Total clients: {len(self.clients)}\n")
            
            # Send welcome message
            welcome_msg: Dict[str, Any] = {
                'type': 'welcome',
                'message': f'Welcome to the game, {player_name}!',
                'player_id': str(client_address),
                'player_count': len(self.clients),
                'color': color
            }
            self.send_to_client(client_address, welcome_msg)
        else:
            # Client reconnecting
            self.clients[client_address]['last_seen'] = time.time()
            # print(f"🔄 Client reconnected: {player_name} from {client_address[0]}:{client_address[1]}")
    
    def handle_disconnect(self, client_address: Tuple[str, int]) -> None:
        """Handle client disconnection"""
        if client_address in self.clients:
            _player_name = self.clients[client_address]['player_name']
            player_color = self.clients[client_address].get('color')
            
            # Free up the color for reuse
            if player_color and player_color in self.used_colors:
                self.used_colors.remove(player_color)
            
            # Remove occupied cells of this player
            snake_set = self.clients[client_address].get('snake_set', set())
            self.occupied_cells.difference_update(snake_set)
            del self.clients[client_address]
            
            # Remove from game state
            if str(client_address) in self.game_state['players']:
                del self.game_state['players'][str(client_address)]
            
            # print(f"❌ Client disconnected: {player_name} from {client_address[0]}:{client_address[1]}")
            # print(f"   Color RGB{player_color} is now available")
            # print(f"   Total clients: {len(self.clients)}\n")
    
    def handle_player_update(self, client_address: Tuple[str, int], message: Dict[str, Any]) -> None:
        """Handle player state updates (direction changes, respawns)"""
        if client_address in self.clients:
            # Update player data
            player_data: Dict[str, Any] = message.get('data', {})
            
            # Only allow certain updates from client (direction, respawn)
            if 'direction' in player_data:
                self.clients[client_address]['direction'] = player_data['direction']
            
            if 'respawn' in player_data and player_data['respawn']:
                # Handle respawn
                import random
                start_x = random.randint(5, 35)
                start_y = random.randint(5, 25)
                
                # Keep half of previous score
                previous_score = self.clients[client_address].get('score', 0)
                new_score = previous_score // 2
                
                # Get a safe initial direction
                safe_direction = self.get_safe_direction(start_x, start_y)
                
                start_pos = (start_x, start_y)
                # Update snake and snake_set
                old_set = self.clients[client_address].get('snake_set', set())
                self.occupied_cells.difference_update(old_set)
                self.clients[client_address]['snake'] = [start_pos]
                self.clients[client_address]['snake_set'] = {start_pos}
                self.clients[client_address]['direction'] = safe_direction
                self.clients[client_address]['score'] = new_score
                self.clients[client_address]['alive'] = True
                self.clients[client_address]['bullets'] = 0
                # Add new occupied cell
                self.occupied_cells.add(start_pos)
                # print(f"🔄 {self.clients[client_address]['player_name']} respawned (score: {previous_score} → {new_score})")
            
            self.clients[client_address]['last_seen'] = time.time()
            
            # Update game state will happen in the game loop
    
    def calculate_brick_count(self) -> int:
        """Calculate how many bricks should be active based on player count"""
        player_count = len([c for c in self.clients.values() if c.get('alive', True)])
        if player_count == 0:
            return 0
        elif player_count == 1:
            return 1
        else:
            # 2-3 players: 2 bricks, 4-5 players: 3 bricks, etc.
            return 1 + ((player_count - 1) // 2) + 1
    
    def spawn_brick(self) -> bool:
        """Spawn a brick at a random empty location (5% chance of bullet brick)"""
        import random
        
        # Use cached occupied cells and bricks_set
        occupied = set(self.occupied_cells)
        occupied.update(self.bricks_set)
        occupied.update(self.bullet_bricks_set)
        
        # Find random empty position
        max_attempts = 100
        for _ in range(max_attempts):
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            pos = (x, y)
            
            if pos not in occupied:
                # 5% chance of spawning a bullet brick
                if random.random() < 0.05:
                    self.bullet_bricks.append([x, y])
                    self.bullet_bricks_set.add(pos)
                else:
                    self.bricks.append([x, y])
                    self.bricks_set.add(pos)
                return True
        
        # print(f"⚠️  Could not find empty space for brick")
        return False
    
    def update_bricks(self) -> None:
        """Update brick count based on player count"""
        required_bricks = self.calculate_brick_count()
        
        # Count total bricks (regular + bullet)
        total_bricks = len(self.bricks) + len(self.bullet_bricks)
        
        # Add bricks if needed
        while total_bricks < required_bricks:
            self.spawn_brick()
            total_bricks = len(self.bricks) + len(self.bullet_bricks)
        
        # Remove excess bricks if needed (e.g., when players leave)
        while total_bricks > required_bricks:
            # Remove regular bricks first, then bullet bricks
            if self.bricks:
                removed = self.bricks.pop()
                self.bricks_set.discard((removed[0], removed[1]))
            elif self.bullet_bricks:
                removed = self.bullet_bricks.pop()
                self.bullet_bricks_set.discard((removed[0], removed[1]))
            total_bricks = len(self.bricks) + len(self.bullet_bricks)
    
    def check_brick_collection(self, client_address: Tuple[str, int], snake: List[Tuple[int, int]]) -> Optional[str]:
        """Check if snake head collected a brick or bullet brick.
        Returns 'regular' for regular brick, 'bullet' for bullet brick, or None."""
        if not snake:
            return None
        
        head = snake[0]
        
        # Check for bullet brick collection
        if head in self.bullet_bricks_set:
            # Remove the bullet brick from both structures
            self.bullet_bricks_set.discard(head)
            for i, brick in enumerate(self.bullet_bricks):
                if (brick[0], brick[1]) == head:
                    self.bullet_bricks.pop(i)
                    break
            # Give player a bullet
            self.clients[client_address]['bullets'] = self.clients[client_address].get('bullets', 0) + 1
            # Spawn new brick
            self.spawn_brick()
            return 'bullet'
        
        # Check for regular brick collection
        if head in self.bricks_set:
            # Remove the brick from both structures
            self.bricks_set.discard(head)
            # Also remove from list (find and remove once)
            for i, brick in enumerate(self.bricks):
                if (brick[0], brick[1]) == head:
                    self.bricks.pop(i)
                    break
            # Spawn new brick
            self.spawn_brick()
            return 'regular'
        
        return None
    
    def handle_shoot(self, client_address: Tuple[str, int]) -> None:
        """Handle shoot request from client"""
        if client_address in self.clients:
            client_data = self.clients[client_address]
            
            # Check if player has bullets and is alive
            if not client_data.get('alive', True):
                return
            
            bullets_count = client_data.get('bullets', 0)
            if bullets_count <= 0:
                return
            
            # Deduct bullet
            self.clients[client_address]['bullets'] = bullets_count - 1
            
            # Get player position and direction
            snake = client_data.get('snake', [])
            if not snake:
                return
            
            head = snake[0]
            direction = client_data.get('direction', 'RIGHT')
            
            # Create bullet at head position moving in player's direction
            bullet: BulletData = {
                'pos': list(head),  # [x, y] for JSON serialization
                'direction': direction,
                'owner': str(client_address)
            }
            self.bullets.append(bullet)
    
    def update_bullets(self) -> None:
        """Move bullets and check for collisions"""
        bullets_to_remove: List[int] = []
        
        for i, bullet in enumerate(self.bullets):
            x, y = bullet['pos']
            direction: str = bullet['direction']
            
            # Move bullet twice (double speed)
            for _ in range(2):
                # Calculate new position
                if direction == 'UP':
                    y -= 1
                elif direction == 'DOWN':
                    y += 1
                elif direction == 'LEFT':
                    x -= 1
                elif direction == 'RIGHT':
                    x += 1
                
                # Check wall collision
                if x < 0 or x >= self.grid_width or y < 0 or y >= self.grid_height:
                    bullets_to_remove.append(i)
                    break
                
                bullet['pos'] = [x, y]
                bullet_pos = (x, y)
                
                # Check collision with snakes
                hit_occurred = False
                for _bullet_client_address, client_data in self.clients.items():
                    if not client_data.get('alive', True):
                        continue
                    
                    snake = client_data.get('snake', [])
                    if not snake:
                        continue
                    
                    # Check if bullet hit this snake
                    if bullet_pos in client_data.get('snake_set', set()):
                        # Find the hit position in the snake
                        hit_index = None
                        for idx, segment in enumerate(snake):
                            if segment == bullet_pos:
                                hit_index = idx
                                break
                        
                        if hit_index is not None:
                            # Check if it's a headshot (index 0)
                            if hit_index == 0:
                                # Kill the snake and clean up
                                client_data['alive'] = False
                                client_data['bullets'] = 0
                                
                                # Remove snake from occupied cells
                                snake_set = client_data.get('snake_set', set())
                                self.occupied_cells.difference_update(snake_set)
                                snake_set.clear()
                                
                                # print(f"💀 {client_data['player_name']} was headshotted!")
                            else:
                                # Truncate snake after hit position
                                removed_segments = snake[hit_index:]
                                snake[:] = snake[:hit_index]
                                
                                # Update snake_set
                                snake_set = client_data.get('snake_set', set())
                                for seg in removed_segments:
                                    snake_set.discard(seg)
                                    self.occupied_cells.discard(seg)
                                
                                # Deduct score (50 points per removed segment)
                                score_deduction = len(removed_segments) * 50
                                client_data['score'] = max(0, client_data.get('score', 0) - score_deduction)
                        
                        hit_occurred = True
                        bullets_to_remove.append(i)
                        break
                
                if hit_occurred:
                    break
        
        # Remove bullets that hit something or went out of bounds
        for i in reversed(sorted(set(bullets_to_remove))):
            if i < len(self.bullets):
                self.bullets.pop(i)
    
    def handle_ping(self, client_address: Tuple[str, int]) -> None:
        """Handle ping from client"""
        if client_address in self.clients:
            self.clients[client_address]['last_seen'] = time.time()
            
            # Send pong response
            pong_msg: Dict[str, Any] = {'type': 'pong', 'timestamp': time.time()}
            self.send_to_client(client_address, pong_msg)
    
    def update_game_logic(self) -> None:
        """Update snake positions and check collisions"""
        
        for client_address, client_data in list(self.clients.items()):
            if not client_data.get('alive', True):
                continue
            
            snake = client_data['snake']
            direction = client_data['direction']
            
            if not snake:
                continue
            
            head_x, head_y = snake[0]
            
            # Calculate new head position
            if direction == 'UP':
                new_head = (head_x, head_y - 1)
            elif direction == 'DOWN':
                new_head = (head_x, head_y + 1)
            elif direction == 'LEFT':
                new_head = (head_x - 1, head_y)
            elif direction == 'RIGHT':
                new_head = (head_x + 1, head_y)
            else:
                continue
            
            # Check collision with walls
            if (new_head[0] < 0 or new_head[0] >= self.grid_width or
                new_head[1] < 0 or new_head[1] >= self.grid_height):
                client_data['alive'] = False
                client_data['bullets'] = 0
                # print(f"💀 {client_data['player_name']} hit a wall!")
                continue
            
            # Check collision with own snake via set membership
            if new_head in client_data.get('snake_set', set()):
                client_data['alive'] = False
                client_data['bullets'] = 0
                # print(f"💀 {client_data['player_name']} hit themselves!")
                continue
            
            # Check collision with other players' snakes using global occupied cells
            collision = False
            if new_head in self.occupied_cells:
                # If it's in occupied, ensure it's not own body (already checked) and belongs to another
                collision = True
            
            if collision:
                continue
            
            # Add new head
            snake.insert(0, new_head)
            # Update per-player set and global occupied
            client_data.setdefault('snake_set', set()).add(new_head)
            self.occupied_cells.add(new_head)
            
            # Check if collected a brick
            collected_brick = self.check_brick_collection(client_address, snake)
            
            if collected_brick == 'regular':
                # Snake grows (don't remove tail) and award points
                client_data['score'] += 100  # Bonus points for collecting brick
            elif collected_brick == 'bullet':
                # Bullet brick collected - remove tail (no growth, no bonus points)
                tail = snake.pop()
                # Update sets for tail removal
                client_data.get('snake_set', set()).discard(tail)
                self.occupied_cells.discard(tail)
            else:
                # Normal movement (remove tail)
                tail = snake.pop()
                # Update sets for tail removal
                client_data.get('snake_set', set()).discard(tail)
                self.occupied_cells.discard(tail)
            
            # Increase score for each move
            client_data['score'] += 1
            
            self.clients[client_address]['snake'] = snake
    
    def broadcast_game_state(self) -> None:
        """Broadcast game state to all connected clients at 2Hz"""
        while self.running:
            if self.clients:
                # Rebuild occupied_cells from alive players once per tick (safety sync)
                occ: Set[Tuple[int, int]] = set()
                for _addr, data in self.clients.items():
                    if data.get('alive', True):
                        occ.update(data.get('snake_set', set()))
                self.occupied_cells = occ
                
                # Update brick count based on player count
                self.update_bricks()
                
                # Update bullets (move and check collisions)
                self.update_bullets()
                
                # Update game logic (move snakes, check collisions)
                self.update_game_logic()
                
                # Update game state timestamp
                self.game_state['timestamp'] = time.time()
                self.game_state['game_time'] += self.broadcast_interval
                
                # Rebuild players sub-dict excluding non-serializable fields
                players_snapshot: Dict[str, PlayerData] = {}
                for client_address, client_data in self.clients.items():
                    # Build a filtered dict (exclude snake_set)
                    filtered: PlayerData = {
                        'player_name': client_data.get('player_name'),
                        'connected_at': client_data.get('connected_at'),
                        'last_seen': client_data.get('last_seen'),
                        'snake': client_data.get('snake'),  # list of tuple positions OK (tuples JSON → lists)
                        'direction': client_data.get('direction'),
                        'score': client_data.get('score'),
                        'alive': client_data.get('alive'),
                        'color': client_data.get('color'),
                        'bullets': client_data.get('bullets', 0)
                    }
                    players_snapshot[str(client_address)] = filtered
                self.game_state['players'] = players_snapshot
                
                # Update bricks and bullets in game state
                self.game_state['bricks'] = self.bricks.copy()
                self.game_state['bullet_bricks'] = self.bullet_bricks.copy()
                self.game_state['bullets'] = self.bullets.copy()
                
                # Prepare broadcast message
                broadcast_msg: Dict[str, Any] = {
                    'type': 'game_state',
                    'state': self.game_state
                }
                
                # Send to all connected clients
                disconnected: List[Tuple[str, int]] = []
                for client_address in self.clients:
                    try:
                        self.send_to_client(client_address, broadcast_msg)
                    except Exception as e:
                        print(f"❌ Error sending to {client_address}: {e}")
                        disconnected.append(client_address)
                
                # Remove disconnected clients
                for client_address in disconnected:
                    self.handle_disconnect(client_address)
                
                # Check for inactive clients (timeout after 10 seconds)
                current_time: float = time.time()
                inactive: List[Tuple[str, int]] = []
                for client_address, client_data in self.clients.items():
                    if current_time - client_data['last_seen'] > 10:
                        inactive.append(client_address)
                
                for client_address in inactive:
                    # print(f"⏱️  Client timeout: {client_address}")
                    self.handle_disconnect(client_address)
            
            time.sleep(self.broadcast_interval)
    
    def send_to_client(self, client_address: Tuple[str, int], message: Dict[str, Any]) -> None:
        """Send message to specific client"""
        data = json.dumps(message).encode('utf-8')
        self.socket.sendto(data, client_address)
    
    def stop(self) -> None:
        """Stop the server"""
        self.running = False
        self.socket.close()
        # print("\n🛑 Server stopped")

def main():
    # print("="*60)
    # print("🎮 GAME SERVER")
    # print("="*60)
    
    server = GameServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        # print("\n\n⚠️  Shutting down server...")
        server.stop()
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        server.stop()

if __name__ == "__main__":
    main()
