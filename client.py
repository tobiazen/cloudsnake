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
SCREEN_HEIGHT = 700
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
        self.font = pygame.font.Font(None, 32)
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
        self.font = pygame.font.Font(None, 32)
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
        
        self.ip_input = InputBox(300, 250, 400, 40, server_ip)
        self.name_input = InputBox(300, 320, 400, 40, last_name)
        self.dropdown_button = Button(705, 320, 40, 40, '▼', DARK_GRAY)
        self.connect_button = Button(400, 400, 200, 50, 'Connect', GREEN)
        self.stats_button = Button(325, 470, 350, 50, 'View Statistics', PURPLE)
        
        # Screen state
        self.current_screen = 'connection'  # 'connection', 'statistics', 'connecting', 'game'
        
        # Game settings
        self.grid_size = 20  # Size of each grid cell
        self.grid_width = 40  # Number of cells wide
        self.grid_height = 30  # Number of cells high
        self.game_area_width = self.grid_width * self.grid_size
        self.game_area_height = self.grid_height * self.grid_size
        self.game_offset_x = 20
        self.game_offset_y = 80
        
        # Game state
        self.last_update = time.time()
        self.update_interval = 0.15  # Move every 0.15 seconds
        
        # Respawn button (shown when dead)
        self.respawn_button = Button(350, 350, 300, 60, 'Respawn', GREEN)
        
        # Fonts
        self.title_font = pygame.font.Font(None, 72)
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
    
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
        
        # Title with shadow
        self.draw_text_with_shadow("CloudSnake", self.title_font, SCREEN_WIDTH // 2 - 150, 80, CYAN, 3)
        
        # Labels
        ip_label = self.font.render("Server IP:", True, TEXT_COLOR)
        self.screen.blit(ip_label, (300, 220))
        
        name_label = self.font.render("Player Name:", True, TEXT_COLOR)
        self.screen.blit(name_label, (300, 290))
        
        # Input boxes and button
        self.ip_input.draw(self.screen)
        self.name_input.draw(self.screen)
        self.dropdown_button.draw(self.screen)
        self.connect_button.draw(self.screen)
        self.stats_button.draw(self.screen)
        
        # Draw dropdown menu if open
        if self.dropdown_open and self.settings['player_names']:
            dropdown_y = 365
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
            error_rect = error_text.get_rect(center=(SCREEN_WIDTH // 2, 480))
            self.screen.blit(error_text, error_rect)
        
        # Instructions
        instruction = self.small_font.render("Click input boxes to edit, then click Connect", True, GRAY)
        inst_rect = instruction.get_rect(center=(SCREEN_WIDTH // 2, 550))
        self.screen.blit(instruction, inst_rect)
    
    def draw_statistics_screen(self) -> None:
        """Draw the statistics/leaderboard screen"""
        # Background
        self.screen.fill(BG_COLOR)
        
        # Title with shadow
        self.draw_text_with_shadow("Statistics & Leaderboard", self.title_font, 120, 30, CYAN, 3)
        
        # Back button
        back_button = Button(50, 30, 120, 40, '← Back', GRAY)
        back_button.draw(self.screen)
        
        # Get leaderboard data from game state
        leaderboard = []
        all_time_high = 0
        all_time_player = "None"
        
        if self.client and self.client.game_state:
            leaderboard = self.client.game_state.get('leaderboard', [])
            all_time_high = self.client.game_state.get('all_time_highscore', 0)
            all_time_player = self.client.game_state.get('all_time_highscore_player', 'None')
        
        # All-time highscore panel
        panel_y = 100
        panel_rect = pygame.Rect(50, panel_y, SCREEN_WIDTH - 100, 80)
        self.draw_gradient_rect(panel_rect.x, panel_rect.y, panel_rect.width, panel_rect.height, 
                               PANEL_BG, (20, 20, 35))
        pygame.draw.rect(self.screen, CYAN, panel_rect, 2)
        
        trophy_label = self.font.render("TROPHY", True, YELLOW)
        self.screen.blit(trophy_label, (panel_rect.x + 20, panel_rect.y + 20))
        
        all_time_label = self.font.render("All-Time Highscore", True, TEXT_COLOR)
        self.screen.blit(all_time_label, (panel_rect.x + 100, panel_rect.y + 15))
        
        all_time_value = self.font.render(f"{all_time_high:,} by {all_time_player}", True, YELLOW)
        self.screen.blit(all_time_value, (panel_rect.x + 100, panel_rect.y + 45))
        
        # Leaderboard section
        leaderboard_y = panel_y + 100
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
            no_data_text = self.font.render("Connect to server to view statistics", True, GRAY)
            no_data_rect = no_data_text.get_rect(center=(SCREEN_WIDTH // 2, 400))
            self.screen.blit(no_data_text, no_data_rect)
        
        # Store back button for click detection
        self.back_button = back_button
    
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
            
            for player_id, player_info in players.items():
                snake = player_info.get('snake', [])
                alive = player_info.get('alive', True)
                color = player_info.get('color', (255, 255, 255))
                
                if not snake or not alive:
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
        
        # Check if current player is dead and show respawn button
        show_respawn = False
        if self.client and self.client.game_state:
            players = self.client.game_state.get('players', {})
            my_data = players.get(self.client.player_id, {})
            if not my_data.get('alive', True):
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
            
            # Respawn button
            self.respawn_button.draw(self.screen)
        
        # Side panel for game state
        panel_x = self.game_offset_x + self.game_area_width + 20
        panel_y = 80
        panel_width = SCREEN_WIDTH - panel_x - 20
        panel = pygame.Rect(panel_x, panel_y, panel_width, SCREEN_HEIGHT - 100)
        pygame.draw.rect(self.screen, LIGHT_GRAY, panel)
        pygame.draw.rect(self.screen, DARK_GRAY, panel, 2)
        
        # Panel title
        panel_title = self.small_font.render("Players", True, BLACK)
        self.screen.blit(panel_title, (panel_x + 10, panel_y + 10))
        
        # Display player list
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
                
                # Draw player info
                name_text = self.small_font.render(f"{name} {status}", True, text_color)
                self.screen.blit(name_text, (panel_x + 5, y_offset))
                
                score_text = self.small_font.render(f"Score: {score}", True, DARK_GRAY)
                self.screen.blit(score_text, (panel_x + 5, y_offset + 18))
                
                # Show bullet count under score
                bullets_text = self.small_font.render(f"Bullets: {bullets}", True, BLUE)
                self.screen.blit(bullets_text, (panel_x + 5, y_offset + 36))
                
                y_offset += 58
                
                if y_offset > panel_y + SCREEN_HEIGHT - 200:
                    break
        
        # Controls info at bottom
        controls_y = SCREEN_HEIGHT - 50
        controls = self.small_font.render("Arrow Keys: Move | SPACE: Shoot | R: Respawn | ESC: Quit", True, BLACK)
        self.screen.blit(controls, (20, controls_y))
    
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
        
        if self.stats_button.handle_event(event):
            # Switch to statistics screen
            self.current_screen = 'statistics'
    
    def handle_statistics_events(self, event: Any) -> None:
        """Handle events on statistics screen"""
        if hasattr(self, 'back_button') and self.back_button.handle_event(event):
            # Return to connection screen
            self.current_screen = 'connection'
    
    def handle_game_events(self, event: Any) -> None:
        """Handle events during game"""
        if not self.client:
            return
        
        # Check if player is dead
        is_dead = False
        if self.client.game_state:
            players = self.client.game_state.get('players', {})
            my_data = players.get(self.client.player_id, {})
            is_dead = not my_data.get('alive', True)
        
        # Handle respawn button if dead
        if is_dead:
            if self.respawn_button.handle_event(event):
                self.client.respawn()
                return
        
        # Handle keyboard input for snake direction (only if alive)
        if event.type == pygame.KEYDOWN and not is_dead:
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
                
                # Handle statistics screen (separate from state for flexibility)
                if self.current_screen == 'statistics':
                    self.handle_statistics_events(event)
            
            # Update game logic
            if self.state == 'game':
                self.update_snake_game()
            
            # Draw appropriate screen based on current_screen when not in game
            if self.state == 'connection':
                if self.current_screen == 'statistics':
                    self.draw_statistics_screen()
                else:
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
