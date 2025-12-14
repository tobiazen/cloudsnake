"""
Game State Management Module

This module handles all game state queries and data extraction from the server's game state.
It provides a clean interface for accessing player data, game objects, and other state information.
"""
from typing import Dict, List, Tuple, Optional, Any

# Key mappings for optimized network protocol (short keys)
# Maps long key names to short keys used in network transmission
# NOTE: As of latest optimization, game_state broadcasts only send dynamic data:
#   s, d, sc, a, bu, bo (snake, direction, score, alive, bullets, bombs)
# Static data (n=name, c=color) is sent once via metadata updates
KEY_MAP = {
    'player_name': 'n',
    'connected_at': 'ca',
    'last_seen': 'ls',
    'snake': 's',
    'direction': 'd',
    'score': 'sc',
    'alive': 'a',
    'color': 'c',
    'bullets': 'bu',
    'bombs': 'bo',
    'in_game': 'ig'
}


def _get_key(data: Dict[str, Any], long_key: str, default: Any = None) -> Any:
    """
    Get value from data dict using either long or short key name.
    Tries short key first (for optimized protocol), falls back to long key.
    """
    short_key = KEY_MAP.get(long_key, long_key)
    # Try short key first, then long key, then default
    return data.get(short_key, data.get(long_key, default))


