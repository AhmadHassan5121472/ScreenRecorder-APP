import json
import os


class SettingsManager:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.defaults = {
            "profile": "Standard",
            "fps": 30,
            "resolution": "Original",
            "recording_area": "Primary Monitor",
            "output_folder": "recordings",
            "microphone_enabled": False,
            "system_audio_enabled": False,
            "webcam_enabled": False,
            "webcam_index": 0,
            "webcam_width": 640,
            "webcam_height": 480,
            "webcam_fps": 30,
            "capture_cursor": True,
        }

    def load(self):
        data = {}
        try:
            if os.path.isfile(self.filename):
                with open(self.filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception:
            data = {}
        result = self.defaults.copy()
        if isinstance(data, dict):
            result.update(data)
        return result

    def save(self, settings):
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception:
            return False

    def reset(self):
        return self.save(self.defaults.copy())
