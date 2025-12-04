import socket
import threading
import time
import json
import pygame
import os
from typing import Optional, Dict, Any, Tuple

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
FPS = 60

# Colors - Enhanced palette
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (80, 80, 80)
LIGHT_GRAY = (240, 240, 240)
GREEN = (34, 177, 76)
DARK_GREEN = (25, 130, 55)
RED = (237, 41, 57)
DARK_RED = (180, 30, 43)
BLUE = (0, 120, 215)
DARK_BLUE = (0, 90, 160)
YELLOW = (255, 185, 0)
DARK_YELLOW = (200, 145, 0)
ORANGE = (255, 140, 0)
PURPLE = (136, 23, 152)
CYAN = (0, 188, 212)

# Fonts: ensure Unicode-capable font for icons (e.g., '▼', '✕')
def get_unicode_font(size: int) -> pygame.font.Font:
    """Return a pygame Font with good Unicode coverage (fallbacks to default)."""
    try:
        # Try common Unicode-capable fonts
        font_path = pygame.font.match_font('dejavusans,arial unicode ms,noto sans,liberation sans')
        if font_path:
            return pygame.font.Font(font_path, size)
    except Exception:
        pass
    # Fallback to default font
    return pygame.font.Font(None, size)

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        import sys
        base_path = sys._MEIPASS  # type: ignore
        print(f"DEBUG: Running in PyInstaller bundle, base_path: {base_path}")
    except Exception:
        base_path = os.path.abspath(".")
        print(f"DEBUG: Running in development mode, base_path: {base_path}")
    
    full_path = os.path.join(base_path, relative_path)
    
    # Debug: list what's in the assets directory
    assets_dir = os.path.join(base_path, 'assets')
    if os.path.exists(assets_dir):
        print(f"DEBUG: Contents of assets directory:")
        try:
            for item in os.listdir(assets_dir):
                print(f"  - {item}")
        except Exception as e:
            print(f"  ERROR listing directory: {e}")
    else:
        print(f"DEBUG: Assets directory does not exist at: {assets_dir}")
    
    return full_path

# UI Colors
BG_COLOR = (15, 15, 25)
PANEL_BG = (25, 25, 40)
BORDER_COLOR = (60, 60, 80)
HIGHLIGHT_COLOR = (80, 80, 120)
TEXT_COLOR = (220, 220, 230)
TEXT_SHADOW = (10, 10, 15)

