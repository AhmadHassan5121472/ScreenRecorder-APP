import cv2
import os
import time
import threading


class WebcamRecorder:
    """Record a webcam to a separate AVI file. No picture-in-picture."""

    def __init__(self, output_folder="recordings", camera_index=0,
                 width=640, height=480, fps=30):
        self.output_folder = output_folder
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = max(1, int(fps))
        self.camera = None
        self.writer = None
        self.recording = False
        self.paused = False
        self.thread = None
        self.output_file = None
        self.error = None

    def start(self):
        if self.recording:
            return False
        os.makedirs(self.output_folder, exist_ok=True)
        self.error = None

        # CAP_DSHOW is useful on Windows; fall back to default backend.
        camera = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not camera.isOpened():
            camera.release()
            camera = cv2.VideoCapture(self.camera_index)

        if not camera.isOpened():
            self.error = "Unable to open webcam."
            camera.release()
            return False

        self.camera = camera
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_FPS, self.fps)

        actual_w = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or self.width
        actual_h = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self.height
        actual_w = max(2, actual_w - actual_w % 2)
        actual_h = max(2, actual_h - actual_h % 2)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.output_folder, f"webcam_{timestamp}.avi")
        counter = 1
        while os.path.exists(path):
            path = os.path.join(
                self.output_folder, f"webcam_{timestamp}_{counter}.avi"
            )
            counter += 1

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        self.writer = cv2.VideoWriter(
            path, fourcc, self.fps, (actual_w, actual_h)
        )
        if not self.writer.isOpened():
            self.error = "Unable to create webcam video file."
            self._release()
            return False

        self.output_file = path
        self.actual_size = (actual_w, actual_h)
        self.recording = True
        self.paused = False
        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()
        return True

    def _record_loop(self):
        interval = 1.0 / self.fps
        next_time = time.perf_counter()
        try:
            while self.recording:
                if self.paused:
                    time.sleep(0.05)
                    next_time = time.perf_counter() + interval
                    continue
                ok, frame = self.camera.read()
                if not ok:
                    raise RuntimeError("Failed to read a webcam frame.")
                if (frame.shape[1], frame.shape[0]) != self.actual_size:
                    frame = cv2.resize(frame, self.actual_size)
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
            self._release()
            self.recording = False

    def pause(self):
        if self.recording:
            self.paused = True

    def resume(self):
        if self.recording:
            self.paused = False

    def stop(self):
        self.recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        self._release()
        return self.output_file

    def _release(self):
        if self.writer:
            try:
                self.writer.release()
            except Exception:
                pass
            self.writer = None
        if self.camera:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None

    def is_recording(self):
        return self.recording

    def is_paused(self):
        return self.paused

    def get_error(self):
        return self.error

    def get_output_file(self):
        return self.output_file
