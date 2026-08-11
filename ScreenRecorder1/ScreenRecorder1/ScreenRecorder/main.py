import os
import sys
import time
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    import keyboard
except ImportError:
    keyboard = None

from recorder.screen_recorder import ScreenRecorder
from recorder.audio_recorder import AudioRecorder
from recorder.system_audio_recorder import SystemAudioRecorder
from recorder.webcam_recorder import WebcamRecorder
from recorder.area_selector import AreaSelector
from utils.media_library import MediaLibrary
from utils.settings_manager import SettingsManager
from utils.recording_profiles import RecordingProfiles
from utils.screenshot import ScreenshotManager
from utils.logger import AppLogger
from utils.ffmpeg_path import get_ffmpeg_path


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def app_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class ScreenRecorderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.root_dir = app_root()
        os.chdir(self.root_dir)

        self.title("Screen Recorder")
        self.geometry("1100x820")
        self.minsize(900, 680)

        self.logger = AppLogger(
            os.path.join(self.root_dir, "logs")
        )
        self.settings_manager = SettingsManager(
            os.path.join(self.root_dir, "settings.json")
        )
        self.settings = self.settings_manager.load()

        self.recording = False
        self.paused = False
        self.start_time = None
        self.elapsed_time = 0.0
        self.timer_job = None
        self.stats_job = None

        self.recorder = None
        self.audio_recorder = None
        self.system_audio_recorder = None
        self.webcam_recorder = None

        self.output_file = None
        self.audio_file = None
        self.system_audio_file = None
        self.webcam_file = None
        self.selected_area = None

        self.output_folder = self.settings.get("output_folder", "recordings")
        if not os.path.isabs(self.output_folder):
            self.output_folder = os.path.join(self.root_dir, self.output_folder)
        os.makedirs(self.output_folder, exist_ok=True)

        self.recordings_folder = os.path.join(self.root_dir, "recordings")
        self.screenshots_folder = os.path.join(self.root_dir, "screenshots")
        os.makedirs(self.recordings_folder, exist_ok=True)
        os.makedirs(self.screenshots_folder, exist_ok=True)

        self.media_library = MediaLibrary(
            self.recordings_folder, self.screenshots_folder
        )
        self.screenshot_manager = ScreenshotManager(self.screenshots_folder)

        self.build_ui()
        self.restore_settings()
        self.register_hotkeys()
        self.update_timer()
        self.update_stats()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.logger.info("Application started.")

    # ------------------------------------------------------------
    # UI
    # ------------------------------------------------------------

    def build_ui(self):
        header = ctk.CTkFrame(self, corner_radius=14, height=75)
        header.pack(fill="x", padx=15, pady=(15, 8))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="SCREEN RECORDER",
            font=ctk.CTkFont(size=25, weight="bold")
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            header, text="Professional PC screen capture • v1.0",
            text_color="gray"
        ).pack(side="left")

        self.recording_indicator = ctk.CTkLabel(
            header, text="● READY", text_color="#4CAF50",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.recording_indicator.pack(side="right", padx=20)

        self.main = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.main.pack(fill="both", expand=True, padx=10, pady=5)

        timer = ctk.CTkFrame(self.main, corner_radius=18)
        timer.pack(fill="x", padx=5, pady=8)

        self.status_label = ctk.CTkLabel(
            timer, text="● READY", text_color="#4CAF50",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.status_label.pack(pady=(18, 3))

        self.timer_label = ctk.CTkLabel(
            timer, text="00:00:00",
            font=ctk.CTkFont(size=48, weight="bold")
        )
        self.timer_label.pack(pady=(0, 18))

        controls = ctk.CTkFrame(self.main, fg_color="transparent")
        controls.pack(fill="x", padx=5, pady=8)
        for i in range(5):
            controls.grid_columnconfigure(i, weight=1)

        self.record_button = ctk.CTkButton(
            controls, text="●  START", height=48,
            command=self.start_recording
        )
        self.record_button.grid(row=0, column=0, padx=4, sticky="ew")

        self.pause_button = ctk.CTkButton(
            controls, text="Ⅱ  PAUSE", height=48,
            state="disabled", command=self.pause_recording
        )
        self.pause_button.grid(row=0, column=1, padx=4, sticky="ew")

        self.stop_button = ctk.CTkButton(
            controls, text="■  STOP", height=48,
            state="disabled", command=self.stop_recording
        )
        self.stop_button.grid(row=0, column=2, padx=4, sticky="ew")

        self.screenshot_button = ctk.CTkButton(
            controls, text="📸  SCREENSHOT", height=48,
            command=self.take_screenshot
        )
        self.screenshot_button.grid(row=0, column=3, padx=4, sticky="ew")

        self.library_button = ctk.CTkButton(
            controls, text="📁  LIBRARY", height=48,
            command=self.open_library
        )
        self.library_button.grid(row=0, column=4, padx=4, sticky="ew")

        self.hotkey_label = ctk.CTkLabel(
            self.main,
            text="F8 Start/Stop  •  F7 Pause/Resume  •  F9 Screenshot",
            text_color="gray"
        )
        self.hotkey_label.pack(pady=(0, 8))

        settings = ctk.CTkFrame(self.main, corner_radius=18)
        settings.pack(fill="x", padx=5, pady=8)
        settings.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            settings, text="RECORDING SETTINGS",
            font=ctk.CTkFont(size=19, weight="bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w",
               padx=20, pady=(18, 12))

        self.area_menu = ctk.CTkOptionMenu(
            settings,
            values=["Primary Monitor", "Full Screen", "Custom Area"],
            height=38,
            command=self.area_changed
        )
        self.area_menu.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.fps_menu = ctk.CTkOptionMenu(
            settings, values=["24 FPS", "30 FPS", "60 FPS"], height=38
        )
        self.fps_menu.grid(row=1, column=1, padx=20, pady=5, sticky="ew")

        self.resolution_menu = ctk.CTkOptionMenu(
            settings,
            values=["Original", "1920 × 1080", "1600 × 900", "1280 × 720", "854 × 480"],
            height=38
        )
        self.resolution_menu.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.profile_menu = ctk.CTkOptionMenu(
            settings, values=RecordingProfiles.get_names(),
            height=38, command=self.profile_changed
        )
        self.profile_menu.grid(row=2, column=1, padx=20, pady=5, sticky="ew")

        self.mic_switch = ctk.CTkSwitch(settings, text="Microphone")
        self.mic_switch.grid(row=3, column=0, sticky="w", padx=20, pady=8)

        self.system_audio_switch = ctk.CTkSwitch(settings, text="System Audio")
        self.system_audio_switch.grid(row=3, column=1, sticky="w", padx=20, pady=8)

        self.webcam_switch = ctk.CTkSwitch(settings, text="Webcam (separate file)")
        self.webcam_switch.grid(row=4, column=0, sticky="w", padx=20, pady=8)

        self.cursor_switch = ctk.CTkSwitch(settings, text="Show cursor marker")
        self.cursor_switch.grid(row=4, column=1, sticky="w", padx=20, pady=8)

        output_frame = ctk.CTkFrame(settings, fg_color="transparent")
        output_frame.grid(row=5, column=0, columnspan=2, sticky="ew",
                          padx=20, pady=(8, 18))
        output_frame.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(output_frame, height=38)
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.browse_button = ctk.CTkButton(
            output_frame, text="Browse", width=100, height=38,
            command=self.choose_output_folder
        )
        self.browse_button.grid(row=0, column=1)

        stats = ctk.CTkFrame(self.main, corner_radius=18)
        stats.pack(fill="x", padx=5, pady=8)
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            stats, text="LIVE STATUS",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w",
               padx=20, pady=(15, 8))

        self.file_size_value = self._stat(stats, "FILE SIZE", "0 B", 0, 1)
        self.fps_value = self._stat(stats, "FPS", "30", 1, 1)
        self.audio_value = self._stat(stats, "AUDIO", "OFF", 2, 1)
        self.webcam_value = self._stat(stats, "WEBCAM", "OFF", 3, 1)

        self.output_value = ctk.CTkLabel(
            stats, text="Output: —", text_color="gray", anchor="w"
        )
        self.output_value.grid(row=2, column=0, columnspan=4,
                               sticky="ew", padx=20, pady=(5, 15))

        utility = ctk.CTkFrame(self.main, corner_radius=18)
        utility.pack(fill="x", padx=5, pady=8)
        ctk.CTkButton(
            utility, text="SAVE SETTINGS", command=self.save_settings
        ).pack(side="left", padx=10, pady=12)
        ctk.CTkButton(
            utility, text="RESET SETTINGS", command=self.reset_settings
        ).pack(side="left", padx=10, pady=12)
        ctk.CTkButton(
            utility, text="VIEW LOG", command=self.open_log
        ).pack(side="left", padx=10, pady=12)

    def _stat(self, parent, title, value, column, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=column, padx=10, pady=4)
        ctk.CTkLabel(frame, text=title, text_color="gray").pack()
        label = ctk.CTkLabel(
            frame, text=value, font=ctk.CTkFont(size=16, weight="bold")
        )
        label.pack()
        return label

    # ------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------

    def restore_settings(self):
        self.area_menu.set(self.settings.get("recording_area", "Primary Monitor"))
        self.fps_menu.set(f'{self.settings.get("fps", 30)} FPS')
        self.resolution_menu.set(self.settings.get("resolution", "Original"))
        self.profile_menu.set(self.settings.get("profile", "Standard"))
        self.output_entry.insert(0, self.output_folder)

        if self.settings.get("microphone_enabled", False):
            self.mic_switch.select()
        if self.settings.get("system_audio_enabled", False):
            self.system_audio_switch.select()
        if self.settings.get("webcam_enabled", False):
            self.webcam_switch.select()
        if self.settings.get("capture_cursor", True):
            self.cursor_switch.select()

    def profile_changed(self, name):
        profile = RecordingProfiles.get_profile(name)
        self.fps_menu.set(f'{profile["fps"]} FPS')

    def area_changed(self, value):
        if value == "Custom Area" and not self.recording:
            selected = AreaSelector().select()
            if selected:
                self.selected_area = selected
            else:
                self.area_menu.set("Primary Monitor")
                self.selected_area = None

    def save_settings(self):
        folder = self.output_entry.get().strip() or self.output_folder
        settings = {
            "profile": self.profile_menu.get(),
            "fps": self.get_fps(),
            "resolution": self.resolution_menu.get(),
            "recording_area": self.area_menu.get(),
            "output_folder": folder,
            "microphone_enabled": bool(self.mic_switch.get()),
            "system_audio_enabled": bool(self.system_audio_switch.get()),
            "webcam_enabled": bool(self.webcam_switch.get()),
            "webcam_index": int(self.settings.get("webcam_index", 0)),
            "webcam_width": int(self.settings.get("webcam_width", 640)),
            "webcam_height": int(self.settings.get("webcam_height", 480)),
            "webcam_fps": int(self.settings.get("webcam_fps", 30)),
            "capture_cursor": bool(self.cursor_switch.get()),
        }
        self.settings = settings
        if self.settings_manager.save(settings):
            self.logger.info("Settings saved.")
        else:
            messagebox.showerror("Settings", "Unable to save settings.")

    def reset_settings(self):
        if not messagebox.askyesno("Reset Settings",
                                   "Reset all settings to defaults?"):
            return
        self.settings_manager.reset()
        self.settings = self.settings_manager.load()
        messagebox.showinfo("Settings", "Settings reset. Restart the application to apply defaults.")

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def get_fps(self):
        try:
            return int(self.fps_menu.get().split()[0])
        except Exception:
            return 30

    def get_resolution(self):
        value = self.resolution_menu.get()
        if value == "Original":
            return None
        try:
            w, h = value.replace("×", "x").split("x")
            return int(w.strip()), int(h.strip())
        except Exception:
            return None

    def get_monitor(self):
        return 0 if self.area_menu.get() == "Full Screen" else 1

    def set_controls(self, recording):
        state = "disabled" if recording else "normal"
        self.record_button.configure(state=state)
        self.stop_button.configure(state="normal" if recording else "disabled")
        self.pause_button.configure(state="normal" if recording else "disabled")
        for widget in (self.area_menu, self.fps_menu, self.resolution_menu,
                       self.profile_menu, self.browse_button):
            widget.configure(state=state)

    def set_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)
        self.recording_indicator.configure(text=text, text_color=color)

    # ------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------

    def start_recording(self):
        if self.recording:
            return

        try:
            output_folder = self.output_entry.get().strip()
            if not output_folder:
                raise RuntimeError("Please choose an output folder.")
            os.makedirs(output_folder, exist_ok=True)

            fps = self.get_fps()
            resolution = self.get_resolution()
            monitor = self.get_monitor()
            area = self.selected_area if self.area_menu.get() == "Custom Area" else None
            cursor = bool(self.cursor_switch.get())

            self.recorder = ScreenRecorder(
                output_folder, fps, monitor, resolution, cursor, area
            )
            if not self.recorder.start():
                raise RuntimeError(
                    self.recorder.get_error() or "Unable to start screen recording."
                )

            stamp = time.strftime("%Y%m%d_%H%M%S")
            self.audio_file = os.path.join(output_folder, f"mic_{stamp}.wav")
            self.system_audio_file = os.path.join(output_folder, f"system_{stamp}.wav")
            self.webcam_file = None

            if self.mic_switch.get():
                self.audio_recorder = AudioRecorder(self.audio_file)
                if not self.audio_recorder.start():
                    self.logger.warning(
                        f"Microphone could not start: {self.audio_recorder.get_error()}"
                    )
                    self.audio_recorder = None

            if self.system_audio_switch.get():
                self.system_audio_recorder = SystemAudioRecorder(self.system_audio_file)
                if not self.system_audio_recorder.start():
                    self.logger.warning(
                        f"System audio could not start: {self.system_audio_recorder.get_error()}"
                    )
                    self.system_audio_recorder = None

            if self.webcam_switch.get():
                self.webcam_recorder = WebcamRecorder(
                    output_folder=output_folder,
                    camera_index=int(self.settings.get("webcam_index", 0)),
                    width=int(self.settings.get("webcam_width", 640)),
                    height=int(self.settings.get("webcam_height", 480)),
                    fps=int(self.settings.get("webcam_fps", 30)),
                )
                if not self.webcam_recorder.start():
                    self.logger.warning(
                        f"Webcam could not start: {self.webcam_recorder.get_error()}"
                    )
                    self.webcam_recorder = None

            self.output_file = self.recorder.get_output_file()
            self.recording = True
            self.paused = False
            self.start_time = time.time()
            self.elapsed_time = 0.0
            self.set_controls(True)
            self.set_status("● RECORDING", "#FF4444")
            self.logger.info(f"Recording started: {self.output_file}")

        except Exception as exc:
            self.logger.exception("Start recording failed.")
            self._stop_components()
            self.recording = False
            self.set_controls(False)
            self.set_status("● READY", "#4CAF50")
            messagebox.showerror("Recording Error", str(exc))

    def pause_recording(self):
        if not self.recording:
            return

        if not self.paused:
            self.elapsed_time = time.time() - self.start_time
            self.paused = True
            self.recorder.pause()
            if self.audio_recorder: self.audio_recorder.pause()
            if self.system_audio_recorder: self.system_audio_recorder.pause()
            if self.webcam_recorder: self.webcam_recorder.pause()
            self.pause_button.configure(text="▶  RESUME")
            self.set_status("● PAUSED", "#FFA500")
            self.logger.info("Recording paused.")
        else:
            self.start_time = time.time() - self.elapsed_time
            self.paused = False
            self.recorder.resume()
            if self.audio_recorder: self.audio_recorder.resume()
            if self.system_audio_recorder: self.system_audio_recorder.resume()
            if self.webcam_recorder: self.webcam_recorder.resume()
            self.pause_button.configure(text="Ⅱ  PAUSE")
            self.set_status("● RECORDING", "#FF4444")
            self.logger.info("Recording resumed.")

    def stop_recording(self):
        if not self.recording:
            return

        self.recording = False
        self.paused = False
        self.set_controls(False)
        self.set_status("● FINALIZING", "#FFA500")
        self.update_idletasks()

        try:
            video = self.recorder.stop() if self.recorder else self.output_file
            mic = self.audio_recorder.stop() if self.audio_recorder else None
            system = (
                self.system_audio_recorder.stop()
                if self.system_audio_recorder else None
            )
            webcam = (
                self.webcam_recorder.stop()
                if self.webcam_recorder else None
            )

            self.recorder = None
            self.audio_recorder = None
            self.system_audio_recorder = None
            self.webcam_recorder = None
            self.webcam_file = webcam

            final_video = self._finalize_video(video, mic, system)

            # Delete temporary WAV files after a successful finalization.
            for path in (mic, system):
                if path and os.path.isfile(path) and final_video:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

            self.elapsed_time = 0.0
            self.timer_label.configure(text="00:00:00")
            self.output_value.configure(
                text=f"Output: {final_video or video or 'No file'}"
            )
            self.set_status("● READY", "#4CAF50")
            self.logger.info(
                f"Recording stopped. Video={final_video or video}, Webcam={webcam}"
            )

            if final_video or video:
                message = f"Screen recording saved:\n\n{final_video or video}"
                if webcam:
                    message += f"\n\nWebcam saved separately:\n{webcam}"
                messagebox.showinfo("Recording Complete", message)

        except Exception as exc:
            self.logger.exception("Stop recording failed.")
            self.set_status("● READY", "#4CAF50")
            messagebox.showerror("Stop Error", str(exc))

    def _stop_components(self):
        for component in (
            self.recorder,
            self.audio_recorder,
            self.system_audio_recorder,
            self.webcam_recorder,
        ):
            if component:
                try:
                    component.stop()
                except Exception:
                    pass
        self.recorder = self.audio_recorder = None
        self.system_audio_recorder = self.webcam_recorder = None

    def _finalize_video(self, video, mic, system):
        if not video or not os.path.isfile(video):
            return None

        audio_files = [
            p for p in (mic, system)
            if p and os.path.isfile(p) and os.path.getsize(p) > 44
        ]
        if not audio_files:
            return video

        ffmpeg = get_ffmpeg_path()
        if not ffmpeg:
            self.logger.warning("FFmpeg not found; keeping video without audio.")
            return video

        base, ext = os.path.splitext(video)
        final = base + "_final.mp4"
        cmd = [ffmpeg, "-y", "-i", video]

        for audio in audio_files:
            cmd += ["-i", audio]

        if len(audio_files) == 1:
            cmd += [
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", final
            ]
        else:
            cmd += [
                "-filter_complex",
                "[1:a][2:a]amix=inputs=2:duration=longest:dropout_transition=2[aout]",
                "-map", "0:v:0", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", final
            ]

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            self.logger.error("FFmpeg finalization failed:\n" + result.stderr[-4000:])
            return video

        if os.path.isfile(final):
            try:
                os.remove(video)
            except OSError:
                pass
            return final
        return video

    # ------------------------------------------------------------
    # Timer / live stats
    # ------------------------------------------------------------

    def update_timer(self):
        if self.recording and not self.paused and self.start_time:
            self.elapsed_time = time.time() - self.start_time
        seconds = int(self.elapsed_time)
        self.timer_label.configure(
            text=f"{seconds//3600:02d}:{(seconds%3600)//60:02d}:{seconds%60:02d}"
        )
        self.timer_job = self.after(250, self.update_timer)

    @staticmethod
    def format_size(size):
        if size < 1024: return f"{size} B"
        if size < 1024**2: return f"{size/1024:.1f} KB"
        if size < 1024**3: return f"{size/1024**2:.1f} MB"
        return f"{size/1024**3:.2f} GB"

    def update_stats(self):
        if self.output_file and os.path.isfile(self.output_file):
            try:
                size = os.path.getsize(self.output_file)
                self.file_size_value.configure(text=self.format_size(size))
            except OSError:
                pass

        self.fps_value.configure(text=str(self.get_fps()))
        audio_on = bool(self.mic_switch.get()) or bool(self.system_audio_switch.get())
        self.audio_value.configure(text="ON" if audio_on else "OFF")
        self.webcam_value.configure(
            text="ON" if bool(self.webcam_switch.get()) else "OFF"
        )
        self.stats_job = self.after(500, self.update_stats)

    # ------------------------------------------------------------
    # Screenshots / folder / log
    # ------------------------------------------------------------

    def take_screenshot(self):
        try:
            area = self.selected_area if self.area_menu.get() == "Custom Area" else None
            path = self.screenshot_manager.take_screenshot(
                monitor_index=self.get_monitor(), area=area
            )
            if path:
                self.logger.info(f"Screenshot saved: {path}")
                messagebox.showinfo("Screenshot Saved", f"Saved to:\n{path}")
            else:
                messagebox.showerror("Screenshot Error", "Unable to capture screenshot.")
        except Exception as exc:
            self.logger.exception("Screenshot failed.")
            messagebox.showerror("Screenshot Error", str(exc))

    def choose_output_folder(self):
        if self.recording:
            return
        folder = filedialog.askdirectory(
            title="Select Recording Folder",
            initialdir=self.output_folder
        )
        if folder:
            self.output_folder = folder
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)

    def open_log(self):
        if not os.path.isfile(self.logger.log_path):
            messagebox.showinfo("Log", "No log file exists yet.")
            return
        MediaLibrary.open_file(self.logger.log_path)

    # ------------------------------------------------------------
    # Media Library
    # ------------------------------------------------------------

    def open_library(self):
        library = ctk.CTkToplevel(self)
        library.title("Screen Recorder - Media Library")
        library.geometry("1050x700")
        library.minsize(850, 550)

        header = ctk.CTkFrame(library, corner_radius=12)
        header.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(
            header, text="MEDIA LIBRARY",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(side="left", padx=15, pady=12)

        tabs = ctk.CTkTabview(library)
        tabs.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        recordings_tab = tabs.add("🎬 Recordings")
        screenshots_tab = tabs.add("📸 Screenshots")

        rec_scroll = ctk.CTkScrollableFrame(recordings_tab)
        rec_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        shot_scroll = ctk.CTkScrollableFrame(screenshots_tab)
        shot_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        def refresh():
            for frame in (rec_scroll, shot_scroll):
                for child in frame.winfo_children():
                    child.destroy()
            for info in self.media_library.get_recordings():
                add_card(rec_scroll, info)
            for info in self.media_library.get_screenshots():
                add_card(shot_scroll, info)

        def add_card(parent, info):
            card = ctk.CTkFrame(parent, corner_radius=10)
            card.pack(fill="x", padx=5, pady=5)
            ctk.CTkLabel(
                card, text="🎬" if info["type"] == "video" else "📸",
                font=ctk.CTkFont(size=24), width=45
            ).pack(side="left", padx=10, pady=10)

            detail = ctk.CTkFrame(card, fg_color="transparent")
            detail.pack(side="left", fill="x", expand=True, padx=5)
            ctk.CTkLabel(
                detail, text=info["name"], anchor="w",
                font=ctk.CTkFont(weight="bold")
            ).pack(fill="x")
            ctk.CTkLabel(
                detail,
                text=f'{info["size_text"]}  •  {info["date"]} {info["time"]}',
                text_color="gray", anchor="w"
            ).pack(fill="x")

            buttons = ctk.CTkFrame(card, fg_color="transparent")
            buttons.pack(side="right", padx=8)

            ctk.CTkButton(
                buttons, text="OPEN", width=75,
                command=lambda p=info["path"]: MediaLibrary.open_file(p)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                buttons, text="FOLDER", width=75,
                command=lambda p=info["path"]: MediaLibrary.open_folder(p)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                buttons, text="RENAME", width=80,
                command=lambda i=info: rename(i)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                buttons, text="DELETE", width=75,
                fg_color="#8B0000", hover_color="#B00000",
                command=lambda i=info: delete(i)
            ).pack(side="left", padx=2)

        def delete(info):
            if messagebox.askyesno("Delete File", f'Delete "{info["name"]}"?', parent=library):
                if not MediaLibrary.delete_file(info["path"]):
                    messagebox.showerror("Delete", "Unable to delete file.", parent=library)
                refresh()

        def rename(info):
            dialog = ctk.CTkInputDialog(
                text="Enter the new filename:", title="Rename File"
            )
            name = dialog.get_input()
            if name:
                if not MediaLibrary.rename_file(info["path"], name):
                    messagebox.showerror(
                        "Rename", "Unable to rename file. The name may already exist.",
                        parent=library
                    )
                refresh()

        ctk.CTkButton(
            header, text="↻ REFRESH", width=110, command=refresh
        ).pack(side="right", padx=15)

        refresh()

    # ------------------------------------------------------------
    # Hotkeys / close
    # ------------------------------------------------------------

    def register_hotkeys(self):
        if not keyboard:
            self.logger.warning("keyboard package unavailable; hotkeys disabled.")
            return
        try:
            keyboard.add_hotkey("f8", self.toggle_recording)
            keyboard.add_hotkey("f7", lambda: self.after(0, self.pause_recording))
            keyboard.add_hotkey("f9", lambda: self.after(0, self.take_screenshot))
        except Exception as exc:
            self.logger.warning(f"Hotkey registration failed: {exc}")

    def toggle_recording(self):
        try:
            self.after(0, self._toggle_recording_ui)
        except Exception:
            pass

    def _toggle_recording_ui(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def on_close(self):
        if self.recording:
            if not messagebox.askyesno(
                "Recording in Progress",
                "A recording is running. Stop it and exit?"
            ):
                return
            self.stop_recording()

        self.save_settings()

        if keyboard:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass

        for job in (self.timer_job, self.stats_job):
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass

        self.logger.info("Application closed.")
        self.destroy()


if __name__ == "__main__":
    app = ScreenRecorderApp()
    app.mainloop()
