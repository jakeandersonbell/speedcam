import cv2, time, collections, subprocess, numpy as np, os, threading
from pi.config import *
from pi.firebase_utils import upload_observation

# --- INITIALISATION ---
roi_mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
roi_mask[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2] = 255
fgbg = cv2.createBackgroundSubtractorMOG2(history=800, varThreshold=100, detectShadows=True)

hw_history = collections.deque(maxlen=RATIO_HISTORY_SIZE)
last_clocked_times = {'near': 0, 'far': 0}

def get_rain_offset():
    """ Lifts tracking points if reflections are present. """
    if len(hw_history) < 5: return 0
    avg_ratio = np.median(hw_history)
    return int((avg_ratio - DRY_HW_RATIO) * 80) if avg_ratio > DRY_HW_RATIO else 0

def get_blobs_as_instances(frame):
    masked = cv2.bitwise_and(frame, frame, mask=roi_mask)
    fgmask = fgbg.apply(masked)
    kernel = np.ones((5,5), np.uint8)
    fgmask = cv2.dilate(fgmask, kernel, iterations=3)
    _, thresh = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    instances = []
    for cnt in contours:
        if cv2.contourArea(cnt) > MIN_AREA:
            x, y, w, h = cv2.boundingRect(cnt)
            instances.append({'center': (x + w//2, y + h//2), 'w': w, 'h': h, 'ratio': h / w})
    return instances

def analyse_event(frames_with_times, ts):
    global last_clocked_times, hw_history
    active_tracks = [] 

    for frame, arrival_time in frames_with_times:
        current_blobs = get_blobs_as_instances(frame)
        for blob in current_blobs:
            matched = False
            for track in active_tracks:
                lx, ly, _ = track['points'][-1]
                if np.sqrt((blob['center'][0]-lx)**2 + (blob['center'][1]-ly)**2) < 95:
                    track['points'].append((blob['center'][0], blob['center'][1], arrival_time))
                    track['widths'].append(blob['w'])
                    track['ratios'].append(blob['ratio'])
                    matched = True
                    break
            if not matched:
                active_tracks.append({'points': [(blob['center'][0], blob['center'][1], arrival_time)], 'widths': [blob['w']], 'ratios': [blob['ratio']]})

    for car in active_tracks:
        path = car['points']
        if len(path) < MIN_POINTS_FOR_TRACK: continue

        this_car_ratio = np.median(car['ratios'])
        hw_history.append(this_car_ratio)
        median_w = np.median(car['widths'])
        lane = 'near' if median_w > LANE_WIDTH_THRESHOLD else 'far'
        
        if time.time() - last_clocked_times[lane] < 0.4: continue

        offset, mpp = get_rain_offset(), (MPP_NEAR if lane == 'near' else MPP_FAR)
        speeds = []
        for i in range(len(path) - 1):
            dx, dt = (path[i+1][0] - path[i][0]), (path[i+1][2] - path[i][2])
            if abs(dx) > 3 and dt > 0:
                speeds.append((abs(dx) * mpp / dt) * 2.237)

        if not speeds: continue
        final_speed, std_dev = np.median(speeds), np.std(speeds)

        if not (MIN_PLAUSIBLE_SPEED < final_speed < MAX_PLAUSIBLE_SPEED) or std_dev > MAX_VARIANCE:
            continue

        # Success!
        last_clocked_times[lane] = time.time()
        # res_img = frames_with_times[len(frames_with_times)//2][0].copy()
        # for p in path:
        #     cv2.circle(res_img, (int(p[0]), int(p[1]) - offset), 5, (0, 255, 0), -1)
        
        # cv2.putText(res_img, f"{final_speed:.1f} MPH", (20, 435), 2, 1.1, (0, 255, 0), 2)
        # cv2.putText(res_img, f"{lane.upper()} | Width: {int(median_w)}px", (20, 465), 2, 0.45, (255, 255, 255), 1)
        
        # img_name = f"verified_{lane}_{int(final_speed)}mph_{int(time.time())}.jpg"
        # cv2.imwrite(img_name, res_img)
        
        # Threaded Cloud Sync
        threading.Thread(target=upload_observation, args=(lane, final_speed, median_w, np.mean(hw_history), "")).start()
        print(f"🎯 CLOCKED {lane.upper()}: {final_speed:.1f} MPH")

# --- MAIN CAPTURE LOOP ---
cmd = ['rpicam-vid', '-t', '0', '--width', str(WIDTH), '--height', str(HEIGHT), '--nopreview', '--codec', 'yuv420', '--framerate', '30', '-o', '-']
pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=FRAME_SIZE * 30)
rolling_buffer = collections.deque(maxlen=PRE_ROLL)
is_recording, last_trigger, frame_count = False, 0, 0

print(f"📡 Stretford Radar v9.2 [Cloud Integrated] Active.")

try:
    while True:
        raw = pipe.stdout.read(FRAME_SIZE)
        if len(raw) != FRAME_SIZE: continue 
        frame_count += 1
        
        if frame_count % 2 == 0:
            yuv = np.frombuffer(raw, dtype=np.uint8).reshape((int(HEIGHT * 1.5), WIDTH))
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            now = time.time()
            frame_data = (frame, now)
            rolling_buffer.append(frame_data)
            
            mask = fgbg.apply(cv2.bitwise_and(frame, frame, mask=roi_mask))
            score = np.sum(cv2.threshold(mask, 250, 255, cv2.THRESH_BINARY)[1]) // 255
            
            if score > MOTION_THRESHOLD and not is_recording and (now - last_trigger) > TRIGGER_COOLDOWN:
                is_recording, last_trigger, event_buffer = True, now, list(rolling_buffer)

            if is_recording:
                event_buffer.append(frame_data)
                if len(event_buffer) >= (PRE_ROLL + POST_ROLL):
                    threading.Thread(target=analyse_event, args=(list(event_buffer), ""), daemon=True).start()
                    is_recording, event_buffer = False, []
except KeyboardInterrupt:
    pipe.terminate()