import socket
import threading
import time
import json
import pygame
from typing import Optional

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
LIGHT_GRAY = (230, 230, 230)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
BLUE = (0, 100, 200)
YELLOW = (255, 200, 0)

class GameClient:
    def __init__(self, server_ip: str, server_port: int = 9089, player_name: str = "Player"):
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
    
    def connect(self):
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
                print(f"✅ Connected successfully!")
                print(f"   {response.get('message')}")
                print(f"   Player ID: {self.player_id}")
                print(f"   Assigned color: RGB{self.my_color}")
                print(f"   Players online: {response.get('player_count')}\n")
                return True
            
        except socket.timeout:
            print("❌ Connection timeout - server not responding")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
        
        return False
    
    def start(self):
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
    
    def receive_messages(self):
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
    
    def handle_server_message(self, message: dict):
        """Handle messages from server"""
        message_type = message.get('type', '')
        
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
        else:
            print(f"⚠️  Unknown message type: {message_type}")
    
    def display_game_state(self):
        """Display current game state"""
        if not self.game_state:
            return
        
        players = self.game_state.get('players', {})
        game_time = self.game_state.get('game_time', 0)
        
        # Clear previous output (simple approach)
        print("\n" + "="*60)
        print(f"🎮 GAME STATE (Time: {game_time:.1f}s)")
        print("="*60)
        
        if players:
            print(f"👥 Players online: {len(players)}")
            print()
            for player_id, player_info in players.items():
                name = player_info.get('player_name', 'Unknown')
                x = player_info.get('x', 0)
                y = player_info.get('y', 0)
                score = player_info.get('score', 0)
                
                indicator = "⭐ (You)" if player_id == self.player_id else ""
                print(f"  {name} {indicator}")
                print(f"    Position: ({x}, {y}) | Score: {score}")
        else:
            print("No players online")
        
        print("="*60)
    
    def send_heartbeat(self):
        """Send periodic ping to server to maintain connection"""
        while self.running:
            if self.connected:
                ping_msg = {'type': 'ping'}
                try:
                    self.send_to_server(ping_msg)
                except Exception as e:
                    print(f"❌ Error sending heartbeat: {e}")
            
            time.sleep(2.0)
    
    def update_player_data(self):
        """Send player direction to server"""
        update_msg = {
            'type': 'update',
            'data': self.player_data
        }
        
        self.send_to_server(update_msg)
    
    def respawn(self):
        """Request respawn from server"""
        respawn_msg = {
            'type': 'update',
            'data': {
                'respawn': True
            }
        }
        self.send_to_server(respawn_msg)
    
    def send_to_server(self, message: dict):
        """Send message to server"""
        data = json.dumps(message).encode('utf-8')
        self.socket.sendto(data, self.server_address)
    
    def disconnect(self):
        """Disconnect from server"""
        if self.connected:
            disconnect_msg = {'type': 'disconnect'}
            try:
                self.send_to_server(disconnect_msg)
            except:
                pass
            
            self.connected = False
            print("\n👋 Disconnected from server")
    
    def check_connection_timeout(self):
        """Check if connection has timed out"""
        if self.connected:
            time_since_update = time.time() - self.last_update_time
            if time_since_update > self.update_timeout:
                print(f"⚠️  Connection timeout: No updates for {time_since_update:.1f}s")
                self.connected = False
                return True
        return False
    
    def run(self):
        """Main client loop - for background operation with GUI"""
        while self.running:
            self.check_connection_timeout()
            time.sleep(0.1)

class InputBox:
    """Simple input box for text entry"""
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = GRAY
        self.text = text
        self.font = pygame.font.Font(None, 32)
        self.active = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = BLUE if self.active else GRAY
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return False
    
    def draw(self, screen):
        # Draw box
        pygame.draw.rect(screen, self.color, self.rect, 2)
        pygame.draw.rect(screen, LIGHT_GRAY, self.rect)
        pygame.draw.rect(screen, self.color, self.rect, 2)
        # Draw text
        txt_surface = self.font.render(self.text, True, BLACK)
        screen.blit(txt_surface, (self.rect.x + 5, self.rect.y + 5))

class Button:
    """Simple button widget"""
    def __init__(self, x, y, w, h, text, color=BLUE):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = (min(color[0] + 30, 255), min(color[1] + 30, 255), min(color[2] + 30, 255))
        self.font = pygame.font.Font(None, 32)
        self.hovered = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False
    
    def draw(self, screen):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        txt_surface = self.font.render(self.text, True, WHITE)
        txt_rect = txt_surface.get_rect(center=self.rect.center)
        screen.blit(txt_surface, txt_rect)

