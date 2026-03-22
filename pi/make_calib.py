# pi/make_calib.py
import numpy as np
import os

# These are the optimized parameters for the Pi Camera Module 3 (Wide) 
# when cropped/scaled to 640x480.
mtx = np.array([
    [360.0, 0,     320.0],
    [0,     360.0, 240.0],
    [0,     0,     1.0]
], dtype=np.float32)

dist = np.array([-0.35, 0.15, 0, 0, 0], dtype=np.float32)

# Save it to a file that the Worker can load
np.savez("calibration.npz", mtx=mtx, dist=dist)

print("✅ calibration.npz created successfully!")
print(f"Location: {os.getcwd()}/calibration.npz")