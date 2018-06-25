
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
from preprocessing.classes.BaseImage import *
from preprocessing.classes.ImageViewer import *
from preprocessing.settings import *

## f3 : 4 mice, 1 frame
## f2 : 2 mice
## f1 : 2 mice, 40 frames
def do_f1():
	myimg = PETImage(f1,fpath)
	myimg.load_image()
	ie = ImageEditor(myimg,nmice=2)
	# ie.animated_cutter(view_ax='y',exposure_scale=14.0,method='collapse',interval=50)
	frames = ie.animate_collapse('y',exposure_scale=14.0,method='max')
	ie.do_animation(frames,interval=50)

def do_f2():
	myimg = PETImage(f2,fpath)
	myimg.load_image()
	ie = ImageEditor(myimg,nmice=2)
	ie.animated_cutter(view_ax='y',exposure_scale=14.0,method='collapse',interval=50)


def do_f3():
	myimg = PETImage(f3,fpath)
	myimg.load_image()
	ie = ImageEditor(myimg,nmice=4)
	ie.animated_cutter(view_ax='z',exposure_scale=100.0,method='each_slice',interval=10)

def rot_ex():
	im1.image.load_image()
	im1.animated_axes(collapse='max',exposure_scale=14.0)
	im1.image.rotate_on_axis('x')
	im1.animated_axes(collapse='max',exposure_scale=14.0)

im1 = ImageEditor(PETImage(f1,fpath),nmice=2)
im2 = ImageEditor(PETImage(f2,fpath),nmice=2)
im3 = ImageEditor(PETImage(f3,fpath),nmice=4)

