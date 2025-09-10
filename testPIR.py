import lgpio
import time
from picamera2 import Picamera2

# PIR setup
PIR_PIN = 17
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_input(chip, PIR_PIN)

# Camera setup
picam2 = Picamera2()
config = picam2.create_still_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

print("PIR + Camera test started. Press CTRL+C to stop.")

try:
    while True:
        state = lgpio.gpio_read(chip, PIR_PIN)
        if state == 1:
            print("Motion detected! Capturing image...")
            filename = f"capture_{int(time.time())}.jpg"
            picam2.capture_file(filename)
            print(f"Saved {filename}")
            time.sleep(2)  # debounce delay
        else:
            print("No motion")
        
        time.sleep(1)  # check every second

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    lgpio.gpiochip_close(chip)
    picam2.stop()
