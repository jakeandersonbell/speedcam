import cv2
import numpy as np
import os

# Load a sample image
# Ensure you have 'roi_debug.jpg' in your /home/jake/speedcam folder
img_path = 'roi_debug.jpg'
img = cv2.imread(img_path)

if img is None:
    print(f"❌ Could not find {img_path}. Please capture a frame first!")
    exit()

def nothing(x):
    pass

# 1. Create the window FIRST
win_name = 'Lens Calibrator'
cv2.namedWindow(win_name)

# 2. Add sliders (Corrected with 5 arguments)
# Name, Window, Start Value, Max Value, Callback
cv2.createTrackbar('K1_Bend', win_name, 50, 100, nothing) 
cv2.createTrackbar('Zoom', win_name, 360, 800, nothing)

print("📐 Instructions:")
print("1. Adjust K1 until the vertical lines (houses) are straight.")
print("2. Adjust Zoom to scale the road back into view.")
print("3. Press 'q' to exit and save your numbers.")

while True:
    k1_pos = cv2.getTrackbarPos('K1_Bend', win_name)
    zoom = cv2.getTrackbarPos('Zoom', win_name)
    
    # Map 0-100 slider to -0.50 to 0.00 distortion
    k1 = (k1_pos - 100) / 100.0
    
    # Ensure zoom isn't zero to avoid math errors
    zoom = max(1, zoom)
    
    # Update matrices
    mtx = np.array([[zoom, 0, 320], [0, zoom, 240], [0, 0, 1]], dtype=np.float32)
    dist = np.array([k1, 0, 0, 0, 0], dtype=np.float32)
    
    h, w = img.shape[:2]
    new_mtx, _ = cv2.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
    dst = cv2.undistort(img, mtx, dist, None, new_mtx)
    
    # Add a red reference grid
    for x in range(0, w, 40): cv2.line(dst, (x, 0), (x, h), (0, 0, 255), 1)
    for y in range(0, h, 40): cv2.line(dst, (0, y), (w, y), (0, 0, 255), 1)

    cv2.imshow(win_name, dst)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print(f"\n✅ CALIBRATION COMPLETE")
        print(f"K1 Coefficient: {k1}")
        print(f"Zoom (Focal): {zoom}")
        break

cv2.destroyAllWindows()