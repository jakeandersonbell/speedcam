import cv2, numpy as np, os, glob, time

# --- LOAD CALIBRATION & PERSPECTIVE ---
calib = np.load("calibration.npz")
MTX, DIST = calib["mtx"], calib["dist"]

# Your perspective values from the photo
Y_FAR, MPP_FAR = 250, 0.056
Y_NEAR, MPP_NEAR = 400, 0.035
SLOPE = (MPP_NEAR - MPP_FAR) / (Y_NEAR - Y_FAR)

# --- AI SETUP ---
net = cv2.dnn.readNetFromONNX("yolov8n.onnx")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

def undistort(frame):
    h, w = frame.shape[:2]
    new_mtx, _ = cv2.getOptimalNewCameraMatrix(MTX, DIST, (w,h), 1, (w,h))
    return cv2.undistort(frame, MTX, DIST, None, new_mtx)

def get_car_data(img_path):
    img = undistort(cv2.imread(img_path))
    blob = cv2.dnn.blobFromImage(img, 1/255.0, (640, 640), swapRB=True)
    net.setInput(blob)
    out = np.transpose(net.forward()[0])
    best = None
    for r in out:
        if r[4:].max() > 0.45 and np.argmax(r[4:]) == 2:
            if best is None or r[4:].max() > best[1]:
                best = ((int(r[0]), int(r[1] + r[3]/2)), r[4:].max())
    return best[0] if best else None

def process_event(folder):
    print(f"🕵️ Analyzing {folder}...")
    f0 = get_car_data(f"{folder}/frame_000.jpg")
    f10 = get_car_data(f"{folder}/frame_010.jpg")
    f19 = get_car_data(f"{folder}/frame_019.jpg")

    if not all([f0, f10, f19]):
        with open(f"{folder}/done.txt", "w") as f: f.write("fail")
        return

    # Speed Math
    def calc_s(p_start, p_end, dt):
        mpp = MPP_FAR + SLOPE * (p_end[1] - Y_FAR)
        return (abs(p_end[0] - p_start[0]) * mpp / dt) * 2.237

    s1, s2 = calc_s(f0, f10, 1.0), calc_s(f10, f19, 0.9)
    avg, var = (s1 + s2) / 2, abs(s1 - s2)

    if var < 6.5:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(folder)))
        # Create Evidence Photo
        res = undistort(cv2.imread(f"{folder}/frame_010.jpg"))
        cv2.rectangle(res, (5, 420), (350, 475), (0,0,0), -1)
        cv2.putText(res, f"{avg:.1f} MPH", (15, 445), 2, 0.8, (0,255,0), 2)
        cv2.putText(res, ts, (15, 468), 2, 0.4, (255,255,255), 1)
        cv2.imwrite(f"verified_{int(avg)}_{int(time.time())}.jpg", res)
        with open("log.csv", "a") as f: f.write(f"{ts},{avg:.1f}\n")
        print(f"🎯 SUCCESS: {avg:.1f} MPH")
    
    with open(f"{folder}/done.txt", "w") as f: f.write("done")

while True:
    for d in sorted(glob.glob("captures/event_*")):
        if not os.path.exists(f"{d}/done.txt"): process_event(d)
    time.sleep(5)