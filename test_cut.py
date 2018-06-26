# -*- coding: UTF-8 -*-
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation
from preprocessing.classes.BaseImage import *
from preprocessing.classes.ImageViewer import *
from preprocessing.settings import *

## f3 : 4 mice, 1 frame
## f2 : 2 mice
## f1 : 2 mice, 40 frames

f3 = "mpet3745a_em1_v1.pet"
f2 = "mpet3724a_em1_v1.pet"
f1 = "mpet3630a_em1_v1.pet"


im1 = ImageEditor(PETImage(f1,fpath),nmice=2,escale=14.0)
im2 = ImageEditor(PETImage(f2,fpath),nmice=2,escale=14.0)
im3 = ImageEditor(PETImage(f3,fpath),nmice=4,escale=24.0)

im3.image.load_image()

im3.animated_cutter('x')

im3.cut_image()

im3.animate_cuts('x')