from flask import Flask, render_template, Response, jsonify, send_from_directory
import lgpio
import time
import threading
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import cv2
import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage


app = Flask(__name__)

# PIR + Buzzer setup
PIR_PIN = 24
BUZZER_PIN = 23
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(chip, PIR_PIN)
lgpio.gpio_claim_output(chip, BUZZER_PIN)

# Camera setup
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (960, 720)}, encode="main")
picam2.configure(config)
picam2.start()

# Motion logs
motion_logs = []

# Recording state
is_recording = False
video_file = None
encoder = H264Encoder()
last_motion_time = None

# Auto-stop timer
STOP_DELAY = 5

# Folders
VIDEO_FOLDER = "recordings"
SNAPSHOT_FOLDER = "snapshots"
os.makedirs(VIDEO_FOLDER, exist_ok=True)
os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

# Email config
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "ambidaearl@gmail.com"
EMAIL_PASSWORD = "ayhv xcdd okof eizw"  # Use an App Password if using Gmail
EMAIL_RECEIVER = "2022-205142@rtu.edu.ph"
EMAIL_COOLDOWN = 60  # seconds between emails
last_email_time = 0


def send_email_alert(snapshot_path):
    """Send an email with a snapshot attachment"""
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = "🚨 Motion Detected Alert!"

        # Email body
        body = "Motion has been detected. See attached snapshot."
        msg.attach(MIMEText(body, "plain"))

        # Attach snapshot
        with open(snapshot_path, "rb") as f:
            img_data = f.read()
            image = MIMEImage(img_data, name=os.path.basename(snapshot_path))
            msg.attach(image)

        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print(f"Email alert sent with snapshot: {snapshot_path}")
    except Exception as e:
        print(f"Error sending email: {e}")



def gen_frames():
    """Generate live preview frames"""
    while True:
        frame = picam2.capture_array("main")
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/motion')
def motion():
    global is_recording, video_file, last_motion_time, last_email_time
    state = lgpio.gpio_read(chip, PIR_PIN)

    if state == 1:  # Motion detected
        lgpio.gpio_write(chip, BUZZER_PIN, 1)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        motion_logs.append(f"{timestamp} - Motion Detected")
        last_motion_time = time.time()

        # Save snapshot
        frame = picam2.capture_array("main")
        snapshot_path = os.path.join(SNAPSHOT_FOLDER, f"motion_{timestamp}.jpg")
        cv2.imwrite(snapshot_path, frame)

        # Send email if cooldown passed
        if time.time() - last_email_time > EMAIL_COOLDOWN:
            threading.Thread(target=send_email_alert, args=(snapshot_path,), daemon=True).start()
            last_email_time = time.time()

        # Start recording
        if not is_recording:
            video_file = os.path.join(VIDEO_FOLDER, f"motion_{timestamp}.h264")
            picam2.start_encoder(encoder, FileOutput(video_file))
            is_recording = True
            print(f"Started recording: {video_file}")
        return "Motion Detected!"

    else:
        lgpio.gpio_write(chip, BUZZER_PIN, 0)
        return "No Motion"


@app.route('/logs')
def logs():
    return jsonify(motion_logs[-10:])


@app.route('/snapshot')
def snapshot():
    """Capture a snapshot"""
    frame = picam2.capture_array("main")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(SNAPSHOT_FOLDER, f"snapshot_{timestamp}.jpg")
    cv2.imwrite(file_path, frame)
    return jsonify({"status": "ok", "message": f"Snapshot saved: {file_path}"})

@app.route('/start_record')
def start_record():
    """Manual start recording"""
    global is_recording, video_file
    if not is_recording:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        video_file = os.path.join(VIDEO_FOLDER, f"manual_{timestamp}.h264")
        picam2.start_encoder(encoder, FileOutput(video_file))
        is_recording = True
        return jsonify({"status": "ok", "message": "Recording started"})
    return jsonify({"status": "error", "message": "Already recording"})

@app.route('/stop_record')
def stop_record():
    """Manual stop recording + convert to MP4"""
    global is_recording, video_file
    if is_recording:
        picam2.stop_encoder(encoder)
        is_recording = False
        print(f"Stopped recording: {video_file}")

        mp4_file = video_file.replace(".h264", ".mp4")
        subprocess.run(["ffmpeg", "-y", "-i", video_file, "-c", "copy", mp4_file])
        os.remove(video_file)
        return jsonify({"status": "ok", "message": f"Recording saved: {mp4_file}"})
    return jsonify({"status": "error", "message": "Not recording"})



@app.route('/recordings')
def recordings():
    """List saved recordings"""
    files = sorted(os.listdir(VIDEO_FOLDER), reverse=True)
    mp4_files = [f for f in files if f.endswith(".mp4")]
    return render_template("recordings.html", files=mp4_files)


@app.route('/recordings/<filename>')
def download_recording(filename):
    return send_from_directory(VIDEO_FOLDER, filename)


def monitor_stop_recording():
    """Stop recording automatically after motion ends"""
    global is_recording, last_motion_time, video_file
    while True:
        if is_recording and last_motion_time is not None:
            if time.time() - last_motion_time > STOP_DELAY:
                picam2.stop_encoder(encoder)
                print(f"Stopped recording: {video_file}")
                # Convert to MP4
                mp4_file = video_file.replace(".h264", ".mp4")
                subprocess.run(["ffmpeg", "-y", "-i", video_file, "-c", "copy", mp4_file])
                os.remove(video_file)
                is_recording = False
                last_motion_time = None
        time.sleep(1)


if __name__ == "__main__":
    try:
        t = threading.Thread(target=monitor_stop_recording, daemon=True)
        t.start()
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        lgpio.gpiochip_close(chip)
        picam2.stop()
