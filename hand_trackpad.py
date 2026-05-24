import cv2
import mediapipe as mp
import time
import pyautogui

global cursor_movement_multiplier
cursor_movement_multiplier = 1

def update_multiplier(multipler):
    global cursor_movement_multiplier
    cursor_movement_multiplier = multipler

multiplier_min = 1
multiplier_max = 10

mpHands = mp.solutions.hands
hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

prevTime = 0
currTime = 0

prev_single_hand_detected = False
prev_index_on_top = False
prev_index_tip_pos = None
prev_hand_count = 0
is_mouse_down = False

last_multiplier_change_time = 0
min_secs_since_multiplier_change = 2

while True:
    try:
        trackbar_pos = cv2.getTrackbarPos('Multiplier', 'Hand Trackpad')
    except:
        cv2.namedWindow('Hand Trackpad')
        cv2.createTrackbar('Multiplier', 'Hand Trackpad', cursor_movement_multiplier, 
                           multiplier_max, update_multiplier)
        cv2.setTrackbarMin('Multiplier', 'Hand Trackpad', multiplier_min)

    success, img = cap.read()
    img = cv2.flip(img, 1)
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    if results.multi_hand_landmarks:
        hand_count = len(results.multi_hand_landmarks)
        if hand_count == 1:
            single_hand_detected = True
        else:
            single_hand_detected = False

        lms_map_list = [{} for i in range(hand_count)]
        for hand_index, handLms in enumerate(results.multi_hand_landmarks):
            for id, lm in enumerate(handLms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                lms_map_list[hand_index][id] = (cx, cy)

            mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS)
        
        for lms_map in lms_map_list:
            index_tip_pos = lms_map[8]
            thump_tip_pos = lms_map[4]
            middle_tip_pos = lms_map[12]
            ring_tip_pos = lms_map[16]
            pinky_tip_pos = lms_map[20]

            index_on_top = (index_tip_pos[1] < thump_tip_pos[1] and
                            index_tip_pos[1] < middle_tip_pos[1] and
                            index_tip_pos[1] < ring_tip_pos[1] and
                            index_tip_pos[1] < pinky_tip_pos[1])
            
            index_left_most = (index_tip_pos[0] < thump_tip_pos[0] and
                            index_tip_pos[0] < middle_tip_pos[0] and
                            index_tip_pos[0] < ring_tip_pos[0] and
                            index_tip_pos[0] < pinky_tip_pos[0])
            
            index_right_most = (index_tip_pos[0] > thump_tip_pos[0] and
                                index_tip_pos[0] > middle_tip_pos[0] and
                                index_tip_pos[0] > ring_tip_pos[0] and
                                index_tip_pos[0] > pinky_tip_pos[0])
            
            thumb_on_top = (thump_tip_pos[1] < index_tip_pos[1] and
                            thump_tip_pos[1] < middle_tip_pos[1] and
                            thump_tip_pos[1] < ring_tip_pos[1] and
                            thump_tip_pos[1] < pinky_tip_pos[1])
            
            if index_on_top:
                cv2.circle(img, (index_tip_pos[0], index_tip_pos[1]), 10, (255, 0, 0), cv2.FILLED)
                break

            if (thumb_on_top and index_left_most) or (thumb_on_top and index_right_most):
                cv2.circle(img, (index_tip_pos[0], index_tip_pos[1]), 10, (0, 255, 0), cv2.FILLED)
                break                    

        if not (index_on_top and prev_index_tip_pos != None and hand_count == 2 and 
                prev_hand_count == 2):
            if is_mouse_down:
                pyautogui.mouseUp()
                is_mouse_down = False
        if (index_on_top and prev_index_tip_pos != None):
            x_offset = (index_tip_pos[0] - prev_index_tip_pos[0]) * cursor_movement_multiplier
            y_offset = (index_tip_pos[1] - prev_index_tip_pos[1]) * cursor_movement_multiplier
            if single_hand_detected and prev_single_hand_detected:
                pyautogui.move(x_offset, y_offset)
            elif hand_count == 2 and prev_hand_count == 2:
                if not is_mouse_down:
                    pyautogui.mouseDown()
                    is_mouse_down = True
                pyautogui.move(x_offset, y_offset)
        elif hand_count == 2 and prev_hand_count < 2 and not index_on_top:
            pyautogui.click()
        
        elif thumb_on_top and index_left_most:
            time_elapsed =  time.time() - last_multiplier_change_time
            if time_elapsed > min_secs_since_multiplier_change:
                new_multiplier = cursor_movement_multiplier - 1
                new_multiplier = min(max(new_multiplier, multiplier_min), multiplier_max)
                cv2.setTrackbarPos('Multiplier', 'Hand Trackpad', new_multiplier)
                last_multiplier_change_time = time.time()
        elif thumb_on_top and index_right_most:
            time_elapsed =  time.time() - last_multiplier_change_time
            if time_elapsed > min_secs_since_multiplier_change:
                new_multiplier = cursor_movement_multiplier + 1
                new_multiplier = max(min(new_multiplier, multiplier_max), multiplier_min)
                cv2.setTrackbarPos('Multiplier', 'Hand Trackpad', new_multiplier)
                last_multiplier_change_time = time.time()

        if is_mouse_down:
            cv2.circle(img, (index_tip_pos[0], index_tip_pos[1]), 15, (0, 0, 255), cv2.FILLED)

        prev_single_hand_detected = single_hand_detected
        prev_index_on_top = index_on_top
        prev_index_tip_pos = index_tip_pos
        prev_hand_count = hand_count

    else:
        prev_single_hand_detected = False
        prev_index_on_top = False
        prev_index_tip_pos = None
        prev_hand_count = 0
        if is_mouse_down:
            pyautogui.mouseUp()
        is_mouse_down = False

    currTime = time.time()
    fps = 1 / (currTime - prevTime)
    prevTime = currTime

    cv2.putText(img, str(int(fps)) + ' fps', (10, 70), cv2.FONT_HERSHEY_PLAIN, 3,
                (255, 0, 0), 3)

    cv2.imshow("Hand Trackpad", img)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()