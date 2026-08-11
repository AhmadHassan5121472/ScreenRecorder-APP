import os
import wave
import threading

import numpy as np
import soundcard as sc


class SystemAudioRecorder:
    """Record Windows speaker loopback audio to WAV."""

    def __init__(self, output_file, samplerate=48000, channels=2, block_size=2048):
        self.output_file = output_file
        self.samplerate = samplerate
        self.channels = channels
        self.block_size = block_size
        self.recording = False
        self.paused = False
        self.audio_data = []
        self.thread = None
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
            speaker = sc.default_speaker()
            if speaker is None:
                raise RuntimeError("No default Windows speaker was found.")
            loopback = sc.get_microphone(id=speaker.id, include_loopback=True)
            with loopback.recorder(
                samplerate=self.samplerate,
                channels=self.channels
            ) as recorder:
                while self.recording:
                    data = recorder.record(numframes=self.block_size)
                    if not self.paused and data is not None:
                        self.audio_data.append(np.asarray(data).copy())
        except Exception as exc:
            self.error = str(exc)
        finally:
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

        try:
            if not self.audio_data:
                return None
            audio = np.concatenate(self.audio_data, axis=0)
            audio = np.clip(audio, -1.0, 1.0)
            if audio.ndim == 1:
                audio = audio[:, None]
            channels = min(self.channels, audio.shape[1])
            audio = audio[:, :channels]
            audio_int16 = (audio * 32767).astype(np.int16)
            os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
            with wave.open(self.output_file, "wb") as wav:
                wav.setnchannels(channels)
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
