import zwoasi as asi

camera = None

def initialize():
	# Initialize the ASI camera library and confirm we have at least one ASI camera connected:
	# 
	# Note that this application will always pick the first camera - fine for me because I will only have one camera connected but could be an issue if that is not the case for you.  If you need support for more than one ASI camera, edit the code below accordingly.

	global camera

	# Hard coded library location as fallback:
	#TODO: Generalize this so that library does not need to be hard coded
	ASI_LIBRARY="/usr/local/lib/libASICamera2.so"
	asi.init(ASI_LIBRARY)

	num_cameras = asi.get_num_cameras()
	if num_cameras == 0:
		print('No cameras found')
		sys.exit(0)
	else:
		cameras_found = asi.list_cameras()
		print('Found %d cameras' % num_cameras)
		for n in range(num_cameras):
			print('    %d: %s' % (n, cameras_found[n]))
		camera_id = 0
		print('Using #%d: %s' % (camera_id, cameras_found[camera_id]))

	# Setup Camera:
	camera=asi.Camera(camera_id)
	return camera

def set_controls(gain=50, gamma=50, image_type=1, wbb=90, wbr=53, flip=0):
	global camera
	camera.set_control_value(asi.ASI_GAIN, gain)
	camera.set_control_value(asi.ASI_GAMMA, gamma)
	camera.set_control_value(asi.ASI_WB_B, wbb)
	camera.set_control_value(asi.ASI_WB_R, wbr)
	camera.set_control_value(asi.ASI_FLIP, flip)

	if image_type==0:
	    image_type=asi.ASI_IMG_RAW8
	    msg = "8-bit Mono"
	elif image_type==1:
	    image_type=asi.ASI_IMG_RGB24
	    msg = "24-bit Colour"
	elif image_type==2:
	    image_type=asi.ASI_IMG_RAW16
	    msg = "16-bit Mono"
	else:
	    print('Invalid image format specified')
	    sys.exit(1)
	camera.set_image_type(image_type)

def capture(exp=500000, filename="image.jpg"):
	
	global camera
	
	camera.set_control_value(asi.ASI_EXPOSURE, exp)

	# Stop any current exposures / video captures:
	try:
	    # Force any single exposure to be halted
	    camera.stop_video_capture()
	    camera.stop_exposure()
	except (KeyboardInterrupt, SystemExit):
	    raise
	except:
	    pass

	camera.capture(filename=filename)


	

