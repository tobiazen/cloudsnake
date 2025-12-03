# Player Statistics System

The CloudSnake game server now tracks comprehensive player statistics that persist across server restarts.

## Features

### Tracked Statistics

For each player:
- **Highscore**: The highest score ever achieved
- **Games Played**: Total number of game sessions
- **Total Kills**: Number of successful headshots on other players
- **Total Deaths**: Number of times the player died
- **Last Seen**: Timestamp of last activity

Global statistics:
- **All-Time Highscore**: The highest score ever achieved by any player
- **All-Time Highscore Player**: The player who achieved the all-time highscore
- **Total Games**: Total number of game sessions across all players

### Data Persistence

Statistics are automatically saved to `player_stats.json` in the server directory:
- On player join
- On player score change
- On player death
- On player disconnect

The JSON file survives server restarts, allowing the leaderboard to persist.

### Leaderboard

The server broadcasts a top-10 leaderboard to all clients with each game state update. The leaderboard includes:
- Player name
- Highscore
- Games played
- Total kills
- Total deaths

Clients can display this information in their UI.

## Implementation Details

### Server-Side

The statistics system tracks events automatically:

1. **Player Joins**: Increments `games_played` counter
2. **Player Dies**: 
   - From wall collision → increments `total_deaths`
   - From self-collision → increments `total_deaths`
   - From headshot → increments victim's `total_deaths` and shooter's `total_kills`
3. **Player Disconnects**: Updates final score and saves statistics
4. **Score Changes**: Updates `highscore` if current score exceeds previous record

### Client-Side

Clients receive leaderboard data in the game state broadcast:

```python
game_state = {
    'players': {...},
    'bricks': [...],
    'leaderboard': [
        {
            'name': 'PlayerName',
            'highscore': 1500,
            'games_played': 10,
            'total_kills': 25,
            'total_deaths': 8
        },
        ...
    ],
    'all_time_highscore': 2000,
    'all_time_highscore_player': 'TopPlayer'
}
```

## File Format

The `player_stats.json` file structure:

```json
{
  "players": {
    "PlayerName": {
      "highscore": 1500,
      "games_played": 10,
      "total_kills": 25,
      "total_deaths": 8,
      "last_seen": "2025-12-03T10:30:45.123456"
    }
  },
  "all_time_highscore": 2000,
  "all_time_highscore_player": "TopPlayer",
  "total_games": 100,
  "last_updated": "2025-12-03T10:30:45.123456"
}
```

## Systemd Service

When running as a systemd service, the statistics file will be created in the service's working directory. Make sure the service has write permissions to that directory.

Example systemd service configuration:

```ini
[Unit]
Description=CloudSnake Game Server
After=network.target

[Service]
Type=simple
User=gameserver
WorkingDirectory=/opt/cloudsnake
ExecStart=/usr/bin/python3 /opt/cloudsnake/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

The statistics file will be located at `/opt/cloudsnake/player_stats.json`.

## Testing

Run the test suite to verify statistics functionality:

```bash
python test_stats.py
```

This tests:
- Player stat updates
- Kill/death tracking
- All-time highscore tracking
- Persistence (save/load)
- Leaderboard sorting
