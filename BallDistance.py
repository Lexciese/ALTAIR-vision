import cv2
import numpy as np

prev_data=[]

def ball(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_orange = np.array([1, 120, 75])
    upper_orange = np.array([25, 255, 255])

    mask_ball = cv2.inRange(hsv, lower_orange, upper_orange)

    kernel = np.ones((15, 15), np.uint8)
    mask_ball = cv2.morphologyEx(mask_ball, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask_ball, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area_threshold = 700  # Ambang batas minimum area hijau untuk dianggap sebagai lapangan
    ball_cleaned = np.zeros_like(mask_ball)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area_threshold:
            cv2.drawContours(ball_cleaned, [contour], -1, 255, thickness=cv2.FILLED)  # Hanya gambar area besar

    return ball_cleaned

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

    mask_field = cv2.bitwise_or(mask_green, mask_white)

    # Langkah morfologi "closing" untuk menghubungkan area hijau
    kernel = np.ones((15, 15), np.uint8)  # Ukuran kernel menyesuaikan dengan ukuran area hijau yang diharapkan
    mask_field = cv2.morphologyEx(mask_field, cv2.MORPH_CLOSE, kernel)

    # Menjaga hanya area hijau besar (area yang memenuhi batas minimum area dianggap lapangan)
    contours, _ = cv2.findContours(mask_field, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area_threshold = 5000  # Ambang batas minimum area hijau untuk dianggap sebagai lapangan
    field_cleaned = np.zeros_like(mask_field)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area_threshold:
            cv2.drawContours(field_cleaned, [contour], -1, 255, thickness=cv2.FILLED)  # Hanya gambar area besar

    return field_cleaned

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

            R = int(r * 1.5)  #jarak deteksi
            x1, y1 = max(x - R, 0), max(y - R, 0)
            x2, y2 = min(x + R, frame.shape[1]), min(y + R, frame.shape[0])

            surrounding_field = mask_field[y1:y2, x1:x2]
            field_ratio = np.sum(surrounding_field == 255) / surrounding_field.size

            surrounding_ball = mask_ball[y1:y2, x1:x2]
            ball_ratio = np.sum(surrounding_ball == 255) / surrounding_ball.size

            # mask berbentuk lingkaran untuk membatasi area di dalam lingkaran
            mask_circle = np.zeros(mask_ball.shape, dtype=np.uint8)
            cv2.circle(mask_circle, (x, y), R, 255, thickness=-1)

            # Ambil area mask yang hanya di dalam bola
            masked_orange_in_circle = cv2.bitwise_and(mask_ball, mask_ball, mask=mask_circle)

            # Garis horizontal di tengah lingkaran
            line_y = y
            line_x_start = max(x - R, 0)
            line_x_end = min(x + R, frame.shape[1])

            # Ambil piksel pada garis horizontal yang melewati lingkaran
            orange_line = masked_orange_in_circle[line_y, line_x_start:line_x_end]

            first_orange = None
            last_orange = None

            # Mencari indeks pertama dari piksel oranye
            for idx in range(orange_line.size):
                if orange_line[idx] == 255:  # 255 menandakan piksel oranye di mask
                    first_orange = idx + line_x_start  # posisi di garis asli
                    break

            # Mencari indeks terakhir dari piksel oranye
            for idx in range(orange_line.size - 1, -1, -1):
                if orange_line[idx] == 255:
                    last_orange = idx + line_x_start  # posisi di garis asli
                    break

            #gambar garis diameter bola
            cv2.line(frame, (first_orange, line_y), (last_orange, line_y), (0, 255, 0), 2)

            orange_pixel_count = np.sum(orange_line == 255)
            total_pixel = last_orange - first_orange

            # Tampilkan jumlah piksel oranye dan total piksel pada gambar
            text= f"Diameter: {total_pixel} pixel"
            cv2.putText(frame, text, (x - r, y + r + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Tandai piksel yang bukan bola dengan titik merah
            for px in range(first_orange, last_orange):
                if orange_line[px - line_x_start] != 255:
                    cv2.circle(frame, (px, line_y), 1, (0, 0, 255), -1)

            #cek apakah bola berada di atas lapangan
            if (field_ratio > 0.16 and ball_ratio < 0.37):
                x_new= int((last_orange + first_orange)/2)  #nilai titik pusat baru setelah cek pixel
                r_new= int(orange_pixel_count/2)            #nilai jari jari baru setelah cek pixel
                cv2.circle(frame, (x_new, y), r_new, (0, 255, 0), 2)
                cv2.circle(frame, (x_new, y), 2, (0, 0, 255), 3)
                prev_data= [x_new, y, r_new]                #simpan posisi dan jari jari bola
            elif circles is None:                           #gunakan frame sebelumnya jika bola tidak terdetect
                x, y, r= prev_data
                cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
                cv2.circle(frame, (x, y), 2, (0, 0, 255), 3)
                break

            #distance
            actual_diameter= 0.13 #meter
            focal_length= 700
            detected_diameter= total_pixel
            distance= (actual_diameter*focal_length)/detected_diameter
            text2 = f"Distance: {distance:.2f} meter"
            cv2.putText(frame, text2, (x - r, y + r + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            #print("pixel= ", total_pixel, "distance= ", int(distance*100))

    return frame

cap = cv2.VideoCapture('sample2.mp4')

if not cap.isOpened():
    print("Error: Tidak dapat membuka video.")
    exit()

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

out = cv2.VideoWriter('test2_3.mp4', fourcc, fps, (width, height))

while True:
    ret, frame = cap.read()
    if not ret:
        break

    mask_ball = ball(frame)
    mask_field = field(frame)
    final_frame = detect(mask_ball, mask_field, frame)

    if final_frame is not None:
        out.write(final_frame)

    #if cv2.waitKey(1) & 0xFF == ord('q'):
    #    break


cap.release()
out.release()
cv2.destroyAllWindows()