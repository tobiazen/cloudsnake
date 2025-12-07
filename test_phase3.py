"""Test Phase 3: UI Widgets Extraction"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ui_widgets_import():
    """Test that widgets can be imported from ui module"""
    try:
        from ui.widgets import InputBox, Button
        assert InputBox is not None, "InputBox should not be None"
        assert Button is not None, "Button should not be None"
        print("✓ InputBox and Button imported from ui.widgets")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_inputbox_class():
    """Test InputBox class structure"""
    import pygame
    pygame.init()
    
    from ui.widgets import InputBox
    
    # Test instantiation
    input_box = InputBox(100, 100, 200, 40, "test text")
    
    # Test attributes
    assert hasattr(input_box, 'rect'), "InputBox should have rect attribute"
    assert hasattr(input_box, 'text'), "InputBox should have text attribute"
    assert hasattr(input_box, 'color'), "InputBox should have color attribute"
    assert hasattr(input_box, 'font'), "InputBox should have font attribute"
    assert hasattr(input_box, 'active'), "InputBox should have active attribute"
    
    # Test methods
    assert hasattr(input_box, 'handle_event'), "InputBox should have handle_event method"
    assert hasattr(input_box, 'draw'), "InputBox should have draw method"
    
    # Test initial values
    assert input_box.text == "test text", f"Expected text='test text', got {input_box.text}"
    assert input_box.active == False, "InputBox should not be active initially"
    
    print("✓ InputBox class structure validated")
    return True


def test_button_class():
    """Test Button class structure"""
    import pygame
    pygame.init()
    
    from ui.widgets import Button
    from config.constants import BLUE
    
    # Test instantiation
    button = Button(100, 100, 150, 50, "Click Me", BLUE)
    
    # Test attributes
    assert hasattr(button, 'rect'), "Button should have rect attribute"
    assert hasattr(button, 'text'), "Button should have text attribute"
    assert hasattr(button, 'color'), "Button should have color attribute"
    assert hasattr(button, 'hover_color'), "Button should have hover_color attribute"
    assert hasattr(button, 'font'), "Button should have font attribute"
    assert hasattr(button, 'hovered'), "Button should have hovered attribute"
    
    # Test methods
    assert hasattr(button, 'handle_event'), "Button should have handle_event method"
    assert hasattr(button, 'draw'), "Button should have draw method"
    
    # Test initial values
    assert button.text == "Click Me", f"Expected text='Click Me', got {button.text}"
    assert button.color == BLUE, f"Expected color=BLUE, got {button.color}"
    assert button.hovered == False, "Button should not be hovered initially"
    
    print("✓ Button class structure validated")
    return True


def test_client_imports_widgets():
    """Test that client.py can import widgets from ui module"""
    try:
        from ui import InputBox, Button
        assert InputBox is not None, "InputBox should not be None"
        assert Button is not None, "Button should not be None"
        print("✓ client.py can import widgets from ui module")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_widgets_module_dependencies():
    """Test that widgets module has correct dependencies"""
    with open(os.path.join(os.path.dirname(__file__), "ui", "widgets.py"), 'r') as f:
        content = f.read()
        assert 'import pygame' in content, "Widgets module should import pygame"
        assert 'from config.constants import' in content, "Widgets module should import from config.constants"
        assert 'from utils.helpers import get_unicode_font' in content, "Widgets module should import get_unicode_font"
    
    print("✓ Widgets module has correct dependencies")
    return True


def main():
    """Run all Phase 3 tests"""
    print("=" * 60)
    print("Phase 3 Tests: UI Widgets Extraction")
    print("=" * 60)
    
    tests = [
        ("UI Widgets Import", test_ui_widgets_import),
        ("InputBox Class", test_inputbox_class),
        ("Button Class", test_button_class),
        ("Client Imports", test_client_imports_widgets),
        ("Module Dependencies", test_widgets_module_dependencies),
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
        print("\n🎉 All Phase 3 tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
