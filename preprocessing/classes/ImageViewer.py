import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
import numpy as np
import warnings
from .BaseImage import PETImage, SubPET

class ImageViewer:

	def __init__(self, image=None, collapse='max', escale=1.0):
		self.image = image    # data_handler.MyImage superclass

		# toggle for animation
		self.pause = False

		# cut coords (only used in ImageEditor)
		self.cx = 64
		self.cy = 64

		# scaling to use when displaying images
		self.escale = escale

		# method of collapsing axes for 2d viewing of 3d data
		self.collapse = collapse

	def is_x(self,ax):
		return [k for k,v in self.image.ax_map.items() if v==ax][0]=='x'

	def check_frames(self):
		self.image.check_data()
		if self.image.nframes <= 1:
			warnings.warn('{} frame(s) loaded into image.  Cannot animate'.format(self.image.nframes))

	
	def swap_x(self,frames):	
		return [f.swapaxes(0,1) for f in frames]


	def connect_controls(self,fig):
		
		def onKey(event):
		    global pause
		    if event.key == ' ':
		    	self.pause ^= True
		    elif event.key == 'c':
		    	plt.close()

		def onClick(event):
			self.cx,self.cy = (int(round(event.xdata)),int(round(event.ydata)))
			print(self.cx,self.cy)

		fig.canvas.mpl_connect('key_press_event', onKey)
		fig.canvas.mpl_connect('button_press_event', onClick)

	def view_each_axis(self, frame_range=None):
		if frame_range is None:
			# collapse over frames using sum or max
			frame = self.image.collapse_over_frames(method=self.collapse)
		else:
			fs = range(frame_range[0],frame_range[1]+1)
			frames = np.stack([self.image.get_frame(k) for k in fs],axis=-1)
			frame = self.image.collapse_over_frames(method=self.collapse,matrix=frames)
		
		# collapse and scale frame
		xmat = getattr(frame,self.collapse)(axis=self.image.get_axis('x')).swapaxes(0,1)
		ymat = getattr(frame,self.collapse)(axis=self.image.get_axis('y'))
		zmat = getattr(frame,self.collapse)(axis=self.image.get_axis('z'))
		xmat = xmat*(self.escale/xmat.max())
		ymat = ymat*(self.escale/ymat.max())
		zmat = zmat*(self.escale/zmat.max())

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


	def animate_slice(self,view_ax,slice_ix):
		self.check_frames()
		view_ax = self.image.get_axis(view_ax)
		frames = np.take(self.image.img_data, slice_ix, view_ax)
		frames = self.escale*frames/frames.max()
		frames = self.image.split_on_axis(frames,2)
		if self.is_x(view_ax):
			frames = self.swap_x(frames)
		return frames

	def animate_collapse(self,view_ax):
		self.check_frames()
		view_ax = self.image.get_axis(view_ax)
		f1,f2 = self.image.frame_range
		mats = [self.image.collapse_frame(axis=view_ax,frame=ix,method=self.collapse) for ix in range(f1,f2+1)]
		scale = self.escale/np.array(mats).max()
		mats = [m*scale for m in mats]
		if self.is_x(view_ax):
			mats = self.swap_x(mats)
		return mats

	def animate_along_axis(self,axis,frame=None):
		if frame is None:
			frame = self.image.frame_range[0]
		frame_mat = self.image.get_frame(frame)
		scale = self.escale/frame_mat.max()
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

		
	def animate_axes(self, interval=100):
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
		xblock = getattr(img_data,self.collapse)(axis=self.image.get_axis('x'))
		yblock = getattr(img_data,self.collapse)(axis=self.image.get_axis('y'))
		zblock = getattr(img_data,self.collapse)(axis=self.image.get_axis('z'))
		
		# normalize blocks
		xblock = (self.escale/xblock.max())*xblock
		yblock = (self.escale/yblock.max())*yblock
		zblock = (self.escale/zblock.max())*zblock

		# split into list of matrices
		xmats = self.image.split_on_axis(xblock,2)
		ymats = self.image.split_on_axis(yblock,2)
		zmats = self.image.split_on_axis(zblock,2)

		# swap x axes (for visualization)
		xmats = self.swap_x(xmats)
		if len(xmats)==1 or len(ymats)==1 or len(zmats)==1:
			xmats = xmats+xmats
			ymats = ymats+ymats
			zmats = zmats+zmats
			nframes = 2

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




