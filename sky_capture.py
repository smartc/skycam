import sunpos
import skycam
from clean_folders import *
from pushover import sendPushoverAlert
import pause, pytz, os, sys, glob, json
from datetime import datetime, timedelta
from math import ceil, log10
from collections import OrderedDict
from startrailer import star_trails

# Declare some global variables:
# Variables to be loaded from settings file:
LOCALTZ = None
BASEDIR = None
LATITUDE = None
LONGITUDE = None
EXPOSURE_TIME = None
GAIN = None
GAMMA = None
WAIT_BETWEEN = None
PHASE = None
FILE_EXT = None
CAMERA = None
CREATE_TIMELAPSE = False
TIMELAPSE_FPS = 25
CREATE_STARTRAILS = False
REMOTE_SERVER = None
REMOTE_PATH = None
REMOTE_COMMAND = None
USE_PUSHOVER = None
CLEAN_UP = True
DAYS_TO_KEEP = 3

# Fixed variables:
UTC = pytz.timezone('UTC')
SUNSET = 0
CIVIL = 1
NAUTICAL = 2
ASTRO = 3

def main():
	global LOCALTZ, BASEDIR, LATITUDE, LONGITUDE, EXPOSURE_TIME, GAIN, GAMMA, WAIT_BETWEEN, PHASE, FILE_EXT
	global CREATE_TIMELAPSE, TIMELAPSE_FPS,CREATE_STARTRAILS, REMOTE_SERVER, REMOTE_PATH, REMOTE_COMMAND, USE_PUSHOVER
	global CLEAN_UP, DAYS_TO_KEEP

	load_settings()

	while True:
		NIGHTDIR = start_capture()
		[target_dir, padding] = sort_files(NIGHTDIR)
		night_path = os.path.basename(os.path.normpath(NIGHTDIR))
		
		# If no remote server is set, then generate the timelapse on local machine and leave it here
		if REMOTE_SERVER is None and CREATE_TIMELAPSE:				
			timelapse = generate_timelapse(target_dir, TIMELAPSE_FPS)

		# If remote server is set and we have no remote command, upload all files after generating timelapse (if we want one)
		elif REMOTE_COMMAND is None:								
			if CREATE_TIMELAPSE: timelapse = generate_timelapse(target_dir, TIMELAPSE_FPS)
			os.system("rsync -aq " + NIGHTDIR + "/* " + REMOTE_SERVER + ":" + REMOTE_PATH + "/" + night_path)

		# If remote server is set and we have a remote command, upload to server and generate timelapse on remote machine (if we want one)	
		else:														
			os.system("rsync -aq " + NIGHTDIR + "/* " + REMOTE_SERVER + ":" + REMOTE_PATH + "/" + night_path)
			command = "ssh " + REMOTE_SERVER + " '" + REMOTE_COMMAND + " " + REMOTE_PATH + "/" + night_path +"' " + TIMELAPSE_FPS
			if CREATE_TIMELAPSE: os.system(command)
		

		# Generate Star Trail image if desired and sync to remote server:
		file_pattern = ""
		if CREATE_STARTRAILS:
			for i in range(padding):
				file_pattern = file_pattern + "[0-9]"
			file_pattern = file_pattern + ".jpg"
			star_trails_file = "star_trails_" + night_path + ".jpg"

			star_trails(NIGHTDIR, star_trails_file, "jpg", file_pattern)
			if not REMOTE_SERVER is None:
				os.system("rsync -aq " + NIGHTDIR + "/" + star_trails_file + " " + REMOTE_SERVER + ":" + REMOTE_PATH + "/" + night_path)

		if USE_PUSHOVER:
			title = "SkyCam Sequence Complete"
			message = "Image capture is complete for " + night_path + " at " + datetime.now().strftime("%H:%M %d-%b-%Y")
			if REMOTE_SERVER: message = message + "\nFiles have been uploaded to:" + REMOTE_SERVER + ":" + REMOTE_PATH + "/" + night_path
			sendPushoverAlert(title, message)


		# Purge subfolders older than specified numbers of days:
		if CLEAN_UP:
			logdiv("=")
			logmsg("Purging folders older than " + str(DAYS_TO_KEEP) + " days.")
			purgeFolders(BASEDIR, DAYS_TO_KEEP)


		# Pause for a while before starting another loop.
		# Workaround for issue with sunrise / sunset calculation in sunpos that causes repeated loops if calculation is run before sunrise
		next_sunset = LOCALTZ.localize(sunpos.next_sunset(LATITUDE, LONGITUDE))
		logdiv("-")
		logmsg("Run complete. Next sunset is at: " + str_local(next_sunset))
		logmsg("Next run will set up at: " + str_local(next_sunset - timedelta(minutes=30)))
		logdiv("-")
		pause.until(next_sunset - timedelta(minutes=30))

