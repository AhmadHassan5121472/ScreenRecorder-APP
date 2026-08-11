import os
import time
import cv2
import mss
import numpy as np


class ScreenshotManager:
    def __init__(self, output_folder):
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)

    def take_screenshot(self, monitor_index=1, area=None):
        try:
            with mss.mss() as sct:
                if area:
                    monitor = {
                        "left": int(area["left"]),
                        "top": int(area["top"]),
                        "width": int(area["width"]),
                        "height": int(area["height"]),
                    }
                else:
                    monitors = sct.monitors
                    index = monitor_index if 0 <= monitor_index < len(monitors) else (1 if len(monitors) > 1 else 0)
                    monitor = monitors[index]

                frame = cv2.cvtColor(
                    np.asarray(sct.grab(monitor)), cv2.COLOR_BGRA2BGR
                )
                stamp = time.strftime("%Y%m%d_%H%M%S")
                ms = int((time.time() % 1) * 1000)
                path = os.path.join(self.output_folder, f"screenshot_{stamp}_{ms:03d}.png")
                return path if cv2.imwrite(path, frame) else None
        except Exception:
            return None
