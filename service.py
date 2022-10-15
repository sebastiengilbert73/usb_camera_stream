# Adapted from https://github.com/EbenKouao/pi-camera-stream-flask/blob/master/main.py
import os
from flask import Flask, Response
import cv2
import xml.etree.ElementTree as ET
import ast
from datetime import datetime
import time

def ExtractConfig(filepath):
	config_dict = dict()
	tree = ET.parse(filepath)
	root_elm = tree.getroot()
	for level1_elm in root_elm:
		if level1_elm.tag == 'CameraID':
			config_dict['CameraID'] = int(level1_elm.text)
		elif level1_elm.tag == 'VideoFeedName':
			config_dict['VideoFeedName'] = level1_elm.text
		elif level1_elm.tag == 'WriteTimestamp':
			config_dict['WriteTimestamp'] = ast.literal_eval(level1_elm.text)
		elif level1_elm.tag == 'Flip':
			config_dict['Flip'] = ast.literal_eval(level1_elm.text)
		elif level1_elm.tag == 'StillImageName':
			config_dict['StillImageName'] = level1_elm.text
	return config_dict
	
def WriteTimestamp(image):
	timestamp = datetime.now().strftime("%Y-%b-%d %H:%M:%S")
	text_origin = (image.shape[1] - 400, image.shape[0] - 30)
	cv2.putText(image, timestamp, text_origin, cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255))
	
	
def ValidUSBCameraPaths(base_directory="/dev/v4l/by-id"):
	filenames = os.listdir(base_directory)#[f for f in os.listdir(base_directory) ]
	valid_camera_paths = []
	for filename in filenames:
		filepath = os.path.join(base_directory, filename)
		print(f"filepath = {filepath}")
		test_capture = cv2.VideoCapture(filepath)
		capture_is_open = test_capture.isOpened()
		print(f"capture_is_open = {capture_is_open}")
		if capture_is_open:
			valid_camera_paths.append(filepath)
			test_capture.release()
	return valid_camera_paths


app = Flask(__name__)

config = ExtractConfig("./service_config.xml")

valid_camera_paths = ValidUSBCameraPaths()
print(f"valid_camera_paths = {valid_camera_paths}")
capture = cv2.VideoCapture(valid_camera_paths[config['CameraID']])

@app.route('/')
def index():
	return f"Base service address. Append /{config['VideoFeedName']} to get the video feed"
	
def gen(vid_stream):
	while True:
		while not vid_stream.isOpened():
			vid_stream = cv2.VideoCapture(valid_camera_paths[config['CameraID']])
			time.sleep(0.1)
		ret_val, image = vid_stream.read()
		if ret_val == True:
			if config['Flip'] == True:
				image = cv2.flip(image, 0)
			if config['WriteTimestamp'] == True:
				WriteTimestamp(image)
    
			ret, jpeg = cv2.imencode('.jpg', image)
			image = jpeg.tobytes()
			yield(b'--frame\r\n'
				b'Content-Type: image/jpeg\r\n\r\n' + image + b'\r\n\r\n')
		else:
			print(f"gen(): vid_stream.read() returned ret_val = False")
		      
@app.route(f"/{config['VideoFeedName']}")
def video_feed():
	return Response(gen(capture), mimetype='multipart/x-mixed-replace; boundary=frame')
	

@app.route(f"/{config['StillImageName']}")
def still_capture():
	ret_val, image = capture.read()
	if config['Flip'] == True:
			image = cv2.flip(image, 0)
	if config['WriteTimestamp'] == True:
		WriteTimestamp(image)
	ret, png = cv2.imencode('.png', image)
	image = png.tobytes()
	return Response(image)
	

	
if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=False, port=5100)
