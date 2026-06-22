import cv2
import mediapipe as mp
import time
import pyautogui
import pyttsx3

pyautogui.FAILSAFE = False

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

prev_hand_count = 0
prev_main_control_hand = None
is_mouse_down = False

min_secs_since_multiplier_change = 2
min_secs_till_click = 2
two_hands_for_click_start_time = 0
min_secs_till_right_click = 2
two_hands_for_right_click_start_time = 0
min_secs_till_double_click = 2 
two_hands_for_double_click_start_time = 0
min_secs_till_mouse_down = 2
two_hands_for_mouse_down_start_time = 0
min_secs_till_mouse_up = 2
last_mouse_down_time = 0

keys = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", 
        "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
        "u", "v", "w", "x", "y", "z", "space", "backspace", "enter"]
curr_key_index = 0
min_secs_for_key_press = 2
min_secs_since_key_change = 2

is_cropped = False

class hand():
    def __init__(self, type):
        self.type = type

        self.index_tip_pos = None
        self.prev_index_tip_pos = None
        self.thumb_tip_pos = None
        self.middle_tip_pos = None
        self.ring_tip_pos = None
        self.pinky_tip_pos = None

        self.prev_index_on_top = False
        self.prev_pointing_right = False
        self.point_right_start_time = 0
        self.prev_pointing_left = False
        self.point_left_start_time = 0
        self.prev_index_at_bottom = False
        self.index_at_bottom_start_time = 0

        self.in_main_control= False
        self.min_secs_till_contol_loss = 1
        self.last_in_main_control_time = 0
    def is_index_on_top(self):
        if self.index_tip_pos == None:
            return False
        return (self.index_tip_pos[1] < self.thumb_tip_pos[1] and 
                self.index_tip_pos[1] < self.middle_tip_pos[1] and
                self.index_tip_pos[1] < self.ring_tip_pos[1] and
                self.index_tip_pos[1] < self.pinky_tip_pos[1])
    def is_thumb_on_top(self):
        if self.thumb_tip_pos == None:
            return False
        return (self.thumb_tip_pos[1] < self.index_tip_pos[1] and
                self.thumb_tip_pos[1] < self.middle_tip_pos[1] and
                self.thumb_tip_pos[1] < self.ring_tip_pos[1] and
                self.thumb_tip_pos[1] < self.pinky_tip_pos[1])
    def is_pointing_right(self):
        if self.index_tip_pos == None:
            return False
        is_index_right_most = (self.index_tip_pos[0] > self.thumb_tip_pos[0] and
                               self.index_tip_pos[0] > self.middle_tip_pos[0] and
                               self.index_tip_pos[0] > self.ring_tip_pos[0] and
                               self.index_tip_pos[0] > self.pinky_tip_pos[0])
        return self.is_thumb_on_top() and is_index_right_most
    def is_pointing_left(self):
        if self.index_tip_pos == None:
            return False
        is_index_left_most = (self.index_tip_pos[0] < self.thumb_tip_pos[0] and
                              self.index_tip_pos[0] < self.middle_tip_pos[0] and
                              self.index_tip_pos[0] < self.ring_tip_pos[0] and
                              self.index_tip_pos[0] < self.pinky_tip_pos[0])
        return self.is_thumb_on_top() and is_index_left_most
    def is_index_at_bottom(self):
        if self.index_tip_pos == None:
            return False
        return (self.index_tip_pos[1] > self.thumb_tip_pos[1] and 
                self.index_tip_pos[1] > self.middle_tip_pos[1] and
                self.index_tip_pos[1] > self.ring_tip_pos[1] and
                self.index_tip_pos[1] > self.pinky_tip_pos[1])
    def set_prev_attributes(self):
        self.prev_index_tip_pos = self.index_tip_pos
        self.prev_index_on_top = self.is_index_on_top()
        self.prev_pointing_right = self.is_pointing_right()
        self.prev_pointing_left = self.is_pointing_left()
        self.prev_index_at_bottom = self.is_index_at_bottom()
    def reset_tip_pos_attributes(self):
        self.index_tip_pos = None
        self.thumb_tip_pos = None
        self.middle_tip_pos = None
        self.ring_tip_pos = None
        self.pinky_tip_pos = None
    def is_showing_control_gesture(self):
        return (self.is_index_on_top() or self.is_pointing_right() or self.is_pointing_left() or
                self.is_index_at_bottom())  
    def has_lost_main_control(self):
        time_elapsed = time.time() - self.last_in_main_control_time
        if time_elapsed > self.min_secs_till_contol_loss:
            self.in_main_control = False
            return True
        return False 
    def set_in_main_control(self):
        self.in_main_control = True
        self.last_in_main_control_time = time.time() 

