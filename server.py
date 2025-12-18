import socket
import threading
import time
import json
import os
import logging
from typing import Dict, Tuple, Any, List, Set, Optional
from datetime import datetime

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    # Note: Logging not yet initialized at import time
    # Warning will be logged when server starts if msgpack not available

# Direction mappings for optimization
DIRECTION_TO_INT = {'UP': 0, 'DOWN': 1, 'LEFT': 2, 'RIGHT': 3}
INT_TO_DIRECTION = {0: 'UP', 1: 'DOWN', 2: 'LEFT', 3: 'RIGHT'}

def hash_address_to_player_id(address: Tuple[str, int]) -> int:
    """Hash IP:port tuple to a 2-byte integer (0-65535) for network efficiency.
    
    Reduces player ID from ~27 bytes to 2-3 bytes in messages.
    Uses simple hash that's deterministic and collision-resistant for small player counts.
    """
    # Combine IP and port into single string
    addr_str = f"{address[0]}:{address[1]}"
    # Python's hash() is deterministic within same process
    # Take modulo to fit in 16-bit unsigned int (0-65535)
    return hash(addr_str) & 0xFFFF

# Type alias for player data dictionary
PlayerData = Dict[str, Any]
# Type alias for bullet data dictionary  
BulletData = Dict[str, Any]
# Type alias for bomb data dictionary
BombData = Dict[str, Any]

