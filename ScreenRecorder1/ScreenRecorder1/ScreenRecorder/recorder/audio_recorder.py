import os
import wave
import threading

import numpy as np
import sounddevice as sd


class AudioRecorder:
    """Record microphone input to a WAV file."""

    def __init__(self, output_file, device=None, samplerate=44100, channels=1):
        self.output_file = output_file
        self.device = device
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.paused = False
        self.audio_data = []
        self.thread = None
        self.stream = None
        self.error = None

    def start(self):
        if self.recording:
            return False
        self.audio_data = []
        self.error = None
        self.recording = True
        self.paused = False
        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()
        return True

    def _record_loop(self):
        try:
            def callback(indata, frames, time_info, status):
                if status:
                    self.error = str(status)
                if self.recording and not self.paused:
                    self.audio_data.append(indata.copy())

            self.stream = sd.InputStream(
                device=self.device,
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="float32",
                callback=callback,
            )
            self.stream.start()
            while self.recording:
                sd.sleep(100)
            self.stream.stop()
            self.stream.close()
            self.stream = None
        except Exception as exc:
            self.error = str(exc)
            self.recording = False
            if self.stream:
                try:
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

    def pause(self):
        if self.recording:
            self.paused = True

    def resume(self):
        if self.recording:
            self.paused = False

    def stop(self):
        if not self.recording:
            return self.output_file if os.path.exists(self.output_file) else None

        self.recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        try:
            if not self.audio_data:
                return None
            audio = np.concatenate(self.audio_data, axis=0)
            audio = np.clip(audio, -1.0, 1.0)
            audio_int16 = (audio * 32767).astype(np.int16)
            os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
            with wave.open(self.output_file, "wb") as wav:
                wav.setnchannels(self.channels)
                wav.setsampwidth(2)
                wav.setframerate(self.samplerate)
                wav.writeframes(audio_int16.tobytes())
            return self.output_file
        except Exception as exc:
            self.error = str(exc)
            return None
        finally:
            self.audio_data = []
            self.thread = None

    def is_recording(self):
        return self.recording

    def is_paused(self):
        return self.paused

    def get_error(self):
        return self.error
