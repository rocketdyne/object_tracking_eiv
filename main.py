import os
import errno
import itertools
import math

import cv2
import constants


def binarize_frame(frame):
    gauss_frame = cv2.GaussianBlur(frame, (3, 3), 0.95, 0)
    hsv_frame = cv2.cvtColor(gauss_frame, cv2.COLOR_BGR2HSV)
    bin_frame = cv2.inRange(hsv_frame, constants.RED_TH_DOWN, constants.RED_TH_UP)
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

    while (capture.isOpened()):

        valid_blobs = []

        #TODO: clock for 30 fps

        retval, frame = capture.read()

        if retval == False:
            break


        bin_frame = binarize_frame(frame) #gaussian + hsv conversion + thresholding

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
                cv2.line(frame, (int(actual_marker.x_barycenter-20), int(actual_marker.y_barycenter)),
                         (int(actual_marker.x_barycenter + 20), int(actual_marker.y_barycenter)),
                         color=(0, 250, 0), thickness=2)
                cv2.line(frame, (int(actual_marker.x_barycenter), int(actual_marker.y_barycenter-20)),
                         (int(actual_marker.x_barycenter), int(actual_marker.y_barycenter + 20)),
                         color=(0, 250, 0), thickness=2)

            else:
                pass
                #TODO ...

            cv2.imshow('Test', frame)
            cv2.waitKey(1)



    capture.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':

    main('./2small.mp4')