class GameServer:
    mess_count: int = 0

    def __init__(self, host: str = '0.0.0.0', port: int = 50000) -> None:
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger('CloudsnakeServer')
        
        self.host = host
        self.port = port
        self.game_port = 50001  # Game communication port
        
        # Create control socket (port 50000) for connect, heartbeat, commands
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_socket.bind((self.host, self.port))
        
        # Create game socket (port 50001) for game controls and state updates
        self.game_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.game_socket.bind((self.host, self.game_port))
        
        # Map control addresses to their game socket addresses: {control_address: game_address}
        self.game_addresses: Dict[Tuple[str, int], Tuple[str, int]] = {}
        
        # Map player IDs to addresses: {player_id: client_address}
        self.id_to_address: Dict[int, Tuple[str, int]] = {}
        
        # Store connected clients: {client_address: {player_data}}
        self.clients: Dict[Tuple[str, int], PlayerData] = {}
        
        # Game state
        self.game_state: Dict[str, Any] = {
            'players': {},
            'bricks': [],  # List of brick positions
            'bullet_bricks': [],  # List of bullet brick positions
            'bomb_bricks': [],  # List of bomb brick positions
            'bullets': [],  # List of active bullets
            'bombs': [],  # List of active bombs
            'explosions': [],  # List of active explosions with positions and progress
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
        # Bomb bricks (special bricks that give bombs)
        self.bomb_bricks: List[List[int]] = []
        # Active explosions: list of dicts with {positions: [(x,y),...], start_time: float, duration: float}
        self.explosions: List[Dict[str, Any]] = []
        self.bomb_bricks_set: Set[Tuple[int, int]] = set()
        # Active bombs: list of dicts with {pos: (x,y), explode_time: float, owner: client_address}
        self.bombs: List[BombData] = []
        
        # Brick colors that should NOT be used for players:
        # - ORANGE (255, 140, 0) - regular bricks
        # - YELLOW (255, 185, 0) - regular brick border
        # - CYAN (0, 188, 212) - bullet bricks
        # - BLUE (0, 120, 215) - bullet brick border
        # - RED (237, 41, 57) - bomb bricks
        
        # Color pool for players (excluding brick colors)
        self.available_colors: List[Tuple[int, int, int]] = [
            (0, 255, 0),      # Green
            (255, 0, 255),    # Magenta
            (128, 0, 255),    # Purple
            (255, 192, 203),  # Pink
            (0, 255, 128),    # Spring Green
            (128, 255, 0),    # Chartreuse
            (64, 255, 64),    # Light Green
            (255, 128, 255),  # Light Magenta
            (160, 32, 240),   # Purple (darker)
            (255, 20, 147),   # Deep Pink
            (50, 205, 50),    # Lime Green
            (138, 43, 226),   # Blue Violet
            (0, 255, 200),    # Turquoise
            (200, 255, 0),    # Yellow-Green
            (255, 105, 180),  # Hot Pink
            (147, 112, 219),  # Medium Purple
        ]
        self.used_colors: Set[Tuple[int, int, int]] = set()  # Track colors currently in use
        self.max_players = 16  # Maximum number of players allowed
        
        self.running = False
        self.broadcast_interval = 0.25  # 4Hz = 0.25 seconds
        # Cached occupied cells for quick membership checks
        self.occupied_cells: set[Tuple[int, int]] = set()
        
        # Statistics tracking
        self.stats_file = 'player_stats.json'
        self.stats: Dict[str, Any] = self.load_stats()
    
    def setup_logging(self) -> None:
        """Configure logging for the server"""
        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create handlers
        file_handler = logging.FileHandler(os.path.join(log_dir, 'cloudsnake-server.log'))
        file_handler.setLevel(logging.DEBUG)  # Changed to DEBUG to capture all debug messages
        
        error_handler = logging.FileHandler(os.path.join(log_dir, 'cloudsnake-server-errors.log'))
        error_handler.setLevel(logging.ERROR)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        logging.basicConfig(
            level=logging.DEBUG,  # Changed to DEBUG to allow debug messages
            handlers=[file_handler, error_handler, console_handler]
        )
        
    def load_stats(self) -> Dict[str, Any]:
        """Load player statistics from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    stats = json.load(f)
                    logging.info(f"Loaded statistics for {len(stats.get('players', {}))} players")
                    return stats
            except Exception as e:
                logging.error(f"Error loading stats: {e}", exc_info=True)
                return self.create_empty_stats()
        logging.info("No existing stats file found, creating new one")
        return self.create_empty_stats()
    
    def create_empty_stats(self) -> Dict[str, Any]:
        """Create empty statistics structure"""
        return {
            'players': {},  # {player_name: {highscore, games_played, total_kills, total_deaths, last_seen}}
            'all_time_highscore': 0,
            'all_time_highscore_player': None,
            'total_games': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def save_stats(self) -> None:
        """Save player statistics to file"""
        try:
            self.stats['last_updated'] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            logging.debug("Statistics saved successfully")
        except Exception as e:
            logging.error(f"Error saving stats: {e}", exc_info=True)
    
    def update_player_stats(self, player_name: str, score: int, kills: int = 0, died: bool = False) -> None:
        """Update statistics for a player"""
        if player_name not in self.stats['players']:
            self.stats['players'][player_name] = {
                'highscore': 0,
                'games_played': 0,
                'total_kills': 0,
                'total_deaths': 0,
                'last_seen': datetime.now().isoformat()
            }
        
        player_stats = self.stats['players'][player_name]
        
        # Update highscore
        if score > player_stats['highscore']:
            player_stats['highscore'] = score
            
        # Update all-time highscore
        if score > self.stats['all_time_highscore']:
            self.stats['all_time_highscore'] = score
            self.stats['all_time_highscore_player'] = player_name
        
        # Update kills and deaths
        player_stats['total_kills'] += kills
        if died:
            player_stats['total_deaths'] += 1
        
        player_stats['last_seen'] = datetime.now().isoformat()
        
        # Save periodically
        self.save_stats()
    
    def get_top_players(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top players by highscore"""
        players = []
        for name, stats in self.stats['players'].items():
            players.append({
                'name': name,
                'highscore': stats['highscore'],
                'games_played': stats['games_played'],
                'total_kills': stats['total_kills'],
                'total_deaths': stats['total_deaths']
            })
        
        # Sort by highscore descending
        players.sort(key=lambda x: x['highscore'], reverse=True)
        return players[:limit]
        
    def start(self) -> None:
        """Start the server"""
        self.running = True
        self.logger.info(f"Starting game server on {self.host}:{self.port}")
        self.logger.info(f"Game socket listening on port {self.game_port}")
        self.logger.info(f"Max players: {self.max_players}")
        
        # Log msgpack availability
        if MSGPACK_AVAILABLE:
            self.logger.info("MessagePack enabled - optimized binary protocol active")
        else:
            self.logger.warning("MessagePack not installed - using JSON protocol (larger messages)")
            self.logger.warning("Install msgpack for 30% bandwidth reduction: pip install msgpack")
        
        # Start broadcast thread (game state at 2Hz)
        broadcast_thread = threading.Thread(target=self.broadcast_game_state, daemon=True)
        broadcast_thread.start()
        self.logger.info("Broadcast thread started")
        
        # Start leaderboard broadcast thread (slower updates at 0.2Hz / every 5 seconds)
        leaderboard_thread = threading.Thread(target=self.broadcast_leaderboard, daemon=True)
        leaderboard_thread.start()
        self.logger.info("Leaderboard broadcast thread started")
        
        # Start listening threads for both sockets
        control_thread = threading.Thread(target=self.listen_control, daemon=True)
        control_thread.start()
        self.logger.info("Control socket thread started")
        
        game_thread = threading.Thread(target=self.listen_game, daemon=True)
        game_thread.start()
        self.logger.info("Game socket thread started")
        
        self.logger.info("Server is ready and waiting for connections")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
            self.stop()
    
    def listen_control(self) -> None:
        """Listen for control messages on port 50000 (connect, heartbeat, commands)"""
        while self.running:
            client_address = None
            try:
                data, client_address = self.control_socket.recvfrom(1024)
                
                # Try msgpack first, fallback to JSON
                message = None
                try:
                    if MSGPACK_AVAILABLE:
                        try:
                            message = msgpack.unpackb(data, raw=False)
                        except msgpack.exceptions.ExtraData:
                            # Fallback to JSON if msgpack fails
                            message = json.loads(data.decode('utf-8'))
                    else:
                        message = json.loads(data.decode('utf-8'))
                except (ValueError, UnicodeDecodeError) as e:
                    # Binary msgpack data received but msgpack not available
                    addr_str = f"from {client_address}" if client_address else ""
                    self.logger.warning(f"Received binary data on control socket {addr_str}, but msgpack not installed. Install with: pip install msgpack")
                    continue
                
                if message is None:
                    continue
                
                # Handle control message types
                message_type: str = message.get('type', '')
                if message_type in ['connect', 'disconnect', 'ping']:
                    self.handle_client_message(client_address, message)
                else:
                    self.logger.warning(f"Unknown control message type '{message_type}' from {client_address}")
                
            except json.JSONDecodeError as e:
                addr_str = f"from {client_address}" if client_address else ""
                self.logger.warning(f"Received invalid JSON on control socket {addr_str}: {e}")
            except Exception as e:
                self.logger.error(f"Error receiving control data: {e}", exc_info=True)
    
    def listen_game(self) -> None:
        """Listen for game messages on port 50001 (game controls, actions)"""
        while self.running:
            game_address = None
            try:
                data, game_address = self.game_socket.recvfrom(1024)
                
                # Try msgpack first, fallback to JSON
                message = None
                try:
                    if MSGPACK_AVAILABLE:
                        try:
                            message = msgpack.unpackb(data, raw=False)
                        except msgpack.exceptions.ExtraData:
                            # Fallback to JSON if msgpack fails
                            message = json.loads(data.decode('utf-8'))
                    else:
                        message = json.loads(data.decode('utf-8'))
                except (ValueError, UnicodeDecodeError) as e:
                    # Binary msgpack data received but msgpack not available
                    addr_str = f"from {game_address}" if game_address else ""
                    self.logger.warning(f"Received binary data on game socket {addr_str}, but msgpack not installed. Install with: pip install msgpack")
                    continue
                
                if message is None:
                    continue
                
                # Find the control address for this game message
                # First, try to match by player_id in message (most reliable)
                player_id = message.get('player_id')
                control_address = None
                
                if player_id:
                    # player_id is now a short integer, look up full address
                    if isinstance(player_id, int):
                        control_address = self.id_to_address.get(player_id)
                        if control_address and control_address not in self.clients:
                            control_address = None
                    # Legacy fallback for old string-based IDs
                    elif isinstance(player_id, str):
                        import ast
                        try:
                            control_address = ast.literal_eval(player_id)
                            if control_address not in self.clients:
                                control_address = None
                        except:
                            control_address = None
                
                # Fallback: match by IP and port proximity (least reliable, but handles old clients)
                if not control_address:
                    client_ip = game_address[0]
                    # Check if there's already a mapping for this game address
                    for ctrl_addr, game_addr in self.game_addresses.items():
                        if game_addr == game_address:
                            control_address = ctrl_addr
                            break
                    
                    # If still not found, check unmapped clients from same IP
                    if not control_address:
                        for addr in self.clients.keys():
                            if addr[0] == client_ip and addr not in self.game_addresses:
                                control_address = addr
                                break
                
                if control_address:
                    # Register game socket address for this control address
                    self.game_addresses[control_address] = game_address
                    
                    # Handle game message types
                    message_type: str = message.get('type', '')
                    if message_type in ['update', 'shoot', 'throw_bomb', 'start_game', 'leave_game', 'lobby_ping']:
                        if message_type != 'lobby_ping':  # Don't process lobby_ping, just register address
                            self.handle_client_message(control_address, message)
                
            except json.JSONDecodeError as e:
                addr_str = f"from {game_address}" if game_address else ""
                self.logger.warning(f"Received invalid JSON on game socket {addr_str}: {e}")
            except Exception as e:
                self.logger.error(f"Error receiving game data: {e}", exc_info=True)
    
    def listen(self) -> None:
        """DEPRECATED: Old single-socket listen method"""
        pass
    
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
        elif message_type == 'throw_bomb':
            self.handle_throw_bomb(client_address)
        elif message_type == 'start_game':
            self.handle_start_game(client_address)
        elif message_type == 'leave_game':
            self.handle_leave_game(client_address)
    
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
        """Handle new client connections - players enter lobby first"""
        player_name: str = message.get('player_name', f'Player_{len(self.clients) + 1}')
        
        if client_address not in self.clients:
            self.logger.info(f"New connection: {player_name} from {client_address[0]}:{client_address[1]}")
            # Create minimal lobby entry (no game initialization yet)
            self.clients[client_address] = {
                'player_name': player_name,
                'connected_at': time.time(),
                'last_seen': time.time(),
                'snake': [],
                'snake_set': set(),
                'direction': 'RIGHT',
                'score': 0,
                'alive': False,
                'color': None,  # Color assigned when joining game
                'bullets': 0,
                'bombs': 0,
                'in_game': False  # Start in lobby
            }
            
            # Generate short player ID (2-byte int)
            player_id = hash_address_to_player_id(client_address)
            self.id_to_address[player_id] = client_address
            
            # Initialize player stats if new
            if player_name not in self.stats['players']:
                self.stats['players'][player_name] = {
                    'highscore': 0,
                    'games_played': 0,
                    'total_kills': 0,
                    'total_deaths': 0,
                    'last_seen': datetime.now().isoformat()
                }
            self.stats['players'][player_name]['last_seen'] = datetime.now().isoformat()
            self.save_stats()
            
            # Send welcome message (no color yet)
            welcome_msg: Dict[str, Any] = {
                'type': 'welcome',
                'message': f'Welcome to the lobby, {player_name}!',
                'player_id': player_id,
                'player_count': len(self.clients),
                'color': None
            }
            self.send_to_client(client_address, welcome_msg)
            self.logger.info(f"{player_name} entered the lobby (Total: {len(self.clients)} connected)")
            
            # Send metadata for all existing in-game players to the new client
            # This ensures the new client has name/color info for all active players
            for other_address, other_data in self.clients.items():
                if other_address != client_address and other_data.get('in_game', False):
                    other_color = other_data.get('color')
                    other_name = other_data.get('player_name')
                    if other_color and other_name:
                        color_int = (other_color[0] << 16) | (other_color[1] << 8) | other_color[2]
                        other_player_id = hash_address_to_player_id(other_address)
                        metadata_msg = {
                            'type': 'player_metadata',
                            'player_id': other_player_id,
                            'n': other_name,
                            'c': color_int
                        }
                        self.send_to_client(client_address, metadata_msg)
        else:
            # Client reconnecting
            self.clients[client_address]['last_seen'] = time.time()
            self.logger.debug(f"{player_name} reconnected from {client_address[0]}")
    
    def handle_disconnect(self, client_address: Tuple[str, int]) -> None:
        """Handle client disconnection"""
        if client_address in self.clients:
            player_name = self.clients[client_address]['player_name']
            player_color = self.clients[client_address].get('color')
            final_score = self.clients[client_address].get('score', 0)
            was_in_game = self.clients[client_address].get('in_game', False)
            
            self.logger.info(f"Player disconnected: {player_name} (Score: {final_score}, Was in game: {was_in_game})")
            
            # Update player statistics on disconnect (only if was in game)
            if was_in_game:
                self.update_player_stats(player_name, final_score)
            
            # Free up the color for reuse (only if color was assigned)
            if player_color and player_color in self.used_colors:
                self.used_colors.remove(player_color)
            
            # Remove occupied cells of this player
            snake_set = self.clients[client_address].get('snake_set', set())
            self.occupied_cells.difference_update(snake_set)
            
            # Remove game socket address mapping
            if client_address in self.game_addresses:
                del self.game_addresses[client_address]
            
            # Remove player ID mapping
            player_id = hash_address_to_player_id(client_address)
            if player_id in self.id_to_address:
                del self.id_to_address[player_id]
            
            del self.clients[client_address]
            
            # Note: game_state['players'] is rebuilt every broadcast from self.clients,
            # so no need to manually remove entries here
            
            remaining_players = len(self.clients)
            self.logger.info(f"Remaining players: {remaining_players}")
    
    def handle_player_update(self, client_address: Tuple[str, int], message: Dict[str, Any]) -> None:
        """Handle player state updates (direction changes, respawns)"""
        if client_address in self.clients:
            # Update player data
            player_data: Dict[str, Any] = message.get('data', {})
            
            # Only allow certain updates from client (direction, respawn)
            if 'direction' in player_data:
                new_direction = player_data['direction']
                current_direction = self.clients[client_address]['direction']
                
                # Prevent 180-degree turns (can't reverse direction)
                opposite_directions = {
                    'UP': 'DOWN',
                    'DOWN': 'UP',
                    'LEFT': 'RIGHT',
                    'RIGHT': 'LEFT'
                }
                
                # Only update if not trying to go in opposite direction
                if opposite_directions.get(current_direction) != new_direction:
                    self.clients[client_address]['direction'] = new_direction
            
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
                self.clients[client_address]['bombs'] = 0
                # Add new occupied cell
                self.occupied_cells.add(start_pos)
            
            self.clients[client_address]['last_seen'] = time.time()
            
            # Update game state will happen in the game loop
    
    def handle_start_game(self, client_address: Tuple[str, int]) -> None:
        """Handle player starting game (joining from lobby) - full game initialization"""
        if client_address not in self.clients:
            return
        
        player_name = self.clients[client_address]['player_name']
        
        # Check if game is full (count players already in game)
        players_in_game = len([c for c in self.clients.values() if c.get('in_game', False)])
        if players_in_game >= self.max_players:
            self.logger.warning(f"{player_name} tried to join full game ({players_in_game}/{self.max_players})")
            # Send game full message via game socket (since start_game came via game socket)
            # Game address should already be registered by listen_game() before this handler is called
            full_msg: Dict[str, Any] = {
                'type': 'game_full',
                'message': f'Game is full ({self.max_players}/{self.max_players} players). Please wait for a slot.',
                'max_players': self.max_players,
                'current_players': players_in_game
            }
            # Use game socket since request came via game socket
            game_address = self.game_addresses.get(client_address)
            if game_address:
                self.send_to_client(game_address, full_msg, use_game_socket=True)
            return
        
        import random
        
        # Allocate color (find first available)
        available = [c for c in self.available_colors if c not in self.used_colors]
        if not available:
            # No colors available (shouldn't happen if max_players <= len(available_colors))
            return
        
        color = available[0]
        self.used_colors.add(color)
        
        # Random starting position for snake
        start_x = random.randint(5, 35)
        start_y = random.randint(5, 25)
        
        # Get a safe initial direction
        safe_direction = self.get_safe_direction(start_x, start_y)
        
        # Initialize game state
        start_pos = (start_x, start_y)
        old_set = self.clients[client_address].get('snake_set', set())
        self.occupied_cells.difference_update(old_set)
        
        self.clients[client_address]['in_game'] = True
        self.clients[client_address]['alive'] = True
        self.clients[client_address]['snake'] = [start_pos]
        self.clients[client_address]['snake_set'] = {start_pos}
        self.clients[client_address]['direction'] = safe_direction
        self.clients[client_address]['score'] = 0
        self.clients[client_address]['color'] = color
        self.clients[client_address]['bullets'] = 0
        self.clients[client_address]['bombs'] = 0
        self.occupied_cells.add(start_pos)
        
        # Track game session start
        self.stats['players'][self.clients[client_address]['player_name']]['games_played'] += 1
        self.stats['total_games'] += 1
        self.save_stats()
        
        self.logger.info(f"{player_name} started game at ({start_x}, {start_y}) with color {color} (Players in game: {players_in_game + 1}/{self.max_players})")
        
        # Broadcast player metadata (name + color) to all clients
        # This optimization removes these fields from game_state updates (saves ~40-80 bytes per player per update)
        color_int = (color[0] << 16) | (color[1] << 8) | color[2]  # RGB to 0xRRGGBB
        player_id = hash_address_to_player_id(client_address)
        metadata_msg = {
            'type': 'player_metadata',
            'player_id': player_id,
            'n': player_name,
            'c': color_int
        }
        for other_client in self.clients:
            self.send_to_client(other_client, metadata_msg)
    
    def handle_leave_game(self, client_address: Tuple[str, int]) -> None:
        """Handle player leaving game (returning to lobby) - same as dying"""
        if client_address in self.clients:
            player_name = self.clients[client_address]['player_name']
            final_score = self.clients[client_address].get('score', 0)
            player_color = self.clients[client_address].get('color')
            
            self.logger.info(f"{player_name} left the game (Final score: {final_score})")
            
            # Update player statistics (treat as death)
            self.update_player_stats(player_name, final_score, died=True)
            
            # Free up the color for reuse
            if player_color and player_color in self.used_colors:
                self.used_colors.remove(player_color)
            
            # Mark as not in game and not alive
            self.clients[client_address]['in_game'] = False
            self.clients[client_address]['alive'] = False
            self.clients[client_address]['color'] = None
            self.clients[client_address]['bullets'] = 0
            self.clients[client_address]['bombs'] = 0
            
            # Remove from occupied cells
            old_set = self.clients[client_address].get('snake_set', set())
            self.occupied_cells.difference_update(old_set)
            old_set.clear()
    
    def calculate_brick_count(self) -> int:
        """Calculate how many bricks should be active based on player count"""
        player_count = len([c for c in self.clients.values() if c.get('alive', True) and c.get('in_game', True)])
        if player_count == 0:
            return 0
        elif player_count == 1:
            return 1
        else:
            # 2-3 players: 2 bricks, 4-5 players: 3 bricks, etc.
            return 1 + ((player_count - 1) // 2) + 1
    
    def spawn_brick(self) -> bool:
        """Spawn a brick at a random empty location (15% bullet brick, 15% bomb brick)"""
        import random
        
        # Use cached occupied cells and bricks_set
        occupied = set(self.occupied_cells)
        occupied.update(self.bricks_set)
        occupied.update(self.bullet_bricks_set)
        occupied.update(self.bomb_bricks_set)
        
        # Find random empty position
        max_attempts = 100
        for _ in range(max_attempts):
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            pos = (x, y)
            
            if pos not in occupied:
                # 15% chance of spawning a bomb brick
                rand_val = random.random()
                if rand_val < 0.15:
                    self.bomb_bricks.append([x, y])
                    self.bomb_bricks_set.add(pos)
                # 15% chance of spawning a bullet brick
                elif rand_val < 0.30:
                    self.bullet_bricks.append([x, y])
                    self.bullet_bricks_set.add(pos)
                else:
                    self.bricks.append([x, y])
                    self.bricks_set.add(pos)
                return True
        
        return False
    
    def update_bricks(self) -> None:
        """Update brick count based on player count"""
        required_bricks = self.calculate_brick_count()
        
        # Count total bricks (regular + bullet + bomb)
        total_bricks = len(self.bricks) + len(self.bullet_bricks) + len(self.bomb_bricks)
        
        # Add bricks if needed
        while total_bricks < required_bricks:
            self.spawn_brick()
            total_bricks = len(self.bricks) + len(self.bullet_bricks) + len(self.bomb_bricks)
        
        # Remove excess bricks ONLY when all players are dead (required_bricks == 0)
        if required_bricks == 0:
            while total_bricks > 0:
                # Remove regular bricks first, then bullet bricks, then bomb bricks
                if self.bricks:
                    removed = self.bricks.pop()
                    self.bricks_set.discard((removed[0], removed[1]))
                elif self.bullet_bricks:
                    removed = self.bullet_bricks.pop()
                    self.bullet_bricks_set.discard((removed[0], removed[1]))
                elif self.bomb_bricks:
                    removed = self.bomb_bricks.pop()
                    self.bomb_bricks_set.discard((removed[0], removed[1]))
                total_bricks = len(self.bricks) + len(self.bullet_bricks) + len(self.bomb_bricks)
    
    def check_brick_collection(self, client_address: Tuple[str, int], snake: List[Tuple[int, int]]) -> Optional[str]:
        """Check if snake head collected a brick, bullet brick, or bomb brick.
        Returns 'regular', 'bullet', 'bomb', or None."""
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
            # Give player a bullet (max 5)
            current_bullets = self.clients[client_address].get('bullets', 0)
            if current_bullets < 5:
                self.clients[client_address]['bullets'] = current_bullets + 1
            # Spawn new brick
            self.spawn_brick()
            return 'bullet'
        
        # Check for bomb brick collection
        if head in self.bomb_bricks_set:
            # Remove the bomb brick from both structures
            self.bomb_bricks_set.discard(head)
            for i, brick in enumerate(self.bomb_bricks):
                if (brick[0], brick[1]) == head:
                    self.bomb_bricks.pop(i)
                    break
            # Give player a bomb (max 5)
            current_bombs = self.clients[client_address].get('bombs', 0)
            if current_bombs < 5:
                self.clients[client_address]['bombs'] = current_bombs + 1
            # Spawn new brick
            self.spawn_brick()
            return 'bomb'
        
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
                'owner': str(client_address),
                'shooter_name': client_data.get('player_name', 'Unknown')
            }
            self.bullets.append(bullet)
    
    def handle_throw_bomb(self, client_address: Tuple[str, int]) -> None:
        """Handle throw bomb request from client"""
        if client_address in self.clients:
            client_data = self.clients[client_address]
            
            # Check if player has bombs and is alive
            if not client_data.get('alive', True):
                return
            
            bombs_count = client_data.get('bombs', 0)
            if bombs_count <= 0:
                return
            
            # Deduct bomb
            self.clients[client_address]['bombs'] = bombs_count - 1
            
            # Get player position and direction
            snake = client_data.get('snake', [])
            if not snake:
                return
            
            import random
            head = snake[0]
            direction = client_data.get('direction', 'RIGHT')
            
            # Throw bomb perpendicular to current direction (90 degrees)
            # Random distance between 2 and 5 cells
            distance = random.randint(2, 5)
            
            # Determine perpendicular directions based on current direction
            if direction in ['UP', 'DOWN']:
                # Moving vertically, throw horizontally (LEFT or RIGHT)
                throw_direction = random.choice(['LEFT', 'RIGHT'])
                if throw_direction == 'LEFT':
                    bomb_x = head[0] - distance
                else:  # RIGHT
                    bomb_x = head[0] + distance
                bomb_y = head[1]
            else:  # LEFT or RIGHT
                # Moving horizontally, throw vertically (UP or DOWN)
                throw_direction = random.choice(['UP', 'DOWN'])
                bomb_x = head[0]
                if throw_direction == 'UP':
                    bomb_y = head[1] - distance
                else:  # DOWN
                    bomb_y = head[1] + distance
            
            # Clamp position to grid bounds
            bomb_x = max(0, min(bomb_x, self.grid_width - 1))
            bomb_y = max(0, min(bomb_y, self.grid_height - 1))
            
            # Random explosion time between 2 and 4 seconds
            explode_time = time.time() + random.uniform(2.0, 4.0)
            
            # Create bomb
            bomb: BombData = {
                'pos': [bomb_x, bomb_y],  # [x, y] for JSON serialization
                'explode_time': explode_time,
                'owner': str(client_address),
                'thrower_name': client_data.get('player_name', 'Unknown')
            }
            self.bombs.append(bomb)
    
    def update_bullets(self) -> None:
        """Move bullets and check for collisions"""
        bullets_to_remove: List[int] = []
        
        for i, bullet in enumerate(self.bullets):
            x, y = bullet['pos']
            direction: str = bullet['direction']
            
            # Move bullet 3 times (triple speed - 3x snake speed)
            for _ in range(3):
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
                                victim_name = client_data['player_name']
                                victim_score = client_data.get('score', 0)
                                shooter_name = bullet.get('shooter_name', 'Unknown')
                                self.logger.info(f"💀 {shooter_name} headshotted {victim_name} (Score: {victim_score})")
                                client_data['alive'] = False
                                client_data['bullets'] = 0
                                client_data['bombs'] = 0
                                
                                # Update statistics for killer and victim
                                shooter_name = bullet.get('shooter_name', 'Unknown')
                                if shooter_name != 'Unknown':
                                    self.update_player_stats(shooter_name, 0, kills=1)
                                    # Award 250 points to the killer
                                    for addr, data in self.clients.items():
                                        if data.get('player_name') == shooter_name:
                                            data['score'] = data.get('score', 0) + 250
                                            break
                                self.update_player_stats(victim_name, victim_score, died=True)
                                
                                # Remove snake from occupied cells
                                snake_set = client_data.get('snake_set', set())
                                self.occupied_cells.difference_update(snake_set)
                                snake_set.clear()
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
                                shooter_name = bullet.get('shooter_name', 'Unknown')
                                victim_name = client_data['player_name']
                                self.logger.debug(f"{shooter_name} hit {victim_name}'s body, removed {len(removed_segments)} segments (-{score_deduction} points)")
                        
                        hit_occurred = True
                        bullets_to_remove.append(i)
                        break
                
                if hit_occurred:
                    break
        
        # Remove bullets that hit something or went out of bounds
        for i in reversed(sorted(set(bullets_to_remove))):
            if i < len(self.bullets):
                self.bullets.pop(i)
    
    def update_bombs(self) -> None:
        """Check bomb timers and handle explosions"""
        current_time = time.time()
        bombs_to_remove: List[int] = []
        
        for i, bomb in enumerate(self.bombs):
            explode_time = bomb.get('explode_time', 0)
            
            # Check if bomb should explode
            if current_time >= explode_time:
                bomb_x, bomb_y = bomb['pos']
                
                # 3x3 explosion area centered on bomb
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        explosion_x = bomb_x + dx
                        explosion_y = bomb_y + dy
                        
                        # Check bounds
                        if (explosion_x < 0 or explosion_x >= self.grid_width or
                            explosion_y < 0 or explosion_y >= self.grid_height):
                            continue
                        
                        explosion_pos = (explosion_x, explosion_y)
                        
                        # Check collision with snakes
                        for client_address, client_data in self.clients.items():
                            if not client_data.get('alive', True):
                                continue
                            
                            snake = client_data.get('snake', [])
                            if not snake:
                                continue
                            
                            # Check if explosion hit this snake
                            if explosion_pos in client_data.get('snake_set', set()):
                                # Find the hit position in the snake
                                hit_index = None
                                for idx, segment in enumerate(snake):
                                    if segment == explosion_pos:
                                        hit_index = idx
                                        break
                                
                                if hit_index is not None:
                                    # Check if it's a headshot (index 0)
                                    if hit_index == 0:
                                        # Kill the snake and clean up
                                        victim_name = client_data['player_name']
                                        victim_score = client_data.get('score', 0)
                                        thrower_name = bomb.get('thrower_name', 'Unknown')
                                        self.logger.info(f"💣 {thrower_name}'s bomb killed {victim_name} (Score: {victim_score})")
                                        client_data['alive'] = False
                                        client_data['bullets'] = 0
                                        client_data['bombs'] = 0
                                        
                                        # Update statistics for killer and victim
                                        thrower_name = bomb.get('thrower_name', 'Unknown')
                                        if thrower_name != 'Unknown':
                                            self.update_player_stats(thrower_name, 0, kills=1)
                                            # Award 250 points to the killer
                                            for addr, data in self.clients.items():
                                                if data.get('player_name') == thrower_name:
                                                    data['score'] = data.get('score', 0) + 250
                                                    break
                                        self.update_player_stats(victim_name, victim_score, died=True)
                                        
                                        # Remove snake from occupied cells
                                        snake_set = client_data.get('snake_set', set())
                                        self.occupied_cells.difference_update(snake_set)
                                        snake_set.clear()
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
                
                # Create explosion animation (3x3 area, 0.4 second duration)
                explosion_positions = []
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        exp_x = bomb_x + dx
                        exp_y = bomb_y + dy
                        if (0 <= exp_x < self.grid_width and 0 <= exp_y < self.grid_height):
                            explosion_positions.append([exp_x, exp_y])
                
                self.explosions.append({
                    'positions': explosion_positions,
                    'start_time': current_time,
                    'duration': 0.4  # 400ms animation
                })
                
                bombs_to_remove.append(i)
        
        # Remove exploded bombs
        for i in reversed(sorted(set(bombs_to_remove))):
            if i < len(self.bombs):
                self.bombs.pop(i)
    
    def update_explosions(self) -> None:
        """Remove expired explosion animations"""
        current_time = time.time()
        self.explosions = [exp for exp in self.explosions 
                          if current_time < exp['start_time'] + exp['duration']]
    
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
            # Skip players not in active game
            if not client_data.get('in_game', False):
                continue
                
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
                player_name = client_data['player_name']
                final_score = client_data.get('score', 0)
                self.logger.info(f"💥 {player_name} hit a wall (Score: {final_score})")
                client_data['alive'] = False
                client_data['bullets'] = 0
                client_data['bombs'] = 0
                self.update_player_stats(player_name, final_score, died=True)
                continue
            
            # Check collision with own snake via set membership
            if new_head in client_data.get('snake_set', set()):
                player_name = client_data['player_name']
                final_score = client_data.get('score', 0)
                self.logger.info(f"🔄 {player_name} collided with themselves (Score: {final_score})")
                client_data['alive'] = False
                client_data['bullets'] = 0
                client_data['bombs'] = 0
                self.update_player_stats(player_name, final_score, died=True)
                continue
            
            # Check collision with other players' snakes using global occupied cells
            if new_head in self.occupied_cells:
                # Collision with another snake - player dies
                player_name = client_data['player_name']
                final_score = client_data.get('score', 0)
                self.logger.info(f"🐍 {player_name} collided with another snake (Score: {final_score})")
                client_data['alive'] = False
                client_data['bullets'] = 0
                client_data['bombs'] = 0
                self.update_player_stats(player_name, final_score, died=True)
                # Remove snake from occupied cells
                snake_set = client_data.get('snake_set', set())
                self.occupied_cells.difference_update(snake_set)
                snake_set.clear()
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
                # Rebuild occupied_cells from alive players in game once per tick (safety sync)
                occ: Set[Tuple[int, int]] = set()
                for _addr, data in self.clients.items():
                    if data.get('alive', True) and data.get('in_game', False):
                        occ.update(data.get('snake_set', set()))
                self.occupied_cells = occ
                
                # Update brick count based on player count
                self.update_bricks()
                
                # Update bullets (move and check collisions)
                self.update_bullets()
                
                # Update bombs (check timers and explosions)
                self.update_bombs()
                self.update_explosions()
                
                # Update game logic (move snakes, check collisions)
                self.update_game_logic()
                
                # Update game state timestamp
                self.game_state['timestamp'] = time.time()
                self.game_state['game_time'] += self.broadcast_interval
                
                # Rebuild players sub-dict excluding non-serializable fields
                players_snapshot: Dict[int, PlayerData] = {}
                for client_address, client_data in self.clients.items():
                    # Convert direction string to int for network efficiency
                    direction_str = client_data.get('direction', 'RIGHT')
                    direction_int = DIRECTION_TO_INT.get(direction_str, 3)  # Default to RIGHT
                    
                    # Optimize snake transmission: send head + length instead of all segments
                    # This reduces a 50-segment snake from ~400 bytes to ~16 bytes
                    snake = client_data.get('snake', [])
                    if snake:
                        # Send only head position and length
                        # Client reconstructs snake based on direction and previous state
                        snake_data = [snake[0], len(snake)]  # [head_position, length]
                    else:
                        snake_data = []
                    
                    # Build a filtered dict with only dynamic data (short keys for network efficiency)
                    # Static data (name, color) is sent via metadata updates only
                    # Removed: n (name), c (color), ca/ls (timestamps), ig (redundant)
                    # Use short player ID (2-byte int) instead of full address string
                    filtered: PlayerData = {
                        's': snake_data,                          # snake (head + length only)
                        'd': direction_int,                        # direction (int)
                        'sc': client_data.get('score'),           # score
                        'a': client_data.get('alive'),            # alive
                        'bu': client_data.get('bullets', 0),      # bullets
                        'bo': client_data.get('bombs', 0)         # bombs
                    }
                    player_id = hash_address_to_player_id(client_address)
                    players_snapshot[player_id] = filtered
                self.game_state['players'] = players_snapshot
                
                # Update bricks and bullets in game state
                self.game_state['bricks'] = self.bricks.copy()
                self.game_state['bullet_bricks'] = self.bullet_bricks.copy()
                self.game_state['bomb_bricks'] = self.bomb_bricks.copy()
                self.game_state['bullets'] = self.bullets.copy()
                self.game_state['bombs'] = self.bombs.copy()
                self.game_state['explosions'] = self.explosions.copy()
                
                # Leaderboard is now broadcast separately at a slower rate
                
                # Prepare broadcast message
                broadcast_msg: Dict[str, Any] = {
                    'message_count': self.mess_count,
                    'type': 'game_state',
                    'state': self.game_state
                }
                self.mess_count += 1

                # Send only to clients that are in game
                disconnected: List[Tuple[str, int]] = []
                sent_count = 0
                for client_address, client_data in self.clients.items():
                    # Only send game state to clients actively in the game
                    if not client_data.get('in_game', False):
                        continue
                    
                    try:
                        # Use the game socket address for this control address
                        game_address = self.game_addresses.get(client_address)
                        
                        if game_address:
                            # Send to the registered game socket address
                            self.send_to_client(game_address, broadcast_msg, use_game_socket=True)
                            sent_count += 1
                        else:
                            # Client hasn't sent any game messages yet, skip
                            pass
                    except Exception as e:
                        self.logger.error(f"Error sending to {client_address}: {e}")
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
                    player_name = self.clients[client_address].get('player_name', 'Unknown')
                    self.logger.warning(f"Client timeout: {player_name} ({client_address[0]})")
                    self.handle_disconnect(client_address)
            
            time.sleep(self.broadcast_interval)
    
    def broadcast_leaderboard(self) -> None:
        """Broadcast leaderboard separately at slower rate (0.2Hz / every 5 seconds)"""
        leaderboard_interval = 5.0  # 5 seconds between leaderboard updates
        
        while self.running:
            if self.clients:
                # Prepare leaderboard message
                leaderboard_msg: Dict[str, Any] = {
                    'type': 'leaderboard',
                    'leaderboard': self.get_top_players(10),
                    'all_time_highscore': self.stats['all_time_highscore'],
                    'all_time_highscore_player': self.stats['all_time_highscore_player']
                }
                
                # Send to all clients (both in-game and lobby)
                for client_address, client_data in self.clients.items():
                    try:
                        # Use game socket address if available, otherwise control socket
                        game_address = self.game_addresses.get(client_address)
                        if game_address:
                            self.send_to_client(game_address, leaderboard_msg, use_game_socket=True)
                        else:
                            # Client hasn't registered game address yet, use control socket
                            self.send_to_client(client_address, leaderboard_msg, use_game_socket=False)
                    except Exception as e:
                        self.logger.error(f"Error sending leaderboard to {client_address}: {e}")
            
            time.sleep(leaderboard_interval)
    
    def send_to_client(self, client_address: Tuple[str, int], message: Dict[str, Any], use_game_socket: bool = False) -> None:
        """Send message to specific client
        
        Args:
            client_address: Client address tuple
            message: Message to send
            use_game_socket: If True, use game socket (port 50001), otherwise use control socket (port 50000)
        """
        # Use MessagePack if available (40-60% smaller), otherwise fallback to JSON
        if MSGPACK_AVAILABLE:
            data = msgpack.packb(message, use_bin_type=True)
        else:
            data = json.dumps(message).encode('utf-8')
        
        if use_game_socket:
            self.game_socket.sendto(data, client_address)
        else:
            self.control_socket.sendto(data, client_address)
    
    def stop(self) -> None:
        """Stop the server"""
        self.logger.info("Shutting down server...")
        self.running = False
        self.control_socket.close()
        self.game_socket.close()
        self.logger.info("Server stopped")

def main():
    server = GameServer()
    logger = logging.getLogger('Main')
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        server.stop()
    except Exception as e:
        logger.critical(f"Fatal server error: {e}", exc_info=True)
        server.stop()

if __name__ == "__main__":
    main()
