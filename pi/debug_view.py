import cv2, numpy as np
from pi.main import roi_mask, fgbg 

# Take one frame from the camera and apply the mask
# (Or just manually check if your roi_mask has gone all black)
# If this file is mostly black, the Heatmap was too aggressive!
cv2.imwrite("roi_status.jpg", roi_mask)
print("Check roi_status.jpg. If the road is black, the heatmap is the problem.")