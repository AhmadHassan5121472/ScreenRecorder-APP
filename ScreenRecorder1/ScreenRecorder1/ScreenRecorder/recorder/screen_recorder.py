import os
import time
import threading
import ctypes

import cv2
import mss
import numpy as np


class ScreenRecorder:
    """Capture a monitor or rectangular area to an MP4 video."""

    def __init__(self, output_folder, fps=30, monitor_index=1,
                 resolution=None, capture_cursor=True, recording_area=None):
        self.output_folder = output_folder
        self.fps = max(1, int(fps))
        self.monitor_index = int(monitor_index)
        self.resolution = resolution
        self.capture_cursor = bool(capture_cursor)
        self.recording_area = recording_area

        self.recording = False
        self.paused = False
        self.thread = None
        self.writer = None
        self.sct = None
        self.output_file = None
        self.error = None
        self.frame_width = 0
        self.frame_height = 0

    def start(self):
        if self.recording:
            return False

        try:
            os.makedirs(self.output_folder, exist_ok=True)
            self.error = None
            self.sct = mss.mss()
            monitors = self.sct.monitors
            if not monitors:
                raise RuntimeError("No display monitor was detected.")

            if self.recording_area:
                monitor = {
                    "left": int(self.recording_area["left"]),
                    "top": int(self.recording_area["top"]),
                    "width": int(self.recording_area["width"]),
                    "height": int(self.recording_area["height"]),
                }
            else:
                index = self.monitor_index
                if index < 0 or index >= len(monitors):
                    index = 1 if len(monitors) > 1 else 0
                monitor = monitors[index]

            source_w = int(monitor["width"])
            source_h = int(monitor["height"])
            if source_w < 2 or source_h < 2:
                raise RuntimeError("The selected recording area is invalid.")

            if self.resolution:
                width, height = map(int, self.resolution)
            else:
                width, height = source_w, source_h

            width = max(2, width - width % 2)
            height = max(2, height - height % 2)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            # Avoid collisions when starting twice in one second.
            path = os.path.join(self.output_folder, f"recording_{timestamp}.mp4")
            counter = 1
            while os.path.exists(path):
                path = os.path.join(
                    self.output_folder, f"recording_{timestamp}_{counter}.mp4"
                )
                counter += 1

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.writer = cv2.VideoWriter(path, fourcc, self.fps, (width, height))
            if not self.writer.isOpened():
                raise RuntimeError(
                    "OpenCV could not create the MP4 file. "
                    "Check that the output folder is writable."
                )

            self.output_file = path
            self.frame_width = width
            self.frame_height = height
            self._monitor = monitor

            self.recording = True
            self.paused = False
            self.thread = threading.Thread(
                target=self._record_loop, daemon=True
            )
            self.thread.start()
            return True

        except Exception as exc:
            self.error = str(exc)
            self.cleanup()
            return False

    def _record_loop(self):
        interval = 1.0 / self.fps
        next_time = time.perf_counter()
        try:
            while self.recording:
                if self.paused:
                    time.sleep(0.05)
                    next_time = time.perf_counter() + interval
                    continue

                shot = self.sct.grab(self._monitor)
                frame = cv2.cvtColor(np.asarray(shot), cv2.COLOR_BGRA2BGR)

                if self.capture_cursor:
                    self._draw_cursor(frame, self._monitor)

                if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
                    frame = cv2.resize(
                        frame, (self.frame_width, self.frame_height),
                        interpolation=cv2.INTER_AREA
                    )

                self.writer.write(frame)

                next_time += interval
                delay = next_time - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                else:
                    next_time = time.perf_counter() + interval

        except Exception as exc:
            self.error = str(exc)
        finally:
            self._release_writer()
            self.recording = False

    @staticmethod
    def _draw_cursor(frame, monitor):
        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            point = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            x = int(point.x - monitor["left"])
            y = int(point.y - monitor["top"])
            if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                cv2.circle(frame, (x, y), 9, (255, 255, 255), 2)
                cv2.circle(frame, (x, y), 3, (255, 255, 255), -1)
        except Exception:
            # Cursor visualization is optional and must never stop recording.
            pass

    def pause(self):
        if self.recording:
            self.paused = True

    def resume(self):
        if self.recording:
            self.paused = False

    def stop(self):
        if not self.recording:
            return self.output_file
        self.recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        self._release_writer()
        return self.output_file

    def _release_writer(self):
        if self.writer is not None:
            try:
                self.writer.release()
            except Exception:
                pass
            self.writer = None
        if self.sct is not None:
            try:
                self.sct.close()
            except Exception:
                pass
            self.sct = None

    def cleanup(self):
        self.recording = False
        self.paused = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self._release_writer()
        self.thread = None

    def is_recording(self):
        return self.recording

    def is_paused(self):
        return self.paused

    def get_output_file(self):
        return self.output_file

    def get_error(self):
        return self.error
