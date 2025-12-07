#!/usr/bin/env python3
"""
CloudSnake Test Runner
Runs all unit tests and integration tests for the CloudSnake project.
"""
import sys
import unittest

# Define all test modules
UNIT_TEST_MODULES = [
    'config.test_constants',
    'utils.test_helpers',
    'utils.test_settings',
    'network.test_game_client',
    'ui.test_widgets',
    'game.test_game_state',
]

def run_unit_tests():
    """Run all unit tests"""
    print("=" * 70)
    print("Running Unit Tests")
    print("=" * 70)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for module in UNIT_TEST_MODULES:
        try:
            tests = loader.loadTestsFromName(module)
            suite.addTests(tests)
        except Exception as e:
            print(f"Error loading {module}: {e}")
            return False
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """Run integration tests"""
    print("\n" + "=" * 70)
    print("Running Integration Tests")
    print("=" * 70)
    
    try:
        import test_final
        result = test_final.main()
        return result == 0
    except Exception as e:
        print(f"Error running integration tests: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("CloudSnake Test Suite")
    print("=" * 70)
    
    unit_success = run_unit_tests()
    integration_success = run_integration_tests()
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Unit Tests: {'✓ PASS' if unit_success else '✗ FAIL'}")
    print(f"Integration Tests: {'✓ PASS' if integration_success else '✗ FAIL'}")
    
    if unit_success and integration_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