class ImageEditor(ImageViewer):

	def __init__(self, image, nmice, collapse='max', escale=1.0):
		ImageViewer.__init__(self, image, collapse=collapse, escale=escale)

		# for displaying cut
		self.line_map = {4:2, 2:1, 1:0}
		if nmice not in [1,2,4]:
			raise ValueError('Unexpected nmice: {}'.format(nmice))
		self.nmice = nmice




	def animated_cutter(self, view_ax='z', method='collapse', frame_range=None, slice_ix=None, interval=100):

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
			elif self.nmice == 4:
				for j,line in enumerate(lines):
					line.set_data(lp[j])
			else:
				raise ValueError('Unexpected nmice in animated_cutter: {}'.format(self.nmice))

			img.set_array(mats[k])
			return patches


		# method routine
		if method not in ['collapse','slice','each_slice']:
			raise ValueError('Unexpected method passed {}'.format(method))
		
		if frame_range is None:
			frame_range = self.image.frame_range

		if method == 'collapse':	# add frame_range info
			mats = self.animate_collapse(view_ax=view_ax)
		elif method == 'slice':		# add frame_range info
			if slice_ix is None:
				print('No slice index indicated. Using 0.')
				slice_ix = 0
			mats = self.animate_slice(view_ax=view_ax,
								slice_ix=slice_ix)
		else:
			frames = range(frame_range[0],frame_range[1]+1)
			mat_groups = [self.animate_along_axis(view_ax,frame=f) for f in frames]
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


	def cut_image(self):

		cx,cy = self.cx,self.cy

		# cut in half in y,z plane
		if self.nmice == 2:
			img_data = self.image.img_data
			left_half = img_data[:,:,:cx,:]
			right_half = img_data[:,:,cx:,:]
			lh_name = 'half1_'+self.image.fileprefix
			rh_name = 'half2_'+self.image.fileprefix
			left_im = SubPET(fileprefix=lh_name, parent_image=self.image, img_data=left_half)
			right_im = SubPET(fileprefix=rh_name, parent_image=self.image, img_data=right_half)
			
			self.image.cuts = (left_im, right_im)
			return self.image.cuts

		# cut in quadrants in y,z and x,z planes
		elif self.nmice == 4:
			img_data = self.image.img_data
			
			# cut in half in y,z
			left_half = img_data[:,:,:cx,:]
			right_half = img_data[:,:,cx:,:]

			# in half again, in x,z
			bottom_left = left_half[:,:cy,:,:]
			top_left = left_half[:,cy:,:,:]

			bottom_right = right_half[:,:cy,:,:]
			top_right = right_half[:,cy:,:,:]

			tlname = 'topleft_'+self.image.fileprefix
			trname = 'topright_'+self.image.fileprefix
			blname = 'bottomleft_'+self.image.fileprefix
			brname = 'bottomright_'+self.image.fileprefix

			tl = SubPET(fileprefix=tlname, parent_image=self.image, img_data=top_left)
			tr = SubPET(fileprefix=trname, parent_image=self.image, img_data=top_right)
			bl = SubPET(fileprefix=blname, parent_image=self.image, img_data=bottom_left)
			br = SubPET(fileprefix=brname, parent_image=self.image, img_data=bottom_right)

			self.image.cuts = (tl,tr,bl,br)

			return self.image.cuts


		elif self.nmice == 1:
			raise ValueError('Do not need to cut image with 1 mouse.')
		else:
			raise ValueError('ImageEditor with nmice = {} calling self.cut_image()')


	def animate_cuts(self, view_ax='z', interval=100):
		
		def genIx():
			dt = 1
			t = 0
			while t < nframes-1:
				if not self.pause:
					t +=1
				yield t

		def genAni(k):
			f_img[0].set_array(fmats[k])
			for j,im in enumerate(imgs):
				im.set_array(cut_list[j][k])
			return all_imgs

		if self.image.cuts is None:
			raise ValueError('Image has not been cut in ImageEditor.animate_cuts.')

		# for splitting collapsed data into frames
		split_frames = lambda x: self.image.split_on_axis(x,2)
		
		fdata = self.image.img_data
		axis = self.image.get_axis(view_ax)
		fdata = getattr(fdata,self.collapse)(axis=axis)
		scale = self.escale/fdata.max()
		fdata = fdata*scale
		fmats = split_frames(fdata)
		nframes = len(fmats)

		cuts = self.image.cuts
		cut_list = [cut.img_data for cut in cuts]
		
		# join data if necessary
		if self.nmice == 4 and axis in [1,2]:
			if axis == 1:
				# join on y axis
				cuts = [np.concatenate([cuts[0],cuts[2]],axis=1),np.concatenate([cuts[1],cuts[3]],axis=1)]
			else:
				# join on x axis
				cuts = [np.concatenate([cuts[0],cuts[1]],axis=2),np.concatenate([cuts[2],cuts[3]],axis=2)]	


		cut_list = [getattr(img_data,self.collapse)(axis=axis)*scale for img_data in cut_list]
		cut_list = [split_frames(img_data) for img_data in cut_list]
		
		if len(fmats) == 1:
			fmats = fmats + fmats
			cut_list = [frames+frames for frames in cut_list]
			nframes = 2
		
		if self.is_x(axis):
			fmats = self.swap_x(fmats)
			cut_list = [self.swap_x(frames) for frames in cut_list]

		# plotting
		fig = plt.figure()
		grid = gridspec.GridSpec(2,4)
		full_ax = plt.subplot(grid[:,2:])
		if self.nmice == 2:
			if axis not in [0,1]:
				raise ValueError('Invalid view axis for nmice = 2 in animate_cuts: {}'.format(view_ax))
			plt_nrows = 1
			plt_ncols = 2 
			axes = [plt.subplot(grid[:,0]), plt.subplot(grid[:,1])]	# tall in half

		# todo: animation
		elif self.nmice == 4:
			plt_map = {0:(2,2),1:(1,2),2:(2,1)}
			plt_ncols,plt_nrows = plt_map[axis]
			if axis == 0:
				axes = [plt.subplot(grid[k//2,k%2]) for k in range(4)]	# quadrants
			elif axis == 1:
				axes = [plt.subplot(grid[:,0]), plt.subplot(grid[:,1])] # tall in half
			else:
				axes = [plt.subplot(grid[0,:2]), plt.subplot(grid[1,:2])]

		else:
			raise ValueError('Unexpected nmice in ImageEditor.animate_cuts: {}'.format(self.nmice))

		pairs = [[axes[j],cut_list[j]] for j in range(len(axes))]
		for p in pairs:
			ax,cl = p
			by,bx = cl[0].shape
			ax.set_xlim(0,bx),ax.set_ylim(0,by)
		by,bx = fmats[0].shape
		full_ax.set_xlim(0,bx), full_ax.set_ylim(0,by)
		imgs = [p[0].imshow(p[1][0], cmap='gray', clim=(0,1), animated=True) for p in pairs]
		f_img = [full_ax.imshow(fmats[0], cmap='gray', clim=(0,1), animated=True)]
		all_imgs = f_img + imgs
		
		self.connect_controls(fig)
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=interval,
		    repeat=True)
		plt.tight_layout()
		plt.show()