class GameStateManager:
    """
    Manages game state queries and provides convenient access to game data.
    
    This class acts as a facade over the raw game_state dictionary received from the server,
    providing type-safe and convenient methods to access various game elements.
    """
    
    def __init__(self, game_state: Optional[Dict[str, Any]] = None):
        """
        Initialize the game state manager.
        
        Args:
            game_state: The raw game state dictionary from the server
        """
        self._game_state = game_state or {}
        # Cache for reconstructed snakes (to handle delta encoding)
        self._snake_cache: Dict[str, List[Tuple[int, int]]] = {}
        # Cache for player metadata (name, color) - sent separately from game_state
        self._player_metadata: Dict[str, Dict[str, Any]] = {}
    
    def update(self, game_state: Optional[Dict[str, Any]]) -> None:
        """
        Update the internal game state.
        
        Args:
            game_state: New game state dictionary from server
        """
        self._game_state = game_state or {}
    
    def update_player_metadata(self, player_id: str, name: str, color: int) -> None:
        """
        Update cached player metadata (name, color).
        Called when receiving 'player_metadata' messages from server.
        
        Args:
            player_id: The player's unique ID
            name: The player's name
            color: The player's color as hex int (0xRRGGBB)
        """
        self._player_metadata[player_id] = {'n': name, 'c': color}
    
    @property
    def is_valid(self) -> bool:
        """Check if game state is valid and not empty."""
        return bool(self._game_state)
    
    # Player-related methods
    
    def get_players(self) -> Dict[str, Dict[str, Any]]:
        """Get all players in the game."""
        return self._game_state.get('players', {})
    
    def get_player_data(self, player_id: str) -> Dict[str, Any]:
        """
        Get data for a specific player.
        
        Args:
            player_id: The player's unique ID
            
        Returns:
            Player data dictionary, or empty dict if not found
        """
        players = self.get_players()
        return players.get(player_id, {})
    
    def get_player_name(self, player_id: int) -> str:
        """Get a player's name (from metadata cache or player data)."""
        # Check metadata cache first (optimization - name not sent in game_state updates)
        if player_id in self._player_metadata:
            return self._player_metadata[player_id].get('n', 'Unknown')
        # Fallback to player data (for backward compatibility)
        return _get_key(self.get_player_data(player_id), 'player_name', 'Unknown')
    
    def get_player_score(self, player_id: int) -> int:
        """Get a player's score."""
        return _get_key(self.get_player_data(player_id), 'score', 0)
    
    def get_player_snake(self, player_id: int) -> List[Tuple[int, int]]:
        """
        Get a player's snake segments.
        Handles delta encoding: if snake is [head, length], reconstructs from cache.
        
        Returns:
            List of (x, y) tuples representing snake segments
        """
        snake_data = _get_key(self.get_player_data(player_id), 'snake', [])
        
        if not snake_data:
            return []
        
        # Check if this is delta-encoded (new format: [head_pos, length])
        if len(snake_data) == 2 and isinstance(snake_data[1], int):
            # Delta encoding: [head_position, length]
            head_pos = tuple(snake_data[0]) if isinstance(snake_data[0], list) else snake_data[0]
            target_length = snake_data[1]
            
            # Get cached snake for this player
            cached_snake = self._snake_cache.get(player_id, [])
            
            # Reconstruct snake: add new head, keep length segments
            if cached_snake and len(cached_snake) > 0:
                # Check if head moved (not the same position)
                if not cached_snake or cached_snake[0] != head_pos:
                    # Head moved, reconstruct: new head + old segments (up to length-1)
                    new_snake = [head_pos] + cached_snake[:target_length-1]
                else:
                    # Head didn't move (shouldn't happen), use cached
                    new_snake = cached_snake[:target_length]
            else:
                # No cache, create snake at head position
                new_snake = [head_pos] * target_length
            
            # Update cache
            self._snake_cache[player_id] = new_snake
            return new_snake
        else:
            # Full snake data (old format or initial sync)
            # Convert to tuples if they're lists
            full_snake = [tuple(seg) if isinstance(seg, list) else seg for seg in snake_data]
            # Update cache with full data
            self._snake_cache[player_id] = full_snake
            return full_snake
    
    def get_player_color(self, player_id: int) -> Tuple[int, int, int]:
        """Get a player's color as RGB tuple (from metadata cache or player data)."""
        # Check metadata cache first (optimization - color not sent in game_state updates)
        if player_id in self._player_metadata:
            color_int = self._player_metadata[player_id].get('c')
            if color_int is not None:
                # Convert hex int back to RGB tuple: 0xRRGGBB -> (R, G, B)
                r = (color_int >> 16) & 0xFF
                g = (color_int >> 8) & 0xFF
                b = color_int & 0xFF
                return (r, g, b)
        
        # Fallback to player data (for backward compatibility)
        color = _get_key(self.get_player_data(player_id), 'color', (255, 255, 255))
        if color is None:
            return (255, 255, 255)  # Default white
        # Handle both hex int and RGB tuple formats
        if isinstance(color, int):
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            return (r, g, b)
        return tuple(color)
    
    def get_player_bullets(self, player_id: int) -> int:
        """Get number of bullets a player has."""
        return _get_key(self.get_player_data(player_id), 'bullets', 0)
    
    def get_player_bombs(self, player_id: int) -> int:
        """Get number of bombs a player has."""
        return _get_key(self.get_player_data(player_id), 'bombs', 0)
    
    def is_player_alive(self, player_id: int) -> bool:
        """Check if a player is alive."""
        return _get_key(self.get_player_data(player_id), 'alive', True)
    
    def is_player_in_game(self, player_id: int) -> bool:
        """Check if a player is actively in the game (not in lobby)."""
        return _get_key(self.get_player_data(player_id), 'in_game', False)
    
    def get_sorted_players(self, limit: Optional[int] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Get players sorted by score (highest first).
        
        Args:
            limit: Optional maximum number of players to return
            
        Returns:
            List of (player_id, player_data) tuples sorted by score
        """
        players = self.get_players()
        sorted_players = sorted(
            players.items(),
            key=lambda x: _get_key(x[1], 'score', 0),
            reverse=True
        )
        
        if limit is not None:
            sorted_players = sorted_players[:limit]
        
        return sorted_players
    
    # Game objects methods
    
    def get_bricks(self) -> List[Tuple[int, int]]:
        """
        Get all regular bricks in the game.
        
        Returns:
            List of (x, y) tuples for brick positions
        """
        bricks = self._game_state.get('bricks', [])
        return [tuple(brick) if isinstance(brick, list) else brick for brick in bricks]
    
    def get_bullet_bricks(self) -> List[Tuple[int, int]]:
        """
        Get all bullet bricks (special bricks that give bullets).
        
        Returns:
            List of (x, y) tuples for bullet brick positions
        """
        bullet_bricks = self._game_state.get('bullet_bricks', [])
        return [tuple(brick) if isinstance(brick, list) else brick for brick in bullet_bricks]
    
    def get_bomb_bricks(self) -> List[Tuple[int, int]]:
        """
        Get all bomb bricks (special bricks that give bombs).
        
        Returns:
            List of (x, y) tuples for bomb brick positions
        """
        bomb_bricks = self._game_state.get('bomb_bricks', [])
        return [tuple(brick) if isinstance(brick, list) else brick for brick in bomb_bricks]
    
    def get_bullets(self) -> List[Dict[str, Any]]:
        """
        Get all bullets in the game.
        
        Returns:
            List of bullet dictionaries with 'pos' and other data
        """
        return self._game_state.get('bullets', [])
    
    def get_bombs(self) -> List[Dict[str, Any]]:
        """
        Get all bombs in the game.
        
        Returns:
            List of bomb dictionaries with 'pos', 'timer', etc.
        """
        return self._game_state.get('bombs', [])
    
    def get_explosions(self) -> List[Dict[str, Any]]:
        """
        Get all active explosions in the game.
        
        Returns:
            List of explosion dictionaries with 'pos', 'timer', etc.
        """
        return self._game_state.get('explosions', [])
    
    # Leaderboard methods
    
    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get the leaderboard data."""
        return self._game_state.get('leaderboard', [])
    
    def get_all_time_highscore(self) -> int:
        """Get the all-time high score."""
        return self._game_state.get('all_time_highscore', 0)
    
    def get_all_time_highscore_player(self) -> str:
        """Get the name of the player with the all-time high score."""
        return self._game_state.get('all_time_highscore_player', 'None')


class PlayerInfo:
    """
    Convenience class for working with player data.
    
    Provides a cleaner interface for accessing player information
    without repeated dictionary lookups.
    """
    
    def __init__(self, player_id: str, player_data: Dict[str, Any], game_state_manager: Optional['GameStateManager'] = None):
        """
        Initialize player info.
        
        Args:
            player_id: The player's unique ID
            player_data: The player's data dictionary
            game_state_manager: Optional reference to GameStateManager for snake reconstruction
        """
        self.player_id = player_id
        self._data = player_data
        self._game_state_manager = game_state_manager
    
    @property
    def name(self) -> str:
        """Player's name (from metadata cache or player data)."""
        # Use game state manager to get name from metadata cache
        if self._game_state_manager:
            return self._game_state_manager.get_player_name(self.player_id)
        return _get_key(self._data, 'player_name', 'Unknown')
    
    @property
    def score(self) -> int:
        """Player's score."""
        return _get_key(self._data, 'score', 0)
    
    @property
    def snake(self) -> List[Tuple[int, int]]:
        """Player's snake segments as list of (x, y) tuples."""
        # Use game state manager for proper snake reconstruction if available
        if self._game_state_manager:
            return self._game_state_manager.get_player_snake(self.player_id)
        # Fallback: direct access (won't handle delta encoding)
        snake = _get_key(self._data, 'snake', [])
        return [tuple(seg) if isinstance(seg, list) else seg for seg in snake]
    
    @property
    def color(self) -> Tuple[int, int, int]:
        """Player's color as RGB tuple (from metadata cache or player data)."""
        # Use game state manager to get color from metadata cache
        if self._game_state_manager:
            return self._game_state_manager.get_player_color(self.player_id)
        
        # Fallback for when no game state manager is available
        color = _get_key(self._data, 'color', (255, 255, 255))
        if color is None:
            return (255, 255, 255)  # Default white
        # Handle hex int color (from optimized network protocol)
        if isinstance(color, int):
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            return (r, g, b)
        # Handle array/list color [R, G, B]
        return tuple(color)
    
    @property
    def bullets(self) -> int:
        """Number of bullets the player has."""
        return _get_key(self._data, 'bullets', 0)
    
    @property
    def bombs(self) -> int:
        """Number of bombs the player has."""
        return _get_key(self._data, 'bombs', 0)
    
    @property
    def is_alive(self) -> bool:
        """Whether the player is alive."""
        return _get_key(self._data, 'alive', True)
    
    @property
    def in_game(self) -> bool:
        """Whether the player is actively in the game (not in lobby)."""
        return _get_key(self._data, 'in_game', False)
    
    @property
    def head_position(self) -> Optional[Tuple[int, int]]:
        """Position of the snake's head, or None if snake is empty."""
        snake = self.snake
        return snake[0] if snake else None
    
    @property
    def body_color(self) -> Tuple[int, int, int]:
        """Darker color for snake body (70% of head color)."""
        return tuple(int(c * 0.7) for c in self.color)
    
    def get_truncated_name(self, max_length: int = 10) -> str:
        """
        Get player name truncated to max length.
        
        Args:
            max_length: Maximum length of name
            
        Returns:
            Truncated name with ".." if longer than max_length
        """
        name = self.name
        if len(name) > max_length:
            return name[:max_length] + ".."
        return name
