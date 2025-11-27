import socket
import threading
import time
import json
from typing import Dict, Tuple, Any

class GameServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 50000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        
        # Store connected clients: {client_address: {player_data}}
        self.clients: Dict[Tuple[str, int], dict] = {}
        
        # Game state
        self.game_state: Dict[str, Any] = {
            'players': {},
            'bricks': [],  # List of brick positions
            'timestamp': 0,
            'game_time': 0
        }
        
        # Game settings
        self.grid_width = 40
        self.grid_height = 30
        self.bricks = []  # Active bricks in the game
        
        # Color pool for players
        self.available_colors = [
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
        self.used_colors = set()  # Track colors currently in use
        self.max_players = 16  # Maximum number of players allowed
        
        self.running = False
        self.broadcast_interval = 0.5  # 2Hz = 0.5 seconds
        
    def start(self):
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
    
    def listen(self):
        """Listen for incoming UDP messages from clients"""
        while self.running:
            try:
                data, client_address = self.socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                # Handle different message types
                self.handle_client_message(client_address, message)
                
            except json.JSONDecodeError:
                print(f"❌ Received invalid JSON from {client_address}")
            except Exception as e:
                print(f"❌ Error receiving data: {e}")
    
    def handle_client_message(self, client_address: Tuple[str, int], message: dict):
        """Handle messages from clients"""
        message_type = message.get('type', '')
        
        if message_type == 'connect':
            self.handle_connect(client_address, message)
        elif message_type == 'disconnect':
            self.handle_disconnect(client_address)
        elif message_type == 'update':
            self.handle_player_update(client_address, message)
        elif message_type == 'ping':
            self.handle_ping(client_address)
        else:
            pass  # print(f"⚠️  Unknown message type: {message_type} from {client_address}")
    
    def get_safe_direction(self, x: int, y: int) -> str:
        """Get a safe initial direction that won't hit walls or other players within 2 steps"""
        import random
        
        # Collect all occupied positions from other players
        occupied = set()
        for client_data in self.clients.values():
            if client_data.get('alive', True):
                snake = client_data.get('snake', [])
                for segment in snake:
                    if isinstance(segment, tuple):
                        occupied.add(segment)
                    else:
                        occupied.add(tuple(segment))
        
        # Check each direction for safety (2 steps ahead)
        safe_directions = []
        
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
            directions = []
            if y >= 2:
                directions.append('UP')
            if y < self.grid_height - 2:
                directions.append('DOWN')
            if x >= 2:
                directions.append('LEFT')
            if x < self.grid_width - 2:
                directions.append('RIGHT')
            return random.choice(directions) if directions else 'RIGHT'
    
    def handle_connect(self, client_address: Tuple[str, int], message: dict):
        """Handle client connection"""
        player_name = message.get('player_name', f'Player_{len(self.clients) + 1}')
        
        if client_address not in self.clients:
            # Check if server is full
            if len(self.clients) >= self.max_players:
                # print(f"⛔ Server full! Rejected connection from {player_name} at {client_address[0]}:{client_address[1]}")
                
                # Send server full message
                full_msg = {
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
            
            self.clients[client_address] = {
                'player_name': player_name,
                'connected_at': time.time(),
                'last_seen': time.time(),
                'snake': [(start_x, start_y)],
                'direction': safe_direction,
                'score': 0,
                'alive': True,
                'color': color
            }
            
            # Add to game state
            self.game_state['players'][str(client_address)] = self.clients[client_address].copy()
            
            # print(f"✅ Client connected: {player_name} from {client_address[0]}:{client_address[1]}")
            # print(f"   Assigned color: RGB{color}")
            # print(f"   Total clients: {len(self.clients)}\n")
            
            # Send welcome message
            welcome_msg = {
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
    
    def handle_disconnect(self, client_address: Tuple[str, int]):
        """Handle client disconnection"""
        if client_address in self.clients:
            player_name = self.clients[client_address]['player_name']
            player_color = self.clients[client_address].get('color')
            
            # Free up the color for reuse
            if player_color and player_color in self.used_colors:
                self.used_colors.remove(player_color)
            
            del self.clients[client_address]
            
            # Remove from game state
            if str(client_address) in self.game_state['players']:
                del self.game_state['players'][str(client_address)]
            
            # print(f"❌ Client disconnected: {player_name} from {client_address[0]}:{client_address[1]}")
            # print(f"   Color RGB{player_color} is now available")
            # print(f"   Total clients: {len(self.clients)}\n")
    
    def handle_player_update(self, client_address: Tuple[str, int], message: dict):
        """Handle player state updates (direction changes, respawns)"""
        if client_address in self.clients:
            # Update player data
            player_data = message.get('data', {})
            
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
                
                self.clients[client_address]['snake'] = [(start_x, start_y)]
                self.clients[client_address]['direction'] = safe_direction
                self.clients[client_address]['score'] = new_score
                self.clients[client_address]['alive'] = True
                # print(f"🔄 {self.clients[client_address]['player_name']} respawned (score: {previous_score} → {new_score})")
            
            self.clients[client_address]['last_seen'] = time.time()
            
            # Update game state will happen in the game loop
    
    def calculate_brick_count(self):
        """Calculate how many bricks should be active based on player count"""
        player_count = len([c for c in self.clients.values() if c.get('alive', True)])
        if player_count == 0:
            return 0
        elif player_count == 1:
            return 1
        else:
            # 2-3 players: 2 bricks, 4-5 players: 3 bricks, etc.
            return 1 + ((player_count - 1) // 2) + 1
    
    def spawn_brick(self):
        """Spawn a brick at a random empty location"""
        import random
        
        # Collect all occupied positions
        occupied = set()
        for client_data in self.clients.values():
            snake = client_data.get('snake', [])
            for segment in snake:
                if isinstance(segment, tuple):
                    occupied.add(segment)
                else:
                    occupied.add(tuple(segment))
        
        # Add existing bricks to occupied
        for brick in self.bricks:
            occupied.add(tuple(brick))
        
        # Find random empty position
        max_attempts = 100
        for _ in range(max_attempts):
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            pos = (x, y)
            
            if pos not in occupied:
                self.bricks.append([x, y])
                # print(f"🧱 Brick spawned at ({x}, {y})")
                return True
        
        # print(f"⚠️  Could not find empty space for brick")
        return False
    
    def update_bricks(self):
        """Update brick count based on player count"""
        required_bricks = self.calculate_brick_count()
        
        # Add bricks if needed
        while len(self.bricks) < required_bricks:
            self.spawn_brick()
        
        # Remove excess bricks if needed (e.g., when players leave)
        while len(self.bricks) > required_bricks:
            if self.bricks:
                removed = self.bricks.pop()
                # print(f"🧱 Brick removed from ({removed[0]}, {removed[1]})")
    
    def check_brick_collection(self, client_address, snake):
        """Check if snake head collected a brick"""
        if not snake:
            return False
        
        head = tuple(snake[0]) if isinstance(snake[0], list) else snake[0]
        
        for i, brick in enumerate(self.bricks):
            brick_pos = tuple(brick)
            if head == brick_pos:
                # Snake collected brick
                client_data = self.clients[client_address]
                # print(f"🎉 {client_data['player_name']} collected a brick!")
                
                # Remove the brick
                self.bricks.pop(i)
                
                # Spawn new brick
                self.spawn_brick()
                
                return True
        
        return False
    
    def handle_ping(self, client_address: Tuple[str, int]):
        """Handle ping from client"""
        if client_address in self.clients:
            self.clients[client_address]['last_seen'] = time.time()
            
            # Send pong response
            pong_msg = {'type': 'pong', 'timestamp': time.time()}
            self.send_to_client(client_address, pong_msg)
    
    def update_game_logic(self):
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
                # print(f"💀 {client_data['player_name']} hit a wall!")
                continue
            
            # Check collision with own snake
            if new_head in snake:
                client_data['alive'] = False
                # print(f"💀 {client_data['player_name']} hit themselves!")
                continue
            
            # Check collision with other players' snakes
            collision = False
            for other_address, other_data in self.clients.items():
                if other_address != client_address and other_data.get('alive', True):
                    other_snake = other_data.get('snake', [])
                    if new_head in [tuple(pos) if isinstance(pos, list) else pos for pos in other_snake]:
                        client_data['alive'] = False
                        # print(f"💀 {client_data['player_name']} hit {other_data['player_name']}'s snake!")
                        collision = True
                        break
            
            if collision:
                continue
            
            # Add new head
            snake.insert(0, new_head)
            
            # Check if collected a brick
            collected_brick = self.check_brick_collection(client_address, snake)
            
            if collected_brick:
                # Snake grows (don't remove tail)
                client_data['score'] += 100  # Bonus points for collecting brick
            else:
                # Normal movement (remove tail)
                snake.pop()
            
            # Increase score for each move
            client_data['score'] += 1
            
            self.clients[client_address]['snake'] = snake
    
    def broadcast_game_state(self):
        """Broadcast game state to all connected clients at 2Hz"""
        while self.running:
            if self.clients:
                # Update brick count based on player count
                self.update_bricks()
                
                # Update game logic (move snakes, check collisions)
                self.update_game_logic()
                
                # Update game state timestamp
                self.game_state['timestamp'] = time.time()
                self.game_state['game_time'] += self.broadcast_interval
                
                # Update all players in game state
                for client_address, client_data in self.clients.items():
                    self.game_state['players'][str(client_address)] = client_data.copy()
                
                # Update bricks in game state
                self.game_state['bricks'] = self.bricks.copy()
                
                # Prepare broadcast message
                broadcast_msg = {
                    'type': 'game_state',
                    'state': self.game_state
                }
                
                # Send to all connected clients
                disconnected = []
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
                current_time = time.time()
                inactive = []
                for client_address, client_data in self.clients.items():
                    if current_time - client_data['last_seen'] > 10:
                        inactive.append(client_address)
                
                for client_address in inactive:
                    # print(f"⏱️  Client timeout: {client_address}")
                    self.handle_disconnect(client_address)
            
            time.sleep(self.broadcast_interval)
    
    def send_to_client(self, client_address: Tuple[str, int], message: dict):
        """Send message to specific client"""
        data = json.dumps(message).encode('utf-8')
        self.socket.sendto(data, client_address)
    
    def stop(self):
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
