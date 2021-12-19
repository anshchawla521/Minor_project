import pickle
import os
from PIL.Image import new
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request

import io
import cv2
from matplotlib import pyplot as plt
import numpy as np
import imutils
import easyocr
from sqlalchemy.sql.functions import user
import user_website
import SMS

from threading import Thread


 



scopes = ['https://www.googleapis.com/auth/drive']
#text_id = '1M1_8Zl8C4s6Yo9LVnPIvO1ZAOpfqYa9H'


def calculate_bill(old_reading: int, new_reading: int) -> int:
    '''This function calculates the bill according to the guide lines of PSPCL

    Paramters :
        old and new kilo watt hour reading

    Returns :
        the bill amount

    '''
    connected_load = 5000

    meter_mul = 1.0
    line_ct = 100/5
    meter_ct = 50/5

    overall_mul = meter_mul*line_ct/meter_ct

    unit_consumed = overall_mul*(new_reading - old_reading)

    # fixed charges calculation
    fcharge_per_kw = 35
    days_per_cycle = 30
    fix_charges = (connected_load/1000)*0.8 * \
        days_per_cycle*fcharge_per_kw*12/365

    # variable charges
    var_charge = 0
    rate_units_less_than_100 = 4.49  # rate for units less than 100
    rate_units_less_than_300 = 6.34  # rate for units less than 100
    rate_above_300 = 7.3
    if unit_consumed <= 100:
        var_charge += unit_consumed*rate_units_less_than_100
    elif unit_consumed <= 300:
        var_charge += 100*rate_units_less_than_100
        var_charge += (unit_consumed - 100)*rate_units_less_than_100
    else:
        var_charge += 100*rate_units_less_than_100
        var_charge += 200*rate_units_less_than_300
        var_charge += (unit_consumed - 300)*rate_above_300

    rent = 20  # meter rent

    # other dependent charges
    electricity_duty = (fix_charges + var_charge + rent)*0.15
    idf = (fix_charges + var_charge + rent)*0.05
    MC_tax = (fix_charges + var_charge + rent)*0.02
    cow_cess = unit_consumed*0.02

    total = fix_charges + var_charge + rent + \
        electricity_duty + idf + MC_tax + cow_cess

    surcharge = 1.02*total

    print("Bill value if paid in time")
    print(total)
    print("Bill value after surcharge")
    print(surcharge)
    return round(total , 2)


def get_image(client_secret_file, api_name, api_version, text_file_id, *scopes):
    '''This function downloads the image from the google drive
       and also sets up the drive accesss

    Paramters :
        client_secret_file
        api_name
        api_version
        scopes
        text_file_id   

    Returns :
        a downloaded image in images folder ith name ESP.JPG

    '''
    #print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    print(SCOPES)

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME, 'service created successfully')

    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None

    request = service.files().get_media(fileId=text_file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fd=fh, request=request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print('Downloading ID of image {0}'.format(status.progress()*100))

    fh.seek(0)
    # print("this is the data " + str(fh.read()))
    fh = str(fh.read())
    fh = fh[2:fh.__len__()-1]  # string slicing
    # print(fh)
    file_id = fh
    file_name = 'ESP.JPG'
    request = service.files().get_media(fileId=file_id)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fd=fh, request=request)

    done = False

    while not done:
        status, done = downloader.next_chunk()
        print('Downloading image {0}'.format(status.progress()*100))

    fh.seek(0)
    with open(os.path.join('./images', file_name), 'wb') as f:
        f.write(fh.read())
        f.close()
    return service


# def image_detection():
#     '''This function takes the image in the images folder amd then applies counter detection and returns the cropped image

#         Paramters :
#             none

#         Returns :
#             cv2 image object which has the 
#             cropped image

#     '''
#     img = cv2.imread('images/ESP.JPG')
#     img = cv2.rotate(img, cv2.ROTATE_180)
#     # cv2.imshow('Captured image', img) # show the captured image
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     #gray = cv2.GaussianBlur(gray , (3,3), cv2.BORDER_DEFAULT)
#     cv2.imshow('GrayScale image', gray)  # show the grayscale version of image
#     bfilter = cv2.bilateralFilter(gray, 11, 17, 17)
#     edged = cv2.Canny(bfilter, 125, 175)
#     edged = cv2.dilate(edged, (3, 3), iterations=2)
#     edged = cv2.erode(edged, (3, 3), iterations=2)
#     cv2.imshow('Filtered Image', edged)
#     # image gray conversion and filtering

#     keypoints = cv2.findContours(
#         edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
#     contours = imutils.grab_contours(keypoints)
#     contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

#     location = None
#     contour_found = False
#     cropped_image = img
#     for contour in contours:
#         # can be set higher for more rougher approximation
#         approx = cv2.approxPolyDP(contour, 10, True)
#         if len(approx) == 4:
#             location = approx
#             contour_found = True
#             break
#     if contour_found:
#         mask = np.zeros(gray.shape, np.uint8)
#         new_image = cv2.drawContours(mask, [location], 0, 255, -1)
#         new_image = cv2.bitwise_and(img, img, mask=mask)
#         (x, y) = np.where(mask == 255)
#         (x1, y1) = (np.min(x), np.min(y))
#         (x2, y2) = (np.max(x), np.max(y))
#         cropped_image = gray[x1:x2+1, y1:y2+1]
#         cv2.imshow('Cropped Image', new_image)

#         res = cv2.rectangle(img, tuple(location[0][0]), tuple(
#             location[2][0]), (0, 255, 0), 3)  # BGR
#         cv2.imshow('Result', res)
#         cv2.imwrite('images/result.jpg', res)  # save the captured image
#         cv2.waitKey(0)  # the code wont move forward until windows closed
#     else:
#         print('no contour found')
#     return cropped_image


def number_detection():
    ''' return the current reading of meter that needs to be collected 
    the image for the user whose reading is to be found will be in the images folder by the name of ESP.jpg'''

    return 100


# def myfunc():
    
#     user_website.db.session.query(user_website.views.User).get(user_website.views.current_user.id).amount = 87
#     while True:
#         pass
        
if __name__ == '__main__':
    # thread = Thread(target = myfunc)
    # thread.start()
    # thread.run()

    # open database for every user get esp id , fetch umage , update amount
    app = user_website.create_app()
    with app.app_context():
        for user in user_website.db.session.query(user_website.views.User).all():
            text_id = user.text_id        
            get_image('credentials.json', 'drive', 'v3', text_id, scopes)
            #user.last_reading  = user.current_reading execute this on payment in future
            user.current_reading = int(number_detection())
            user.amount = calculate_bill(user.last_reading , user.current_reading)

            SMS.send_sms(user.amount , user.Phone_number , user.first_name)
        user_website.db.session.commit()


    app.run(debug=True)