"""Main-menu adapter with the corrected unified save/load contract."""
from somm_simulator.scenes.main_menu import MainMenuScene


class UnifiedMainMenuScene(MainMenuScene):
    def _load_game(self):
        saves = self.game.save_system.list_saves()
        if not saves:
            return
        # list_saves returns a slot name. The legacy menu incorrectly requested
        # a non-existent "filename" field.
        save_data = self.game.save_system.load(saves[0]["slot"])
        if save_data:
            self.game.scene_manager.switch_to("hub", save_data=save_data)