class GameGUI:
    """Main GUI for the game client"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Multiplayer Snake Game")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Client instance
        self.client: Optional[GameClient] = None
        
        # GUI state
        self.state = 'connection'  # 'connection', 'connecting', 'game'
        self.connection_error = ""
        
        # Connection screen widgets
        self.ip_input = InputBox(300, 250, 400, 40, 'localhost')
        self.name_input = InputBox(300, 320, 400, 40, f'Player_{int(time.time()) % 1000}')
        self.connect_button = Button(400, 400, 200, 50, 'Connect', GREEN)
        
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
        self.title_font = pygame.font.Font(None, 64)
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
        
    def draw_connection_screen(self):
        """Draw the connection screen"""
        self.screen.fill(WHITE)
        
        # Title
        title = self.title_font.render("🎮 Network Game", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)
        
        # Labels
        ip_label = self.font.render("Server IP:", True, BLACK)
        self.screen.blit(ip_label, (300, 220))
        
        name_label = self.font.render("Player Name:", True, BLACK)
        self.screen.blit(name_label, (300, 290))
        
        # Input boxes and button
        self.ip_input.draw(self.screen)
        self.name_input.draw(self.screen)
        self.connect_button.draw(self.screen)
        
        # Error message
        if self.connection_error:
            error_text = self.font.render(self.connection_error, True, RED)
            error_rect = error_text.get_rect(center=(SCREEN_WIDTH // 2, 480))
            self.screen.blit(error_text, error_rect)
        
        # Instructions
        instruction = self.small_font.render("Click input boxes to edit, then click Connect", True, DARK_GRAY)
        inst_rect = instruction.get_rect(center=(SCREEN_WIDTH // 2, 550))
        self.screen.blit(instruction, inst_rect)
    
    def draw_connecting_screen(self):
        """Draw the connecting screen"""
        self.screen.fill(WHITE)
        
        # Connecting message
        connecting = self.title_font.render("Connecting...", True, BLACK)
        connecting_rect = connecting.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(connecting, connecting_rect)
        
        # Animated dots
        dots = "." * ((pygame.time.get_ticks() // 500) % 4)
        dots_text = self.font.render(dots, True, BLACK)
        dots_rect = dots_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        self.screen.blit(dots_text, dots_rect)
    
    def update_snake_game(self):
        """Game logic is handled by server, client just displays"""
        # No client-side game logic needed - server handles everything
        pass
    
    def draw_game_screen(self):
        """Draw the game screen with snake game"""
        self.screen.fill(WHITE)
        
        # Title bar
        pygame.draw.rect(self.screen, DARK_GRAY, (0, 0, SCREEN_WIDTH, 60))
        
        if self.client:
            # Player info
            player_text = self.font.render(f"Player: {self.client.player_name}", True, WHITE)
            self.screen.blit(player_text, (20, 15))
            
            # Score - get from server game state
            score = 0
            alive = True
            if self.client.game_state:
                players = self.client.game_state.get('players', {})
                my_data = players.get(self.client.player_id, {})
                score = my_data.get('score', 0)
                alive = my_data.get('alive', True)
            
            score_text = self.font.render(f"Score: {score}", True, WHITE)
            self.screen.blit(score_text, (300, 15))
            
            # Connection status - check timeout
            if self.client.connected:
                time_since_update = time.time() - self.client.last_update_time
                if time_since_update > self.client.update_timeout:
                    # Timeout detected
                    status_text = self.small_font.render("🔴 Disconnected", True, RED)
                    self.screen.blit(status_text, (SCREEN_WIDTH - 180, 20))
                    
                    # Show timeout info
                    timeout_info = self.small_font.render(f"(No updates for {time_since_update:.1f}s)", True, RED)
                    self.screen.blit(timeout_info, (SCREEN_WIDTH - 250, 40))
                else:
                    status_text = self.small_font.render("🟢 Connected", True, GREEN)
                    self.screen.blit(status_text, (SCREEN_WIDTH - 150, 20))
            else:
                status_text = self.small_font.render("🔴 Disconnected", True, RED)
                self.screen.blit(status_text, (SCREEN_WIDTH - 180, 20))
        
        # Game area (snake game)
        game_area = pygame.Rect(self.game_offset_x, self.game_offset_y, 
                               self.game_area_width, self.game_area_height)
        pygame.draw.rect(self.screen, BLACK, game_area)  # Black background
        pygame.draw.rect(self.screen, WHITE, game_area, 3)  # White border
        
        # Draw grid lines (subtle)
        for x in range(0, self.game_area_width, self.grid_size):
            pygame.draw.line(self.screen, DARK_GRAY,
                           (self.game_offset_x + x, self.game_offset_y),
                           (self.game_offset_x + x, self.game_offset_y + self.game_area_height))
        for y in range(0, self.game_area_height, self.grid_size):
            pygame.draw.line(self.screen, DARK_GRAY,
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
                
                # Draw snake
                for i, segment in enumerate(snake):
                    if isinstance(segment, list):
                        segment = tuple(segment)
                    
                    x, y = segment
                    rect = pygame.Rect(
                        self.game_offset_x + x * self.grid_size + 1,
                        self.game_offset_y + y * self.grid_size + 1,
                        self.grid_size - 2,
                        self.grid_size - 2
                    )
                    
                    # Head is brighter
                    segment_color = head_color if i == 0 else body_color
                    pygame.draw.rect(self.screen, segment_color, rect)
                    pygame.draw.rect(self.screen, BLACK, rect, 1)
        
        # Draw bricks
        if self.client and self.client.game_state:
            bricks = self.client.game_state.get('bricks', [])
            
            for brick in bricks:
                if isinstance(brick, list):
                    x, y = brick
                else:
                    x, y = brick
                
                # Draw brick as orange square
                brick_rect = pygame.Rect(
                    self.game_offset_x + x * self.grid_size + 1,
                    self.game_offset_y + y * self.grid_size + 1,
                    self.grid_size - 2,
                    self.grid_size - 2
                )
                pygame.draw.rect(self.screen, (255, 128, 0), brick_rect)  # Orange
                pygame.draw.rect(self.screen, YELLOW, brick_rect, 2)  # Yellow border
        
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
                
                # Truncate long names
                if len(name) > 10:
                    name = name[:10] + ".."
                
                # Highlight current player
                if player_id == self.client.player_id:
                    name = f"► {name}"
                    color = BLUE
                else:
                    color = BLACK
                
                # Show dead status
                status = "💀" if not alive else ""
                
                # Draw player info
                name_text = self.small_font.render(f"{name} {status}", True, color)
                self.screen.blit(name_text, (panel_x + 5, y_offset))
                
                score_text = self.small_font.render(f"Score: {score}", True, DARK_GRAY)
                self.screen.blit(score_text, (panel_x + 5, y_offset + 18))
                
                y_offset += 40
                
                if y_offset > panel_y + SCREEN_HEIGHT - 200:
                    break
        
        # Controls info at bottom
        controls_y = SCREEN_HEIGHT - 50
        controls = self.small_font.render("Arrow Keys: Move | ESC: Quit", True, BLACK)
        self.screen.blit(controls, (20, controls_y))
    
    def handle_connection_events(self, event):
        """Handle events on connection screen"""
        self.ip_input.handle_event(event)
        self.name_input.handle_event(event)
        
        if self.connect_button.handle_event(event):
            # Start connection
            self.start_connection()
    
    def handle_game_events(self, event):
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
            
            # Send direction change to server
            if new_direction:
                self.client.player_data['direction'] = new_direction
                self.client.update_player_data()
    
    def start_connection(self):
        """Start connection to server"""
        server_ip = self.ip_input.text.strip()
        player_name = self.name_input.text.strip()
        
        if not server_ip:
            self.connection_error = "Please enter server IP"
            return
        
        if not player_name:
            player_name = f"Player_{int(time.time()) % 1000}"
        
        self.state = 'connecting'
        self.connection_error = ""
        
        # Start connection in background thread
        thread = threading.Thread(target=self.connect_to_server, 
                                 args=(server_ip, player_name), 
                                 daemon=True)
        thread.start()
    
    def connect_to_server(self, server_ip, player_name):
        """Connect to server in background"""
        try:
            self.client = GameClient(server_ip, 9089, player_name)
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
                self.connection_error = "Connection failed"
        except Exception as e:
            self.state = 'connection'
            self.connection_error = f"Error: {str(e)[:30]}"
    
    def run(self):
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

def main():
    print("="*60)
    print("🎮 GAME CLIENT - GUI Mode")
    print("="*60)
    print("Starting GUI...")
    
    gui = GameGUI()
    
    try:
        gui.run()
    except Exception as e:
        print(f"\n❌ GUI error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
