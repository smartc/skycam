import ephem,json
from math import pi
from datetime import datetime
import pytz

# Define twilight angles:
SUNSET=0
CIVIL=-6
NAUTICAL=-12
ASTRO=-18
TWILIGHT = [SUNSET, CIVIL, NAUTICAL, ASTRO]


# Default values for latitude and longitude
with open('settings.json', 'r') as f:
	data = json.load(f)
LAT=data['latitude']
LON=data['longitude']


def sun_angle(lat=LAT,lon=LON):
	o = ephem.Observer()
	o.lat = lat*pi/180
	o.long = lon*pi/180
	o.date = ephem.now()
	s=ephem.Sun()
	s.compute(o)
	angle=s.alt*180/pi
	return angle


def twilight_phase(lat=LAT, lon=LON):
	# Start by converting coordiantes to radian for calculations:
	lat = lat*pi/180
	lon = lon*pi/180

	# Calculate sun angle and determine what phase of the day we are in:
	alt=sun_angle(lat,lon)
	if alt >= SUNSET:
		return 0  			# "DAY"
	if alt < 0 & alt >= CIVIL:
		return 1  			# "CIVIL"
	if alt < CIVIL & alt >= NAUTICAL:
		return 2			# "NAUTICAL"
	if alt < NAUTICAL & alt >= ASTRO:
		return 3			# "ASTRONOMICAL"
	if alt < ASTRO:
		return 4			# "NIGHT"


def twilight_time(twilight=0,lat=LAT,lon=LON,date=datetime.utcnow(),clean_seconds=True):
	# Returns twilight start and end time for tonight.
	# 
	# Arguments are:
	#	twilight 	0 - Sunset
	#			1 - Civil twilight
	#			2 - Nautical twilight
	#			3 - Astronomical twilight
	#	lat		Latitude in degrees, +ve values are North of equator
	#	lon		Longitude in degrees, +ve values are East of the prime meridian
	#	date		Today's date - must be TZ aware. If not, we assume UTC.
	#	clean_seconds	I hate seeing fractional seconds in my results so I'll round off by default.  Set this to False if you want different behaviour.

	# Start by converting coordiantes to radian for calculations
	lat = lat*pi/180
	lon = lon*pi/180

	# Check whether date provided is TZ aware. If yes and not in UTC, then convert to UTC.
	# try:
	isAware = (date.tzinfo is not None)
	isUTC = date.tzinfo == pytz.timezone('UTC')
	if isAware and not isUTC:
		print "Date provided is not UTC time, converting to UTC."
		date = date.astimezone(pytz.timezone('UTC'))
	elif not isAware:
		print "Warning - date provided is not UTC aware.  Calculations will assume UTC."
	# except:
	# 	pass

	# Set up our observer location and sun object
	sun = ephem.Sun()
	o = ephem.Observer()
	o.lat = lat
	o.lon = lon
	o.date = date
	o.horizon = TWILIGHT[twilight]*pi/180

	# And now calculate the start and end of  twilight (or sunset/sunrise):
	try:
		start = o.next_setting(sun)
		end = o.next_rising(sun)

		if start > end:	# This means we're running at night and the sun has already set.  In this case we will switch to the previous setting.
			start = o.previous_setting(sun)

		# Convert to local time:
		start = ephem.localtime(start)
		end = ephem.localtime(end)

		# Cleanup Seconds so that we don't have fractional results
		if clean_seconds:
			start = datetime(start.year, start.month, start.day, start.hour, start.minute, start.second)
			end = datetime(end.year, end.month, end.day, end.hour, end.minute, end.second)

	
	except ephem.AlwaysUpError:
		start = None
		end = None
	except:
		raise

	# Finally, return the values but in local time:
	return [start, end]

def next_sunset(lat=LAT,lon=LON,date=datetime.utcnow(),clean_seconds=True):
	# Returns twilight start and end time for tonight.
	# 
	# Arguments are:
	#	twilight 	0 - Sunset
	#			1 - Civil twilight
	#			2 - Nautical twilight
	#			3 - Astronomical twilight
	#	lat		Latitude in degrees, +ve values are North of equator
	#	lon		Longitude in degrees, +ve values are East of the prime meridian
	#	date		Today's date - must be TZ aware. If not, we assume UTC.
	#	clean_seconds	I hate seeing fractional seconds in my results so I'll round off by default.  Set this to False if you want different behaviour.

	# Start by converting coordiantes to radian for calculations
	lat = lat*pi/180
	lon = lon*pi/180

	# Check whether date provided is TZ aware. If yes and not in UTC, then convert to UTC.
	# try:
	isAware = date.tzinfo is not None
	isUTC = date.tzinfo == pytz.timezone('UTC')
	if isAware and not isUTC:
		print "Date provided is not UTC time, converting to UTC."
		date = date.astimezone(pytz.timezone('UTC'))
	elif not isAware:
		print "Warning - date provided is not UTC aware.  Calculations will assume UTC."
	# except:
	# 	pass

	# Set up our observer location and sun object
	sun = ephem.Sun()
	o = ephem.Observer()
	o.lat = lat
	o.lon = lon
	o.date = date

	try:
		setting = o.next_setting(sun)
	
		# Convert to local time:
		setting = ephem.localtime(setting)
	
		# Cleanup Seconds so that we don't have fractional results
		if clean_seconds:
			setting = datetime(setting.year, setting.month, setting.day, setting.hour, setting.minute, setting.second)
	
	except ephem.AlwaysUpError:
		setting = None

	except:
		raise

	return setting