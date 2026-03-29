import cv2, time, collections, subprocess, numpy as np, os, threading, requests
from pi.config import *
from pi.firebase_utils import upload_observation, upload_env_data

# --- INITIALISATION ---
roi_mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
roi_mask[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2] = 255
fgbg = cv2.createBackgroundSubtractorMOG2(history=800, varThreshold=100, detectShadows=True)

hw_history = collections.deque(maxlen=RATIO_HISTORY_SIZE)
last_clocked_times = {'near': 0, 'far': 0}

class EnvironmentMonitor:
    def __init__(self):
        self.brightness_samples = []
        self.is_sampling = False

    def get_weather(self):
        """ Fetch real-time precipitation for Stretford via wttr.in """
        try:
            # format=j1 returns clean JSON
            r = requests.get("https://wttr.in/Stretford?format=j1", timeout=10).json()
            curr = r['current_condition'][0]
            return {
                "rain": float(curr.get('precipMM', 0)),
                "temp": float(curr.get('temp_C', 0)),
                "cloud": int(curr.get('cloudcover', 0)),
                "cond": curr.get('weatherDesc', [{}])[0].get('value', 'clear')
            }
        except Exception as e:
            print(f"⚠️ Weather Error: {e}")
            return {"rain": 0, "temp": 0, "cloud": 0, "cond": "unknown"}

    def log_environment(self):
        if not self.brightness_samples: return
        avg_light = np.mean(self.brightness_samples)
        w = self.get_weather()
        
        data = {
            "t": int(time.time()),
            "lux": round(avg_light, 2),
            "rain": w['rain'],
            "temp": w['temp'],
            "cloud": w['cloud'],
            "cond": w['cond']
        }
        threading.Thread(target=upload_env_data, args=(data,)).start()
        print(f"☁️ ENV LOG: Light {avg_light:.1f} | Rain {w['rain']}mm | {w['cond']}")
        self.brightness_samples = []

    def start_window(self):
        print("🕒 Research: Starting 60s Light/Weather sample...")
        self.is_sampling = True
        threading.Timer(60, self.stop_window).start()

    def stop_window(self):
        self.is_sampling = False
        self.log_environment()

env_monitor = EnvironmentMonitor()

def analyse_event(frames_with_times):
    global last_clocked_times
    tracks = [] 

    for frame, arrival_time in frames_with_times:
        # Get blobs
        masked = cv2.bitwise_and(frame, frame, mask=roi_mask)
        fg = fgbg.apply(masked)
        _, thr = cv2.threshold(cv2.dilate(fg, np.ones((5,5), np.uint8), iterations=3), 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            if cv2.contourArea(cnt) > MIN_AREA:
                x, y, w, h = cv2.boundingRect(cnt)
                cx, cy = x + w//2, y + h//2
                matched = False
                for t in tracks:
                    lx, ly, _ = t['p'][-1]
                    if np.sqrt((cx-lx)**2 + (cy-ly)**2) < 95:
                        t['p'].append((cx, cy, arrival_time))
                        t['w'].append(w)
                        t['r'].append(h/w)
                        matched = True
                        break
                if not matched:
                    tracks.append({'p': [(cx, cy, arrival_time)], 'w': [w], 'r': [h/w]})

    for car in tracks:
        path = car['p']
        if len(path) < MIN_POINTS_FOR_TRACK: continue

        # DIRECTIONAL LANE LOGIC
        dx_total = path[-1][0] - path[0][0]
        lane = 'near' if dx_total > 0 else 'far'
        
        if time.time() - last_clocked_times[lane] < 0.4: continue
        
        mpp = MPP_NEAR if lane == 'near' else MPP_FAR
        speeds = []
        for i in range(len(path) - 1):
            dx, dt = abs(path[i+1][0] - path[i][0]), path[i+1][2] - path[i][2]
            if dx > 2 and dt > 0:
                speeds.append((dx * mpp / dt) * 2.237)

        if not speeds: continue
        final_speed = np.median(speeds)

        if MIN_PLAUSIBLE_SPEED < final_speed < MAX_PLAUSIBLE_SPEED and abs(dx_total) > (WIDTH * 0.25):
            last_clocked_times[lane] = time.time()
            hw_history.append(np.median(car['r']))
            threading.Thread(target=upload_observation, args=(lane, round(final_speed,1), int(np.median(car['w'])), round(np.mean(hw_history),2))).start()
            print(f"🎯 {lane.upper()}: {final_speed:.1f} MPH")

def schedule_env():
    env_monitor.start_window()
    threading.Timer(1800, schedule_env).start()

# --- MAIN LOOP ---
cmd = ['rpicam-vid', '-t', '0', '--width', str(WIDTH), '--height', str(HEIGHT), '--nopreview', '--codec', 'yuv420', '--framerate', '30', '-o', '-']
pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=FRAME_SIZE * 30)
rolling_buffer = collections.deque(maxlen=PRE_ROLL)
is_recording, frame_count = False, 0

print(f"📡 Stretford Radar v10.1 [wttr.in edition] Active.")
schedule_env()

try:
    while True:
        raw = pipe.stdout.read(FRAME_SIZE)
        if len(raw) != FRAME_SIZE: continue 
        frame_count += 1
        
        if frame_count % 2 == 0:
            yuv = np.frombuffer(raw, dtype=np.uint8).reshape((int(HEIGHT * 1.5), WIDTH))
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            now = time.time()
            rolling_buffer.append((frame, now))
            
            if env_monitor.is_sampling and frame_count % 60 == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                env_monitor.brightness_samples.append(cv2.mean(gray, mask=roi_mask)[0])

            mask = fgbg.apply(cv2.bitwise_and(frame, frame, mask=roi_mask))
            if np.sum(cv2.threshold(mask, 250, 255, cv2.THRESH_BINARY)[1]) // 255 > MOTION_THRESHOLD and not is_recording:
                is_recording, event_buffer = True, list(rolling_buffer)

            if is_recording:
                event_buffer.append((frame, now))
                if len(event_buffer) >= (PRE_ROLL + POST_ROLL):
                    threading.Thread(target=analyse_event, args=(list(event_buffer),), daemon=True).start()
                    is_recording = False
except KeyboardInterrupt:
    pipe.terminate()