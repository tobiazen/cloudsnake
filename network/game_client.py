"""GameClient - Network communication for CloudSnake"""
import socket
import time
import json
from typing import Optional, Dict, Any


class GameClient:
    """Handle network communication with CloudSnake game server"""

    def __init__(self, server_ip: str, server_port: int = 50000, player_name: str = "Player"):
        self.server_ip = server_ip
        self.server_port = server_port
        self.game_port = 50001  # Game communication port
        self.server_address = (server_ip, server_port)
        self.game_address = (server_ip, self.game_port)
        self.player_name = player_name
        
        # Create UDP sockets
        # Control socket (port 50000): connect, heartbeat, commands
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.control_socket.settimeout(2.0)  # 2 second timeout for receiving
        
        # Game socket (port 50001): game controls, game state updates
        self.game_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.game_socket.settimeout(2.0)  # 2 second timeout for receiving
        
        # Client state
        self.connected = False  # Connected to server on control port
        self.in_game = False    # Connected to game on game port
        self.running = False
        self.player_id = None
        self.game_state = None
        self.last_update_time = time.time()
        self.update_timeout = 5.0  # 5 seconds timeout
        self.my_color = None  # Assigned by server
        
        # Player data (snake game)
        self.player_data = {
            'direction': 'RIGHT',  # Only track direction on client side
        }
    
    def connect(self) -> bool:
        """Connect to the game server"""
        print(f"🔌 Connecting to server at {self.server_ip}:{self.server_port}...")
        
        # Send connection message
        connect_msg = {
            'type': 'connect',
            'player_name': self.player_name
        }
        
        try:
            self.send_to_server(connect_msg)
            
            # Wait for welcome message
            data, addr = self.control_socket.recvfrom(1024)
            response = json.loads(data.decode('utf-8'))
            
            if response.get('type') == 'welcome':
                self.connected = True
                self.player_id = response.get('player_id')
                self.my_color = response.get('color')  # Will be None in lobby
                
                # Send initial message on game socket to register game address with server
                # This ensures we receive game state broadcasts even while in lobby
                lobby_msg = {
                    'type': 'lobby_ping',
                    'player_id': str(self.player_id)
                }
                self.send_to_server(lobby_msg, use_game_socket=True)
                
                # Don't join game yet - wait for user to click "Start Game"
                
                return True
            elif response.get('type') == 'server_full':
                return False
            
        except socket.timeout:
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
        
        return False
    
    def receive_messages(self) -> None:
        """Receive messages from server (game state updates on game socket)"""
        while self.running:
            try:
                data, addr = self.game_socket.recvfrom(4096)
                message = json.loads(data.decode('utf-8'))
                self.handle_server_message(message)
                
            except socket.timeout:
                # Timeout is normal, continue
                continue
            except json.JSONDecodeError:
                print("❌ Received invalid JSON from server")
            except Exception as e:
                if self.running:
                    print(f"❌ Error receiving data: {e}")
    
    def receive_control_messages(self) -> None:
        """Receive messages from server (pong responses on control socket)"""
        while self.running:
            try:
                data, addr = self.control_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                message_type = message.get('type', '')
                
                if message_type == 'pong':
                    # Heartbeat acknowledged
                    self.last_update_time = time.time()
                
            except socket.timeout:
                # Timeout is normal, continue
                continue
            except json.JSONDecodeError:
                pass
            except Exception:
                pass
    
    def handle_server_message(self, message: Dict[str, Any]) -> None:
        """Handle messages from server"""
        message_type: str = message.get('type', '')
        
        # Update last received time for any message from server
        self.last_update_time = time.time()
        
        if message_type == 'game_state':
            self.game_state = message.get('state')
            self.display_game_state()
            
            # Update my_color from game state if player is in game
            if self.player_id and self.game_state:
                players = self.game_state.get('players', {})
                if self.player_id in players:
                    player_data = players[self.player_id]
                    if player_data.get('in_game') and player_data.get('color'):
                        self.my_color = tuple(player_data['color'])
        elif message_type == 'pong':
            # Heartbeat acknowledged
            pass
        elif message_type == 'game_full':
            # Game is full, can't join
            print(f"⛔ {message.get('message', 'Game is full')}")
        elif message_type == 'server_full':
            # Server is full, can't connect
            print(f"⛔ {message.get('message', 'Server is full')}")
        elif message_type == 'welcome':
            # Already handled in connect()
            pass
        elif message_type == 'server_full':
            # Server is full
            print(f"⛔ {message.get('message', 'Server is full')}")
            self.connected = False
        else:
            print(f"⚠️  Unknown message type: {message_type}")
    
    def display_game_state(self) -> None:
        """Display current game state"""
        if not self.game_state:
            return
        
        players: Dict[str, Any] = self.game_state.get('players', {})
        
        # Update local direction from server's authoritative state
        if self.player_id and self.player_id in players:
            server_direction = players[self.player_id].get('direction')
            if server_direction:
                self.player_data['direction'] = server_direction
    
    def send_heartbeat(self) -> None:
        """Send periodic ping to server to maintain connection"""
        while self.running:
            if self.connected:
                ping_msg: Dict[str, str] = {'type': 'ping'}
                try:
                    self.send_to_server(ping_msg)
                except Exception:
                    pass
            
            time.sleep(2.0)
    
    def update_player_data(self) -> None:
        """Send player direction to server"""
        update_msg: Dict[str, Any] = {
            'type': 'update',
            'data': self.player_data
        }
        self.send_to_server(update_msg, use_game_socket=True)
    
    def shoot(self) -> None:
        """Send shoot request to server"""
        shoot_msg: Dict[str, str] = {
            'type': 'shoot'
        }
        self.send_to_server(shoot_msg, use_game_socket=True)
    
    def throw_bomb(self) -> None:
        """Send throw bomb request to server"""
        throw_bomb_msg: Dict[str, str] = {
            'type': 'throw_bomb'
        }
        self.send_to_server(throw_bomb_msg, use_game_socket=True)
    
    def respawn(self) -> None:
        """Request respawn from server"""
        respawn_msg: Dict[str, Any] = {
            'type': 'update',
            'data': {
                'respawn': True
            }
        }
        self.send_to_server(respawn_msg, use_game_socket=True)
    
    def send_to_server(self, message: Dict[str, Any], use_game_socket: bool = False) -> None:
        """Send message to server
        
        Args:
            message: Message to send
            use_game_socket: If True, use game socket (port 50001), otherwise use control socket (port 50000)
        """
        # Add player_id to game socket messages for proper client identification
        if use_game_socket and self.player_id:
            message['player_id'] = str(self.player_id)
        
        data = json.dumps(message).encode('utf-8')
        if use_game_socket:
            self.game_socket.sendto(data, self.game_address)
        else:
            self.control_socket.sendto(data, self.server_address)
    
    def disconnect(self) -> None:
        """Disconnect from server"""
        if self.connected:
            disconnect_msg: Dict[str, str] = {'type': 'disconnect'}
            try:
                self.send_to_server(disconnect_msg)
            except:
                pass
            
            self.connected = False
            print("\n👋 Disconnected from server")
    
    def check_connection_timeout(self) -> None:
        """Check if connection has timed out"""
        if self.connected:
            time_since_update = time.time() - self.last_update_time
            if time_since_update > self.update_timeout:
                self.connected = False
