import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import warnings
from .BaseImage import PETImage, SubPET

class ImageViewer:

	def __init__(self, image=None):
		self.image = image    # data_handler.MyImage superclass

		# toggle for animation
		self.pause = False

		# cut coords (only used in ImageEditor)
		self.cx = 64
		self.cy = 64

	def is_x(self,ax):
		return [k for k,v in self.image.ax_map.items() if v==ax][0]=='x'

	def check_frames(self):
		if self.image.nframes <= 1:
			warnings.warn('{} frame(s) loaded into image.  Cannot animate'.format(self.image.nframes))

	
	def swapX(self,frames):	
		return [f.swapaxes(0,1) for f in frames]


	def connect_controls(self,fig):
		
		def onKey(event):
		    global pause
		    if event.key == ' ':
		    	self.pause ^= True
		    elif event.key == 'c':
		    	plt.close()

		def onClick(event):
			self.cx,self.cy = (event.xdata,event.ydata)
			print(self.cx,self.cy)

		fig.canvas.mpl_connect('key_press_event', onKey)
		fig.canvas.mpl_connect('button_press_event', onClick)

	def view_each_axis(self, frame_range=None, collapse='sum', exposure_scale=1.0):
		if frame_range is None:
			# collapse over frames using sum or max
			frame = self.image.collapse_over_frames(method=collapse)
		else:
			fs = range(frame_range[0],frame_range[1]+1)
			frames = np.stack([self.image.get_frame(k) for k in fs],axis=-1)
			frame = self.image.collapse_over_frames(method=collapse,matrix=frames)
		
		# collapse and scale frame
		xmat = getattr(frame,collapse)(axis=self.image.get_axis('x')).swapaxes(0,1)
		ymat = getattr(frame,collapse)(axis=self.image.get_axis('y'))
		zmat = getattr(frame,collapse)(axis=self.image.get_axis('z'))
		xmat = xmat*(exposure_scale/xmat.max())
		ymat = ymat*(exposure_scale/ymat.max())
		zmat = zmat*(exposure_scale/zmat.max())

		# plot with control
		ax_title = {0:'x axis', 1:'y axis', 2:'z axis'}
		fig, (ax1,ax2,ax3) = plt.subplots(1, 3, sharey=False)
		self.connect_controls(fig)
		pairs = [(ax1,xmat),(ax2,ymat),(ax3,zmat)]
		for j,pair in enumerate(pairs):
			ax,mat = pair
			ax.imshow(mat, cmap='gray', clim=(0,1))
			ax.set_xlim(0,mat.shape[1])
			ax.set_ylim(0,mat.shape[0])
			ax.set_title(ax_title[j])
		plt.show()


	def animate_slice(self,view_ax,slice_ix,exposure_scale=1):
		self.check_frames()
		view_ax = self.image.get_axis(view_ax)
		frames = np.take(self.image.img_data, slice_ix, view_ax)
		frames = exposure_scale*frames/frames.max()
		frames = self.image.split_on_axis(frames,2)
		if self.is_x(view_ax):
			frames = self.swapX(frames)
		return frames

	def animate_collapse(self,view_ax,exposure_scale=1, method='sum'):
		self.check_frames()
		view_ax = self.image.get_axis(view_ax)
		f1,f2 = self.image.frame_range
		mats = [self.image.collapse_frame(axis=view_ax,frame=ix,method=method) for ix in range(f1,f2+1)]
		scale = exposure_scale/np.array(mats).max()
		mats = [m*scale for m in mats]
		if self.is_x(view_ax):
			mats = self.swapX(mats)
		return mats

	def animate_along_axis(self,axis,frame=None,exposure_scale=1):
		if frame is None:
			frame = self.image.frame_range[0]
		frame_mat = self.image.get_frame(frame)
		scale = exposure_scale/frame_mat.max()
		frame_mat = frame_mat*scale
		mats = self.image.split_on_axis(frame_mat, axis)
		return mats


	def do_animation(self,frames,interval=50):
		
		def genIx():
			dt = 1
			t = 0
			while t < len(frames)-1:
				if not self.pause:
					t +=1
				yield t

		def genAni(k):
			img.set_array(frames[k])
			return patches

		# prevents error in matplotlib.animation if only one image
		if len(frames) == 1:
			frames = frames + frames

		self.pause = False

		by, bx = frames[0].shape
		fig = plt.figure()

		ax = fig.add_subplot(111)
		img = ax.imshow(frames[0], cmap='gray', clim=(0,1), animated=True)
		patches=[img]
		ax.set_xlim(0, bx)
		ax.set_ylim(0, by)

		self.connect_controls(fig)
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=interval,
		    repeat=True)
		plt.show()


