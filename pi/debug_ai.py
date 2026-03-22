import cv2
import numpy as np
import subprocess
import time

# 1. Load Model
net = cv2.dnn.readNetFromONNX("yolov8n.onnx")
# Lower confidence to 0.1 just for testing
CONF_THRESHOLD = 0.1 

# 2. Grab ONE frame from the camera
WIDTH, HEIGHT = 640, 480
FRAME_SIZE = int(WIDTH * HEIGHT * 1.5)
cmd = ['rpicam-vid', '-t', '1000', '--width', str(WIDTH), '--height', str(HEIGHT), '--nopreview', '--codec', 'yuv420', '-o', '-']
pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**8)

raw_image = pipe.stdout.read(FRAME_SIZE)
if len(raw_image) != FRAME_SIZE:
    print("❌ Camera Error: Could not read frame from pipe.")
    exit()

yuv = np.frombuffer(raw_image, dtype=np.uint8).reshape((int(HEIGHT * 1.5), WIDTH))
frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

# 3. Run AI
blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
net.setInput(blob)
output = net.forward()[0]
output = np.transpose(output)

print(f"Checking AI output... Shape: {output.shape}")

detected = False
for row in output:
    classes_scores = row[4:]
    class_id = np.argmax(classes_scores)
    score = classes_scores[class_id]
    
    if score > CONF_THRESHOLD:
        detected = True
        cx, cy, w, h = row[0:4]
        # Draw on the frame to see where the AI is looking
        x = int((cx - w/2) * (WIDTH / 640))
        y = int((cy - h/2) * (HEIGHT / 640))
        cv2.rectangle(frame, (x, y), (x + int(w), y + int(h)), (0, 255, 0), 2)
        cv2.putText(frame, f"ID:{class_id} {score:.2f}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

if detected:
    print("✅ AI detected something! Saving debug.jpg...")
else:
    print("❌ AI found nothing. Try moving a toy car in front of the lens.")

cv2.imwrite("debug.jpg", frame)
pipe.terminate()