def load_settings():
	global LOCALTZ, BASEDIR, LATITUDE, LONGITUDE, EXPOSURE_TIME, GAIN, GAMMA, WAIT_BETWEEN, PHASE, FILE_EXT
	global CREATE_TIMELAPSE, TIMELAPSE_FPS, CREATE_STARTRAILS, REMOTE_SERVER, REMOTE_PATH, REMOTE_COMMAND, USE_PUSHOVER
	global CLEAN_UP, DAYS_TO_KEEP

	this_folder = os.path.abspath(os.path.dirname(__file__))
	with open(this_folder + '/' + 'settings.json', 'r') as f:
		data = json.load(f)

	LOCALTZ = pytz.timezone(data['local_timezone'])
	BASEDIR = data['image_folder'] + '/'
	LATITUDE = data['latitude']
	LONGITUDE = data['longitude']
	EXPOSURE_TIME = data['exposure']
	GAIN = data['camera_gain']
	GAMMA = data['image_gamma']
	WAIT_BETWEEN = data['interval']
	PHASE = data['twilight_phase']
	FILE_EXT = data['file_type']
	CREATE_TIMELAPSE = data['create_timelapse']
	TIMELAPSE_FPS = data['timelapse_fps']
	CREATE_STARTRAILS = data['create_startrails']
	REMOTE_SERVER = data['upload_server']
	REMOTE_PATH = data['upload_path']
	REMOTE_COMMAND = data['remote_command']
	USE_PUSHOVER = data['use_pushover']
	CLEAN_UP = data['clean_up_folders']
	DAYS_TO_KEEP = data['days_to_keep']


def str_utc(time):
	if time.tzinfo is None:
		time = LOCALTZ.localize(time)
	return time.astimezone(UTC).strftime("%d-%b-%Y %H:%M:%S %Z")

def str_local(time):
	if time.tzinfo is None:
		time = LOCALTZ.localize(time)
	return time.astimezone(LOCALTZ).strftime("%d-%b-%Y %H:%M:%S %Z")

def name_utc(time):
	if time.tzinfo is None:
		time = LOCALTZ.localize(time)
	return time.astimezone(UTC).strftime("%Y%m%d_%H%M%S")

def name_local(time):
	if time.tzinfo is None:
		time = LOCALTZ.localize(time)
	return time.astimezone(LOCALTZ).strftime("%Y%m%d_%H%M%S")

