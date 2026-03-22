import cv2, time, collections, subprocess, numpy as np, os, threading

# --- 1. CONFIGURATION ---
WIDTH, HEIGHT = 640, 480
FRAME_SIZE = int(WIDTH * HEIGHT * 1.5)
PRE_ROLL, POST_ROLL = 3, 7

# Perspective (Stretford POV)
Y_FAR, MPP_FAR = 250, 0.056
Y_NEAR, MPP_NEAR = 400, 0.035
SLOPE = (MPP_NEAR - MPP_FAR) / (Y_NEAR - Y_FAR)

# --- THE SURGICAL CROP & VERTICAL FILTER ---
CROP_X1, CROP_X2 = 260, 520  
CROP_Y1, CROP_Y2 = 270, 430  
CROP_W, CROP_H = (CROP_X2 - CROP_X1), (CROP_Y2 - CROP_Y1)

# NEW: Ignore anything where the car's bottom Y is less than this.
# This effectively 'blinds' the AI to the parked cars near the kerb.
IGNORE_Y_ABOVE = 345  

# Thresholds
MIN_CONF = 0.18             
MIN_DISPLACEMENT_PX = 25    
MAX_VARIANCE = 9.0          
MOTION_THRESHOLD = 15000    
TRIGGER_COOLDOWN = 2.5      

MODEL_FILE = "yolov8n.onnx"
LOG_FILE = "traffic_log.csv"

# --- 2. INITIALISE ---
print("🧠 Loading AI (Vertical Exclusion Mode)...")
net = cv2.dnn.readNetFromONNX(MODEL_FILE)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

roi_mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
roi_mask[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2] = 255

# --- 3. HELPER FUNCTIONS ---

def get_mpp(y):
    return np.clip(MPP_FAR + SLOPE * (y - Y_FAR), 0.030, 0.065)

def get_car_coords_direct(img):
    roi = img[CROP_Y1:CROP_Y2, CROP_X1:CROP_X2]
    blob = cv2.dnn.blobFromImage(roi, 1/255.0, (640, 640), swapRB=True)
    net.setInput(blob)
    out = np.transpose(net.forward()[0])
    
    best = None
    for r in out:
        conf = r[4:].max()
        if conf > MIN_CONF and np.argmax(r[4:]) == 2:
            # Map coordinates
            real_cx = int((r[0] / 640) * CROP_W) + CROP_X1
            real_cy = int((r[1] / 640) * CROP_H) + CROP_Y1
            real_h = int((r[3] / 640) * CROP_H)
            real_w = int((r[2] / 640) * CROP_W)
            
            y_bottom = real_cy + (real_h // 2)
            
            # --- THE VERTICAL FILTER ---
            if y_bottom < IGNORE_Y_ABOVE:
                continue # Skip the parked cars!

            if best is None or conf > best[1]:
                coords = (real_cx, y_bottom)
                box = [real_cx - real_w//2, real_cy - real_h//2, real_w, real_h]
                best = (coords, conf, box)
    return best

# --- 4. THE DETECTIVE ---

def analyse_event(frames, ts):
    print(f"🕵️ Analysing lane event from {ts}...")
    pts = []
    debug_frames = []
    
    for i in [0, 4, 8]:
        if i >= len(frames): break
        img = frames[i].copy()
        res = get_car_coords_direct(img)
        
        if res:
            coords, conf, box = res 
            pts.append(coords)
            cv2.rectangle(img, (box[0], box[1]), (box[0]+box[2], box[1]+box[3]), (0, 255, 255), 2)
            cv2.circle(img, coords, 5, (0, 0, 255), -1)
        else:
            pts.append(None)
        
        # Draw the filter line on debug images (Red Line)
        cv2.line(img, (CROP_X1, IGNORE_Y_ABOVE), (CROP_X2, IGNORE_Y_ABOVE), (0, 0, 255), 2)
        debug_frames.append(img)
    
    cv2.imwrite(f"debug_filtered_{int(time.time())}.jpg", np.hstack(debug_frames))

    if len(pts) < 3 or not all(pts):
        return 

    # Speed Maths (0.4s intervals)
    x0, y0 = pts[0]
    x4, y4 = pts[1]
    x8, y8 = pts[2]

    s1 = (abs(x4 - x0) * get_mpp(y4) / 0.4) * 2.237
    s2 = (abs(x8 - x4) * get_mpp(y8) / 0.4) * 2.237
    avg, var = (s1 + s2) / 2, abs(s1 - s2)

    if var < MAX_VARIANCE:
        print(f"🎯 CLOCKED: {avg:.1f} MPH")
        res_img = frames[4].copy()
        cv2.putText(res_img, f"{avg:.1f} MPH", (15, 445), 2, 0.8, (0, 255, 0), 2)
        cv2.imwrite(f"verified_{int(avg)}_{int(time.time())}.jpg", res_img)
        with open(LOG_FILE, "a") as f:
            f.write(f"{ts},{avg:.1f},{var:.1f}\n")

# --- 5. THE MAIN LOOP ---
cmd = ['rpicam-vid', '-t', '0', '--width', '640', '--height', '480', '--nopreview', 
       '--codec', 'yuv420', '--framerate', '30', '--autofocus-mode', 'manual', 
       '--lens-position', '0', '-o', '-']

pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=FRAME_SIZE * 20)
fgbg = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=75)

rolling_buffer = collections.deque(maxlen=PRE_ROLL)
is_recording, last_trigger, frame_count = False, 0, 0

try:
    while True:
        raw = pipe.stdout.read(FRAME_SIZE)
        if len(raw) != FRAME_SIZE: continue 
        frame_count += 1
        
        if frame_count % 3 == 0:
            yuv = np.frombuffer(raw, dtype=np.uint8).reshape((int(HEIGHT * 1.5), WIDTH))
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            rolling_buffer.append(frame)

            mask = fgbg.apply(cv2.bitwise_and(frame, frame, mask=roi_mask))
            score = np.sum(cv2.threshold(mask, 250, 255, cv2.THRESH_BINARY)[1])
            
            now = time.time()
            if score > MOTION_THRESHOLD and not is_recording and (now - last_trigger) > TRIGGER_COOLDOWN:
                is_recording, last_trigger = True, now
                captured_frames = list(rolling_buffer)

            if is_recording:
                captured_frames.append(frame)
                if len(captured_frames) >= (PRE_ROLL + POST_ROLL):
                    t = threading.Thread(target=analyse_event, args=(list(captured_frames), time.strftime("%H:%M:%S")))
                    t.daemon = True
                    t.start()
                    is_recording, captured_frames = False, []

except KeyboardInterrupt:
    pipe.terminate()