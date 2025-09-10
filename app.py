from flask import Flask, render_template, Response, jsonify
import lgpio
import time
import threading
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import cv2
import os

app = Flask(__name__)

# PIR + Buzzer setup
PIR_PIN = 17
BUZZER_PIN = 27
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(chip, PIR_PIN)
lgpio.gpio_claim_output(chip, BUZZER_PIN)

# Camera setup
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (960, 720)},
    encode="main"
)
picam2.configure(config)
picam2.start()

# Motion logs
motion_logs = []

# Recording state
is_recording = False
video_file = None
encoder = H264Encoder()
last_motion_time = None

# Auto-stop timer (seconds after motion ends)
STOP_DELAY = 5  

# Save videos in folder
VIDEO_FOLDER = "recordings"
os.makedirs(VIDEO_FOLDER, exist_ok=True)


def gen_frames():
    """Generate live preview frames for streaming while recording works"""
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
    global is_recording, video_file, last_motion_time
    state = lgpio.gpio_read(chip, PIR_PIN)

    if state == 1:  # Motion detected
        lgpio.gpio_write(chip, BUZZER_PIN, 1)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        motion_logs.append(f"{timestamp} - Motion Detected")
        last_motion_time = time.time()  # refresh timer

        # Start recording if not already
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
    return jsonify(motion_logs[-10:])  # last 10 logs


def monitor_stop_recording():
    """Background thread to stop recording after delay when no motion"""
    global is_recording, last_motion_time, video_file
    while True:
        if is_recording and last_motion_time is not None:
            # If enough time passed since last motion, stop recording
            if time.time() - last_motion_time > STOP_DELAY:
                picam2.stop_encoder(encoder)
                print(f"Stopped recording: {video_file}")
                is_recording = False
                last_motion_time = None
        time.sleep(1)  # check every second


if __name__ == "__main__":
    try:
        # Start background thread
        t = threading.Thread(target=monitor_stop_recording, daemon=True)
        t.start()

        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        lgpio.gpiochip_close(chip)
        picam2.stop()
