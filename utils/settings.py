"""Settings management utilities for CloudSnake client"""
import os
import json
from typing import Dict, Any


def load_settings(settings_file: str = 'settings.json') -> Dict[str, Any]:
    """Load settings from file"""
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'player_names': [], 'last_player_name': '', 'server_ip': '129.151.219.36'}


def save_settings(settings: Dict[str, Any], settings_file: str = 'settings.json') -> None:
    """Save settings to file"""
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")


def add_player_name(settings: Dict[str, Any], name: str, settings_file: str = 'settings.json') -> None:
    """Add player name to history"""
    if name and name.strip():
        name = name.strip()
        # Remove if already exists (to move to front)
        if name in settings['player_names']:
            settings['player_names'].remove(name)
        # Add to front
        settings['player_names'].insert(0, name)
        # Keep only last 10 names
        settings['player_names'] = settings['player_names'][:10]
        # Update last used name
        settings['last_player_name'] = name
        save_settings(settings, settings_file)
