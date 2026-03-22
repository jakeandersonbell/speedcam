import cv2, time, collections, subprocess, numpy as np, os

# --- CONFIG ---
WIDTH, HEIGHT = 640, 480
FRAME_SIZE = int(WIDTH * HEIGHT * 1.5)
PRE_ROLL = 5   # 0.5s head start
POST_ROLL = 15 # 1.5s follow-through
rolling_buffer = collections.deque(maxlen=PRE_ROLL)

# Camera command optimized for Module 3 (Manual focus at infinity)
cmd = [
    'rpicam-vid', '-t', '0', '--width', str(WIDTH), '--height', str(HEIGHT),
    '--nopreview', '--codec', 'yuv420', '--framerate', '30',
    '--autofocus-mode', 'manual', '--lens-position', '0', '-o', '-'
]

pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=FRAME_SIZE * 2)
fgbg = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50)

frame_count, capture_id = 0, 0
is_recording = False
captured_clip = []

print("📡 Radar Trigger Active. Monitoring road...")

try:
    while True:
        raw = pipe.stdout.read(FRAME_SIZE)
        if not raw: break
        frame_count += 1
        
        if frame_count % 3 == 0: # 10 FPS Target
            yuv = np.frombuffer(raw, dtype=np.uint8).reshape((int(HEIGHT * 1.5), WIDTH))
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            rolling_buffer.append(frame)

            mask = fgbg.apply(frame)
            if np.sum(cv2.threshold(mask, 250, 255, cv2.THRESH_BINARY)[1]) > 5000:
                if not is_recording:
                    is_recording = True
                    captured_clip = list(rolling_buffer)

            if is_recording:
                captured_clip.append(frame)
                if len(captured_clip) >= (PRE_ROLL + POST_ROLL):
                    folder = f"captures/event_{int(time.time())}"
                    os.makedirs(folder, exist_ok=True)
                    for i, img in enumerate(captured_clip):
                        cv2.imwrite(f"{folder}/frame_{i:03d}.jpg", img)
                    print(f"💾 Captured Event: {folder}")
                    is_recording, captured_clip = False, []
except KeyboardInterrupt:
    pipe.terminate()