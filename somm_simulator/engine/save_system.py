"""Save/load system using JSON serialization."""

import json
import os
from datetime import datetime
from pathlib import Path


SAVE_DIR = Path.home() / ".somm_simulator" / "saves"


class SaveSystem:
    """Handles saving and loading game state to JSON files."""

    def __init__(self, save_dir: Path | None = None):
        self.save_dir = save_dir or SAVE_DIR
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save(self, slot: str, game_state: dict) -> Path:
        """Save game state to a named slot."""
        save_data = {
            "version": 1,
            "timestamp": datetime.now().isoformat(),
            "slot": slot,
            "state": game_state,
        }
        path = self.save_dir / f"{slot}.json"
        with open(path, "w") as f:
            json.dump(save_data, f, indent=2, default=str)
        return path

    def load(self, slot: str) -> dict | None:
        """Load game state from a named slot. Returns None if not found."""
        path = self.save_dir / f"{slot}.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            save_data = json.load(f)
        return save_data.get("state")

    def list_saves(self) -> list[dict]:
        """List all available save slots with metadata."""
        saves = []
        for path in sorted(self.save_dir.glob("*.json")):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                saves.append({
                    "slot": data.get("slot", path.stem),
                    "timestamp": data.get("timestamp"),
                    "path": str(path),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return saves

    def delete_save(self, slot: str) -> bool:
        """Delete a save slot."""
        path = self.save_dir / f"{slot}.json"
        if path.exists():
            path.unlink()
            return True
        return False
