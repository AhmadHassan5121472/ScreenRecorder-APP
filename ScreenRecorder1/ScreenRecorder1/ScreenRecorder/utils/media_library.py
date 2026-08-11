import os
import subprocess
import sys
from datetime import datetime


class MediaLibrary:
    VIDEO_EXTENSIONS = (".mp4", ".avi", ".mkv", ".mov", ".webm")
    IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")

    def __init__(self, recordings_folder="recordings", screenshots_folder="screenshots"):
        self.recordings_folder = recordings_folder
        self.screenshots_folder = screenshots_folder
        os.makedirs(recordings_folder, exist_ok=True)
        os.makedirs(screenshots_folder, exist_ok=True)

    @staticmethod
    def format_size(size):
        if size < 1024: return f"{size} B"
        if size < 1024**2: return f"{size/1024:.1f} KB"
        if size < 1024**3: return f"{size/1024**2:.1f} MB"
        return f"{size/1024**3:.2f} GB"

    @classmethod
    def get_file_info(cls, filepath):
        try:
            stat = os.stat(filepath)
            ext = os.path.splitext(filepath)[1].lower()
            kind = "video" if ext in cls.VIDEO_EXTENSIONS else "image" if ext in cls.IMAGE_EXTENSIONS else "other"
            dt = datetime.fromtimestamp(stat.st_mtime)
            return {
                "path": filepath,
                "name": os.path.basename(filepath),
                "size": stat.st_size,
                "size_text": cls.format_size(stat.st_size),
                "date": dt.strftime("%Y-%m-%d"),
                "time": dt.strftime("%H:%M:%S"),
                "type": kind,
            }
        except OSError:
            return None

    def _scan(self, folder, extensions):
        result = []
        if not os.path.isdir(folder):
            return result
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and os.path.splitext(name)[1].lower() in extensions:
                info = self.get_file_info(path)
                if info:
                    result.append(info)
        return sorted(result, key=lambda x: x["path"], reverse=True)

    def get_recordings(self):
        return self._scan(self.recordings_folder, self.VIDEO_EXTENSIONS)

    def get_screenshots(self):
        return self._scan(self.screenshots_folder, self.IMAGE_EXTENSIONS)

    @staticmethod
    def open_file(filepath):
        if not os.path.isfile(filepath): return False
        try:
            if sys.platform.startswith("win"): os.startfile(filepath)
            elif sys.platform == "darwin": subprocess.Popen(["open", filepath])
            else: subprocess.Popen(["xdg-open", filepath])
            return True
        except Exception:
            return False

    @staticmethod
    def open_folder(filepath):
        if not os.path.exists(filepath): return False
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", "/select,", os.path.abspath(filepath)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", os.path.dirname(os.path.abspath(filepath))])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(os.path.abspath(filepath))])
            return True
        except Exception:
            return False

    @staticmethod
    def delete_file(filepath):
        try:
            os.remove(filepath)
            return True
        except Exception:
            return False

    @staticmethod
    def rename_file(filepath, new_name):
        if not os.path.isfile(filepath): return False
        new_name = new_name.strip()
        if not new_name: return False
        ext = os.path.splitext(filepath)[1]
        if not new_name.lower().endswith(ext.lower()):
            new_name += ext
        target = os.path.join(os.path.dirname(filepath), new_name)
        if os.path.exists(target): return False
        try:
            os.rename(filepath, target)
            return True
        except Exception:
            return False
