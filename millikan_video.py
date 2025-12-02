import cv2
import tkinter as tk
from tkinter import filedialog
import time
import numpy as np

# --- 1. Global Variables ---
# 1-2: Calibration | 3: Select Particle | 4: Set Start Marker | 5: Set Finish Marker | 6: Measure
STATE = 1 
CALIB_TOP = None
CALIB_BOTTOM = None
PARTICLE_POS = None
MEASUREMENT_START_TIME = None
MEASUREMENT_END_TIME = None
CALIBRATION_MM = 1.0 # The specified distance in mm
PIXELS_PER_MM = None 
DROP_VELOCITY = 0.0

# --- Visual Marker Variables ---
START_MARKER_POS = None  # Absolute (x, y) for the start circle (Yellow)
FINISH_MARKER_POS = None # Absolute (x, y) for the finish circle (Magenta)

# --- Scrolling Variables ---
Y_OFFSET = 0             # Current vertical pixel offset for drawing
IS_DRAGGING = False      # Flag to track right-mouse button drag
DRAG_START_Y = 0         
INITIAL_OFFSET = 0       

# --- 2. Helper Functions ---

def draw_dotted_line(img, y_coord, x_start, x_end, color, thickness=1, dash_length=10):
    """Draws a horizontal dotted line on the image for the scale markers."""
    for x in range(x_start, x_end, dash_length * 2):
        cv2.line(img, (x, y_coord), (x + dash_length, y_coord), color, thickness)

def select_video_file():
    """Opens a file dialog to select the video."""
    root = tk.Tk()
    root.withdraw() 
    video_path = filedialog.askopenfilename(
        title="Select Millikan Experiment Video",
        filetypes=[("Video files", "*.mp4 *.avi")]
    )
    return video_path

# --- 3. Mouse Callback Function (Handles all Clicks and Scrolling) ---

def mouse_callback(event, x, y, flags, param):
    """Handles mouse events for scrolling, calibration, and measurement."""
    global STATE, CALIB_TOP, CALIB_BOTTOM, PARTICLE_POS, MEASUREMENT_START_TIME, MEASUREMENT_END_TIME, PIXELS_PER_MM, DROP_VELOCITY
    global IS_DRAGGING, DRAG_START_Y, INITIAL_OFFSET, Y_OFFSET
    global START_MARKER_POS, FINISH_MARKER_POS
    
    # --- Scrolling/Dragging Logic (Right Mouse Button) ---
    if event == cv2.EVENT_RBUTTONDOWN:
        IS_DRAGGING = True
        DRAG_START_Y = y
        INITIAL_OFFSET = Y_OFFSET
    
    elif event == cv2.EVENT_RBUTTONUP:
        IS_DRAGGING = False
        
    elif event == cv2.EVENT_MOUSEMOVE and IS_DRAGGING:
        delta_y = y - DRAG_START_Y
        Y_OFFSET = INITIAL_OFFSET + delta_y
        return 

    # --- Measurement/Calibration Logic (Left Click) ---
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"L-Click at: ({x}, {y}) - Current State: {STATE}")
        
        # Coordinates must be un-offset (y_true) to refer to the true video frame position
        x_true = x
        y_true = y - Y_OFFSET 

        # --- STATE 1: Calibrate Top Line ---
        if STATE == 1:
            CALIB_TOP = (x_true, y_true)
            STATE = 2
            print("Calibration Top Point Set. Please click the Bottom Line.")

        # --- STATE 2: Calibrate Bottom Line and Calculate Scale ---
        elif STATE == 2:
            CALIB_BOTTOM = (x_true, y_true)
            P_pixels = np.sqrt((CALIB_BOTTOM[0] - CALIB_TOP[0])**2 + (CALIB_BOTTOM[1] - CALIB_TOP[1])**2)
            
            if P_pixels > 0:
                PIXELS_PER_MM = P_pixels / CALIBRATION_MM
                STATE = 3
                print(f"Calibration Complete. Please click the particle you want to track.")
            else:
                print("Error: Calibration points too close. Please re-click.")

        # --- STATE 3: Select Particle to Track ---
        elif STATE == 3:
            PARTICLE_POS = (x_true, y_true)
            STATE = 4
            print("Particle Selected. Now, L-Click the exact START point (on the top line).")

        # --- STATE 4: Set START Marker ---
        elif STATE == 4:
            START_MARKER_POS = (x_true, y_true)
            STATE = 5
            print("Start Marker Set. Now, L-Click the exact FINISH point (on the bottom line).")

        # --- STATE 5: Set FINISH Marker ---
        elif STATE == 5:
            FINISH_MARKER_POS = (x_true, y_true)
            STATE = 6
            print("Finish Marker Set. Ready to measure! L-Click to START timing.")

        # --- STATE 6: Measurement Start/Stop ---
        elif STATE == 6:
            current_time = time.time()
            
            # Start measurement (First click)
            if MEASUREMENT_START_TIME is None:
                MEASUREMENT_START_TIME = current_time
                print("--- Measurement Started ---")
            
            # Stop measurement (Second click)
            else:
                MEASUREMENT_END_TIME = current_time
                t = MEASUREMENT_END_TIME - MEASUREMENT_START_TIME
                d = CALIBRATION_MM 

                if t > 0 and d > 0:
                    DROP_VELOCITY = d / t # velocity in mm/second
                    print(f"Time (t): {t:.4f} s | Velocity (v): {DROP_VELOCITY:.4f} mm/s")
                
                # Reset
                MEASUREMENT_START_TIME = None
                MEASUREMENT_END_TIME = None
                STATE = 3 
                START_MARKER_POS = None 
                FINISH_MARKER_POS = None
                print("Measurement Reset. Select a new particle.")


