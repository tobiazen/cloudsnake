# CloudSnake 🐍

A multiplayer snake game where players compete to collect bricks and grow their snakes while avoiding walls, themselves, and other players.

## Features

- **Multiplayer**: Up to 16 players can connect simultaneously
- **Real-time gameplay**: Server broadcasts game state at 2Hz (every 0.5 seconds)
- **Dynamic brick spawning**: Bricks spawn based on the number of active players
- **Shooting system**: Collect bullet bricks and shoot at opponents
- **Bomb system**: Collect bomb bricks and throw area-of-effect explosives
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
1. Download `SnakeGame-linux.zip` from the [latest release](https://github.com/tobiazen/cloudsnake/releases/latest)
2. Extract the zip file
3. Run: `./snake-game.sh`
4. No Python or dependencies required!

### macOS
1. Download `SnakeGame-macos.zip` from the [latest release](https://github.com/tobiazen/cloudsnake/releases/latest)
2. Extract the zip file
3. Run: `./snake-game.sh`
4. No Python or dependencies required!

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
- **B**: Throw a bomb (if you have bombs available)
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
     - Bullets travel at 3x snake speed
     - **Headshot**: Hitting an opponent's head kills them instantly
     - **Body Shot**: Hitting an opponent's body truncates their snake at the hit point (50 points deducted per removed segment)
     - Bullets are removed when they hit a wall or a snake
   - **Bullet Count**: Displayed in blue text in your player panel (under your score)
5. **Bomb System**:
   - **Bomb Bricks**: Red squares that spawn randomly (2% chance)
   - **Collecting Bomb Bricks**: Gives you 1 bomb (doesn't grow your snake or award points)
   - **Throwing**: Press B to throw a bomb
   - **Bomb Mechanics**:
     - Bombs are thrown **2-5 cells** away (random distance)
     - Direction is random: **left or right** from your snake's head
     - Bombs explode after **2-4 seconds** (random timer)
     - **3x3 Explosion Area**: Damages all snakes within a 3x3 grid centered on the bomb
     - **Headshot**: If the explosion hits a snake's head, instant kill
     - **Body Hit**: If the explosion hits a snake's body, truncates from that point (50 points deducted per removed segment)
     - Multiple snakes can be hit by one explosion
     - Visual: Bombs appear as black spheres with red glow
   - **Bomb Count**: Displayed in red text in your player panel (under bullets)
   - **Strategic Use**: Bombs are powerful but unpredictable - use carefully near groups of snakes!
6. **Death**: You die if you:
   - Hit a wall
   - Hit yourself
   - Hit another player's snake
   - Get hit by a bullet in the head
   - Get hit by a bomb explosion in the head
7. **Death Consequences**:
   - All your bullets and bombs are lost
   - Your snake is removed from the game board
8. **Respawning**: After death, press `R` to respawn with half your previous score and zero bullets/bombs
9. **Safe Spawn**: When spawning, your initial direction is chosen to avoid immediate collisions

### Game Screen

- **Your snake**: Highlighted with a thicker outline
- **Other players**: Different colored snakes
- **Regular Bricks**: Orange squares scattered on the grid
- **Bullet Bricks**: Light blue (cyan) squares with blue border (give you bullets when collected)
- **Bomb Bricks**: Red squares with dark red border (give you bombs when collected)
- **Active Bullets**: Small red circles moving across the grid
- **Active Bombs**: Black spheres with red/dark-red glow (explode after 2-4 seconds)
- **Scoreboard**: Displays all players' names, scores, bullet counts (blue), and bomb counts (red) on the right side

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

### Special Brick Spawn Rates

- **Regular bricks**: 93% chance (orange - grow your snake and award points)
- **Bullet bricks**: 5% chance (cyan - gives 1 bullet)
- **Bomb bricks**: 2% chance (red - gives 1 bomb)

### Shooting Mechanics

- Bullet speed: 3x snake movement speed
- Bullets per bullet brick: 1
- Headshot: Instant kill
- Body shot: Truncates snake, -50 points per removed segment

### Bomb Mechanics

- Throw distance: 2-5 cells (random)
- Throw direction: Left or right (random)
- Explosion timer: 2-4 seconds (random)
- Explosion area: 3x3 grid centered on bomb
- Bombs per bomb brick: 1
- Headshot (explosion): Instant kill
- Body hit (explosion): Truncates snake, -50 points per removed segment
- Area damage: Can hit multiple snakes in one explosion

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