class ImageEditor(ImageViewer):

	def __init__(self, image, nmice):
		ImageViewer.__init__(self, image)

		# for displaying cut
		self.line_map = {4:2, 3:2, 2:1, 1:0}
		if nmice not in [1,2,3,4]:
			raise ValueError('Unexpected nmice: {}'.format(nmice))
		self.nmice = nmice

	def animated_axes(self, collapse='sum',exposure_scale=1.0,interval=100):
		def genIx():
			dt = 1
			t = 0
			while t < nframes-1:
				if not self.pause:
					t +=1
				yield t

		def genAni(k):
			imgs[0].set_array(xmats[k])
			imgs[1].set_array(ymats[k])
			imgs[2].set_array(zmats[k])
			return imgs


		# prevents error in matplotlib.animation if only one image
		img_data = self.image.img_data
		nframes = img_data.shape[-1]
		xblock = getattr(img_data,collapse)(axis=self.image.get_axis('x'))
		yblock = getattr(img_data,collapse)(axis=self.image.get_axis('y'))
		zblock = getattr(img_data,collapse)(axis=self.image.get_axis('z'))
		
		# normalize blocks
		xblock = (exposure_scale/xblock.max())*xblock
		yblock = (exposure_scale/yblock.max())*yblock
		zblock = (exposure_scale/zblock.max())*zblock

		# split into list of matrices
		xmats = self.image.split_on_axis(xblock,2)
		ymats = self.image.split_on_axis(yblock,2)
		zmats = self.image.split_on_axis(zblock,2)

		# swap x axes (for visualization)
		xmats = self.swapX(xmats)

		if len(xmats)==1 or len(ymats)==1 or len(zmats)==1:
			xmats = xmats+xmats
			ymats = ymats+ymats
			zmats = zmats+zmats

		self.cx,self.cy = (64,64)
		self.pause = False

		xbx,xby = self.image.bounds[self.image.get_axis('x')]
		ybx,yby = self.image.bounds[self.image.get_axis('y')]
		zbx,zby = self.image.bounds[self.image.get_axis('z')]

		fig = plt.figure()
		ax1 = plt.subplot(221)
		ax2 = plt.subplot(122)
		ax3 = plt.subplot(223)
		plt.tight_layout()
		imgs = [ax1.imshow(xmats[0], cmap='gray', clim=(0,1), animated=True),
				ax2.imshow(ymats[0], cmap='gray', clim=(0,1), animated=True),
				ax3.imshow(zmats[0], cmap='gray', clim=(0,1), animated=True)]

		ax_title = {0:'x axis', 1:'y axis', 2:'z axis'}
		pairs = [(ax1,xmats[0]),(ax2,ymats[0]),(ax3,zmats[0])]
		for j,pair in enumerate(pairs):
			ax,mat = pair
			ax.set_xlim(0,mat.shape[1])
			ax.set_ylim(0,mat.shape[0])
			ax.set_title(ax_title[j])

		self.connect_controls(fig)
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=interval,
		    repeat=True)
		plt.show()



	def animated_cutter(self, view_ax='z', method='collapse', frame_range=None, exposure_scale=1, slice_ix=None, interval=100):

		def genIx():
			dt = 1
			t = 0
			while t < len(mats)-1:
				if not self.pause:
					t +=1
				yield t

		def genAni(k):
			cx,cy = (self.cx, self.cy)
			lp = [[[cx,cx],[0,by]],
				  [[0,bx],[cy,cy]]]

			if self.nmice == 2:
				lines[0].set_data(lp[0])
			elif self.nmice in [3,4]:
				for j,line in enumerate(lines):
					line.set_data(lp[j])

			img.set_array(mats[k])
			return patches


		# method routine
		if method not in ['collapse','slice','each_slice']:
			raise ValueError('Unexpected method passed {}'.format(method))
		
		if frame_range is None:
			frame_range = self.image.frame_range

		if method == 'collapse':	# add frame_range info
			mats = self.animate_collapse(view_ax=view_ax,exposure_scale=exposure_scale)
		elif method == 'slice':		# add frame_range info
			if slice_ix is None:
				print('No slice index indicated. Using 0.')
				slice_ix = 0
			mats = self.animate_slice(view_ax=view_ax,
								slice_ix=slice_ix,
								exposure_scale=exposure_scale)
		else:
			frames = range(frame_range[0],frame_range[1]+1)
			mat_groups = [self.animate_along_axis(view_ax,frame=f,exposure_scale=exposure_scale) for f in frames]
			mats = [mat for group in mat_groups for mat in group]

		# prevents error in matplotlib.animation if only one image
		if len(mats) == 1:
			mats =  mats + mats

		self.cx,self.cy = (64,64)
		self.pause = False
		nlines = self.line_map[self.nmice]
		view_ax = self.image.get_axis(view_ax)
		bx,by = self.image.bounds[view_ax]

		fig = plt.figure()

		ax = fig.add_subplot(111)
		img = ax.imshow(mats[0], cmap='gray', clim=(0,1), animated=True)
		lines = [ax.plot([],[],'r-')[0] for _ in range(nlines)]
		patches = [img] + lines
		ax.set_xlim(0, bx)
		ax.set_ylim(0, by)

		self.connect_controls(fig)
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=interval,
		    repeat=True)
		plt.show()






