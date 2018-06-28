from preprocessing.classes.ctimage import CTImage
import ntpath

f = open('ctfiles.txt','r')
paths = f.read().split('\n')
for p in paths:
	ct = CTImage(p)
	print(ct.params.total_frames,ntpath.basename(p))