# --- 4. Main Analysis Loop ---

def run_analysis():
    """Main function to run the video analysis with all features."""
    global Y_OFFSET
    
    video_path = select_video_file()
    if not video_path:
        print("No video file selected. Exiting.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return
    
    # Get frame dimensions
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Define the starting X position for the right-aligned text
    RIGHT_ALIGN_X = W - 20 

    cv2.namedWindow('Millikan Analysis')
    cv2.setMouseCallback('Millikan Analysis', mouse_callback)
    
    # Helper function definition for right-aligned text
    def draw_right_aligned_text(frame, text, y_start, color=(255, 255, 255), scale=0.6, thickness=2):
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0]
        text_x = RIGHT_ALIGN_X - text_size[0]
        cv2.putText(frame, text, (text_x, y_start), 
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

    while cap.isOpened():
        ret, frame = cap.read()
        
        # Video Looping Logic
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop video
            continue

        display_frame = frame.copy() 

        # --- Drawing Logic (All drawn elements use Y_OFFSET) ---
        
        # 1. Measurement Scale Lines (Vertical Arrow and Dotted Horizontals)
        if CALIB_TOP and CALIB_BOTTOM:
            calib_top_draw = (CALIB_TOP[0], CALIB_TOP[1] + Y_OFFSET)
            calib_bottom_draw = (CALIB_BOTTOM[0], CALIB_BOTTOM[1] + Y_OFFSET)
            
            # Draw the Vertical Red Line (the 1.0 mm distance)
            cv2.line(display_frame, calib_top_draw, calib_bottom_draw, (0, 0, 255), 2)
            
            # Draw Top Dotted Horizontal Line
            draw_dotted_line(display_frame, calib_top_draw[1], 0, W, (0, 0, 255), 1, 10)

            # Draw Bottom Dotted Horizontal Line
            draw_dotted_line(display_frame, calib_bottom_draw[1], 0, W, (0, 0, 255), 1, 10)
            
            # Draw scale text
            mid_x = (calib_top_draw[0] + calib_bottom_draw[0]) // 2
            mid_y = (calib_top_draw[1] + calib_bottom_draw[1]) // 2
            scale_text = f"Scale: {CALIBRATION_MM} mm"
            cv2.putText(display_frame, scale_text, (mid_x + 10, mid_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)


        # 2. Selected Particle (Red Circle)
        if PARTICLE_POS:
            particle_draw = (PARTICLE_POS[0], PARTICLE_POS[1] + Y_OFFSET)
            cv2.circle(display_frame, particle_draw, 10, (0, 0, 255), 2)
            
        # 3. Starting Position Marker (Yellow Circle)
        if START_MARKER_POS:
            start_draw = (START_MARKER_POS[0], START_MARKER_POS[1] + Y_OFFSET)
            cv2.circle(display_frame, start_draw, 10, (0, 255, 255), 2) # Yellow
            
        # 4. Finishing Position Marker (Magenta Circle)
        if FINISH_MARKER_POS:
            finish_draw = (FINISH_MARKER_POS[0], FINISH_MARKER_POS[1] + Y_OFFSET)
            cv2.circle(display_frame, finish_draw, 10, (255, 0, 255), 2) # Magenta


        # 5. Display Measurement Results (Top Right Corner)
        y_pos = 30 # Initial Y position
        line_spacing = 25 
        
        # Instructions/State
        instruction_text = {
            1: "1. L-Click Top Line ",
            2: "2. L-Click Bottom Line (1.0mm)",
            3: "3. L-Click Particle to Track",
            4: "4. L-Click START Marker",
            5: "5. L-Click FINISH Marker",
            6: "6. L-Click START/STOP Timing"
        }.get(STATE, "Ready")
        
        draw_right_aligned_text(display_frame, instruction_text, y_pos, color=(255, 255, 255), scale=0.6, thickness=2)
        y_pos += line_spacing * 2 

        # Timer Display (Yellow)
        if MEASUREMENT_START_TIME:
            elapsed_time = time.time() - MEASUREMENT_START_TIME
            timer_text = f"TIME: {elapsed_time:.2f} s (In Progress)"
            draw_right_aligned_text(display_frame, timer_text, y_pos, color=(255, 255, 0), scale=0.6, thickness=2)
            y_pos += line_spacing
        
        # Velocity Display (Green)
        if DROP_VELOCITY > 0:
            vel_text = f"VELOCITY: {DROP_VELOCITY:.4f} mm/s"
            draw_right_aligned_text(display_frame, vel_text, y_pos, color=(0, 255, 0), scale=0.6, thickness=2)
            y_pos += line_spacing
            
        # Scroll Instruction (Follows Measurement Info)
        scroll_text = f"RMB Drag to Scroll View. Offset: {Y_OFFSET}"
        draw_right_aligned_text(display_frame, scroll_text, y_pos, color=(100, 255, 255), scale=0.5, thickness=1)

        # Show the frame
        cv2.imshow('Millikan Analysis', display_frame)

        # --- Keyboard Input Handling ---
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# --- Run the program ---
run_analysis()