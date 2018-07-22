from PIL import Image, ImageChops
from glob import glob
import progressbar
import os



def star_trails(tgtDir=None, output_name=None, imageType="jpg", prefix=""):
	filePattern = prefix + "*." + imageType
	
	if tgtDir is None:
		tgtDir = os.getcwd()
	else:
		os.chdir(tgtDir)

	if output_name is None:
		output_name = "star_trails.jpg"
	elif not output_name.lower().endswith(".jpg", ".jpeg"):
		output_name = os.path.splittext(output_name)[0] + ".jpg"

	images = glob(filePattern)
	images.sort()
	final_image = Image.open(images[0])

	bar = progressbar.ProgressBar(maxval=len(images)-1, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
	bar.start()

	for i in range(1, len(images)):
		current_image = Image.open(images[i])
		final_image = ImageChops.lighter(final_image, current_image)
		bar.update(i)
	final_image.save(output_name, "JPEG")

	bar.finish()