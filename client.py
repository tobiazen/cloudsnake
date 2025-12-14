import socket
import threading
import time
import json
import pygame
import os
from typing import Optional, Dict, Any, Tuple

# Import configuration and utilities
from config.constants import *
from utils.helpers import (
    get_unicode_font, get_resource_path, 
    draw_bullet_icon, draw_bomb_icon,
    draw_text_with_shadow, draw_gradient_rect
)
from utils.settings import load_settings, save_settings, add_player_name, add_server_address
from network.game_client import GameClient
from ui.widgets import InputBox, Button
from game.game_state import GameStateManager, PlayerInfo

# Initialize Pygame
pygame.init()

class GameGUI:
    """Main GUI for the game client"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("CloudSnake - Multiplayer Snake Game")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Client instance
        self.client: Optional[GameClient] = None
        
        # Game state manager
        self.game_state_manager = GameStateManager()
        
        # Settings management
        self.settings_file = 'settings.json'
        self.settings = load_settings(self.settings_file)
        
        # GUI state
        self.state = 'connection'  # 'connection', 'connecting', 'lobby', 'game'
        self.connection_error = ""
        
        # Name dropdown state
        self.dropdown_open = False
        self.selected_name_index = 0
        
        # Server dropdown state
        self.server_dropdown_open = False
        self.selected_server_index = 0
        
        # Connection screen widgets
        last_server = self.settings.get('last_server_address', self.settings.get('server_ip', ''))
        last_name = self.settings.get('last_player_name', '')
        
        self.ip_input = InputBox(300, 280, 400, 40, last_server)
        self.server_dropdown_button = Button(705, 280, 40, 40, '▼', DARK_GRAY)
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
        
        # Snake interpolation for smooth movement
        self.snake_positions = {}  # {player_id: [(x, y), ...]} - previous server positions
        self.snake_targets = {}    # {player_id: [(x, y), ...]} - current server positions
        self.interpolation_time = 0.0  # Time elapsed since last server update
        self.server_update_interval = 0.5  # Server updates at 2Hz (0.5 seconds)
        
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
    
    def update_game_state(self) -> None:
        """Update the game state manager with latest data from client."""
        if self.client and self.client.game_state:
            self.game_state_manager.update(self.client.game_state)
            # Update interpolation targets when new state arrives
            self.update_snake_positions_from_server()
        else:
            self.game_state_manager.update(None)
    
    def draw_title_bar(self) -> None:
        """Draw the title bar with player info and connection status"""
        draw_gradient_rect(self.screen, 0, 0, SCREEN_WIDTH, 60, PANEL_BG, BG_COLOR)
        
        if self.client:
            # Player info with modern styling
            player_text = self.font.render(f"Player: {self.client.player_name}", True, TEXT_COLOR)
            self.screen.blit(player_text, (20, 15))
            
            # Score - get from game state manager
            self.update_game_state()
            if self.client.player_id:
                score = self.game_state_manager.get_player_score(self.client.player_id)
            else:
                score = 0
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
    
    def draw_game_area_background(self) -> None:
        """Draw the game area background and grid"""
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
    
    def draw_snakes(self) -> None:
        """Draw all players' snakes"""
        if not self.client or not self.game_state_manager.is_valid:
            return
        
        # Show lobby message if not in game (use self.in_game flag, not game_state)
        # Note: in_game field is no longer sent in game_state updates (optimization)
        if not self.in_game:
            lobby_text = self.title_font.render("LOBBY", True, CYAN)
            lobby_rect = lobby_text.get_rect(center=(self.game_offset_x + self.game_area_width // 2,
                                                     self.game_offset_y + self.game_area_height // 2 - 50))
            self.screen.blit(lobby_text, lobby_rect)
            
            info_text = self.font.render("Open Menu and click 'Start Game' to play", True, TEXT_COLOR)
            info_rect = info_text.get_rect(center=(self.game_offset_x + self.game_area_width // 2,
                                                   self.game_offset_y + self.game_area_height // 2 + 20))
            self.screen.blit(info_text, info_rect)
        
        for player_id, player_data in self.game_state_manager.get_players().items():
            player = PlayerInfo(player_id, player_data, self.game_state_manager)
            
            # Don't draw snakes for dead players or players without snakes
            # Note: All players in game_state are in-game (server only sends to in_game players)
            if not player.snake or not player.is_alive:
                continue
            
            # Use colors from player info
            head_color = player.color
            body_color = player.body_color
            
            # Draw snake with rounded style and glow effect using interpolated positions
            for i, segment in enumerate(player.snake):
                # Get interpolated position for smooth movement
                interp_x, interp_y = self.get_interpolated_position(player_id, i)
                
                rect = pygame.Rect(
                    self.game_offset_x + interp_x * self.grid_size + 2,
                    self.game_offset_y + interp_y * self.grid_size + 2,
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
    
    def draw_game_objects(self) -> None:
        """Draw bricks, bullets, bombs, and explosions"""
        if not self.client or not self.game_state_manager.is_valid:
            return
        
        # Draw bricks with improved graphics
        for x, y in self.game_state_manager.get_bricks():
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
        for x, y in self.game_state_manager.get_bullet_bricks():
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
        for x, y in self.game_state_manager.get_bomb_bricks():
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
        for bullet in self.game_state_manager.get_bullets():
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
        for bomb in self.game_state_manager.get_bombs():
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
        
        # Draw explosion animations
        current_time = time.time()
        for explosion in self.game_state_manager.get_explosions():
            positions = explosion.get('positions', [])
            start_time = explosion.get('start_time', 0)
            duration = explosion.get('duration', 0.4)
            
            # Calculate progress (0.0 to 1.0)
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / duration) if duration > 0 else 1.0
            
            # Draw expanding circles effect
            for pos in positions:
                if isinstance(pos, list) and len(pos) >= 2:
                    exp_x, exp_y = pos[0], pos[1]
                else:
                    exp_x, exp_y = pos
                
                center = (
                    self.game_offset_x + int(exp_x * self.grid_size + self.grid_size // 2),
                    self.game_offset_y + int(exp_y * self.grid_size + self.grid_size // 2)
                )
                
                # Multiple expanding circles with fading colors
                if progress < 0.3:
                    # Bright explosion phase
                    outer_radius = int(self.grid_size * 0.8 * (progress / 0.3))
                    # Bright yellow core
                    if outer_radius > 2:
                        pygame.draw.circle(self.screen, YELLOW, center, outer_radius)
                    # Orange middle
                    mid_radius = int(outer_radius * 0.7)
                    if mid_radius > 1:
                        pygame.draw.circle(self.screen, ORANGE, center, mid_radius)
                elif progress < 0.7:
                    # Expanding fire phase
                    phase_progress = (progress - 0.3) / 0.4
                    outer_radius = int(self.grid_size * (0.8 + 0.2 * phase_progress))
                    # Red outer
                    pygame.draw.circle(self.screen, RED, center, outer_radius)
                    # Orange inner
                    inner_radius = int(outer_radius * 0.6)
                    if inner_radius > 1:
                        pygame.draw.circle(self.screen, ORANGE, center, inner_radius)
                else:
                    # Fading phase
                    phase_progress = (progress - 0.7) / 0.3
                    alpha_factor = 1.0 - phase_progress
                    outer_radius = int(self.grid_size * (1.0 - 0.2 * phase_progress))
                    # Darker red, fading
                    red_value = int(180 * alpha_factor)
                    fade_color = (red_value, int(red_value * 0.2), 0)
                    if outer_radius > 1:
                        pygame.draw.circle(self.screen, fade_color, center, outer_radius)
    
    def draw_death_overlay(self) -> None:
        """Draw death overlay with respawn button"""
        # Check if current player is dead and show respawn button
        show_respawn = False
        if self.client and self.game_state_manager.is_valid and self.client.player_id:
            # Only show respawn if player is in game, dead, and didn't leave voluntarily
            # Note: Use self.in_game since in_game field is no longer in game_state (optimization)
            is_alive = self.game_state_manager.is_player_alive(self.client.player_id)
            if self.in_game and not is_alive and not self.left_voluntarily:
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
    
    def draw_side_panel(self) -> None:
        """Draw side panel with player list"""
        panel_x = self.game_offset_x + self.game_area_width + 20
        panel_y = 110
        panel_width = SCREEN_WIDTH - panel_x - 10
        
        # Draw gray background panel for player list area
        panel_bg = pygame.Rect(panel_x, panel_y, panel_width, SCREEN_HEIGHT - panel_y - 40)
        pygame.draw.rect(self.screen, GRAY, panel_bg)
        pygame.draw.rect(self.screen, DARK_GRAY, panel_bg, 2)
        
        # Panel title
        panel_title = self.small_font.render("Players", True, BLACK)
        self.screen.blit(panel_title, (panel_x + 10, panel_y + 10))
        
        # Display player list with individual panels
        if self.client and self.game_state_manager.is_valid:
            y_offset = panel_y + 40
            
            # Get sorted players
            for player_id, player_data in self.game_state_manager.get_sorted_players(limit=15):
                player = PlayerInfo(player_id, player_data, self.game_state_manager)
                
                # Draw individual panel for each player (with padding from edges)
                player_panel_height = 58
                player_panel_padding = 5
                player_panel = pygame.Rect(panel_x + player_panel_padding, y_offset - 2, 
                                          panel_width - (player_panel_padding * 2), player_panel_height)
                
                # Highlight current player's panel
                if player_id == self.client.player_id:
                    pygame.draw.rect(self.screen, (240, 248, 255), player_panel)  # Light blue background
                    pygame.draw.rect(self.screen, player.color, player_panel, 3)  # Thick colored border
                else:
                    pygame.draw.rect(self.screen, WHITE, player_panel)  # White background
                    pygame.draw.rect(self.screen, LIGHT_GRAY, player_panel, 2)  # Gray border
                
                # Get truncated name
                display_name = player.get_truncated_name(10)
                
                # Highlight current player with arrow
                if player_id == self.client.player_id:
                    display_name = f"► {display_name}"
                
                # Use snake color for the name text
                text_color = player.color
                
                # Show dead status
                status = "💀" if not player.is_alive else ""
                
                # Draw player info inside the panel
                name_text = self.small_font.render(f"{display_name} {status}", True, text_color)
                self.screen.blit(name_text, (panel_x + player_panel_padding + 5, y_offset))
                
                score_text = self.small_font.render(f"Score: {player.score}", True, DARK_GRAY)
                self.screen.blit(score_text, (panel_x + player_panel_padding + 5, y_offset + 18))
                
                # Show bullets and bombs on same line with smaller, tighter icons
                icons_y = y_offset + 38
                icon_size = 12
                
                # Show bullet count as multiple icons (max 5) with tight spacing
                bullet_start_x = panel_x + player_panel_padding + 5
                bullets_to_show = min(player.bullets, 5)
                for i in range(bullets_to_show):
                    draw_bullet_icon(self.screen, bullet_start_x + (i * 11), icons_y, icon_size)
                
                # Show bomb count as multiple icons (max 5) - offset to right of bullets
                bomb_start_x = bullet_start_x + (5 * 11) + 5  # After max bullets + small gap
                bombs_to_show = min(player.bombs, 5)
                for i in range(bombs_to_show):
                    draw_bomb_icon(self.screen, bomb_start_x + (i * 14), icons_y, icon_size)
                
                y_offset += player_panel_height + 4  # 4px spacing between panels
                
                if y_offset > panel_y + SCREEN_HEIGHT - 200:
                    break
    
    def draw_menu_dropdown(self) -> None:
        """Draw menu button and dropdown"""
        if not self.client:
            return
        
        # Menu button positioned under player name on the left
        menu_button = Button(20, 50, 100, 35, 'Menu ▼', PURPLE)
        menu_button.draw(self.screen)
        self.menu_button = menu_button  # Store for event handling
        
        # Draw menu dropdown if open
        if self.game_menu_open:
            menu_x = 20
            menu_y = 90
            # Menu items change based on state
            if self.state == 'game':
                menu_items = ['Statistics', 'Leave Game', 'Disconnect']
            else:  # lobby state
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
            draw_text_with_shadow(self.screen, "CloudSnake", self.title_font, SCREEN_WIDTH // 2 - 150, 80, CYAN, 3)
        
        # Labels
        ip_label = self.font.render("Server IP:", True, TEXT_COLOR)
        self.screen.blit(ip_label, (300, 250))
        
        name_label = self.font.render("Player Name:", True, TEXT_COLOR)
        self.screen.blit(name_label, (300, 320))
        
        # Input boxes and buttons
        self.ip_input.draw(self.screen)
        self.server_dropdown_button.draw(self.screen)
        self.name_input.draw(self.screen)
        self.dropdown_button.draw(self.screen)
        self.connect_button.draw(self.screen)
        
        # Draw server dropdown menu if open
        if self.server_dropdown_open and self.settings.get('server_addresses', []):
            dropdown_y = 325
            for i, address in enumerate(self.settings['server_addresses'][:10]):
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
                
                # Truncate long addresses
                display_address = address if len(address) <= 30 else address[:27] + "..."
                address_text = self.small_font.render(display_address, True, color)
                self.screen.blit(address_text, (item_rect.x + 5, item_rect.y + 8))
        
        # Draw name dropdown menu if open
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
        draw_text_with_shadow(self.screen, "Statistics & Leaderboard", self.title_font, 120, 30, CYAN, 3)
        
        # Close button (X in top right)
        close_button = Button(SCREEN_WIDTH - 120, 30, 100, 40, '✕ Close', RED)
        close_button.draw(self.screen)
        self.stats_close_button = close_button  # Store for event handling
        
        # Get leaderboard data from game state manager
        self.update_game_state()
        leaderboard = self.game_state_manager.get_leaderboard()
        all_time_high = self.game_state_manager.get_all_time_highscore()
        all_time_player = self.game_state_manager.get_all_time_highscore_player()
        
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
        draw_text_with_shadow(self.screen, "Connecting", self.title_font, SCREEN_WIDTH // 2 - 130, SCREEN_HEIGHT // 2 - 30, CYAN, 3)
        
        # Animated dots
        dots = "." * ((pygame.time.get_ticks() // 500) % 4)
        dots_text = self.font.render(dots, True, TEXT_COLOR)
        dots_rect = dots_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        self.screen.blit(dots_text, dots_rect)
    
    def update_snake_game(self) -> None:
        """Game logic is handled by server, client just displays"""
        # No client-side game logic needed - server handles everything
        pass
    
    def draw_lobby_screen(self) -> None:
        """Draw the lobby screen"""
        # If showing statistics overlay, draw that instead
        if self.show_statistics:
            self.draw_statistics_screen()
            return
        
        # Dark background
        self.screen.fill(BG_COLOR)
        
        # Draw title bar and side panel (show connected players)
        self.draw_title_bar()
        self.draw_side_panel()
        
        # Draw game area background
        self.draw_game_area_background()
        
        # Draw lobby message in center of game area
        lobby_text = self.title_font.render("LOBBY", True, CYAN)
        lobby_rect = lobby_text.get_rect(center=(self.game_offset_x + self.game_area_width // 2,
                                                 self.game_offset_y + self.game_area_height // 2 - 50))
        self.screen.blit(lobby_text, lobby_rect)
        
        info_text = self.font.render("Open Menu and click 'Start Game' to play", True, TEXT_COLOR)
        info_rect = info_text.get_rect(center=(self.game_offset_x + self.game_area_width // 2,
                                               self.game_offset_y + self.game_area_height // 2 + 20))
        self.screen.blit(info_text, info_rect)
        
        # Show who else is in the lobby
        # Note: Server only sends game_state to in-game players, so we can't count lobby players from game_state
        # This feature is disabled for now - would need separate lobby player list from server
        # if self.client and self.game_state_manager.is_valid:
        #     pass
        
        # Controls info below game area
        game_area_bottom = self.game_offset_y + self.game_area_height
        controls_y = game_area_bottom + 5
        controls = self.small_font.render("Open Menu to Start Game or view Statistics | ESC: Quit", True, GRAY)
        self.screen.blit(controls, (20, controls_y))
        
        # Menu button and dropdown (rendered last to be on top)
        self.draw_menu_dropdown()
    
    def draw_game_screen(self) -> None:
        """Draw the game screen with snake game"""
        # If showing statistics overlay, draw that instead
        if self.show_statistics:
            self.draw_statistics_screen()
            return
        
        # Dark background
        self.screen.fill(BG_COLOR)
        
        # Draw all screen components
        self.draw_title_bar()
        self.draw_game_area_background()
        self.draw_snakes()
        self.draw_game_objects()
        self.draw_death_overlay()
        self.draw_side_panel()
        
        # Controls info below game area
        game_area_bottom = self.game_offset_y + self.game_area_height
        controls_y = game_area_bottom + 5  # 5px below game area
        controls = self.small_font.render("Arrow Keys: Move | SPACE: Shoot | B: Throw Bomb | R: Respawn | ESC: Quit", True, GRAY)
        self.screen.blit(controls, (20, controls_y))
        
        # Menu button and dropdown (rendered last to be on top)
        self.draw_menu_dropdown()
    
    def handle_connection_events(self, event: Any) -> None:
        """Handle events on connection screen"""
        # Handle server dropdown button
        if self.server_dropdown_button.handle_event(event):
            if self.settings.get('server_addresses', []):
                self.server_dropdown_open = not self.server_dropdown_open
                if self.server_dropdown_open:
                    self.dropdown_open = False  # Close name dropdown
        
        # Handle server dropdown selection
        if event.type == pygame.MOUSEBUTTONDOWN and self.server_dropdown_open:
            mouse_pos = event.pos
            dropdown_y = 325
            for i, address in enumerate(self.settings.get('server_addresses', [])[:10]):
                item_rect = pygame.Rect(300, dropdown_y + i * 35, 400, 35)
                if item_rect.collidepoint(mouse_pos):
                    self.ip_input.text = address
                    self.server_dropdown_open = False
                    return
        
        # Close server dropdown if clicking outside
        if event.type == pygame.MOUSEBUTTONDOWN and self.server_dropdown_open:
            mouse_pos = event.pos
            dropdown_area = pygame.Rect(300, 250, 445, 400)
            if not dropdown_area.collidepoint(mouse_pos):
                self.server_dropdown_open = False
        
        # Handle name dropdown button
        if self.dropdown_button.handle_event(event):
            if self.settings['player_names']:
                self.dropdown_open = not self.dropdown_open
                if self.dropdown_open:
                    self.server_dropdown_open = False  # Close server dropdown
        
        # Handle name dropdown selection
        if event.type == pygame.MOUSEBUTTONDOWN and self.dropdown_open:
            mouse_pos = event.pos
            dropdown_y = 395
            for i, name in enumerate(self.settings['player_names'][:10]):
                item_rect = pygame.Rect(300, dropdown_y + i * 35, 400, 35)
                if item_rect.collidepoint(mouse_pos):
                    self.name_input.text = name
                    self.dropdown_open = False
                    return
        
        # Close name dropdown if clicking outside
        if event.type == pygame.MOUSEBUTTONDOWN and self.dropdown_open:
            mouse_pos = event.pos
            dropdown_area = pygame.Rect(300, 350, 445, 400)
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
    
    def handle_lobby_events(self, event: Any) -> None:
        """Handle events in lobby"""
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
                        elif i == 1:  # Start Game
                            # Start game - join active game
                            self.client.send_to_server({'type': 'start_game'}, use_game_socket=True)
                            self.in_game = True
                            self.left_voluntarily = False
                            self.state = 'game'  # Switch to game state
                            self.game_menu_open = False
                        elif i == 2:  # Disconnect
                            self.client.disconnect()
                            self.state = 'connection'
                            self.game_menu_open = False
                        return
            
            # Close menu if clicking outside
            menu_area = pygame.Rect(20, 50, 180, 168)
            if not menu_area.collidepoint(mouse_pos):
                self.game_menu_open = False
    
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
                        elif i == 1:  # Leave Game (only available in game state)
                            # Leave game - return to lobby
                            self.client.send_to_server({'type': 'leave_game'}, use_game_socket=True)
                            self.in_game = False
                            self.left_voluntarily = True  # Mark as voluntary leave
                            self.state = 'lobby'  # Switch to lobby state
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
        if self.client and self.client.player_id:
            self.update_game_state()
            is_dead = not self.game_state_manager.is_player_alive(self.client.player_id)
        
        # Handle respawn button if dead and in game
        # Note: Use self.in_game since in_game field is no longer in game_state (optimization)
        if is_dead and self.in_game:
            if self.respawn_button.handle_event(event):
                self.client.respawn()
                self.left_voluntarily = False  # Reset flag after respawn
                return
        
        # Handle keyboard input for snake direction (only if alive and in game)
        if event.type == pygame.KEYDOWN and not is_dead and self.in_game:
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
                }, use_game_socket=True)
    
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
        
        # Save the player name and server address to history
        add_player_name(self.settings, player_name, self.settings_file)
        add_server_address(self.settings, server_ip, self.settings_file)
        
        self.state = 'connecting'
        self.connection_error = ""
        self.dropdown_open = False
        self.server_dropdown_open = False
        
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
                
                # Set callback for player metadata messages (optimization)
                self.client.on_player_metadata = self.handle_player_metadata
                
                # Start receive thread for game socket (game state updates)
                receive_thread = threading.Thread(target=self.client.receive_messages, daemon=True)
                receive_thread.start()
                
                # Start receive thread for control socket (pong responses)
                control_thread = threading.Thread(target=self.client.receive_control_messages, daemon=True)
                control_thread.start()
                
                # Start heartbeat thread
                heartbeat_thread = threading.Thread(target=self.client.send_heartbeat, daemon=True)
                heartbeat_thread.start()
                
                self.state = 'lobby'  # Enter lobby after connecting
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
    
    def handle_player_metadata(self, message: Dict[str, Any]) -> None:
        """Handle player metadata messages from server (name, color optimization)"""
        player_id = message.get('player_id')
        name = message.get('n')
        color = message.get('c')
        
        if player_id and name is not None and color is not None:
            # Update game state manager's metadata cache
            self.game_state_manager.update_player_metadata(player_id, name, color)
    
    def update_interpolation(self) -> None:
        """Update interpolation time for smooth snake movement"""
        delta_time = self.clock.get_time() / 1000.0  # Convert ms to seconds
        self.interpolation_time += delta_time
        
        # Cap interpolation time at server update interval
        if self.interpolation_time > self.server_update_interval:
            self.interpolation_time = self.server_update_interval
    
    def update_snake_positions_from_server(self) -> None:
        """Called when new game state arrives from server - update target positions"""
        if not self.game_state_manager.is_valid:
            return
        
        for player_id, player_data in self.game_state_manager.get_players().items():
            player = PlayerInfo(player_id, player_data, self.game_state_manager)
            if player.snake:
                # Store previous positions
                if player_id in self.snake_targets:
                    self.snake_positions[player_id] = self.snake_targets[player_id].copy()
                else:
                    self.snake_positions[player_id] = player.snake.copy()
                
                # Set new target positions
                self.snake_targets[player_id] = player.snake.copy()
        
        # Reset interpolation timer
        self.interpolation_time = 0.0
    
    def get_interpolated_position(self, player_id: int, segment_index: int) -> Tuple[float, float]:
        """Get interpolated position for a snake segment"""
        # Get current and target positions
        if player_id not in self.snake_positions or player_id not in self.snake_targets:
            # No interpolation data, return target position
            if player_id in self.snake_targets and segment_index < len(self.snake_targets[player_id]):
                return self.snake_targets[player_id][segment_index]
            return (0, 0)
        
        current_snake = self.snake_positions[player_id]
        target_snake = self.snake_targets[player_id]
        
        # Handle snake length changes
        if segment_index >= len(current_snake) or segment_index >= len(target_snake):
            # Segment doesn't exist in both states, just return target
            if segment_index < len(target_snake):
                return target_snake[segment_index]
            return (0, 0)
        
        # Interpolate between current and target
        t = min(self.interpolation_time / self.server_update_interval, 1.0)
        
        current_x, current_y = current_snake[segment_index]
        target_x, target_y = target_snake[segment_index]
        
        # Linear interpolation
        interp_x = current_x + (target_x - current_x) * t
        interp_y = current_y + (target_y - current_y) * t
        
        return (interp_x, interp_y)
    
    def run(self) -> None:
        """Main GUI loop"""
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # State-specific event handling
                if self.state == 'connection':
                    self.handle_connection_events(event)
                elif self.state == 'lobby':
                    self.handle_lobby_events(event)
                elif self.state == 'game':
                    self.handle_game_events(event)
            
            # State-specific updates and rendering
            if self.state == 'connection':
                self.draw_connection_screen()
            elif self.state == 'connecting':
                self.draw_connecting_screen()
            elif self.state == 'lobby':
                self.draw_lobby_screen()
            elif self.state == 'game':
                self.update_snake_game()
                self.update_interpolation()
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
