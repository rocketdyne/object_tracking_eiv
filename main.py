import os
import errno

import cv2

def main (videopath):

    if not os.path.isfile(videopath):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), videopath)

    capture = cv2.VideoCapture(videopath)

    while (capture.isOpened()):
        retval, frame = capture.read()

        if retval == False:
            break


    capture.release()
    cv2.destroyAllWindows()

