import os
import shutil
import sys


def get_ffmpeg_path():
    """Return bundled FFmpeg when frozen, otherwise local/PATH FFmpeg."""
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.join(getattr(sys, "_MEIPASS", ""), "ffmpeg", "ffmpeg.exe"),
            os.path.join(os.path.dirname(sys.executable), "ffmpeg", "ffmpeg.exe"),
            os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"),
        ]
    else:
        project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(project, "ffmpeg", "ffmpeg.exe"),
            os.path.join(project, "ffmpeg.exe"),
        ]

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    found = shutil.which("ffmpeg")
    return found


def get_ffprobe_path():
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.join(getattr(sys, "_MEIPASS", ""), "ffmpeg", "ffprobe.exe"),
            os.path.join(os.path.dirname(sys.executable), "ffmpeg", "ffprobe.exe"),
        ]
    else:
        project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [os.path.join(project, "ffmpeg", "ffprobe.exe")]

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return shutil.which("ffprobe")
