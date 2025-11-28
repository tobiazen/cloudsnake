# CloudSnake 🐍

A multiplayer snake game where players compete to collect bricks and grow their snakes while avoiding walls, themselves, and other players.

## Features

- **Multiplayer**: Up to 16 players can connect simultaneously
- **Real-time gameplay**: Server broadcasts game state at 2Hz (every 0.5 seconds)
- **Dynamic brick spawning**: Bricks spawn based on the number of active players
- **Shooting system**: Collect bullet bricks and shoot at opponents
- **Respawn system**: Players can respawn after death, keeping half their score
- **Color-coded players**: Each player gets a unique color
- **GUI interface**: Clean pygame-based graphical interface

## Quick Installation (Recommended)

**For Players**: Download the standalone executable - no installation needed!

### Windows
1. Download `SnakeGame.exe` from the [latest release](https://github.com/tobiazen/cloudsnake/releases/latest)
2. Double-click to run
3. No Python or dependencies required!

### Linux
1. Download `SnakeGame-linux` from the [latest release](https://github.com/tobiazen/cloudsnake/releases/latest)
2. Run: `./SnakeGame-linux`
3. No Python or dependencies required!

### macOS
1. Download `SnakeGame-macos` from the [latest release](https://github.com/tobiazen/cloudsnake/releases/latest)
2. Run: `./SnakeGame-macos`
3. No Python or dependencies required!

**✨ Executables are automatically built for every commit!** The latest version is always available at the releases page.

## Manual Installation (For Developers)

If you want to modify the code or run the server:

1. Clone the repository:
```bash
git clone https://github.com/tobiazen/cloudsnake.git
cd cloudsnake
```

2. Install dependencies:
```bash
pip install pygame
```

## How to Play

### Starting the Server

Run the server on the host machine:

```bash
python server.py
```

The server will start listening on port **50000** by default. Make sure this port is open and accessible to clients on your network.

### Starting the Client

**If you downloaded the executable:**
- **Windows**: Double-click `SnakeGame.exe`
- **Linux**: Run `./SnakeGame`

**If you cloned the repository:**
```bash
python client.py
```

### Game Controls

- **Arrow Keys** or **WASD**: Control snake direction
  - `↑` or `W`: Move up
  - `↓` or `S`: Move down
  - `←` or `A`: Move left
  - `→` or `D`: Move right
- **SPACE**: Shoot a bullet (if you have bullets available)
- **R**: Respawn after death (costs half your score)
- **ESC**: Exit the game

### Connecting to a Server

1. When you start the client, you'll see a connection screen
2. Enter the **server IP address** (use the IP where the server is running)
3. Enter your **player name**
4. Click **Connect** or press Enter

### Gameplay Rules

1. **Movement**: Your snake moves continuously in the current direction
2. **Growing**: Collect bricks (red squares) to grow your snake and increase your score
3. **Scoring**: 
   - +1 point for each move
   - +100 points for collecting a regular brick
4. **Shooting System**:
   - **Bullet Bricks**: Light blue squares that spawn randomly (5% chance)
   - **Collecting Bullet Bricks**: Gives you 1 bullet (doesn't grow your snake or award points)
   - **Shooting**: Press SPACE to fire a bullet in your current direction
   - **Bullet Mechanics**:
     - Bullets travel at 2x snake speed
     - **Headshot**: Hitting an opponent's head kills them instantly
     - **Body Shot**: Hitting an opponent's body truncates their snake at the hit point (50 points deducted per removed segment)
     - Bullets are removed when they hit a wall or a snake
   - **Bullet Count**: Displayed in your player panel (under your score)
5. **Death**: You die if you:
   - Hit a wall
   - Hit yourself
   - Hit another player's snake
   - Get hit by a bullet in the head
6. **Death Consequences**:
   - All your bullets are lost
   - Your snake is removed from the game board
7. **Respawning**: After death, press `R` to respawn with half your previous score and zero bullets
8. **Safe Spawn**: When spawning, your initial direction is chosen to avoid immediate collisions

### Game Screen

- **Your snake**: Highlighted with a thicker outline
- **Other players**: Different colored snakes
- **Regular Bricks**: Red squares scattered on the grid
- **Bullet Bricks**: Light blue squares (give you bullets when collected)
- **Active Bullets**: Small red circles moving across the grid
- **Scoreboard**: Displays all players' names, scores, and bullet counts on the right side

## Network Configuration

### Default Port

The game uses **port 50000** for UDP communication.

### Firewall Settings

If you're hosting a server, make sure to:
- Allow incoming UDP traffic on port 50000
- Configure your router to forward port 50000 to the server machine (for internet play)

### Local Network Play

For LAN play:
1. Server displays its local IP address on startup
2. Clients use this IP to connect (e.g., `192.168.1.100`)

### Internet Play

For internet play:
1. Server needs a public IP or port forwarding configured
2. Clients use the public IP to connect

## Architecture

### Server (`server.py`)

- Handles up to 16 simultaneous connections
- Manages game state (player positions, bricks, scores)
- Broadcasts game updates to all clients at 2Hz
- Handles collision detection and game logic
- Spawns bricks dynamically based on player count

### Client (`client.py`)

- Pygame-based GUI
- Sends player input to server
- Receives and renders game state
- Maintains connection with heartbeat mechanism
- Saves connection settings locally

## Game Configuration

### Grid Size

- Width: 40 cells
- Height: 30 cells

### Timing

- Broadcast interval: 0.5 seconds (2Hz)
- Connection timeout: 10 seconds
- Client update timeout: 5 seconds

### Player Limits

- Maximum players: 16
- Minimum spawn distance from walls: 5 cells

### Brick Spawning

- 1 player: 1 brick
- 2-3 players: 2 bricks
- 4-5 players: 3 bricks
- And so on...

### Shooting Mechanics

- Bullet brick spawn chance: 5%
- Bullet speed: 2x snake movement speed
- Bullets per bullet brick: 1
- Headshot: Instant kill
- Body shot: Truncates snake, -50 points per removed segment

## Troubleshooting

### "Connection timeout - server not responding"

- Verify the server is running
- Check the IP address is correct
- Ensure port 50000 is not blocked by firewall

### "Server is full"

- The server has reached its maximum capacity (16 players)
- Wait for a player to disconnect

### High latency or lag

- Check network connection quality
- Reduce distance between client and server
- Close other network-intensive applications

### Server crashes or errors

- Check console for error messages
- Ensure proper network configuration
- Verify Python and pygame versions

## Development

### File Structure

```
cloudsnake/
├── server.py          # Game server
├── client.py          # Game client with GUI
├── settings.json      # Client settings (auto-generated)
├── README.md          # This file
└── LICENSE            # License file
```

### Protocol

The game uses UDP for communication with JSON messages:

- **connect**: Client requests to join
- **disconnect**: Client leaves the game
- **update**: Client sends direction changes or respawn requests
- **game_state**: Server broadcasts current game state
- **ping/pong**: Keepalive mechanism

## License

See LICENSE file for details.

## Credits

Created with AI assistance (vibecoded).
