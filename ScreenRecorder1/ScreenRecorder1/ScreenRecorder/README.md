# Screen Recorder

A Windows desktop screen recorder built with Python and CustomTkinter.

## Features

- Full-screen or primary-monitor recording
- Custom rectangular recording area
- MP4 screen recording
- 24/30/60 FPS
- Original, 1080p, 900p, 720p and 480p output
- Cursor marker option
- Microphone recording
- Windows system-audio loopback recording
- Separate webcam recording
- **No picture-in-picture**
- Pause/resume
- F7/F8/F9 global hotkeys
- Screenshots
- Media library with open, folder, rename and delete
- Persistent settings
- Application log
- FFmpeg audio/video finalization
- PyInstaller packaging

## Install

Install Python 3.10+ and then:

```bat
python -m pip install -r requirements.txt
```

## FFmpeg

For audio/video finalization, place the Windows FFmpeg executable here:

```text
ffmpeg\ffmpeg.exe
```

The program also checks the Windows PATH for FFmpeg.

## Run

```bat
python main.py
```

## Build EXE

Place `ffmpeg.exe` in `ffmpeg\ffmpeg.exe`, then run:

```text
build_exe.bat
```

The executable will be:

```text
dist\ScreenRecorder\ScreenRecorder.exe
```

Keep the `ffmpeg` folder with the application.

## Notes

Microphone and system audio are optional. They are disabled by default to make the first screen-recording test simpler.

The webcam is recorded to a separate video file and is never composited into the screen recording.

System audio uses Windows speaker loopback through the `soundcard` package.

## Project folders

```text
ScreenRecorder/
├── main.py
├── requirements.txt
├── build_exe.bat
├── ffmpeg/
├── recorder/
├── utils/
├── recordings/
├── screenshots/
└── logs/
```
