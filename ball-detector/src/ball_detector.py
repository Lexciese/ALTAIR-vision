import rclpy 
from rclpy import Node
from std_msgs.msg import Float64
import cv2
import numpy as np
import time

class ball_detector(Node):
    def __init__(self):
        super().__init__('ball_detector')
        self.ball_distance = self.create_publisher(Float64, 'vision/ball_distance', 10)

    # deteksi bola 
def ball(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_orange = np.array([1, 120, 110])
    upper_orange = np.array([25, 255, 255])

    mask_ball = cv2.inRange(hsv, lower_orange, upper_orange)

    ball_detected = cv2.bitwise_and(frame, frame, mask=mask_ball)

    #return ball_detected
    return mask_ball

#deteksi lapangan
def field(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # green
    lower_green = np.array([30, 50, 15])
    upper_green = np.array([100, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    # white
    lower_white = np.array([0, 0, 180])
    upper_white = np.array([190, 25, 255])
    mask_white = cv2.inRange(hsv, lower_white, upper_white)
    white_detected = cv2.bitwise_and(frame, frame, mask=mask_white)

    mask_field = cv2.bitwise_or(mask_green, mask_white)

    field_detected = cv2.bitwise_and(frame, frame, mask=mask_field)

    #return field_detected
    return mask_field

#deteksi bola pada lapangan
def detect(mask_ball, mask_field, frame):
    blurred_ball_mask = cv2.GaussianBlur(mask_ball, (9, 9), 2)

    circles = cv2.HoughCircles(
        blurred_ball_mask,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=10,
        maxRadius=100
    )

    if circles is not None:
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:
            x, y, r = i[0], i[1], i[2]

            margin = int(r * 1.5)
            x1, y1 = max(x - margin, 0), max(y - margin, 0)
            x2, y2 = min(x + margin, frame.shape[1]), min(y + margin, frame.shape[0])

            surrounding_area = mask_field[y1:y2, x1:x2]
            green_ratio = np.sum(surrounding_area == 255) / surrounding_area.size

            surrounding_area2 = mask_ball[y1:y2, x1:x2]
            orange_ratio = np.sum(surrounding_area == 255) / surrounding_area.size

            #cek bola oren di atas lapangan hijau
            if (green_ratio > 0.1 and orange_ratio <0.54):
                cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
                cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)

    return frame

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Tidak dapat membuka video.")
    exit()

# initialize previous time for fps measurement
prev_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("No remained frame, terminated")
        break
    new_frame_time = time.time()
    fps = 1 /(new_frame_time - prev_time)
    prev_time = new_frame_time

    mask_ball = ball(frame)
    mask_field = field(frame)
    final_frame = detect(mask_ball, mask_field, frame)
    cv2.putText(final_frame, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Show the detection frame with FPS
    cv2.imshow("Deteksi Bola", final_frame)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()