right_hand = hand("right")
left_hand = hand("left")   

while True:
    try:
        trackbar_pos = cv2.getTrackbarPos('Multiplier', 'Hand Inputs')
    except:
        cv2.namedWindow('Hand Inputs')
        cv2.createTrackbar('Multiplier', 'Hand Inputs', cursor_movement_multiplier, 
                           multiplier_max, update_multiplier)
        cv2.setTrackbarMin('Multiplier', 'Hand Inputs', multiplier_min)

    success, img = cap.read()
    img = cv2.flip(img, 1)
    full_img = img.copy()
    if is_cropped:
        img = img.copy()[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width]
        full_img_height, full_img_width, _ = full_img.shape
        factor = 1
        if roi_height >= roi_width:
            factor = full_img_height / roi_height
        else:
            factor = full_img_width / roi_width
        img = cv2.resize(img, (0,0), fx=factor, fy=factor)
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    main_control_hand = None
    right_hand.set_prev_attributes()
    right_hand.reset_tip_pos_attributes()
    left_hand.set_prev_attributes()
    left_hand.reset_tip_pos_attributes()

    if results.multi_hand_landmarks != None:
        hand_count = len(results.multi_hand_landmarks)
        handedness = results.multi_handedness

        for hand_index, handLms in enumerate(results.multi_hand_landmarks):
            if handedness[hand_index].ListFields()[0][1][0].label.lower() == "right":
                curr_hand = right_hand
            else:
                curr_hand = left_hand
            for id, lm in enumerate(handLms.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                if id == 4:
                    curr_hand.thumb_tip_pos = (cx, cy)
                if id == 8:
                    curr_hand.index_tip_pos = (cx, cy)
                if id == 12:
                    curr_hand.middle_tip_pos = (cx, cy)
                if id == 16:
                    curr_hand.ring_tip_pos = (cx, cy)
                if id == 20:
                    curr_hand.pinky_tip_pos = (cx, cy)

            mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS)
        
        # The order of conditial statements here is important. It prioritizes the hand that is in
        # control staying in control

        if right_hand.in_main_control and right_hand.is_showing_control_gesture():
            right_hand.set_in_main_control()
            main_control_hand = right_hand
        elif left_hand.in_main_control and left_hand.is_showing_control_gesture():
            left_hand.set_in_main_control()
            main_control_hand = left_hand
        elif right_hand.is_showing_control_gesture() and left_hand.has_lost_main_control():
            right_hand.set_in_main_control()
            main_control_hand = right_hand
        elif left_hand.is_showing_control_gesture() and right_hand.has_lost_main_control():
            left_hand.set_in_main_control()
            main_control_hand = left_hand
        else:
            right_hand.in_main_control = False
            left_hand.in_main_control = False

        if main_control_hand == None:
            time_elapsed = time.time() - last_mouse_down_time
            if is_mouse_down and time_elapsed > min_secs_till_mouse_up:
                pyttsx3.speak("Mouse Up")
                pyautogui.mouseUp()
                is_mouse_down = False

        if main_control_hand != None:
            if main_control_hand.is_index_on_top():
                radius = 10
                if is_mouse_down:
                    radius = 15
                cv2.circle(img, (main_control_hand.index_tip_pos[0], 
                                 main_control_hand.index_tip_pos[1]), radius, (255, 0, 0), 
                                 cv2.FILLED)

            if ((main_control_hand.is_pointing_right() or main_control_hand.is_pointing_left()) 
                and hand_count == 1):
                radius = 10
                if is_mouse_down:
                    radius = 15
                cv2.circle(img, (main_control_hand.index_tip_pos[0], 
                                 main_control_hand.index_tip_pos[1]), radius, (0, 160, 0), 
                                 cv2.FILLED)   

            if ((main_control_hand.is_pointing_right() or main_control_hand.is_pointing_left()) and 
                hand_count == 2):
                radius = 10
                if is_mouse_down:
                    radius = 15
                cv2.circle(img, (main_control_hand.index_tip_pos[0], 
                                 main_control_hand.index_tip_pos[1]), radius, (0, 0, 255), 
                                 cv2.FILLED) 
           
            if main_control_hand.is_index_at_bottom():
                radius = 10
                if is_mouse_down:
                    radius = 15
                cv2.circle(img, (main_control_hand.index_tip_pos[0], 
                                 main_control_hand.index_tip_pos[1]), radius, (0, 0, 0), 
                                 cv2.FILLED)                

            # Move Mouse Up
            two_hands_for_mouse_down_time_elapsed = (time.time() - 
                                                     two_hands_for_mouse_down_start_time)
            if not (hand_count == 2 and main_control_hand.is_index_on_top() and 
                    prev_hand_count == 2 and main_control_hand.prev_index_on_top and 
                    two_hands_for_mouse_down_time_elapsed > min_secs_till_mouse_down):
                time_elapsed = time.time() - last_mouse_down_time
                if is_mouse_down and time_elapsed > min_secs_till_mouse_up:
                    pyttsx3.speak("Mouse Up")
                    pyautogui.mouseUp()
                    is_mouse_down = False

            # Move Cursor
            if (hand_count == 1 and main_control_hand.is_index_on_top() and 
                main_control_hand.prev_index_tip_pos != None):
                index_tip_pos = main_control_hand.index_tip_pos
                prev_index_tip_pos = main_control_hand.prev_index_tip_pos
                x_offset = (index_tip_pos[0] - prev_index_tip_pos[0]) * cursor_movement_multiplier
                y_offset = (index_tip_pos[1] - prev_index_tip_pos[1]) * cursor_movement_multiplier
                pyautogui.move(x_offset, y_offset)
           
            # Move Cursor with Mouse Down
            elif hand_count == 2 and main_control_hand.is_index_on_top():
                time_elapsed = time.time() - two_hands_for_mouse_down_start_time
                if (prev_hand_count == 2 and main_control_hand.prev_index_on_top and 
                    time_elapsed > min_secs_till_mouse_down):
                    if not is_mouse_down:
                        pyttsx3.speak("Mouse Down")
                        pyautogui.mouseDown()
                        is_mouse_down = True
                    last_mouse_down_time = time.time()
                elif (not (prev_hand_count == 2 and main_control_hand.prev_index_on_top) and 
                      not is_mouse_down):
                    two_hands_for_mouse_down_start_time = time.time()
                if (is_mouse_down and main_control_hand.prev_index_tip_pos != None):
                    index_tip_pos = main_control_hand.index_tip_pos
                    prev_index_tip_pos = main_control_hand.prev_index_tip_pos
                    x_offset = ((index_tip_pos[0] - prev_index_tip_pos[0]) * 
                                cursor_movement_multiplier)
                    y_offset = ((index_tip_pos[1] - prev_index_tip_pos[1]) * 
                                cursor_movement_multiplier)
                    pyautogui.move(x_offset, y_offset)

            # Type Key
            elif main_control_hand.is_index_at_bottom():
                time_elapsed =  time.time() - main_control_hand.index_at_bottom_start_time
                if (main_control_hand.prev_index_at_bottom and 
                    time_elapsed > min_secs_for_key_press):
                    key = keys[curr_key_index]
                    pyttsx3.speak("Type - " + key)
                    pyautogui.press(key)
                    main_control_hand.index_at_bottom_start_time = time.time()
                elif not main_control_hand.prev_index_at_bottom:
                    main_control_hand.index_at_bottom_start_time = time.time()

            # Increase Multiplier
            elif (main_control_hand.is_pointing_right() and 
                  main_control_hand.type.lower() == "right" and hand_count == 1):
                time_elapsed =  time.time() - main_control_hand.point_right_start_time
                if (main_control_hand.prev_pointing_right and prev_hand_count == 1 and 
                    time_elapsed > min_secs_since_multiplier_change):
                    new_multiplier = cursor_movement_multiplier + 1
                    new_multiplier = max(min(new_multiplier, multiplier_max), multiplier_min)
                    pyttsx3.speak("Multiplier " + str(new_multiplier))
                    cv2.setTrackbarPos('Multiplier', 'Hand Inputs', new_multiplier)
                    main_control_hand.point_right_start_time = time.time()
                elif not (main_control_hand.prev_pointing_right and prev_hand_count == 1):
                    main_control_hand.point_right_start_time = time.time()
            
            # Decrease Multiplier
            elif (main_control_hand.is_pointing_left() and 
                  main_control_hand.type.lower() == "right" and hand_count == 1):
                time_elapsed =  time.time() - main_control_hand.point_left_start_time
                if (main_control_hand.prev_pointing_left and prev_hand_count == 1 and
                    time_elapsed > min_secs_since_multiplier_change):
                    new_multiplier = cursor_movement_multiplier - 1
                    new_multiplier = min(max(new_multiplier, multiplier_min), multiplier_max)
                    pyttsx3.speak("Multiplier " + str(new_multiplier))
                    cv2.setTrackbarPos('Multiplier', 'Hand Inputs', new_multiplier)
                    main_control_hand.point_left_start_time = time.time()
                elif not (main_control_hand.prev_pointing_left and prev_hand_count == 1):
                    main_control_hand.point_left_start_time = time.time()

            # Switch (to Next) Key (wraps around list of keys)
            elif (main_control_hand.is_pointing_right() and 
                  main_control_hand.type.lower() == "left" and hand_count == 1):
                time_elapsed =  time.time() - main_control_hand.point_right_start_time
                if (main_control_hand.prev_pointing_right and prev_hand_count == 1 and 
                    time_elapsed > min_secs_since_key_change):
                    curr_key_index = (curr_key_index + 1) % len(keys)
                    key = keys[curr_key_index]
                    pyttsx3.speak("Switch Key - " + key)
                    main_control_hand.point_right_start_time = time.time()
                elif not (main_control_hand.prev_pointing_right and prev_hand_count == 1):
                    main_control_hand.point_right_start_time = time.time()

            # Switch (to Previous) Key (wraps around list of keys)
            elif (main_control_hand.is_pointing_left() and 
                  main_control_hand.type.lower() == "left" and hand_count == 1):
                time_elapsed =  time.time() - main_control_hand.point_left_start_time
                if (main_control_hand.prev_pointing_left and prev_hand_count == 1 and
                    time_elapsed > min_secs_since_key_change):
                    curr_key_index = (curr_key_index - 1) % len(keys)
                    key = keys[curr_key_index]
                    pyttsx3.speak("Switch Key - " + key)
                    main_control_hand.point_left_start_time = time.time()
                elif not (main_control_hand.prev_pointing_left and prev_hand_count == 1):
                    main_control_hand.point_left_start_time = time.time()

            # Right Click
            elif (main_control_hand.is_pointing_right() and hand_count == 2):
                time_elapsed =  time.time() - two_hands_for_right_click_start_time
                if (main_control_hand.prev_pointing_right and prev_hand_count == 2 and 
                    time_elapsed > min_secs_till_right_click):
                    pyttsx3.speak("Right Click")
                    pyautogui.click(button="right")
                    two_hands_for_right_click_start_time = time.time()
                elif not (main_control_hand.prev_pointing_right and prev_hand_count == 2):
                    two_hands_for_right_click_start_time = time.time()

            # (Left) Click 
            elif (main_control_hand.is_pointing_left() and hand_count == 2):
                time_elapsed =  time.time() - two_hands_for_click_start_time
                if (main_control_hand.prev_pointing_left and prev_hand_count == 2 and
                    time_elapsed > min_secs_till_click):
                    pyttsx3.speak("Click")
                    pyautogui.click()
                    two_hands_for_click_start_time = time.time()
                elif not (main_control_hand.prev_pointing_left and prev_hand_count == 2):
                    two_hands_for_click_start_time = time.time()

        # Double Click
        elif hand_count == 2:
            time_elapsed = time.time() - two_hands_for_double_click_start_time
            if (prev_hand_count == 2 and prev_main_control_hand == None 
                and time_elapsed > min_secs_till_double_click):
                pyttsx3.speak("Double Click")
                pyautogui.doubleClick()
                two_hands_for_double_click_start_time = time.time()
            elif not (prev_hand_count == 2 and prev_main_control_hand == None):
                two_hands_for_double_click_start_time = time.time()

        prev_hand_count = hand_count

    else:
        prev_hand_count = 0
        last_mouse_down_time_elapsed = time.time() - last_mouse_down_time
        if is_mouse_down and last_mouse_down_time_elapsed > min_secs_till_mouse_up:
            pyttsx3.speak("Mouse Up")
            pyautogui.mouseUp()
            is_mouse_down = False

        right_hand.has_lost_main_control()
        left_hand.has_lost_main_control()

    prev_main_control_hand = main_control_hand

    currTime = time.time()
    fps = 1 / (currTime - prevTime)
    prevTime = currTime

    cv2.putText(img, str(int(fps)) + ' fps', (10, 70), cv2.FONT_HERSHEY_PLAIN, 3,
                (255, 0, 0), 3)
    key_text = keys[curr_key_index]
    cv2.putText(img, key_text, (10, 150), cv2.FONT_HERSHEY_PLAIN, 5, (0, 0, 0), 5)

    cv2.imshow("Hand Inputs", img)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if key == ord("c"):
        roi = cv2.selectROI("Hand Inputs", full_img)
        roi_x, roi_y, roi_width, roi_height = roi
        is_cropped = True

cap.release()
cv2.destroyAllWindows()