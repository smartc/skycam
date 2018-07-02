#!/usr/bin/python

import os, inspect
DIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
activate_this = DIR + "/venv/bin/activate_this.py"
execfile(activate_this, dict(__file__=activate_this))

import sky_capture, json

def subdirs(path):
	output = []
	dirlist = os.listdir(path)
	for entry in dirlist:
		if os.path.isdir(path + "/" + entry):
			output.append(entry)
#	if output == []:
#			output = None
	return output

def process_folder(folder):
	isDone = os.path.isfile(folder + "/timelapse.mp4")
	skipFolder = os.path.isfile(folder + "/.skip")
	if not isDone and not skipFolder:
		return True
	else:
		return False

def build_timelapses():
	this_folder = os.path.abspath(os.path.dirname(__file__))
	with open(this_folder + "/" + 'settings.json', 'r') as f:
		data = json.load(f)
	root_dir = data['image_folder']
	for folder in subdirs(root_dir):
		this_folder = root_dir + "/" + folder + "/"
		if process_folder(this_folder):
			sky_capture.generate_timelapse(this_folder)