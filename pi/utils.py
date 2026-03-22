# pi/utils.py

def calculate_trap_distance(y_pixel):
    """
    Estimates the real-world distance (in meters) between Line 1 and Line 2 
    based on the car's vertical position (y_pixel).
    """
    # Perspective Math: 
    # Cars at the bottom (Y=480) are closer to the lens, so the 'pixel distance' 
    # represents a shorter real-world distance.
    # Cars near the middle (Y=240) represent a much longer stretch of road.
    
    # BASE DISTANCE (The actual distance between your lines on the ground)
    # Change '15' to the number of METERS between your Line 1 and Line 2.
    base_meters = 8.0
    
    # Perspective adjustment: 
    # If Y is low (top of screen), the distance is perceived as longer.
    # This is a basic linear approximation:
    scale_factor = 1.0 + ( (480 - y_pixel) / 480 )
    
    return base_meters * scale_factor

def calculate_speed(distance_meters, time_seconds):
    if time_seconds <= 0:
        return 0
    # Convert meters per second to Miles Per Hour
    mps = distance_meters / time_seconds
    mph = mps * 2.23694
    return mph