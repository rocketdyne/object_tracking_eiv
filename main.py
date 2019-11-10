import os
import errno
import itertools
import math
from types import SimpleNamespace

import cv2
from constants import *
import matplotlib.pyplot as plt

def binarize_frame(frame):
    gauss_frame = cv2.GaussianBlur(frame, (3, 3), 0.95, 0)
    hsv_frame = cv2.cvtColor(gauss_frame, cv2.COLOR_BGR2HSV)
    bin_frame = cv2.inRange(hsv_frame, RED_TH_DOWN, RED_TH_UP)
    return bin_frame

def find_marker(valid_blobs):

    for blob1, blob2 in itertools.combinations(valid_blobs, 2): #avoid a double for. see https://stackoverflow.com/questions/16603282/how-to-compare-each-item-in-a-list-with-the-rest-only-once

        area_ratio = blob1.area / blob2.area
        if area_ratio >= 0.8 and area_ratio <= 1.2:
            dx = blob1.x_center - blob2.x_center
            dy = blob1.y_center - blob2.y_center
            mean_width = (blob1.width + blob2.width)/2
            dist_widths_ratio = (math.sqrt((dx*dx + dy*dy))) / mean_width

            if (dist_widths_ratio >= 0.2 and dist_widths_ratio <= 0.6): # 0.4375 is the value of the real marker
                marker_x_barycenter = (blob1.x_center + blob2.x_center) / 2
                marker_y_barycenter = (blob1.y_center + blob2.y_center) / 2
                actual_marker = Marker(blob1.width, blob2.width, mean_width, marker_x_barycenter, marker_y_barycenter)

                return actual_marker
    return None

def draw_cross(frame, actual_marker):

    cv2.line(frame, (int(actual_marker.x_barycenter - 20), int(actual_marker.y_barycenter)),
             (int(actual_marker.x_barycenter + 20), int(actual_marker.y_barycenter)),
             color=(0, 250, 0), thickness=2)
    cv2.line(frame, (int(actual_marker.x_barycenter), int(actual_marker.y_barycenter - 20)),
             (int(actual_marker.x_barycenter), int(actual_marker.y_barycenter + 20)),
             color=(0, 250, 0), thickness=2)


def showinfo(frame, info_type, mean_speed_data=None, direction=None):

    assert isinstance(info_type, str), "info_type parameter is not a string"

    if info_type == 'NOTARGET':
        cv2.putText(frame, 'N0 TARGET', (int(HEIGHT * 0.05), int(WIDTH*0.55)), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 255), lineType=cv2.LINE_AA)

    if info_type == 'TARGET_AQ':

        if direction is not None:
            direction_string = 'DIRECTION: ' + direction
        else:
            direction_string = 'DIRECTION: -----'

        if mean_speed_data.mean_px_speed != -1: #also mean_kmh_speed will be != -1
            speed_string = 'SPEED: {:5.2f} (pixel/s); {:5.2f} (km/h)'\
                               .format(mean_speed_data.mean_px_speed, mean_speed_data.mean_kmh_speed)
            print (speed_string)
        else:
            speed_string = 'SPEED (): ----- (pixel/s); ----- (km/h)'


        cv2.putText(frame, 'TARGET ACQUIRED', (int(HEIGHT * 0.05), int(WIDTH*0.55)), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), lineType=cv2.LINE_AA)
        cv2.putText(frame, direction_string, (int(HEIGHT * 0.45), int(WIDTH * 0.55)), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), lineType=cv2.LINE_AA)
        cv2.putText(frame, speed_string, (int(HEIGHT * 0.95), int(WIDTH * 0.55)), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), lineType=cv2.LINE_AA)







def get_instant_px_speed(actual_marker, previous_marker):

    if actual_marker is not None and previous_marker is not None:
        dx = actual_marker.x_barycenter - previous_marker.x_barycenter
        dy = actual_marker.y_barycenter - previous_marker.y_barycenter

        bar_distance = math.sqrt( (dx*dx + dy*dy) )

        inst_px_speed = bar_distance * 30 #because the acquisition is @30FPS. See main document

        return inst_px_speed
    else:
        return None

def get_instant_kmh_speed(inst_px_speed, actual_marker):

    if inst_px_speed is not None:
        inst_ms_speed = inst_px_speed * (60 / (actual_marker.mean_width*100)) #meters per second speed. 60cm is the base width of the marker in reality. See main document
        inst_kmh_speed = (inst_ms_speed * 3600) / 1000
        return inst_kmh_speed
    else:
        return None

def get_direction(actual_marker, previous_marker):

    if actual_marker is not None and previous_marker is not None:

        dx = actual_marker.x_barycenter - previous_marker.x_barycenter
        dy = actual_marker.y_barycenter - previous_marker.y_barycenter
        bar_distance = math.sqrt( (dx*dx + dy*dy) )

        if dx == 0 or bar_distance == 0:
            return '-----'
        else:
            ang_coeff = dy / dx

        ratio = actual_marker.mean_width / bar_distance



        if bar_distance > 0:
            if ratio < 16: #is 4 kmh in all videos. If the speed is not at least 4km/h no motion is assumed.

                if dx < 0 and ang_coeff >= -1 and ang_coeff <= 1:
                    return 'WEST'
                if dx < 0 and ang_coeff > 1:
                    return 'NORTH-WEST'
                if dx == 0 and dy < 0:
                    return 'NORTH'
                if dx > 0 and ang_coeff < -1:
                    return 'NORTH-EAST'
                if dx > 0 and ang_coeff >= -1 and ang_coeff <= 1:
                    return 'EAST'
                if dx > 0 and ang_coeff > 1:
                    return 'SOUTH-EAST'
                if dx == 0 and dy > 0:
                    return 'SOUTH'
                if dx < 0 and ang_coeff < -1:
                    return 'SOUTH-WEST'
    else:
        return '-----'

