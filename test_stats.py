#!/usr/bin/env python3
"""
Quick test to verify statistics system works
"""
import os
import json
from server import GameServer

def test_stats_system():
    """Test that statistics are tracked and persisted"""
    print("Testing statistics system...")
    
    # Clean up any existing stats file
    stats_file = 'player_stats_test.json'
    if os.path.exists(stats_file):
        os.remove(stats_file)
    
    # Create server with test stats file
    server = GameServer()
    server.stats_file = stats_file
    server.stats = server.create_empty_stats()
    
    # Test 1: Update player stats
    print("Test 1: Updating player stats...")
    server.update_player_stats('TestPlayer1', 500)
    assert 'TestPlayer1' in server.stats['players']
    assert server.stats['players']['TestPlayer1']['highscore'] == 500
    print("✓ Player stats updated correctly")
    
    # Test 2: Track kills and deaths
    print("Test 2: Tracking kills and deaths...")
    server.update_player_stats('TestPlayer1', 600, kills=3, died=True)
    assert server.stats['players']['TestPlayer1']['highscore'] == 600
    assert server.stats['players']['TestPlayer1']['total_kills'] == 3
    assert server.stats['players']['TestPlayer1']['total_deaths'] == 1
    print("✓ Kills and deaths tracked correctly")
    
    # Test 3: All-time highscore tracking
    print("Test 3: All-time highscore...")
    server.update_player_stats('TestPlayer2', 1000)
    assert server.stats['all_time_highscore'] == 1000
    assert server.stats['all_time_highscore_player'] == 'TestPlayer2'
    print("✓ All-time highscore tracked correctly")
    
    # Test 4: Save and load stats
    print("Test 4: Persistence...")
    server.save_stats()
    assert os.path.exists(stats_file)
    
    # Load stats directly without creating new server
    with open(stats_file, 'r') as f:
        loaded_stats = json.load(f)
    
    assert 'TestPlayer1' in loaded_stats['players']
    assert loaded_stats['players']['TestPlayer1']['highscore'] == 600
    assert loaded_stats['all_time_highscore'] == 1000
    print("✓ Statistics persisted and loaded correctly")
    
    # Test 5: Get top players
    print("Test 5: Leaderboard...")
    server.update_player_stats('TestPlayer3', 800)
    server.update_player_stats('TestPlayer4', 400)
    leaderboard = server.get_top_players(3)
    assert len(leaderboard) == 3  # Top 3 as requested
    assert leaderboard[0]['name'] == 'TestPlayer2'  # Highest score
    assert leaderboard[0]['highscore'] == 1000
    assert leaderboard[1]['name'] == 'TestPlayer3'
    assert leaderboard[1]['highscore'] == 800
    print("✓ Leaderboard sorted correctly")
    
    # Clean up
    if os.path.exists(stats_file):
        os.remove(stats_file)
    
    print("\n✅ All tests passed!")

if __name__ == '__main__':
    test_stats_system()
