"""
Game State Management Module

This module handles all game state queries and data extraction from the server's game state.
It provides a clean interface for accessing player data, game objects, and other state information.
"""
from typing import Dict, List, Tuple, Optional, Any


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
    
    def update(self, game_state: Optional[Dict[str, Any]]) -> None:
        """
        Update the internal game state.
        
        Args:
            game_state: New game state dictionary from server
        """
        self._game_state = game_state or {}
    
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
    
    def get_player_name(self, player_id: str) -> str:
        """Get a player's name."""
        return self.get_player_data(player_id).get('player_name', 'Unknown')
    
    def get_player_score(self, player_id: str) -> int:
        """Get a player's score."""
        return self.get_player_data(player_id).get('score', 0)
    
    def get_player_snake(self, player_id: str) -> List[Tuple[int, int]]:
        """
        Get a player's snake segments.
        
        Returns:
            List of (x, y) tuples representing snake segments
        """
        snake = self.get_player_data(player_id).get('snake', [])
        # Convert to tuples if they're lists
        return [tuple(seg) if isinstance(seg, list) else seg for seg in snake]
    
    def get_player_color(self, player_id: str) -> Tuple[int, int, int]:
        """Get a player's color as RGB tuple."""
        return tuple(self.get_player_data(player_id).get('color', (255, 255, 255)))
    
    def get_player_bullets(self, player_id: str) -> int:
        """Get number of bullets a player has."""
        return self.get_player_data(player_id).get('bullets', 0)
    
    def get_player_bombs(self, player_id: str) -> int:
        """Get number of bombs a player has."""
        return self.get_player_data(player_id).get('bombs', 0)
    
    def is_player_alive(self, player_id: str) -> bool:
        """Check if a player is alive."""
        return self.get_player_data(player_id).get('alive', True)
    
    def is_player_in_game(self, player_id: str) -> bool:
        """Check if a player is actively in the game (not in lobby)."""
        return self.get_player_data(player_id).get('in_game', False)
    
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
            key=lambda x: x[1].get('score', 0),
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
    
    def __init__(self, player_id: str, player_data: Dict[str, Any]):
        """
        Initialize player info.
        
        Args:
            player_id: The player's unique ID
            player_data: The player's data dictionary
        """
        self.player_id = player_id
        self._data = player_data
    
    @property
    def name(self) -> str:
        """Player's name."""
        return self._data.get('player_name', 'Unknown')
    
    @property
    def score(self) -> int:
        """Player's score."""
        return self._data.get('score', 0)
    
    @property
    def snake(self) -> List[Tuple[int, int]]:
        """Player's snake segments as list of (x, y) tuples."""
        snake = self._data.get('snake', [])
        return [tuple(seg) if isinstance(seg, list) else seg for seg in snake]
    
    @property
    def color(self) -> Tuple[int, int, int]:
        """Player's color as RGB tuple."""
        return tuple(self._data.get('color', (255, 255, 255)))
    
    @property
    def bullets(self) -> int:
        """Number of bullets the player has."""
        return self._data.get('bullets', 0)
    
    @property
    def bombs(self) -> int:
        """Number of bombs the player has."""
        return self._data.get('bombs', 0)
    
    @property
    def is_alive(self) -> bool:
        """Whether the player is alive."""
        return self._data.get('alive', True)
    
    @property
    def in_game(self) -> bool:
        """Whether the player is actively in the game (not in lobby)."""
        return self._data.get('in_game', False)
    
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