def get_mean_speeds(inst_px_speed, inst_kmh_speed, mean_speed_data:SimpleNamespace, previous_marker):

    if type(inst_px_speed) is type(inst_kmh_speed): #both None or both Float. Something weird otherwise

        #mean_speed_data.mean_kmh_speed = -1
        #mean_speed_data.mean_px_speed = -1

        if inst_px_speed is not None: #and inst_kmh_speed is not None:
            mean_speed_data.sum_px_speed += inst_px_speed
            mean_speed_data.sum_kmh_speed += inst_kmh_speed
            mean_speed_data.frame_count += 1

        if mean_speed_data.frame_count == 14:
            mean_speed_data.mean_px_speed = mean_speed_data.sum_px_speed/(mean_speed_data.frame_count+1)
            mean_speed_data.mean_kmh_speed = mean_speed_data.sum_kmh_speed / (mean_speed_data.frame_count + 1)

            mean_speed_data.frame_count = 0
            mean_speed_data.sum_px_speed = inst_px_speed
            mean_speed_data.sum_kmh_speed = inst_kmh_speed

        if previous_marker is None: #useful when the marker exits and re-enters
            mean_speed_data.frame_count = -1
            mean_speed_data.sum_px_speed = 0
            mean_speed_data.sum_kmh_speed = 0

    else:
        raise TypeError("isnt_px_speed is {} while inst_kmh_speed is {}. They must be of the same type!"
                        .format(type(inst_px_speed), type(inst_kmh_speed)))

    return mean_speed_data






class Marker(object):
    def __init__(self, width_box_1, width_box_2, mean_width, x_barycenter, y_baricenter):
        self.width_box_1 = width_box_1 #width of the first red box that constitute the marker
        self.width_box_2 = width_box_2 #width of the second red box that constitute the marker
        self.mean_width = mean_width #arith. mean of width_box_1 and width box 2
        self.x_barycenter = x_barycenter #x coordinate of the whole marker
        self.y_barycenter = y_baricenter #y coordinate of the whole marker

class Blob(object):
    def __init__(self, area=0, width=0, height=0, x_center=0, y_center=0):
        self.area = area
        self.width = width
        self.height = height
        self.x_center = x_center
        self.y_center = y_center



def main (videopath):



    if not os.path.isfile(videopath):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), videopath)

    capture = cv2.VideoCapture(videopath)

    #INITIALIZATION

    # they will be Marker objects
    actual_marker = None
    previous_marker = None

    # only avg speed will be displayed, every 15 consecutive frames, counted by frame_count_mean
    mean_speed_data = SimpleNamespace(mean_px_speed=-1, mean_kmh_speed=-1, frame_count=-1,
                                      sum_px_speed=0, sum_kmh_speed=0)  # used to calculate mean values

    while (capture.isOpened()):

        valid_blobs = []

        #TODO: clock for 30 fps

        retval, frame = capture.read()

        if retval == False:
            break

        bin_frame = binarize_frame(frame) #gaussian + hsv conversion + thresholding

        plt.imshow(bin_frame, cmap='gray')

        _, contours, hierarchy = cv2.findContours(bin_frame, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE, offset=(0,0))

        #DEBUG:
        #cv2.drawContours(frame, contours, -1, (0, 255, 0), 3)
        #cv2.imshow('Contours', frame)


        for contour in contours:
            box = cv2.minAreaRect(contour) #in C a cvbox2d struct is returned. Here a tuple with 3 elements, the first is the center (x, y), the secons is (W, H), the third is the angle https://stackoverflow.com/questions/11779100/python-opencv-box2d
            area=box[1][0]*box[1][1]

            if area > 80: #only if the area is > 80 the box will be analyzed by find_marker
                valid_blobs.append(Blob(area=area, width=box[1][0], height=box[1][1],
                                        x_center=box[0][0], y_center=box[0][1]))

        actual_marker = find_marker(valid_blobs)


        if actual_marker is not None:

            #draw a cross in the center of the marker
            draw_cross(frame, actual_marker)

            inst_px_speed = get_instant_px_speed(actual_marker, previous_marker)
            inst_kmh_speed = get_instant_kmh_speed(inst_px_speed, actual_marker)

            direction = get_direction(actual_marker, previous_marker)
            mean_speed_data = get_mean_speeds(inst_px_speed, inst_kmh_speed, mean_speed_data, previous_marker)

            print(mean_speed_data.mean_kmh_speed)

            showinfo(frame, 'TARGET_AQ', mean_speed_data, direction)
        else:
            print('Not found')
            showinfo(frame, 'NOTARGET')

        cv2.waitKey(30)
        cv2.imshow('Test', frame)


        #update marker
        previous_marker=actual_marker

    capture.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':

    main('./11small.mp4')

    #TODO: launch/input management
    #TODO: play at 30fps


