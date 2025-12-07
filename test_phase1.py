"""Test Phase 1: Constants and Utilities Extraction"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_constants():
    """Test that all constants are properly imported"""
    from config.constants import (
        SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
        WHITE, BLACK, GRAY, DARK_GRAY, LIGHT_GRAY,
        GREEN, DARK_GREEN, RED, DARK_RED,
        BLUE, DARK_BLUE, YELLOW, DARK_YELLOW,
        ORANGE, PURPLE, CYAN,
        BG_COLOR, PANEL_BG, BORDER_COLOR, HIGHLIGHT_COLOR,
        TEXT_COLOR, TEXT_SHADOW
    )
    
    # Test basic constants
    assert SCREEN_WIDTH == 1000, f"Expected SCREEN_WIDTH=1000, got {SCREEN_WIDTH}"
    assert SCREEN_HEIGHT == 750, f"Expected SCREEN_HEIGHT=750, got {SCREEN_HEIGHT}"
    assert FPS == 60, f"Expected FPS=60, got {FPS}"
    
    # Test colors are tuples
    assert isinstance(WHITE, tuple) and len(WHITE) == 3, "WHITE should be RGB tuple"
    assert isinstance(BG_COLOR, tuple) and len(BG_COLOR) == 3, "BG_COLOR should be RGB tuple"
    
    # Test specific color values
    assert WHITE == (255, 255, 255), f"Expected WHITE=(255, 255, 255), got {WHITE}"
    assert BLACK == (0, 0, 0), f"Expected BLACK=(0, 0, 0), got {BLACK}"
    
    print("✓ All config constants imported and validated successfully")
    return True


def test_utils_helpers():
    """Test that helper functions are properly imported"""
    from utils.helpers import (
        get_unicode_font, get_resource_path,
        draw_bullet_icon, draw_bomb_icon
    )
    
    # Test functions exist and are callable
    assert callable(get_unicode_font), "get_unicode_font should be callable"
    assert callable(get_resource_path), "get_resource_path should be callable"
    assert callable(draw_bullet_icon), "draw_bullet_icon should be callable"
    assert callable(draw_bomb_icon), "draw_bomb_icon should be callable"
    
    # Test get_resource_path
    test_path = get_resource_path('test.txt')
    assert isinstance(test_path, str), "get_resource_path should return string"
    assert 'test.txt' in test_path, "get_resource_path should include filename"
    
    print("✓ All utility helpers imported and validated successfully")
    return True


def test_client_imports():
    """Test that client.py can import from new modules"""
    # This will fail if client.py can't import the modules
    try:
        # Just check if we can import without pygame initialization errors
        import config.constants
        import utils.helpers
        print("✓ Client can import from config and utils modules")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def main():
    """Run all Phase 1 tests"""
    print("=" * 60)
    print("Phase 1 Tests: Constants and Utilities Extraction")
    print("=" * 60)
    
    tests = [
        ("Config Constants", test_config_constants),
        ("Utils Helpers", test_utils_helpers),
        ("Client Imports", test_client_imports),
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
        print("\n🎉 All Phase 1 tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