def start_capture(PHASE=NAUTICAL):
	# Make a note in the log that we're starting a new run:
	logdiv("=")
	logmsg("Starting new image run at: " + str_local(datetime.now()))	

	# Declare global variables
	global WAIT_BETWEEN, EXPOSURE_TIME, GAIN, GAMMA, LATITUDE, LONGITUDE, CAMERA, USE_PUSHOVER

	# Define a few key variables
	[ START_TIME, END_TIME ] = sunpos.twilight_time(PHASE, LATITUDE, LONGITUDE, datetime.utcnow())		# When to start and finish taking images
	
	while START_TIME is None:									# If sun is always up, fallback one twilight phase
		logmsg("Selected twilight phase does not occur for this location / date.  Falling back to earlier twilight.")
		PHASE = PHASE - 1
		if PHASE < 0:
			logdiv('*')
			logmsg('ERROR: sun always above horizon - cannot set start time.  Exiting')
			logdiv('*')
			raise RuntimeError('Error: sun always above horizon - cannot set start time.')
		[ START_TIME, END_TIME ] = sunpos.twilight_time(PHASE, LATITUDE, LONGITUDE, datetime.utcnow())
	
	duration = END_TIME - START_TIME
	duration_hours = duration.seconds // 3600
	duration_minutes = duration.seconds // 60 % 60

	# WAIT_BETWEEN = 0.1											# Seconds to wait between images
	# EXPOSURE_TIME = 30											# Exposure time in seconds
	# GAIN = 200													# Camera gain setting
	# GAMMA = 50													# Image gamma

	TONIGHT = START_TIME.strftime("%Y%m%d")						# Tonight's date
	NIGHTDIR = BASEDIR + TONIGHT + "/"							# Base directory for images 
	if not os.path.exists(NIGHTDIR):							# Make sure the directory exists, otherwise create it
		os.makedirs(NIGHTDIR)
	LOGFILE = NIGHTDIR + "capture_log_" + TONIGHT + ".log"		# Set up the logging for tonight

	logmsg("Capturing images to folder: " + NIGHTDIR)
	
	# Initialize the camera:
	if CAMERA is None:
		CAMERA = skycam.initialize()
	skycam.set_controls(GAIN, GAMMA)

	# Wait until start of twilight and then start capturing images:
	logdiv("-",LOGFILE)
	logmsg("Exposure = " + str(EXPOSURE_TIME) + " | Gain = " + str(GAIN) + " | Gamma = " + str(GAMMA), LOGFILE)
	logmsg("Current time is     :  " + str_local(datetime.now()), LOGFILE)
	logmsg("Waiting until       :  " + str_local(START_TIME), LOGFILE)
	logmsg("Imaging will end at :  " + str_local(END_TIME), LOGFILE)
	logmsg("Total Duration is   :  " + str(duration_hours) + " hours " + str(duration_minutes) + " minutes", LOGFILE)
	logdiv("-",LOGFILE)

	if USE_PUSHOVER:
		title = "Ready For Next Sequence"
		message = "SkyCam is online and will begin capture at " + START_TIME.strftime("%H:%M %d-%b-%Y")
		sendPushoverAlert(title, message)

	pause.until(START_TIME)						
	
	if USE_PUSHOVER:
		title = "Starting Image Acquisition"
		message = "SkyCam is capturing images.\n\nImage capture will finish at " + END_TIME.strftime("%H:%M %d-%b-%Y")
		sendPushoverAlert(title, message)
	
	while datetime.now() < END_TIME:
		now = datetime.now()
		filename = name_local(now) + FILE_EXT
		skycam.capture(long(EXPOSURE_TIME * 1e6), NIGHTDIR + filename) 
		logmsg("Captured image: " + filename, LOGFILE)
		pause.seconds(WAIT_BETWEEN)

	logmsg("Finished capturing images", LOGFILE)
	logdiv("-",LOGFILE)
	LOGFILE = None

	data = OrderedDict( [
		   	( "start", START_TIME ),
			( "finish", END_TIME ),
			( "exposure", EXPOSURE_TIME),
			( "gain", GAIN ),
			( "gamma", GAMMA ),
			( "interval", WAIT_BETWEEN ),
			( "latitude", LATITUDE ),
			( "longitude", LONGITUDE ),
			( "create_timelapse", CREATE_TIMELAPSE),
			( "create_startrails", CREATE_STARTRAILS),
			( "upload_server", REMOTE_SERVER),
			( "upload_path", REMOTE_PATH),
			( "remote_command", REMOTE_COMMAND),
			( "clean_up_folders", CLEAN_UP),
			( "days_to_keep", DAYS_TO_KEEP)  ],)
	store_data(data, "capture_settings.json", NIGHTDIR)

	return NIGHTDIR

def logmsg(message, filename=None):
	if filename is None:
		filename = BASEDIR + "skycam.log"
	if os.path.isfile(filename):
		f = open(filename, 'a')
	else:
		f = open(filename, 'w')
	print message
	f.write( message + "\n")
	f.close()

