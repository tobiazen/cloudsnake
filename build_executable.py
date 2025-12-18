#!/usr/bin/env python3
"""
Build standalone executables for Snake Game
Creates Windows .exe and Linux binary
"""

import subprocess
import sys
import platform

def check_pyinstaller() -> bool:
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False

def install_pyinstaller() -> None:
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def ensure_dependencies() -> None:
    """Ensure all required dependencies are installed"""
    print("Checking dependencies...")
    dependencies = ["pygame", "msgpack"]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"[OK] {dep} is installed")
        except ImportError:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])

def build_executable() -> bool:
    """Build standalone executable"""
    system = platform.system()
    
    print(f"Building executable for {system}...")
    
    # Base PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # Single executable file
        "--name", "SnakeGame",
        "--hidden-import", "msgpack",  # Ensure msgpack is bundled
        "client.py"
    ]
    
    # Platform-specific options
    if system == "Windows":
        cmd.extend([
            "--noconsole",  # Hide console on Windows
            "--windowed",  # GUI mode
        ])
    elif system == "Darwin":  # macOS
        # Don't use --windowed with --onefile on macOS (deprecated)
        # Just create a regular executable
        pass
    else:  # Linux
        cmd.append("--windowed")  # GUI mode
    
    # Add data files (settings.json and assets folder)
    if system == "Windows":
        cmd.extend(["--add-data", "settings.json;."])
        cmd.extend(["--add-data", "assets;assets"])
    else:
        cmd.extend(["--add-data", "settings.json:."])
        cmd.extend(["--add-data", "assets:assets"])
    
    try:
        subprocess.check_call(cmd)
        print(f"Build successful!")
        print(f"Executable location: dist/SnakeGame{'.exe' if system == 'Windows' else ''}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False

def main() -> None:
    print("="*60)
    print("Snake Game - Executable Builder")
    print("="*60)
    
    # Ensure dependencies are installed
    ensure_dependencies()
    
    # Check/install PyInstaller
    if not check_pyinstaller():
        print("PyInstaller not found")
        install_pyinstaller()
    
    # Build executable
    if build_executable():
        print("\nBuild complete!")
        print("Distribution files are in the 'dist' folder")
        print("You can now distribute the executable to users")
    else:
        print("\nBuild failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
