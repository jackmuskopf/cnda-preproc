#!/usr/bin/python
# -*- coding: ascii -*-
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
from preprocessing.classes.BaseImage import *
from preprocessing.classes.ImageViewer import *
from preprocessing.settings import *

## f3 : 4 mice, 1 frame
## f2 : 2 mice
## f1 : 2 mice, 40 frames

f3 = 'mpet3745a_em1_v1.pet'
f2 = 'mpet3724a_em1_v1.pet'
f1 = 'mpet3630a_em1_v1.pet'

def do_f1():
	if im1.image.img_data is None:
		im1.image.load_image()
	frames = im1.animate_collapse('y')
	im1.do_animation(frames,interval=50)

def do_f2():
	if im2.image.img_data is None:
		im2.image.load_image()
	im2.animated_cutter(view_ax='y',method='collapse',interval=150)


def do_f3():
	if im3.image.img_data is None:
		im3.image.load_image()
	im3.animated_cutter(view_ax='z',method='each_slice',interval=50)

def rot_ex():
	if im1.image.img_data is None:
		im1.image.load_image()
	im1.animate_axes()
	im1.image.rotate_on_axis('x')
	im1.animate_axes()

im1 = ImageEditor(PETImage(f1,fpath),nmice=2,escale=14.0)
im2 = ImageEditor(PETImage(f2,fpath),nmice=2,escale=14.0)
im3 = ImageEditor(PETImage(f3,fpath),nmice=4,escale=24.0)

im3.image.load_image()

im3.animated_cutter()

(tl,tr,bl,br) = im3.cut_image()

tlv = ImageEditor(tl,nmice=1,escale=14.0)
tlv.do_animation(tlv.animate_along_axis('z'))
