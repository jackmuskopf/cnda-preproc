import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
import tkinter as tk
import numpy as np
import warnings
import gc
from .baseimage import PETImage, SubImage

class ImageViewer(tk.Tk):

	def __init__(self, image=None, collapse='max', escale=1.0, interval=100):
		tk.Tk.__init__(self)
		self.image = image  

		# toggle for animation
		self.pause = False

		# scaling to use when displaying images
		self.escale = escale

		# method of collapsing axes for 2d viewing of 3d data
		self.collapse = collapse

		self.interval = interval

	def update_dims(self):

		# cut coords (only used in ImageEditor)
		self.cx_def,self.cy_def = int(round(self.image.xdim/2)),int(round(self.image.ydim/2))
		self.cx,self.cy = self.cx_def,self.cy_def


	def is_x(self,ax):
		return [k for k,v in self.image.ax_map.items() if v==ax][0]=='x'

	def check_frames(self):
		self.image.check_data()
		if self.image.nframes <= 1:
			warnings.warn('{} frame(s) loaded into image.  Cannot animate'.format(self.image.nframes))

	
	def swap_x(self,frames):	
		return [f.swapaxes(0,1) for f in frames]

	def stop_animation(self):
		plt.close()


	def connect_controls(self,fig,cutter=False):
		
		def onKey(event):
		    global pause
		    if event.key == ' ':
		    	self.pause ^= True
		    elif event.key == 'c':
		    	self.stop_animation()

		def onClick(event):
			if event.xdata is not None and event.ydata is not None:
				self.cx,self.cy = (int(round(event.xdata)),int(round(event.ydata)))
				if self.nmice > 2:
					message = 'Cutter coords: (x={0},y={1})'.format(self.cx,self.cy)
				else:
					message = 'Cutter coords: (x={})'.format(self.cx)
				print(message)

		fig.canvas.mpl_connect('key_press_event', onKey)
		if cutter:
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
		xmat = normalize(xmat)*(self.escale)
		ymat = normalize(ymat)*(self.escale)
		zmat = normalize(zmat)*(self.escale)

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


	def animate_slice(self,view_ax,slice_ix, get_mats=False):
		self.check_frames()
		view_ax = self.image.get_axis(view_ax)
		frames = np.take(self.image.img_data, slice_ix, view_ax)
		frames = self.escale*normalize(frames)
		frames = self.image.split_on_axis(frames,2)
		if self.is_x(view_ax):
			frames = self.swap_x(frames)
		
		if get_mats:
			return frames	
		else:
			self.do_animation(frames)

	def animate_collapse(self,view_ax, get_mats=False):
		self.check_frames()
		view_ax = self.image.get_axis(view_ax)
		f1,f2 = self.image.frame_range
		mats = [self.image.collapse_frame(axis=view_ax,frame=ix,method=self.collapse) for ix in range(f1,f2+1)]
		
		# careful dividing, always
		max_val = np.array(mats).max()
		max_val = max_val if not_zero(max_val) else 1
		scale = self.escale/max_val
		mats = [m*scale for m in mats]
		if self.is_x(view_ax):
			mats = self.swap_x(mats)
		
		mats.reverse()

		if get_mats:
			return mats
		else:
			self.do_animation(mats)

	def animate_along_axis(self,axis,frame=None, get_mats=False):
		if frame is None:
			frame = self.image.frame_range[0]
		frame_mat = self.image.get_frame(frame)
		frame_mat = normalize(frame_mat)*self.escale
		mats = self.image.split_on_axis(frame_mat, axis)
		
		if get_mats:
			return mats
		else:
			self.do_animation(mats)


	def do_animation(self,frames):
		
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
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=self.interval,
		    repeat=True)
		plt.show()

		
	def animate_axes(self):
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


		
		img_data = self.image.img_data
		nframes = img_data.shape[-1]
		xblock = getattr(img_data,self.collapse)(axis=self.image.get_axis('x'))
		yblock = getattr(img_data,self.collapse)(axis=self.image.get_axis('y'))
		zblock = getattr(img_data,self.collapse)(axis=self.image.get_axis('z'))
		img_data = None
		gc.collect()

		# normalize blocks
		xblock = (self.escale)*normalize(xblock)
		yblock = (self.escale)*normalize(yblock)
		zblock = (self.escale)*normalize(zblock)

		# split into list of matrices
		xmats = self.image.split_on_axis(xblock,2)
		ymats = self.image.split_on_axis(yblock,2)
		zmats = self.image.split_on_axis(zblock,2)

		# swap x axes (for visualization)
		xmats = self.swap_x(xmats)

		# prevents error in matplotlib.animation if only one image
		if len(xmats)==1 or len(ymats)==1 or len(zmats)==1:
			xmats = xmats+xmats
			ymats = ymats+ymats
			zmats = zmats+zmats
			nframes = 2

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
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=self.interval,
		    repeat=True)
		plt.show()




