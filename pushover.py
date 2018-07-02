# Pushover plugin for LightingSense

import httplib, urllib, json

with open('pushover.json', 'r') as f:
	data = json.load(f)

PO_TOKEN = data['app_token']
PO_USER = data['user_token']

def sendPushoverAlert(title, message):
	
	conn = httplib.HTTPSConnection("api.pushover.net:443")
	conn.request("POST", "/1/messages.json",
	  urllib.urlencode({
	    "token": PO_TOKEN,
	    "user": PO_USER,
	    "priority": -1,
	    "message": message,
	    "title": title
	  }), { "Content-type": "application/x-www-form-urlencoded" })
	conn.getresponse()

