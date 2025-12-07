"""Test Phase 2: Network Layer Extraction"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_network_import():
    """Test that GameClient can be imported from network module"""
    try:
        from network.game_client import GameClient
        assert GameClient is not None, "GameClient should not be None"
        print("✓ GameClient imported from network.game_client")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_gameclient_class():
    """Test GameClient class structure"""
    from network.game_client import GameClient
    
    # Test instantiation
    client = GameClient("127.0.0.1", 50000, "TestPlayer")
    
    # Test attributes
    assert hasattr(client, 'server_ip'), "GameClient should have server_ip attribute"
    assert hasattr(client, 'server_port'), "GameClient should have server_port attribute"
    assert hasattr(client, 'player_name'), "GameClient should have player_name attribute"
    assert hasattr(client, 'connected'), "GameClient should have connected attribute"
    assert hasattr(client, 'running'), "GameClient should have running attribute"
    assert hasattr(client, 'game_state'), "GameClient should have game_state attribute"
    
    # Test methods
    assert hasattr(client, 'connect'), "GameClient should have connect method"
    assert hasattr(client, 'send_to_server'), "GameClient should have send_to_server method"
    assert hasattr(client, 'disconnect'), "GameClient should have disconnect method"
    assert hasattr(client, 'shoot'), "GameClient should have shoot method"
    assert hasattr(client, 'throw_bomb'), "GameClient should have throw_bomb method"
    assert hasattr(client, 'respawn'), "GameClient should have respawn method"
    
    # Test initial values
    assert client.server_ip == "127.0.0.1", f"Expected server_ip='127.0.0.1', got {client.server_ip}"
    assert client.server_port == 50000, f"Expected server_port=50000, got {client.server_port}"
    assert client.player_name == "TestPlayer", f"Expected player_name='TestPlayer', got {client.player_name}"
    assert client.connected == False, "GameClient should not be connected initially"
    assert client.running == False, "GameClient should not be running initially"
    
    print("✓ GameClient class structure validated")
    return True


def test_client_can_import_gameclient():
    """Test that client.py can import GameClient from network module"""
    try:
        # This will test the import statement in client.py
        from network import GameClient
        assert GameClient is not None, "GameClient should not be None"
        print("✓ client.py can import GameClient from network module")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_network_module_isolation():
    """Test that network module doesn't depend on pygame"""
    import importlib.util
    
    # Load the network module without executing client.py
    spec = importlib.util.spec_from_file_location(
        "network.game_client",
        os.path.join(os.path.dirname(__file__), "network", "game_client.py")
    )
    module = importlib.util.module_from_spec(spec)
    
    # Check imports - should not import pygame
    with open(os.path.join(os.path.dirname(__file__), "network", "game_client.py"), 'r') as f:
        content = f.read()
        assert 'import pygame' not in content, "Network module should not import pygame"
        assert 'import socket' in content, "Network module should import socket"
        assert 'import json' in content, "Network module should import json"
    
    print("✓ Network module is properly isolated (no pygame dependency)")
    return True


def main():
    """Run all Phase 2 tests"""
    print("=" * 60)
    print("Phase 2 Tests: Network Layer Extraction")
    print("=" * 60)
    
    tests = [
        ("Network Import", test_network_import),
        ("GameClient Class", test_gameclient_class),
        ("Client Import", test_client_can_import_gameclient),
        ("Network Isolation", test_network_module_isolation),
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
        print("\n🎉 All Phase 2 tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
