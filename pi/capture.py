import subprocess
import time

# Filename for the high-res master
FILENAME = "calibration_master.jpg"

print(f"📸 Taking a high-resolution master shot in 3 seconds...")
print("Make sure the road is clear or has well-positioned 'ruler' cars!")
time.sleep(3)

# Command to take a high-quality, full-res still
# -n: no preview, -e: encoding, -q: quality
cmd = [
    'rpicam-still', 
    '-o', FILENAME, 
    '--width', '4608', 
    '--height', '2592', 
    '--immediate',
    '-n'
]

try:
    subprocess.run(cmd, check=True)
    print(f"✅ Success! File saved as: {FILENAME}")
    print("Download this file to your computer to perform high-precision measurements.")
except Exception as e:
    print(f"❌ Error: {e}")