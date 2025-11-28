# Building Executables for Distribution

This guide is for developers who want to build standalone executables for end users.

## Why Build Executables?

The executables allow users to play the game without:
- Installing Python
- Installing dependencies (pygame)
- Knowing how to run Python scripts
- Using git or command line

Users simply download and double-click to play!

## Prerequisites

Install build dependencies:
```bash
pip install -r requirements-build.txt
```

This installs:
- pygame (required for the game)
- pyinstaller (bundles Python + dependencies into executable)

## Building

### On Windows (to create Windows executable)
```bash
python build_executable.py
```
Creates: `dist/SnakeGame.exe` (~50-80 MB)

### On Linux (to create Linux executable)
```bash
python build_executable.py
```
Creates: `dist/SnakeGame` (~50-80 MB)

### On macOS (to create Mac app)
```bash
python build_executable.py
```
Creates: `dist/SnakeGame.app`

## Distribution

After building:
1. Test the executable to ensure it works
2. Upload to GitHub releases
3. Users can download and run immediately

### Creating a GitHub Release

```bash
# Tag the version
git tag v1.0.0
git push origin v1.0.0

# Upload the executable from dist/ to the release on GitHub
```

## File Size Explanation

The executable is large (~50-80 MB) because it includes:
- Embedded Python interpreter
- Pygame library and all dependencies
- Game code and assets

This is normal for PyInstaller and allows the game to run on systems without Python.

## Troubleshooting

**"PyInstaller not found"**: Run `pip install pyinstaller`

**Missing pygame**: Run `pip install pygame`

**Antivirus flags executable**: This is common with PyInstaller. The executable is safe - it just contains Python + your code. You may need to add an exception.

**Large file size**: This is expected. PyInstaller bundles everything needed.

## Cross-Platform Notes

- Build on Windows to create `.exe` for Windows users
- Build on Linux to create binary for Linux users  
- Build on macOS to create `.app` for Mac users
- Cannot cross-compile (must build on target platform)

