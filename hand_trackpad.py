import cv2
import mediapipe as mp
import time
import pyautogui

global curosor_movement_multiplier
curosor_movement_multiplier = 1

def update_multiplier(multipler):
    global curosor_movement_multiplier
    curosor_movement_multiplier = multipler

cv2.namedWindow('Video') 
cv2.createTrackbar('Multiplier', 'Video', 1, 10, update_multiplier)
cv2.setTrackbarMin('Multiplier', 'Video', 1)

cap = cv2.VideoCapture(0)

mpHands = mp.solutions.hands
hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils

prevTime = 0
currTime = 0

prev_single_hand_dected = False
prev_index_on_top = False
prev_index_tip_pos = None
prev_hand_count = 0
prev_mouse_down = False

while True:
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

            index_on_top = (index_tip_pos[1] < thump_tip_pos[1] 
                            and index_tip_pos[1] < middle_tip_pos[1] 
                            and index_tip_pos[1] < ring_tip_pos[1] 
                            and index_tip_pos[1] < pinky_tip_pos[1])
            
            if index_on_top:
                cv2.circle(img, (index_tip_pos[0], index_tip_pos[1]), 10, (255, 0, 0), cv2.FILLED)
                break

        if (index_on_top and prev_index_tip_pos != None):
            x_offset = (index_tip_pos[0] - prev_index_tip_pos[0]) * curosor_movement_multiplier
            y_offset = (index_tip_pos[1] - prev_index_tip_pos[1]) * curosor_movement_multiplier
            if hand_count == 2 and prev_hand_count == 2:
                if not prev_mouse_down:
                    pyautogui.mouseDown()
                    prev_mouse_down = True
            elif single_hand_detected and prev_single_hand_dected:
                if prev_mouse_down:
                    pyautogui.mouseUp()
                    prev_mouse_down = False
            pyautogui.move(x_offset, y_offset)
        elif hand_count == 2 and prev_hand_count < 2 and not index_on_top:
            if prev_mouse_down:
                pyautogui.mouseUp()
                prev_mouse_down = False
            pyautogui.click()

        prev_single_hand_dected = single_hand_detected
        prev_index_on_top = index_on_top
        prev_index_tip_pos = index_tip_pos
        prev_hand_count = hand_count

    else:
        prev_single_hand_dected = False
        prev_index_on_top = False
        prev_index_tip_pos = None
        prev_hand_count = 0
        if prev_mouse_down:
            pyautogui.mouseUp()
        prev_mouse_down = False

    currTime = time.time()
    fps = 1 / (currTime - prevTime)
    prevTime = currTime

    cv2.putText(img, str(int(fps)), (10, 70), cv2.FONT_HERSHEY_PLAIN, 3,
                (255, 0, 0), 3)

    cv2.imshow("Video", img)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()