class GameClient:
    def __init__(self, server_ip: str, server_port: int = 50000, player_name: str = "Player"):
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_address = (server_ip, server_port)
        self.player_name = player_name
        
        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2.0)  # 1 second timeout for receiving
        
        # Client state
        self.connected = False
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
            data, addr = self.socket.recvfrom(1024)
            response = json.loads(data.decode('utf-8'))
            
            if response.get('type') == 'welcome':
                self.connected = True
                self.player_id = response.get('player_id')
                self.my_color = response.get('color', (0, 255, 0))
                # print(f"✅ Connected successfully!")
                # print(f"   {response.get('message')}")
                # print(f"   Player ID: {self.player_id}")
                # print(f"   Assigned color: RGB{self.my_color}")
                # print(f"   Players online: {response.get('player_count')}\n")
                return True
            elif response.get('type') == 'server_full':
                # print(f"⛔ Server is full!")
                # print(f"   {response.get('message')}")
                # print(f"   {response.get('current_players')}/{response.get('max_players')} players connected\n")
                return False
            
        except socket.timeout:
            # print("❌ Connection timeout - server not responding")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
        
        return False
    
    def start(self) -> None:
        """Start the client"""
        if not self.connected:
            if not self.connect():
                return
        
        self.running = True
        
        # Start receive thread
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()
        
        # Start heartbeat thread (send ping every 2 seconds)
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # Main client loop
        self.run()
    
    def receive_messages(self) -> None:
        """Receive messages from server"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
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
    
    def handle_server_message(self, message: Dict[str, Any]) -> None:
        """Handle messages from server"""
        message_type: str = message.get('type', '')
        
        # Update last received time for any message from server
        self.last_update_time = time.time()
        
        if message_type == 'game_state':
            self.game_state = message.get('state')
            self.display_game_state()
        elif message_type == 'pong':
            # Heartbeat acknowledged
            pass
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
        game_time: float = self.game_state.get('game_time', 0)
        
        # Update local direction from server's authoritative state
        if self.player_id and self.player_id in players:
            server_direction = players[self.player_id].get('direction')
            if server_direction:
                self.player_data['direction'] = server_direction
            # Update in_game status from server
            server_in_game = players[self.player_id].get('in_game', False)
            # Note: We don't update GUI's in_game here - GUI manages it separately
        
        # Clear previous output (simple approach)
        # print("\n" + "="*60)
        # print(f"🎮 GAME STATE (Time: {game_time:.1f}s)")
        # print("="*60)
        
        if players:
            # print(f"👥 Players online: {len(players)}")

            for player_id, player_info in players.items():
                name = player_info.get('player_name', 'Unknown')
                x = player_info.get('x', 0)
                y = player_info.get('y', 0)
                score = player_info.get('score', 0)
                
                indicator = "⭐ (You)" if player_id == self.player_id else ""
                pass  # print(f"  {name} {indicator}")
                # print(f"    Position: ({x}, {y}) | Score: {score}")
        else:
            pass  # print("No players online")
        
        # print("="*60)
    
    def send_heartbeat(self) -> None:
        """Send periodic ping to server to maintain connection"""
        while self.running:
            if self.connected:
                ping_msg: Dict[str, str] = {'type': 'ping'}
                try:
                    self.send_to_server(ping_msg)
                except Exception as e:
                    print(f"❌ Error sending heartbeat: {e}")
            
            time.sleep(2.0)
    
    def update_player_data(self) -> None:
        """Send player direction to server"""
        update_msg: Dict[str, Any] = {
            'type': 'update',
            'data': self.player_data
        }
        
        self.send_to_server(update_msg)
    
    def shoot(self) -> None:
        """Send shoot request to server"""
        shoot_msg: Dict[str, str] = {
            'type': 'shoot'
        }
        self.send_to_server(shoot_msg)
    
    def throw_bomb(self) -> None:
        """Send throw bomb request to server"""
        throw_bomb_msg: Dict[str, str] = {
            'type': 'throw_bomb'
        }
        self.send_to_server(throw_bomb_msg)
    
    def respawn(self) -> None:
        """Request respawn from server"""
        respawn_msg: Dict[str, Any] = {
            'type': 'update',
            'data': {
                'respawn': True
            }
        }
        self.send_to_server(respawn_msg)
    
    def send_to_server(self, message: Dict[str, Any]) -> None:
        """Send message to server"""
        data = json.dumps(message).encode('utf-8')
        self.socket.sendto(data, self.server_address)
    
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
                print(f"⚠️  Connection timeout: No updates for {time_since_update:.1f}s")
                self.connected = False
    
    def run(self) -> None:
        """Main client loop - for background operation with GUI"""
        while self.running:
            self.check_connection_timeout()
            time.sleep(0.1)

class InputBox:
    """Simple input box for text entry"""
    def __init__(self, x: int, y: int, w: int, h: int, text: str = '') -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.color = BORDER_COLOR
        self.text = text
        # ~30% smaller than original then minus 12% more -> 23
        self.font = get_unicode_font(23)
        self.active = False
        
    def handle_event(self, event: Any) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = CYAN if self.active else BORDER_COLOR
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return False
    
    def draw(self, screen: Any) -> None:
        # Draw box background
        pygame.draw.rect(screen, PANEL_BG, self.rect)
        # Draw border
        border_color = CYAN if self.active else self.color
        pygame.draw.rect(screen, border_color, self.rect, 2)
        # Draw text
        txt_surface = self.font.render(self.text, True, TEXT_COLOR)
        screen.blit(txt_surface, (self.rect.x + 5, self.rect.y + 5))

class Button:
    """Simple button widget"""
    def __init__(self, x: int, y: int, w: int, h: int, text: str, color: Tuple[int, int, int] = BLUE) -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = (min(color[0] + 30, 255), min(color[1] + 30, 255), min(color[2] + 30, 255))
        # ~30% smaller than original then minus 12% more -> 23
        self.font = get_unicode_font(23)
        self.hovered = False
        
    def handle_event(self, event: Any) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False
    
    def draw(self, screen: Any) -> None:
        color = self.hover_color if self.hovered else self.color
        # Draw button with shadow effect
        shadow_rect = pygame.Rect(self.rect.x + 2, self.rect.y + 2, self.rect.width, self.rect.height)
        pygame.draw.rect(screen, (0, 0, 0, 50), shadow_rect)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BORDER_COLOR, self.rect, 2)
        
        txt_surface = self.font.render(self.text, True, WHITE)
        txt_rect = txt_surface.get_rect(center=self.rect.center)
        screen.blit(txt_surface, txt_rect)

def draw_bullet_icon(screen: Any, x: int, y: int, size: int = 16) -> None:
    """Draw a bullet icon (simple blue/cyan projectile)"""
    center_x = x + size // 2
    center_y = y + size // 2
    
    # Draw elongated bullet shape (vertical ellipse/capsule)
    # Main body - blue
    bullet_width = size // 2
    bullet_height = size - 2
    
    # Draw rounded capsule shape
    top_y = y + 1
    bottom_y = y + bullet_height - 1
    
    # Top rounded part
    pygame.draw.circle(screen, (0, 150, 255), (center_x, top_y + bullet_width // 2), bullet_width // 2)
    # Middle rectangle
    pygame.draw.rect(screen, (0, 150, 255), (center_x - bullet_width // 2, top_y + bullet_width // 2, bullet_width, bullet_height - bullet_width))
    # Bottom flat/pointed part
    pygame.draw.polygon(screen, (0, 120, 200), [
        (center_x - bullet_width // 2, bottom_y - 2),
        (center_x + bullet_width // 2, bottom_y - 2),
        (center_x, bottom_y + 1)
    ])
    
    # Highlight shine
    pygame.draw.circle(screen, (150, 220, 255), (center_x - 1, top_y + 3), 2)

def draw_bomb_icon(screen: Any, x: int, y: int, size: int = 16) -> None:
    """Draw a bomb icon (black sphere with red fuse)"""
    center_x = x + size // 2
    center_y = y + size // 2 + 2
    
    # Bomb body (black circle with gradient effect)
    pygame.draw.circle(screen, (30, 30, 30), (center_x, center_y), size // 2 - 1)
    pygame.draw.circle(screen, (60, 60, 60), (center_x, center_y), size // 2 - 1, 1)
    
    # Shine highlight on bomb
    pygame.draw.circle(screen, (80, 80, 80), (center_x - 2, center_y - 2), size // 5)
    
    # Fuse (red sparkle line)
    fuse_start_x = center_x - size // 4
    fuse_start_y = y + 2
    pygame.draw.line(screen, (150, 150, 150), (fuse_start_x, fuse_start_y), (fuse_start_x - 2, fuse_start_y - 3), 2)
    # Red spark at fuse tip
    pygame.draw.circle(screen, (255, 50, 50), (fuse_start_x - 2, fuse_start_y - 3), 2)
    pygame.draw.circle(screen, (255, 150, 0), (fuse_start_x - 2, fuse_start_y - 3), 1)

class GameGUI:
    """Main GUI for the game client"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("CloudSnake - Multiplayer Snake Game")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Client instance
        self.client: Optional[GameClient] = None
        
        # Settings management
        self.settings_file = 'settings.json'
        self.settings = self.load_settings()
        
        # GUI state
        self.state = 'connection'  # 'connection', 'connecting', 'game'
        self.connection_error = ""
        
        # Name dropdown state
        self.dropdown_open = False
        self.selected_name_index = 0
        
        # Connection screen widgets
        server_ip = self.settings.get('server_ip', '129.151.219.36')
        last_name = self.settings.get('last_player_name', '')
        
        self.ip_input = InputBox(300, 280, 400, 40, server_ip)
        self.name_input = InputBox(300, 350, 400, 40, last_name)
        self.dropdown_button = Button(705, 350, 40, 40, '▼', DARK_GRAY)
        self.connect_button = Button(400, 430, 200, 50, 'Connect', GREEN)
        
        # Game menu state
        self.game_menu_open = False
        self.show_statistics = False
        self.in_game = False  # Track whether player is in active game or just in lobby
        self.left_voluntarily = False  # Track if player left game via menu (prevents respawn)
        
        # Game settings
        self.grid_size = 20  # Size of each grid cell
        self.grid_width = 40  # Number of cells wide
        self.grid_height = 30  # Number of cells high
        self.game_area_width = self.grid_width * self.grid_size
        self.game_area_height = self.grid_height * self.grid_size
        self.game_offset_x = 20
        self.game_offset_y = 110  # Moved down to create space for menu button
        
        # Game state
        self.last_update = time.time()
        self.update_interval = 0.15  # Move every 0.15 seconds
        
        # Respawn button (shown when dead) - will be positioned dynamically
        self.respawn_button = Button(350, 380, 150, 30, 'Respawn', GREEN)
        
        # Fonts
        # Additional ~12% reduction from the previous step
        self.title_font = get_unicode_font(52)
        self.font = get_unicode_font(23)
        self.small_font = get_unicode_font(18)
        
        # Load logo image
        try:
            logo_path = get_resource_path('assets/cloudesnake.png')
            print(f"DEBUG: Attempting to load logo from: {logo_path}")
            print(f"DEBUG: File exists: {os.path.exists(logo_path)}")
            if os.path.exists(logo_path):
                self.logo_image = pygame.image.load(logo_path)
                # Scale logo if needed (keep aspect ratio)
                logo_width = 500
                logo_height = int(self.logo_image.get_height() * (logo_width / self.logo_image.get_width()))
                self.logo_image = pygame.transform.scale(self.logo_image, (logo_width, logo_height))
                print(f"DEBUG: Logo loaded successfully")
            else:
                print(f"DEBUG: Logo file not found at path")
                self.logo_image = None
        except Exception as e:
            print(f"Warning: Could not load logo image: {e}")
            import traceback
            traceback.print_exc()
            self.logo_image = None
    
    def draw_text_with_shadow(self, text: str, font: Any, x: int, y: int, color: Tuple[int, int, int], shadow_offset: int = 2) -> None:
        """Draw text with shadow for better readability"""
        # Shadow
        shadow_surf = font.render(text, True, TEXT_SHADOW)
        self.screen.blit(shadow_surf, (x + shadow_offset, y + shadow_offset))
        # Text
        text_surf = font.render(text, True, color)
        self.screen.blit(text_surf, (x, y))
    
    def draw_gradient_rect(self, x: int, y: int, width: int, height: int, color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> None:
        """Draw a rectangle with vertical gradient"""
        for i in range(height):
            ratio = i / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (x, y + i), (x + width, y + i))
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'player_names': [], 'last_player_name': '', 'server_ip': '129.151.219.36'}
    
    def save_settings(self) -> None:
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def add_player_name(self, name: str) -> None:
        """Add player name to history"""
        if name and name.strip():
            name = name.strip()
            # Remove if already exists (to move to front)
            if name in self.settings['player_names']:
                self.settings['player_names'].remove(name)
            # Add to front
            self.settings['player_names'].insert(0, name)
            # Keep only last 10 names
            self.settings['player_names'] = self.settings['player_names'][:10]
            # Update last used name
            self.settings['last_player_name'] = name
            self.save_settings()
        
    def draw_connection_screen(self) -> None:
        """Draw the connection screen"""
        # Background gradient
        self.screen.fill(BG_COLOR)
        
        # Logo image or fallback to text title
        if self.logo_image:
            logo_x = (SCREEN_WIDTH - self.logo_image.get_width()) // 2
            logo_y = 0
            self.screen.blit(self.logo_image, (logo_x, logo_y))
        else:
            # Fallback to text title with shadow
            self.draw_text_with_shadow("CloudSnake", self.title_font, SCREEN_WIDTH // 2 - 150, 80, CYAN, 3)
        
        # Labels
        ip_label = self.font.render("Server IP:", True, TEXT_COLOR)
        self.screen.blit(ip_label, (300, 250))
        
        name_label = self.font.render("Player Name:", True, TEXT_COLOR)
        self.screen.blit(name_label, (300, 320))
        
        # Input boxes and button
        self.ip_input.draw(self.screen)
        self.name_input.draw(self.screen)
        self.dropdown_button.draw(self.screen)
        self.connect_button.draw(self.screen)
        
        # Draw dropdown menu if open
        if self.dropdown_open and self.settings['player_names']:
            dropdown_y = 395
            for i, name in enumerate(self.settings['player_names'][:10]):
                item_rect = pygame.Rect(300, dropdown_y + i * 35, 400, 35)
                # Highlight hovered item
                mouse_pos = pygame.mouse.get_pos()
                if item_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, item_rect)
                    color = WHITE
                else:
                    pygame.draw.rect(self.screen, PANEL_BG, item_rect)
                    color = TEXT_COLOR
                pygame.draw.rect(self.screen, BORDER_COLOR, item_rect, 2)
                
                # Truncate long names
                display_name = name if len(name) <= 30 else name[:27] + "..."
                name_text = self.small_font.render(display_name, True, color)
                self.screen.blit(name_text, (item_rect.x + 5, item_rect.y + 8))
        
        # Error message
        if self.connection_error:
            error_text = self.font.render(self.connection_error, True, RED)
            error_rect = error_text.get_rect(center=(SCREEN_WIDTH // 2, 510))
            self.screen.blit(error_text, error_rect)
        
        # Instructions
        instruction = self.small_font.render("Click input boxes to edit, then click Connect", True, GRAY)
        inst_rect = instruction.get_rect(center=(SCREEN_WIDTH // 2, 580))
        self.screen.blit(instruction, inst_rect)
    
    def draw_statistics_screen(self) -> None:
        """Draw the statistics/leaderboard screen"""
        # Background
        self.screen.fill(BG_COLOR)
        
        # Title with shadow
        self.draw_text_with_shadow("Statistics & Leaderboard", self.title_font, 120, 30, CYAN, 3)
        
        # Close button (X in top right)
        close_button = Button(SCREEN_WIDTH - 120, 30, 100, 40, '✕ Close', RED)
        close_button.draw(self.screen)
        self.stats_close_button = close_button  # Store for event handling
        
        # Get leaderboard data from game state
        leaderboard = []
        all_time_high = 0
        all_time_player = "None"
        
        if self.client and self.client.game_state:
            leaderboard = self.client.game_state.get('leaderboard', [])
            all_time_high = self.client.game_state.get('all_time_highscore', 0)
            all_time_player = self.client.game_state.get('all_time_highscore_player', 'None')
        
        # Leaderboard section
        leaderboard_y = 100
        leaderboard_label = self.font.render("Top Players", True, CYAN)
        self.screen.blit(leaderboard_label, (50, leaderboard_y))
        
        # Column headers
        headers_y = leaderboard_y + 40
        header_font = self.small_font
        rank_x = 80
        name_x = 140
        score_x = 400
        games_x = 550
        kills_x = 680
        deaths_x = 800
        
        self.screen.blit(header_font.render("Rank", True, GRAY), (rank_x, headers_y))
        self.screen.blit(header_font.render("Player", True, GRAY), (name_x, headers_y))
        self.screen.blit(header_font.render("Highscore", True, GRAY), (score_x, headers_y))
        self.screen.blit(header_font.render("Games", True, GRAY), (games_x, headers_y))
        self.screen.blit(header_font.render("Kills", True, GRAY), (kills_x, headers_y))
        self.screen.blit(header_font.render("Deaths", True, GRAY), (deaths_x, headers_y))
        
        # Draw leaderboard entries
        entry_y = headers_y + 35
        for i, entry in enumerate(leaderboard[:10]):
            # Alternating background
            if i % 2 == 0:
                entry_rect = pygame.Rect(70, entry_y + i * 35 - 5, SCREEN_WIDTH - 140, 32)
                pygame.draw.rect(self.screen, (20, 20, 30), entry_rect)
            
            # Rank with medal for top 3
            if i == 0:
                rank_text = "#1"
                rank_color = YELLOW
            elif i == 1:
                rank_text = "#2"
                rank_color = (192, 192, 192)  # Silver
            elif i == 2:
                rank_text = "#3"
                rank_color = ORANGE
            else:
                rank_text = f"#{i + 1}"
                rank_color = TEXT_COLOR
            
            rank_surf = self.small_font.render(rank_text, True, rank_color)
            self.screen.blit(rank_surf, (rank_x, entry_y + i * 35))
            
            # Player name (truncate if too long)
            name = entry.get('name', 'Unknown')
            if len(name) > 20:
                name = name[:17] + "..."
            name_surf = self.small_font.render(name, True, TEXT_COLOR)
            self.screen.blit(name_surf, (name_x, entry_y + i * 35))
            
            # Stats
            highscore = entry.get('highscore', 0)
            games_played = entry.get('games_played', 0)
            total_kills = entry.get('total_kills', 0)
            total_deaths = entry.get('total_deaths', 0)
            
            score_surf = self.small_font.render(f"{highscore:,}", True, YELLOW)
            self.screen.blit(score_surf, (score_x, entry_y + i * 35))
            
            games_surf = self.small_font.render(str(games_played), True, TEXT_COLOR)
            self.screen.blit(games_surf, (games_x, entry_y + i * 35))
            
            kills_surf = self.small_font.render(str(total_kills), True, GREEN)
            self.screen.blit(kills_surf, (kills_x, entry_y + i * 35))
            
            deaths_surf = self.small_font.render(str(total_deaths), True, RED)
            self.screen.blit(deaths_surf, (deaths_x, entry_y + i * 35))
        
        # If no data available
        if not leaderboard:
            no_data_text = self.font.render("No statistics available yet", True, GRAY)
            no_data_rect = no_data_text.get_rect(center=(SCREEN_WIDTH // 2, 400))
            self.screen.blit(no_data_text, no_data_rect)
    
    def draw_connecting_screen(self) -> None:
        """Draw the connecting screen"""
        self.screen.fill(BG_COLOR)
        
        # Connecting message with shadow
        self.draw_text_with_shadow("Connecting", self.title_font, SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT // 2 - 30, CYAN, 3)
        
        # Animated dots
        dots = "." * ((pygame.time.get_ticks() // 500) % 4)
        dots_text = self.font.render(dots, True, TEXT_COLOR)
        dots_rect = dots_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        self.screen.blit(dots_text, dots_rect)
    
    def update_snake_game(self) -> None:
        """Game logic is handled by server, client just displays"""
        # No client-side game logic needed - server handles everything
        pass
    
    def draw_game_screen(self) -> None:
        """Draw the game screen with snake game"""
        # If showing statistics overlay, draw that instead
        if self.show_statistics:
            self.draw_statistics_screen()
            return
        
        # Dark background
        self.screen.fill(BG_COLOR)
        
        # Title bar with gradient
        self.draw_gradient_rect(0, 0, SCREEN_WIDTH, 60, PANEL_BG, BG_COLOR)
        
        if self.client:
            # Player info with modern styling
            player_text = self.font.render(f"Player: {self.client.player_name}", True, TEXT_COLOR)
            self.screen.blit(player_text, (20, 15))
            
            # Score - get from server game state
            score = 0
            alive = True
            if self.client.game_state:
                players = self.client.game_state.get('players', {})
                my_data = players.get(self.client.player_id, {})
                score = my_data.get('score', 0)
                alive = my_data.get('alive', True)
            
            score_text = self.font.render(f"Score: {score}", True, YELLOW)
            self.screen.blit(score_text, (300, 15))
            
            # Connection status - check timeout
            if self.client.connected:
                time_since_update = time.time() - self.client.last_update_time
                if time_since_update > self.client.update_timeout:
                    # Timeout detected
                    status_text = self.small_font.render("● Disconnected", True, RED)
                    self.screen.blit(status_text, (SCREEN_WIDTH - 180, 20))
                    
                    # Show timeout info
                    timeout_info = self.small_font.render(f"(No updates for {time_since_update:.1f}s)", True, RED)
                    self.screen.blit(timeout_info, (SCREEN_WIDTH - 250, 40))
                else:
                    status_text = self.small_font.render("● Connected", True, GREEN)
                    self.screen.blit(status_text, (SCREEN_WIDTH - 150, 20))
            else:
                status_text = self.small_font.render("● Disconnected", True, RED)
                self.screen.blit(status_text, (SCREEN_WIDTH - 180, 20))
        
        # Game area (snake game) with modern styling
        game_area = pygame.Rect(self.game_offset_x, self.game_offset_y, 
                               self.game_area_width, self.game_area_height)
        # Dark game background
        pygame.draw.rect(self.screen, (10, 10, 15), game_area)
        # Glowing border effect
        pygame.draw.rect(self.screen, CYAN, game_area, 3)
        pygame.draw.rect(self.screen, (0, 100, 140), (game_area.x - 1, game_area.y - 1, game_area.width + 2, game_area.height + 2), 1)
        
        # Draw grid lines (very subtle)
        grid_color = (20, 20, 30)
        for x in range(0, self.game_area_width, self.grid_size):
            pygame.draw.line(self.screen, grid_color,
                           (self.game_offset_x + x, self.game_offset_y),
                           (self.game_offset_x + x, self.game_offset_y + self.game_area_height))
        for y in range(0, self.game_area_height, self.grid_size):
            pygame.draw.line(self.screen, grid_color,
                           (self.game_offset_x, self.game_offset_y + y),
                           (self.game_offset_x + self.game_area_width, self.game_offset_y + y))
        
        # Draw all players' snakes
        if self.client and self.client.game_state:
            players = self.client.game_state.get('players', {})
            
            # Check if current player is in game
            my_data = players.get(self.client.player_id, {})
            my_in_game = my_data.get('in_game', False)
            
            # Show lobby message if not in game
            if not my_in_game:
                lobby_text = self.title_font.render("LOBBY", True, CYAN)
                lobby_rect = lobby_text.get_rect(center=(self.game_offset_x + self.game_area_width // 2,
                                                         self.game_offset_y + self.game_area_height // 2 - 50))
                self.screen.blit(lobby_text, lobby_rect)
                
                info_text = self.font.render("Open Menu and click 'Start Game' to play", True, TEXT_COLOR)
                info_rect = info_text.get_rect(center=(self.game_offset_x + self.game_area_width // 2,
                                                       self.game_offset_y + self.game_area_height // 2 + 20))
                self.screen.blit(info_text, info_rect)
            
            for player_id, player_info in players.items():
                snake = player_info.get('snake', [])
                alive = player_info.get('alive', True)
                in_game = player_info.get('in_game', False)
                color = player_info.get('color', (255, 255, 255))
                
                # Don't draw snakes for players not in game
                if not in_game or not snake or not alive:
                    continue
                
                # Use color from server
                head_color = color
                body_color = tuple(int(c * 0.7) for c in color)  # Darker body
                
                # Draw snake with rounded style and glow effect
                for i, segment in enumerate(snake):
                    if isinstance(segment, list):
                        segment = tuple(segment)
                    
                    x, y = segment
                    rect = pygame.Rect(
                        self.game_offset_x + x * self.grid_size + 2,
                        self.game_offset_y + y * self.grid_size + 2,
                        self.grid_size - 4,
                        self.grid_size - 4
                    )
                    
                    # Head is brighter with glow
                    if i == 0:
                        # Glow effect for head
                        glow_rect = pygame.Rect(rect.x - 1, rect.y - 1, rect.width + 2, rect.height + 2)
                        pygame.draw.rect(self.screen, head_color, glow_rect)
                        pygame.draw.rect(self.screen, head_color, rect)
                        pygame.draw.rect(self.screen, WHITE, rect, 1)
                    else:
                        pygame.draw.rect(self.screen, body_color, rect)
                        pygame.draw.rect(self.screen, head_color, rect, 1)
        
        # Draw bricks with improved graphics
        if self.client and self.client.game_state:
            bricks = self.client.game_state.get('bricks', [])
            
            for brick in bricks:
                if isinstance(brick, list):
                    x, y = brick
                else:
                    x, y = brick
                
                # Draw brick with gradient effect
                brick_rect = pygame.Rect(
                    self.game_offset_x + x * self.grid_size + 2,
                    self.game_offset_y + y * self.grid_size + 2,
                    self.grid_size - 4,
                    self.grid_size - 4
                )
                # Orange brick with glow
                pygame.draw.rect(self.screen, ORANGE, brick_rect)
                pygame.draw.rect(self.screen, YELLOW, brick_rect, 2)
            
            # Draw bullet bricks (special bricks that give bullets)
            bullet_bricks = self.client.game_state.get('bullet_bricks', [])
            
            for brick in bullet_bricks:
                if isinstance(brick, list):
                    x, y = brick
                else:
                    x, y = brick
                
                # Draw bullet brick with cyan/blue colors
                brick_rect = pygame.Rect(
                    self.game_offset_x + x * self.grid_size + 2,
                    self.game_offset_y + y * self.grid_size + 2,
                    self.grid_size - 4,
                    self.grid_size - 4
                )
                pygame.draw.rect(self.screen, CYAN, brick_rect)
                pygame.draw.rect(self.screen, BLUE, brick_rect, 2)
            
            # Draw bomb bricks (special bricks that give bombs)
            bomb_bricks = self.client.game_state.get('bomb_bricks', [])
            
            for brick in bomb_bricks:
                if isinstance(brick, list):
                    x, y = brick
                else:
                    x, y = brick
                
                # Draw bomb brick with red colors
                brick_rect = pygame.Rect(
                    self.game_offset_x + x * self.grid_size + 2,
                    self.game_offset_y + y * self.grid_size + 2,
                    self.grid_size - 4,
                    self.grid_size - 4
                )
                pygame.draw.rect(self.screen, RED, brick_rect)
                pygame.draw.rect(self.screen, DARK_RED, brick_rect, 2)
            
            # Draw bullets
            bullets = self.client.game_state.get('bullets', [])
            
            for bullet in bullets:
                pos = bullet.get('pos', [0, 0])
                if isinstance(pos, list) and len(pos) >= 2:
                    x, y = pos[0], pos[1]
                else:
                    x, y = pos
                
                # Draw bullet as small red circle
                bullet_center = (
                    self.game_offset_x + int(x * self.grid_size + self.grid_size // 2),
                    self.game_offset_y + int(y * self.grid_size + self.grid_size // 2)
                )
                pygame.draw.circle(self.screen, RED, bullet_center, self.grid_size // 3)
                pygame.draw.circle(self.screen, (255, 150, 150), bullet_center, self.grid_size // 4)
            
            # Draw bombs
            bombs = self.client.game_state.get('bombs', [])
            
            for bomb in bombs:
                pos = bomb.get('pos', [0, 0])
                if isinstance(pos, list) and len(pos) >= 2:
                    x, y = pos[0], pos[1]
                else:
                    x, y = pos
                
                # Draw bomb as a black sphere with red glow
                bomb_center = (
                    self.game_offset_x + int(x * self.grid_size + self.grid_size // 2),
                    self.game_offset_y + int(y * self.grid_size + self.grid_size // 2)
                )
                # Red outer glow
                pygame.draw.circle(self.screen, RED, bomb_center, self.grid_size // 2 + 2)
                # Dark red middle
                pygame.draw.circle(self.screen, DARK_RED, bomb_center, self.grid_size // 2)
                # Black center
                pygame.draw.circle(self.screen, BLACK, bomb_center, self.grid_size // 3)
        
        # Check if current player is dead and show respawn button
        show_respawn = False
        if self.client and self.client.game_state:
            players = self.client.game_state.get('players', {})
            my_data = players.get(self.client.player_id, {})
            # Only show respawn if dead and didn't leave voluntarily
            if not my_data.get('alive', True) and not self.left_voluntarily:
                show_respawn = True
        
        if show_respawn:
            # Semi-transparent overlay
            overlay = pygame.Surface((self.game_area_width, self.game_area_height))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (self.game_offset_x, self.game_offset_y))
            
            # Death message
            death_text = self.title_font.render("YOU DIED!", True, RED)
            death_rect = death_text.get_rect(center=(self.game_offset_x + self.game_area_width // 2,
                                                     self.game_offset_y + self.game_area_height // 2 - 50))
            self.screen.blit(death_text, death_rect)
            
            # Respawn button - center it under the death message
            button_x = self.game_offset_x + self.game_area_width // 2 - 75  # Center 150px button
            button_y = death_rect.bottom + 20  # 20px below the text
            self.respawn_button.rect.x = button_x
            self.respawn_button.rect.y = button_y
            self.respawn_button.draw(self.screen)
        
        # Side panel for game state
        panel_x = self.game_offset_x + self.game_area_width + 20
        panel_y = 110
        panel_width = SCREEN_WIDTH - panel_x - 20
        
        # Draw gray background panel for player list area
        panel_bg = pygame.Rect(panel_x, panel_y, panel_width, SCREEN_HEIGHT - panel_y - 40)
        pygame.draw.rect(self.screen, GRAY, panel_bg)
        pygame.draw.rect(self.screen, DARK_GRAY, panel_bg, 2)
        
        # Panel title
        panel_title = self.small_font.render("Players", True, BLACK)
        self.screen.blit(panel_title, (panel_x + 10, panel_y + 10))
        
        # Display player list with individual panels
        if self.client and self.client.game_state:
            players = self.client.game_state.get('players', {})
            y_offset = panel_y + 40
            
            # Sort by score
            sorted_players = sorted(players.items(), 
                                   key=lambda x: x[1].get('score', 0), 
                                   reverse=True)
            
            for player_id, player_info in sorted_players[:15]:  # Limit to 15 players
                name = player_info.get('player_name', 'Unknown')
                score = player_info.get('score', 0)
                alive = player_info.get('alive', True)
                snake_color = player_info.get('color', (255, 255, 255))
                bullets = player_info.get('bullets', 0)
                bombs = player_info.get('bombs', 0)
                
                # Draw individual panel for each player (with padding from edges)
                player_panel_height = 72
                player_panel_padding = 5
                player_panel = pygame.Rect(panel_x + player_panel_padding, y_offset - 2, 
                                          panel_width - (player_panel_padding * 2), player_panel_height)
                
                # Highlight current player's panel
                if player_id == self.client.player_id:
                    pygame.draw.rect(self.screen, (240, 248, 255), player_panel)  # Light blue background
                    pygame.draw.rect(self.screen, snake_color, player_panel, 3)  # Thick colored border
                else:
                    pygame.draw.rect(self.screen, WHITE, player_panel)  # White background
                    pygame.draw.rect(self.screen, LIGHT_GRAY, player_panel, 2)  # Gray border
                
                # Truncate long names
                if len(name) > 10:
                    name = name[:10] + ".."
                
                # Highlight current player with arrow
                if player_id == self.client.player_id:
                    name = f"► {name}"
                
                # Use snake color for the name text
                text_color = snake_color
                
                # Show dead status
                status = "💀" if not alive else ""
                
                # Draw player info inside the panel
                name_text = self.small_font.render(f"{name} {status}", True, text_color)
                self.screen.blit(name_text, (panel_x + player_panel_padding + 5, y_offset))
                
                score_text = self.small_font.render(f"Score: {score}", True, DARK_GRAY)
                self.screen.blit(score_text, (panel_x + player_panel_padding + 5, y_offset + 18))
                
                # Show bullet count with icon
                bullet_icon_x = panel_x + player_panel_padding + 5
                bullet_icon_y = y_offset + 36
                draw_bullet_icon(self.screen, bullet_icon_x, bullet_icon_y, 16)
                bullets_text = self.small_font.render(f"× {bullets}", True, DARK_GRAY)
                self.screen.blit(bullets_text, (bullet_icon_x + 20, y_offset + 36))
                
                # Show bomb count with icon
                bomb_icon_x = panel_x + player_panel_padding + 5
                bomb_icon_y = y_offset + 54
                draw_bomb_icon(self.screen, bomb_icon_x, bomb_icon_y, 16)
                bombs_text = self.small_font.render(f"× {bombs}", True, DARK_GRAY)
                self.screen.blit(bombs_text, (bomb_icon_x + 20, y_offset + 54))
                
                y_offset += player_panel_height + 4  # 4px spacing between panels
                
                if y_offset > panel_y + SCREEN_HEIGHT - 200:
                    break
        
        # Controls info below game area
        game_area_bottom = self.game_offset_y + self.game_area_height
        controls_y = game_area_bottom + 5  # 5px below game area
        controls = self.small_font.render("Arrow Keys: Move | SPACE: Shoot | B: Throw Bomb | R: Respawn | ESC: Quit", True, GRAY)
        self.screen.blit(controls, (20, controls_y))
        
        # Menu button and dropdown (rendered last to be on top)
        if self.client:
            # Menu button positioned under player name on the left
            menu_button = Button(20, 50, 100, 35, 'Menu ▼', PURPLE)
            menu_button.draw(self.screen)
            self.menu_button = menu_button  # Store for event handling
            
            # Draw menu dropdown if open
            if self.game_menu_open:
                menu_x = 20
                menu_y = 90
                # Menu items change based on game state
                if self.in_game:
                    menu_items = ['Statistics', 'Leave Game', 'Disconnect']
                else:
                    menu_items = ['Statistics', 'Start Game', 'Disconnect']
                
                for i, item in enumerate(menu_items):
                    item_rect = pygame.Rect(menu_x, menu_y + i * 40, 180, 38)
                    mouse_pos = pygame.mouse.get_pos()
                    
                    if item_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, item_rect)
                        text_color = WHITE
                    else:
                        pygame.draw.rect(self.screen, PANEL_BG, item_rect)
                        text_color = TEXT_COLOR
                    
                    pygame.draw.rect(self.screen, BORDER_COLOR, item_rect, 2)
                    item_text = self.small_font.render(item, True, text_color)
                    self.screen.blit(item_text, (item_rect.x + 10, item_rect.y + 10))
                
                # Store menu items for click detection
                self.menu_items_rects = [
                    pygame.Rect(menu_x, menu_y + i * 40, 180, 38) 
                    for i in range(len(menu_items))
                ]
    
    def handle_connection_events(self, event: Any) -> None:
        """Handle events on connection screen"""
        # Handle dropdown button
        if self.dropdown_button.handle_event(event):
            if self.settings['player_names']:
                self.dropdown_open = not self.dropdown_open
        
        # Handle dropdown selection
        if event.type == pygame.MOUSEBUTTONDOWN and self.dropdown_open:
            mouse_pos = event.pos
            dropdown_y = 365
            for i, name in enumerate(self.settings['player_names'][:10]):
                item_rect = pygame.Rect(300, dropdown_y + i * 35, 400, 35)
                if item_rect.collidepoint(mouse_pos):
                    self.name_input.text = name
                    self.dropdown_open = False
                    return
        
        # Close dropdown if clicking outside
        if event.type == pygame.MOUSEBUTTONDOWN and self.dropdown_open:
            mouse_pos = event.pos
            dropdown_area = pygame.Rect(300, 320, 445, 400)
            if not dropdown_area.collidepoint(mouse_pos):
                self.dropdown_open = False
        
        self.ip_input.handle_event(event)
        self.name_input.handle_event(event)
        
        if self.connect_button.handle_event(event):
            # Start connection
            self.start_connection()
    
    def handle_statistics_events(self, event: Any) -> None:
        """Handle events on statistics screen"""
        if hasattr(self, 'stats_close_button') and self.stats_close_button.handle_event(event):
            # Close statistics view, return to game
            self.show_statistics = False
    
    def handle_game_events(self, event: Any) -> None:
        """Handle events during game"""
        if not self.client:
            return
        
        # If showing statistics, handle those events instead
        if self.show_statistics:
            self.handle_statistics_events(event)
            return
        
        # Handle menu button click
        if hasattr(self, 'menu_button') and self.menu_button.handle_event(event):
            self.game_menu_open = not self.game_menu_open
            return
        
        # Handle menu dropdown clicks
        if event.type == pygame.MOUSEBUTTONDOWN and self.game_menu_open:
            mouse_pos = event.pos
            if hasattr(self, 'menu_items_rects'):
                for i, rect in enumerate(self.menu_items_rects):
                    if rect.collidepoint(mouse_pos):
                        if i == 0:  # Statistics
                            self.show_statistics = True
                            self.game_menu_open = False
                        elif i == 1:  # Start Game / Leave Game
                            if self.in_game:
                                # Leave game - return to lobby
                                self.client.send_to_server({'type': 'leave_game'})
                                self.in_game = False
                                self.left_voluntarily = True  # Mark as voluntary leave
                            else:
                                # Start game - join active game
                                self.client.send_to_server({'type': 'start_game'})
                                self.in_game = True
                                self.left_voluntarily = False  # Reset flag when starting game
                            self.game_menu_open = False
                        elif i == 2:  # Disconnect
                            self.client.disconnect()
                            self.state = 'connection'
                            self.game_menu_open = False
                        return
            
            # Close menu if clicking outside
            menu_area = pygame.Rect(20, 50, 180, 168)  # Increased height for 3 items
            if not menu_area.collidepoint(mouse_pos):
                self.game_menu_open = False
        
        # Check if player is dead
        is_dead = False
        is_in_game = False
        if self.client.game_state:
            players = self.client.game_state.get('players', {})
            my_data = players.get(self.client.player_id, {})
            is_dead = not my_data.get('alive', True)
            is_in_game = my_data.get('in_game', False)
        
        # Handle respawn button if dead and in game
        if is_dead and is_in_game:
            if self.respawn_button.handle_event(event):
                self.client.respawn()
                self.left_voluntarily = False  # Reset flag after respawn
                return
        
        # Handle keyboard input for snake direction (only if alive and in game)
        if event.type == pygame.KEYDOWN and not is_dead and is_in_game:
            current_direction = self.client.player_data['direction']
            new_direction = None
            
            if event.key == pygame.K_UP or event.key == pygame.K_w:
                if current_direction != 'DOWN':  # Can't go opposite direction
                    new_direction = 'UP'
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                if current_direction != 'UP':
                    new_direction = 'DOWN'
            elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                if current_direction != 'RIGHT':
                    new_direction = 'LEFT'
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                if current_direction != 'LEFT':
                    new_direction = 'RIGHT'
            elif event.key == pygame.K_SPACE:
                # Shoot a bullet
                self.client.shoot()
                return  # Don't send direction change
            elif event.key == pygame.K_b:
                # Throw a bomb
                self.client.throw_bomb()
                return  # Don't send direction change
            
            # Send direction change to server (don't update local state yet)
            if new_direction:
                # Send to server, but don't update local direction until server confirms
                # This prevents rapid key presses from causing illegal 180-degree turns
                self.client.send_to_server({
                    'type': 'update',
                    'data': {'direction': new_direction}
                })
    
    def start_connection(self) -> None:
        """Start connection to server"""
        server_ip = self.ip_input.text.strip()
        player_name = self.name_input.text.strip()
        
        if not server_ip:
            self.connection_error = "Please enter server IP"
            return
        
        if not player_name:
            self.connection_error = "Please enter a player name"
            return
        
        # Save the player name and server IP
        self.add_player_name(player_name)
        self.settings['server_ip'] = server_ip
        self.save_settings()
        
        self.state = 'connecting'
        self.connection_error = ""
        self.dropdown_open = False
        
        # Start connection in background thread
        thread = threading.Thread(target=self.connect_to_server, 
                                 args=(server_ip, player_name), 
                                 daemon=True)
        thread.start()
    
    def connect_to_server(self, server_ip: str, player_name: str) -> None:
        """Connect to server in background"""
        try:
            self.client = GameClient(server_ip, 50000, player_name)
            if self.client.connect():
                self.client.running = True
                
                # Start receive thread
                receive_thread = threading.Thread(target=self.client.receive_messages, daemon=True)
                receive_thread.start()
                
                # Start heartbeat thread
                heartbeat_thread = threading.Thread(target=self.client.send_heartbeat, daemon=True)
                heartbeat_thread.start()
                
                # Start background thread to run client loop
                client_thread = threading.Thread(target=self.client.run, daemon=True)
                client_thread.start()
                
                self.state = 'game'
            else:
                self.state = 'connection'
                # Check if connection failed due to server being full
                if hasattr(self.client, 'connected') and not self.client.connected:
                    self.connection_error = "Server is full - Try later"
                else:
                    self.connection_error = "Connection failed"
        except Exception as e:
            self.state = 'connection'
            self.connection_error = f"Error: {str(e)[:30]}"
    
    def run(self) -> None:
        """Main GUI loop"""
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                
                # State-specific event handling
                if self.state == 'connection':
                    self.handle_connection_events(event)
                elif self.state == 'game':
                    self.handle_game_events(event)
            
            # Update game logic
            if self.state == 'game':
                self.update_snake_game()
            
            # Draw appropriate screen
            if self.state == 'connection':
                self.draw_connection_screen()
            elif self.state == 'connecting':
                self.draw_connecting_screen()
            elif self.state == 'game':
                self.draw_game_screen()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(FPS)
        
        # Cleanup
        if self.client and self.client.connected:
            self.client.disconnect()
        
        pygame.quit()

def main() -> None:
    # print("="*60)
    # print("🎮 GAME CLIENT - GUI Mode")
    # print("="*60)
    # print("Starting GUI...")
    
    gui = GameGUI()
    
    try:
        gui.run()
    except Exception as e:
        print(f"\n❌ GUI error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
