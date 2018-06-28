from preprocessing.classes.ctimage import CTImage

f = open('ctfiles.txt','r')
paths = f.read().split('\n')
ct = CTImage(paths[0])
ct.load_image()