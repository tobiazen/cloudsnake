"""Test Phase 4: Helper Methods and Settings Extraction"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_helpers_extraction():
    """Test that drawing helpers are properly extracted"""
    from utils.helpers import draw_text_with_shadow, draw_gradient_rect
    
    assert callable(draw_text_with_shadow), "draw_text_with_shadow should be callable"
    assert callable(draw_gradient_rect), "draw_gradient_rect should be callable"
    
    print("✓ Drawing helpers extracted successfully")
    return True


def test_settings_extraction():
    """Test that settings management is properly extracted"""
    from utils.settings import load_settings, save_settings, add_player_name
    
    assert callable(load_settings), "load_settings should be callable"
    assert callable(save_settings), "save_settings should be callable"
    assert callable(add_player_name), "add_player_name should be callable"
    
    print("✓ Settings management extracted successfully")
    return True


def test_settings_functionality():
    """Test settings functions work correctly"""
    import tempfile
    from utils.settings import load_settings, save_settings, add_player_name
    
    # Test load_settings with non-existent file
    settings = load_settings('nonexistent_file.json')
    assert 'player_names' in settings, "Settings should have player_names key"
    assert 'last_player_name' in settings, "Settings should have last_player_name key"
    assert 'server_ip' in settings, "Settings should have server_ip key"
    assert settings['player_names'] == [], "Player names should be empty list initially"
    
    # Test save_settings and add_player_name
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        test_settings = {'player_names': [], 'last_player_name': '', 'server_ip': '127.0.0.1'}
        save_settings(test_settings, temp_file)
        
        # Add player names
        add_player_name(test_settings, 'Player1', temp_file)
        assert test_settings['player_names'][0] == 'Player1', "Player1 should be first"
        assert test_settings['last_player_name'] == 'Player1', "Last player should be Player1"
        
        add_player_name(test_settings, 'Player2', temp_file)
        assert test_settings['player_names'][0] == 'Player2', "Player2 should be first"
        assert test_settings['player_names'][1] == 'Player1', "Player1 should be second"
        
        # Test that re-adding moves to front
        add_player_name(test_settings, 'Player1', temp_file)
        assert test_settings['player_names'][0] == 'Player1', "Player1 should be moved to front"
        assert len(test_settings['player_names']) == 2, "Should only have 2 unique names"
        
        print("✓ Settings functionality working correctly")
        return True
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_client_imports_updated():
    """Test that client.py imports updated helpers"""
    with open(os.path.join(os.path.dirname(__file__), "client.py"), 'r') as f:
        content = f.read()
        assert 'from utils.helpers import' in content, "Should import from utils.helpers"
        assert 'draw_text_with_shadow' in content, "Should import draw_text_with_shadow"
        assert 'draw_gradient_rect' in content, "Should import draw_gradient_rect"
        assert 'from utils.settings import' in content, "Should import from utils.settings"
        assert 'load_settings' in content, "Should import load_settings"
        assert 'save_settings' in content, "Should import save_settings"
        assert 'add_player_name' in content, "Should import add_player_name"
    
    print("✓ Client imports updated correctly")
    return True


def test_methods_removed_from_gamegui():
    """Test that methods were properly removed from GameGUI class"""
    with open(os.path.join(os.path.dirname(__file__), "client.py"), 'r') as f:
        content = f.read()
        
        # These methods should NOT be defined in GameGUI anymore
        assert '    def draw_text_with_shadow(self,' not in content, "draw_text_with_shadow should be removed from GameGUI"
        assert '    def draw_gradient_rect(self,' not in content, "draw_gradient_rect should be removed from GameGUI"
        assert '    def load_settings(self)' not in content, "load_settings should be removed from GameGUI"
        assert '    def save_settings(self)' not in content, "save_settings should be removed from GameGUI"
        assert '    def add_player_name(self,' not in content, "add_player_name should be removed from GameGUI"
    
    print("✓ Methods successfully removed from GameGUI")
    return True


def test_code_reduction():
    """Test that client.py was reduced in size"""
    with open(os.path.join(os.path.dirname(__file__), "client.py"), 'r') as f:
        lines = len(f.readlines())
    
    # After Phase 4, client.py should be significantly smaller
    # Original was ~1444 lines, after Phase 3 was ~1021, Phase 4 should reduce further
    assert lines < 1000, f"Expected client.py < 1000 lines, got {lines}"
    
    print(f"✓ Client.py reduced to {lines} lines")
    return True


def main():
    """Run all Phase 4 tests"""
    print("=" * 60)
    print("Phase 4 Tests: Helper Methods and Settings Extraction")
    print("=" * 60)
    
    tests = [
        ("Helpers Extraction", test_helpers_extraction),
        ("Settings Extraction", test_settings_extraction),
        ("Settings Functionality", test_settings_functionality),
        ("Client Imports", test_client_imports_updated),
        ("Methods Removed", test_methods_removed_from_gamegui),
        ("Code Reduction", test_code_reduction),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        print("-" * 60)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 4 tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