def logdiv(char="-", log=None, N=70):
	line = ''
	for n in range(N):
		line = line + char
	logmsg(line,log)

def sort_files(target_dir):
	# Sorts files by timestamp.  Oldest to newest.
	#
	# Files will be renamed to format '0001.jpg', '0002.jpg', etc.
	global FILE_EXT

	MIN_PADDING = 4										# Minimum number of characters in file name
	starting_dir = os.getcwd()							# Make a note of where we started, so we can get back
	os.chdir(target_dir)								# Change to the target directory

	LOGFILE = glob.glob("capture_log_*.log")[0]			# Get the name of the nightly log file so we can append to it

	files = glob.glob('*' + FILE_EXT)					# Get a list of image files
	files.sort(key=lambda x: os.path.getmtime(x))		# Sort them by timestamp
	filecount = len(files)								# Find out how many files we have

	N = int(ceil(log10(filecount)))						# How many zeros do we need to pad out the number of files we have?
	padding = max(MIN_PADDING, N)						# Make sure we have enough padding to accomodate
	n = 1

	logmsg('Sorting and renaming files based on file timestamp', LOGFILE)
	logdiv("-",LOGFILE)
	for oldname in files:
		newname = ('{:0' + str(padding) + 'd}').format(n) + FILE_EXT
		os.rename(oldname, newname)
		logmsg(oldname + "   ---->   " + newname, LOGFILE)
		n += 1
	logdiv("-",LOGFILE)
	logmsg('Done renaming files', LOGFILE)
	logdiv("-",LOGFILE)
	
	# Store some data about the files we just saved:
	data = { "image_count": filecount, 
			 "padding": padding }
	store_data(data, "file_info.json", target_dir)
	
	os.chdir(starting_dir)
	
	return target_dir, padding

def generate_timelapse(target_dir, rate=TIMELAPSE_FPS, extension=FILE_EXT ):

	starting_dir = os.getcwd()
	os.chdir(target_dir)								# Switch to the target directory
	LOGFILE = glob.glob("capture_log_*.log")[0]			# Get the name of the nightly log file so we can append to it

	data = read_data('file_info.json', target_dir)
	padding = data['padding']

	logdiv("-",LOGFILE)
	logmsg("Starting timelapse    : " + target_dir, LOGFILE)
	
	
	i = ' -i ' + "%0" + str(padding) + "d" + extension
	r = ' -r ' + str(rate)
	f = ' -s hd1080 -vf format=rgb24 -vcodec h264'
	o = ' timelapse.mp4'
	cmd = 'ffmpeg' + r + i + f + o
	logmsg("Running system command: " + cmd, LOGFILE)
	
	if os.path.exists(o.strip()):
		logmsg("** Removing existing file: " + o.strip(), LOGFILE)
		os.remove(o.strip())
	os.system(cmd)
	logmsg("Timelapse generation complete", LOGFILE)
	logdiv("-",LOGFILE)
	
	logmsg("Timelapse generation complete: " + target_dir + o.strip())
	
	os.chdir(starting_dir)
	return o.strip()

def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")

def store_data(data, filename="data.json", target_dir = None):
	# Stores variables in a json encoded file.
	#
	# 'data'	=	Dictionary containing variables to be stored, 'key' = variable name
	if target_dir is None:
			target_dir = os.getcwd() + "/"
	datafile = target_dir + filename
	logdiv()
	logmsg("Storing data to file: " + datafile)
	logdiv()
	f = open(datafile, 'w')
	json.dump(OrderedDict(data), f, indent=4, default=datetime_handler)
	f.close()	
	
def read_data(filename="data.json", target_dir = None):
	# Reads variables in a json encoded file and returns a data dictionary.
	if target_dir is None:
		target_dir = os.getcwd() + "/"
	datafile = target_dir + filename
	f = open(datafile, 'r')
	data = json.load(f)
	f.close()
	return data


if __name__ == "__main__":
	main()
	
