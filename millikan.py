import cv2
import tkinter as tk
from tkinter import filedialog
import time
import numpy as np

# --- Global Variables for State Management ---
# 0: Select Video, 1: Calibrate Top Line, 2: Calibrate Bottom Line, 3: Select Particle, 4: Measure 
STATE = 1 
CALIB_TOP = None
CALIB_BOTTOM = None
PARTICLE_POS = None
MEASUREMENT_START_TIME = None
MEASUREMENT_END_TIME = None
CALIBRATION_MM = 1.0 # The specified distance in mm
PIXELS_PER_MM = None 
DROP_VELOCITY = 0.0

def select_video_file():
    """Opens a file dialog to select the video."""
    root = tk.Tk()
    root.withdraw() # Hide the main window
    video_path = filedialog.askopenfilename(
        title="Select Millikan Experiment Video",
        filetypes=[("Video files", "*.mp4 *.avi")]
    )
    return video_path


# Mouse clicking of scale 

def mouse_callback(event, x, y, flags, param):
    """Handles mouse clicks on the video frame."""
    global STATE, CALIB_TOP, CALIB_BOTTOM, PARTICLE_POS, MEASUREMENT_START_TIME, MEASUREMENT_END_TIME, PIXELS_PER_MM, DROP_VELOCITY

    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Click at: ({x}, {y}) - Current State: {STATE}")

        # --- STATE 1: Calibrate Top Line ---
        if STATE == 1:
            CALIB_TOP = (x, y)
            STATE = 2
            print("Calibration Top Point Set. Please click the Bottom Line.")

        # --- STATE 2: Calibrate Bottom Line and Calculate Scale ---
        elif STATE == 2:
            CALIB_BOTTOM = (x, y)
            
            # Calculate pixel distance between the two clicks
            P_pixels = np.sqrt((CALIB_BOTTOM[0] - CALIB_TOP[0])**2 + (CALIB_BOTTOM[1] - CALIB_TOP[1])**2)
            
            if P_pixels > 0:
                PIXELS_PER_MM = P_pixels / CALIBRATION_MM
                STATE = 3
                print(f"Calibration Complete. {P_pixels:.2f} pixels = {CALIBRATION_MM} mm. Scale: {PIXELS_PER_MM:.2f} pixels/mm. Please select the particle.")
            else:
                print("Error: Calibration points too close. Please re-click.")


        # --- STATE 3: Select Particle to Track ---
        elif STATE == 3:
            PARTICLE_POS = (x, y)
            STATE = 4
            print("Particle Selected. Click again to start the timing.")

        # --- STATE 4: Measurement Start/Stop ---
        elif STATE == 4:
            current_time = time.time()
            
            # Start measurement (First click)
            if MEASUREMENT_START_TIME is None:
                MEASUREMENT_START_TIME = current_time
                print("--- Measurement Started ---")
            
            # Stop measurement (Second click)
            else:
                MEASUREMENT_END_TIME = current_time
                t = MEASUREMENT_END_TIME - MEASUREMENT_START_TIME
                d = CALIBRATION_MM # Known distance is 1.0 mm

                if t > 0 and d > 0:
                    DROP_VELOCITY = d / t # velocity in mm/second
                    print(f"--- Measurement Complete ---")
                    print(f"Time (t): {t:.4f} s")
                    print(f"Distance (d): {d} mm")
                    print(f"Velocity (v): {DROP_VELOCITY:.4f} mm/s")
                
                # Reset for next measurement
                MEASUREMENT_START_TIME = None
                MEASUREMENT_END_TIME = None
                STATE = 3 # Go back to particle selection
                print("Resetting. You can now select a new particle.")

# Analysis 

def run_analysis():
    """Main function to run the video analysis."""
    video_path = select_video_file()
    if not video_path:
        print("No video file selected. Exiting.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    # Create a named window and set the mouse callback
    cv2.namedWindow('Millikan Analysis')
    cv2.setMouseCallback('Millikan Analysis', mouse_callback)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            # Reached end of video
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop video
            continue

        # Create a copy to draw on
        display_frame = frame.copy() 
        H, W, _ = display_frame.shape
        
        # --- Drawing Calibration Line (Red Arrow) ---
        if CALIB_TOP and CALIB_BOTTOM:
            # Draw the line connecting the calibration points
            cv2.line(display_frame, CALIB_TOP, CALIB_BOTTOM, (0, 0, 255), 2) # Red line
            
            # Draw the scale text next to the arrow
            mid_x = (CALIB_TOP[0] + CALIB_BOTTOM[0]) // 2
            mid_y = (CALIB_TOP[1] + CALIB_BOTTOM[1]) // 2
            scale_text = f"Scale: {CALIBRATION_MM} mm"
            cv2.putText(display_frame, scale_text, (mid_x + 10, mid_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)


        # --- Drawing Selected Particle (Red Circle) ---
        if PARTICLE_POS:
            cv2.circle(display_frame, PARTICLE_POS, 10, (0, 0, 255), 2) # Red circle

        
        # --- Displaying Measurement Results ---
        # Position for display text
        text_y_start = 30
        
        # Display current state/instruction
        instruction_text = {
            1: "1. Click Top Calibration Line (10 boxes = 1.0mm)",
            2: "2. Click Bottom Calibration Line",
            3: "3. Click a Particle to Track",
            4: "4. Click to START timing. Click again to STOP."
        }.get(STATE, "Ready")
        
        cv2.putText(display_frame, instruction_text, (10, text_y_start), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Display velocity measurement
        if DROP_VELOCITY > 0:
            vel_text = f"Velocity: {DROP_VELOCITY:.4f} mm/s"
            cv2.putText(display_frame, vel_text, (10, text_y_start + 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Display current timer
        if MEASUREMENT_START_TIME:
            elapsed_time = time.time() - MEASUREMENT_START_TIME
            timer_text = f"Timer: {elapsed_time:.2f} s"
            cv2.putText(display_frame, timer_text, (10, text_y_start + 80), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)


        # Show the frame
        cv2.imshow('Millikan Analysis', display_frame)

        # Break loop on 'q' press
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# --- Run the program ---
run_analysis()