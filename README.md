# Motion Sensor and Raspberry Pi Camera with Website

A Flask-based Raspberry Pi project that combines a PIR motion sensor, buzzer, and Pi Camera into a web dashboard for live monitoring, snapshots, and motion-triggered recording.

## Features

- Live camera stream in a browser
- PIR motion detection status updates
- Buzzer alert when motion is detected
- Motion event log display
- Automatic snapshot capture on motion
- Manual snapshot button
- Manual start/stop recording controls
- Automatic stop recording when motion ends
- MP4 conversion using FFmpeg
- Recordings page to view/download saved videos
- Email alert with snapshot attachment (cooldown-supported)

## Project Structure

- `app.py` - Main Flask application with sensor/camera logic and routes
- `testPIR.py` - Simple PIR + still-image capture test script
- `templates/index.html` - Dashboard UI
- `templates/recordings.html` - Saved recordings page
- `recordings/` - Generated recording output folder
- `snapshots/` - Generated snapshot output folder

## Hardware Requirements

- Raspberry Pi (recommended: Raspberry Pi OS)
- PIR motion sensor
- Active buzzer
- Raspberry Pi Camera module

## Software Requirements

- Python 3
- Flask (`pip` package: `flask`)
- GPIO library (`lgpio`; commonly provided by Raspberry Pi OS package `python3-lgpio`)
- Pi Camera library (`picamera2`; commonly provided by Raspberry Pi OS package `python3-picamera2`)
- OpenCV (`pip` package: `opencv-python`)
- FFmpeg (installed on system)

## Wiring (from current code)

In `app.py`:

- PIR sensor pin: `GPIO 24`
- Buzzer pin: `GPIO 23`

In `testPIR.py`:

- PIR sensor pin: `GPIO 17`

Update these values in code if your wiring is different.

## Setup

1. Clone this repository onto your Raspberry Pi.
2. Install system packages (recommended on Raspberry Pi OS):
   - `sudo apt update && sudo apt install -y python3-lgpio python3-picamera2 ffmpeg`
3. Install Python packages:
   - `pip install flask opencv-python`
4. Enable camera support on Raspberry Pi OS if not already enabled.
5. (Optional) Configure email settings in `app.py`:
   - `SMTP_SERVER`, `SMTP_PORT`, `EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECEIVER`

## Run the App

From the project directory:

```bash
python3 app.py
```

Then open:

- `http://<raspberry-pi-ip>:5000/`

## Dashboard Endpoints

- `/` - Main dashboard
- `/video_feed` - MJPEG camera stream
- `/motion` - Motion status check (also triggers motion handling)
- `/logs` - Recent motion log entries (JSON)
- `/snapshot` - Capture snapshot
- `/start_record` - Start manual recording
- `/stop_record` - Stop manual recording and convert to MP4
- `/recordings` - List saved MP4 recordings
- `/recordings/<filename>` - Download/view recording file

## Testing PIR Sensor Only

Run:

```bash
python3 testPIR.py
```

This script continuously checks PIR input and captures still images when motion is detected.

## Notes

- Ensure the `recordings/` and `snapshots/` folders are writable.
- Email alerts are throttled using `EMAIL_COOLDOWN` (seconds).
- If recording conversion fails, verify FFmpeg installation and file permissions.

## Security Reminder

Do not commit real email passwords or app passwords to source control. Prefer environment variables or a local configuration file excluded by `.gitignore`.
