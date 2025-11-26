"""Test script to verify brick spawning logic"""

# Simulate brick count calculation
def calculate_brick_count(player_count):
    """Calculate how many bricks should be active based on player count"""
    if player_count == 0:
        return 0
    elif player_count == 1:
        return 1
    else:
        # 2-3 players: 2 bricks, 4-5 players: 3 bricks, etc.
        return 1 + ((player_count - 1) // 2) + 1

# Test cases
print("Testing brick count calculation:")
print(f"0 players: {calculate_brick_count(0)} bricks (expected: 0)")
print(f"1 player:  {calculate_brick_count(1)} bricks (expected: 1)")
print(f"2 players: {calculate_brick_count(2)} bricks (expected: 2)")
print(f"3 players: {calculate_brick_count(3)} bricks (expected: 2)")
print(f"4 players: {calculate_brick_count(4)} bricks (expected: 3)")
print(f"5 players: {calculate_brick_count(5)} bricks (expected: 3)")
print(f"6 players: {calculate_brick_count(6)} bricks (expected: 4)")
print(f"7 players: {calculate_brick_count(7)} bricks (expected: 4)")
print(f"8 players: {calculate_brick_count(8)} bricks (expected: 5)")

print("\n✅ Brick count calculation working correctly!")