class ImageEditor(ImageViewer):

	def __init__(self, image=None, nmice=None, collapse='max', escale=1.0):
		ImageViewer.__init__(self, image=image, collapse=collapse, escale=escale)

		# for displaying cut
		self.nmice = nmice
		self.cutter = 'cross'
		self.line_map = {'cross' : 2,
						'up_T' : 2,
						'down_T' : 2,
						'horizontal' : 1,
						'vertical' : 1,
						'no_cut' : 0}
		self.cut_map = {'cross' : 4,
						'up_T' : 3,
						'down_T' : 3,
						'horizontal' : 2,
						'vertical' : 2,
						'no_cut' : 1}

	def check_nmice(self):
		if self.nmice not in range(1,5):
			raise ValueError('ImageEditor.nmice not properly initialized.')



	def animated_cutter(self, view_ax='z', cutter=None, method='collapse', frame_range=None, slice_ix=None):

		def genIx():
			dt = 1
			t = 0
			while t < len(mats)-1:
				if not self.pause:
					t +=1
				yield t

		def genAni(k):
			cx,cy = (self.cx, self.cy)
			if self.cutter == 'up_T':
				lp = [[[cx,cx],[cy,by]],
				  	[[0,bx],[cy,cy]]]
			elif self.cutter == 'down_T':
				lp = [[[cx,cx],[0,cy]],
				  	[[0,bx],[cy,cy]]]
			else:
				lp = [[[cx,cx],[0,by]],
				  	[[0,bx],[cy,cy]]]


			if self.cutter == 'vertical':
				lines[0].set_data(lp[0])
			elif self.cutter == 'horizontal':
				lines[0].set_data(lp[1])
			elif self.cutter in ['cross','up_T','down_T']:
				for j,line in enumerate(lines):
					line.set_data(lp[j])
			else:
				raise ValueError('Unexpected cutter in animated_cutter: {}'.format(self.cutter))

			img.set_array(mats[k])
			return patches

		if cutter is None:
			cutter = self.cutter

		# check cutting method
		if cutter not in ['cross','up_T','down_T','horizontal','vertical']:
			raise ValueError('Unexpected cutting method in animated_cutter: {}'.format(cutter))
		else:
			self.cutter = cutter

		# method routine
		if method not in ['collapse','slice','each_slice']:
			raise ValueError('Unexpected method passed {}'.format(method))
		
		if frame_range is None:
			frame_range = self.image.frame_range

		if method == 'collapse':	# add frame_range info
			mats = self.animate_collapse(view_ax=view_ax, get_mats=True)
		elif method == 'slice':		# add frame_range info
			if slice_ix is None:
				print('No slice index indicated. Using 0.')
				slice_ix = 0
			mats = self.animate_slice(view_ax=view_ax, slice_ix=slice_ix, get_mats=True)
		else:
			frames = range(frame_range[0],frame_range[1]+1)
			mat_groups = [self.animate_along_axis(view_ax, frame=f, get_mats=True) for f in frames]
			mats = [mat for group in mat_groups for mat in group]

		# prevents error in matplotlib.animation if only one image
		if len(mats) == 1:
			mats =  mats + mats

		self.pause = False
		nlines = self.line_map[self.cutter]
		view_ax = self.image.get_axis(view_ax)
		by,bx = mats[0].shape

		if self.cutter in ['up_T','down_T','cross'] and view_ax !=0:
			raise ValueError('Must use {} cutter in z-axis view.'.format(self.cutter))
		elif self.cutter == 'horizontal' and view_ax == 1:
			raise ValueError('Cannot cut images horizontally via y-axis view.')
		if view_ax == 2:
			raise ValueError('Cannot cut images in x-axis view.')

		fig = plt.figure()

		ax = fig.add_subplot(111)
		img = ax.imshow(mats[0], cmap='gray', clim=(0,1), animated=True)
		lines = [ax.plot([],[],'r-')[0] for _ in range(nlines)]
		patches = [img] + lines
		ax.set_xlim(0, bx)
		ax.set_ylim(0, by)


		self.connect_controls(fig,cutter=True)
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=self.interval,
		    repeat=True)
		plt.show()



	def cut_image(self):

		self.image.clean_cuts()
		cx,cy = self.cx,self.cy
		img_data = self.image.img_data

		# cut in half in y,z plane
		if self.cutter == 'vertical':

			# left half
			lhfn, lhd = self.image.submemmap(ix=1, data=img_data[:,:,:cx,:])
			left_im = SubImage(parent_image=self.image, img_data=lhd, filename=lhfn)
			
			# right half
			rhfn, rhd = self.image.submemmap(ix=2, data=img_data[:,:,cx:,:])
			right_im = SubImage(parent_image=self.image, img_data=rhd, filename=rhfn)
			
			self.image.cuts = [left_im, right_im]
			return self.image.cuts

		elif self.cutter == 'horizontal':

			# top half
			thfn, thd = self.image.submemmap(ix=1, data=img_data[:,cy:,:,:])
			top_im = SubImage(parent_image=self.image, img_data=thd, filename=thfn)

			# bottom half
			bhfn, bhd = self.image.submemmap(ix=2, data=img_data[:,:cy,:,:])
			bottom_im = SubImage(parent_image=self.image, img_data=bhd, filename=bhfn)
			
			self.image.cuts = [top_im, bottom_im]
			return self.image.cuts

		elif self.cutter == 'down_T':

			# top half
			thfn, thd = self.image.submemmap(ix=1, data=img_data[:,cy:,:,:])
			top_im = SubImage(parent_image=self.image, img_data=thd, filename=thfn)

			# bottom left
			blfn, bld = self.image.submemmap(ix=2, data=img_data[:,:cy,:cx,:])
			bl = SubImage(parent_image=self.image, img_data=bld, filename=blfn)

			# bottom right
			brfn, brd = self.image.submemmap(ix=3, data=img_data[:,:cy,cx:,:])
			br = SubImage(parent_image=self.image, img_data=brd,  filename=brfn)
			
			self.image.cuts = [top_im, bl, br]
			return self.image.cuts


		elif self.cutter == 'up_T':

			# top left
			tlfn, tld = self.image.submemmap(ix=1, data=img_data[:,cy:,:cx,:])
			tl = SubImage(parent_image=self.image, img_data=tld, filename=tlfn)


			# top right
			trfn, trd = self.image.submemmap(ix=2, data=img_data[:,cy:,cx:,:])
			tr = SubImage(parent_image=self.image, img_data=trd, filename=trfn)

			# bottom half
			bhfn, bhd = self.image.submemmap(ix=3, data=img_data[:,:cy,:,:])
			bottom_im = SubImage(parent_image=self.image, img_data=bhd, filename=bhfn)

			self.image.cuts = [tl, tr, bottom_im]
			return self.image.cuts

		# cut in quadrants in y,z and x,z planes
		elif self.cutter == 'cross':

			# top left
			tlfn, tld = self.image.submemmap(ix=1, data=img_data[:,cy:,:cx,:])
			tl = SubImage(parent_image=self.image, img_data=tld, filename=tlfn)

			# top right
			trfn, trd = self.image.submemmap(ix=2, data=img_data[:,cy:,cx:,:])
			tr = SubImage(parent_image=self.image, img_data=trd, filename=trfn)
			
			# bottom left
			blfn, bld = self.image.submemmap(ix=3, data=img_data[:,:cy,:cx,:])
			bl = SubImage(parent_image=self.image, img_data=bld, filename=blfn)

			# bottom right
			brfn, brd = self.image.submemmap(ix=4, data=img_data[:,:cy,cx:,:])
			br = SubImage(parent_image=self.image, img_data=brd,  filename=brfn)


			self.image.cuts = [tl,tr,bl,br]

			return self.image.cuts
		else:
			raise ValueError('ImageEditor with cutter = {} calling self.cut_image()'.format(self.cutter))

		img_data = None
		gc.collect()


	def animate_cuts(self, title='', view_ax='z'):
		
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
				im.set_array(cuts[j][k])
			return all_imgs

		self.check_nmice()

		if not self.image.cuts:
			raise ValueError('Image has not been cut in ImageEditor.animate_cuts.')

		# for splitting collapsed data into frames
		split_frames = lambda x: self.image.split_on_axis(x,2)
		
		# get the data
		fdata = self.image.img_data	# free this
		axis = self.image.get_axis(view_ax)
		fdata = getattr(fdata,self.collapse)(axis=axis)

		# always careful division
		max_val = fdata.max()
		scale = self.escale/max_val if not_zero(max_val) else self.escale
		fdata = fdata*scale

		fmats = split_frames(fdata)
		nframes = len(fmats)
		fdata = None # freed
		

		cuts = self.image.cuts # free this
		cuts = [cut.img_data for cut in cuts]
		ncuts = len(cuts)

		cuts = [getattr(img_data,self.collapse)(axis=axis)*scale for img_data in cuts]  # freed
		cuts = [split_frames(img_data) for img_data in cuts]
		
		if len(fmats) == 1:
			fmats = fmats + fmats
			cuts = [frames+frames for frames in cuts]
			nframes = 2
		
		if self.is_x(axis):
			fmats = self.swap_x(fmats)
			cuts = [self.swap_x(frames) for frames in cuts]

			
		gc.collect() 

		# plotting
		fig = plt.figure()
		plt.title(title)
		shapes = [cl[0].shape for cl in cuts]	# for grid formatting
		
		if self.cutter == 'vertical':
			w1,w2 = shapes[0][1],shapes[1][1]
			grid = gridspec.GridSpec(2,4,width_ratios=[w1,w2,w1,w2])
			if axis in [0,1]: # z or y
				axes = [plt.subplot(grid[:,0]), plt.subplot(grid[:,1])]	# tall in half
			else: # x
				axes = [plt.subplot(grid[0,:2]),plt.subplot(grid[1,:2])]

		elif self.cutter == 'horizontal':
			h1,h2 = shapes[0][0],shapes[1][0]
			
			if axis in [0,2]: # z or x
				grid = gridspec.GridSpec(2,4,height_ratios=[h1,h2])
				axes = [plt.subplot(grid[0,:2]), plt.subplot(grid[1,:2])]	# tall in half
			else: # y
				grid = gridspec.GridSpec(2,3)
				axes = [plt.subplot(grid[:,0]),plt.subplot(grid[:,1])]

		elif self.cutter == 'up_T':
			if axis == 0:								# quadrants
				w1,w2 = shapes[0][1],shapes[1][1]
				w3 = (w1+w2)/2
				h1,h2 = shapes[0][0],shapes[2][0]			
				grid = gridspec.GridSpec(2, 4, height_ratios=[h1,h2], width_ratios=[w1,w2,w3,w3])				
				axes = [plt.subplot(grid[0,0]),plt.subplot(grid[0,1]),plt.subplot(grid[1,:2])]
			elif axis == 1:	# y axis
				w1,w2 = shapes[0][1],shapes[1][1]
				grid = gridspec.GridSpec(2,4,width_ratios=[w1,w2,w1,w2])
				axes = [plt.subplot(grid[0,0]),plt.subplot(grid[0,1]),plt.subplot(grid[1,:2])]
			else:	# x axis
				h1,h2 = shapes[0][0],shapes[2][0]
				grid = gridspec.GridSpec(4, 4, height_ratios=[h1,h1,h2,h2])
				axes = [plt.subplot(grid[0,:2]), plt.subplot(grid[1,:2]), plt.subplot(grid[2:,:2])]

		elif self.cutter == 'down_T':
			if axis == 0:								# quadrants
				w1,w2 = shapes[1][1],shapes[2][1]
				w3 = (w1+w2)/2
				h1,h2 = shapes[0][0],shapes[1][0]			
				grid = gridspec.GridSpec(2, 4, height_ratios=[h1,h2], width_ratios=[w1,w2,w3,w3])				
				axes = [plt.subplot(grid[0,:2]),plt.subplot(grid[1,0]),plt.subplot(grid[1,1])]
			elif axis == 1:	# y axis
				w1,w2 = shapes[1][1],shapes[2][1]
				grid = gridspec.GridSpec(2,4,width_ratios=[w1,w2,w1,w2])
				axes = [plt.subplot(grid[0,:2]),plt.subplot(grid[1,0]),plt.subplot(grid[1,1])]
			else:	# x axis
				h1,h2 = shapes[0][0],shapes[1][0]
				grid = gridspec.GridSpec(4, 4, height_ratios=[h1,h1,h2,h2])
				axes = [plt.subplot(grid[:2,:2]), plt.subplot(grid[2,:2]), plt.subplot(grid[3,:2])]

		# todo: animation
		elif self.cutter == 'cross':
			if axis == 0:								# quadrants
				w1,w2 = shapes[0][1],shapes[1][1]
				w3 = (w1+w2)/2
				h1,h2 = shapes[0][0],shapes[2][0]			
				grid = gridspec.GridSpec(2, 4, height_ratios=[h1,h2], width_ratios=[w1,w2,w3,w3])				
				axes = [plt.subplot(grid[k//2,k%2]) for k in range(4)]
			elif axis == 1:	# y axis
				w1,w2 = shapes[0][1],shapes[1][1]
				grid = gridspec.GridSpec(2,4,width_ratios=[w1,w2,w1,w2])
				axes = [plt.subplot(grid[k//2,k%2]) for k in range(4)]
			else:	# x axis
				h1,h2 = shapes[0][0],shapes[1][0]
				grid = gridspec.GridSpec(4, 4, height_ratios=[h1,h1,h2,h2])
				axes = [plt.subplot(grid[i,:2]) for i in range(4)]

		else:
			raise ValueError('Unexpected cutter in ImageEditor.animate_cuts: {}'.format(self.cutter))

		full_ax = plt.subplot(grid[:,2:])
		full_ax.set_title('Original')
		if len(axes) != len(cuts):
			raise ValueError('Uneven axes and cuts.')
		pairs = [[axes[j],cuts[j]] for j in range(len(axes))]
		for i,p in enumerate(pairs):
			ax,cl = p
			ax.set_title('New SubImage ({})'.format(i+1))
			by,bx = cl[0].shape
			ax.set_xlim(0,bx),ax.set_ylim(0,by)
		by,bx = fmats[0].shape
		full_ax.set_xlim(0,bx), full_ax.set_ylim(0,by)
		imgs = [p[0].imshow(p[1][0], cmap='gray', clim=(0,1), animated=True) for p in pairs]
		f_img = [full_ax.imshow(fmats[0], cmap='gray', clim=(0,1), animated=True)]
		all_imgs = f_img + imgs
		
		self.connect_controls(fig)
		ani = animation.FuncAnimation(fig, genAni, genIx, blit=True, interval=self.interval,
		    repeat=True)
		plt.tight_layout()
		plt.show()

		
# functions

def not_zero(val):
	return abs(val)>10**-100

def normalize(nparray):
	max_val = nparray.max()
	if not_zero(max_val):
		return nparray/max_val
	else:
		return nparray
