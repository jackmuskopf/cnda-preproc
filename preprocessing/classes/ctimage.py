import os
import sys
import struct
import numpy as np
from collections import namedtuple
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import warnings
from .baseimage import BaseImage

class CTImage(BaseImage):

    def __init__(self, filepath, img_data=None):
        BaseImage.__init__(self, filepath=filepath, img_data=img_data)
        self.type = 'ct'
        self.params = None
        self.header_file = filepath+'.hdr'

        self.keywords = [
                #'axial_blocks',
                #'axial_crystals_per_block',
                #'axial_crystal_pitch',
                'data_type',
                'z_dimension',
                'x_dimension',
                'y_dimension',
                'pixel_size',
                'total_frames',
                'calibration_factor',
                'scale_factor',
                #'isotope_branching_fraction',
                'frame_duration']

        self.integers = ['data_type','z_dimension','total_frames','x_dimension','y_dimension']
        self.per_frame = ['scale_factor','frame_duration'] 
        self.load_header()

    def load_image(self,plane_range=None,frame_range=None,unscaled=False):
        '''
        - loads specified frames into np.ndarray
        - can do range of frames now; maybe implement list of frames
        - same for z-dimension
        - does not support selection over x,y dimensions
        - returns scaled image data; 
        - planes and frames should both be tuples corresponding to the range of planes and frames to be
        returned from the image data; 
        - defaults to all data; 
        - for single plane or single frame, just give n where n is the index
        of the plane or frame to include; 
        - index from 0, e.g. for the first 40 planes, use [0,39]
        '''
        ps = self.params

        if plane_range is None:
            if ps.z_dimension > 1:
                plane_range = [0, ps.z_dimension-1]
            else:
                plane_range = [0,0]
        elif type(plane_range) is int:
            plane_range = [plane_range,plane_range]
        else:
            plane_range = list(plane_range)
            if plane_range[-1] >= self.params.z_dimension:
                plane_range[-1] = self.params.z_dimension-1
                warnings.warn('Input z-plane range exceeds number of z-planes in data file.  Usings z-planes {}.'.format(plane_range))


        if frame_range is None:
            if ps.total_frames > 1:
                frame_range = [0, ps.total_frames-1]
            else:
                frame_range = [0,0]
        elif type(frame_range) is int:
            frame_range = [frame_range,frame_range]
        else:
            frame_range = list(frame_range)
            if frame_range[-1] >= self.params.total_frames:
                frame_range[-1] = self.params.total_frames-1
                warnings.warn('Input frame range exceeds number of frames in data file.  Usings frames {}.'.format(frame_range))


        if plane_range[1]>plane_range[0]:
            multi_plane = True
        else:
            multi_plane = False
        if frame_range[1]>frame_range[0]:
            multi_frame = True
        else:
            multi_frame = False


        pl,fr = plane_range,frame_range
        self.plane_range,self.frame_range = pl,fr

        
        # # some calcs with params
        # axial_fov=ps.axial_blocks*ps.axial_crystals_per_block*ps.axial_crystal_pitch+ps.axial_crystal_pitch
        # Iz_size=ps.z_dimension
        # Iz_pixel=axial_fov/ps.z_dimension
        # aspect=Iz_pixel/ps.pixel_size
        # calib_scale_factor=ps.scale_factor*(ps.calibration_factor/ps.isotope_branching_fraction);
        
        
        # which planes/frames to use
        npl = len(pl)
        nfr = len(fr)

        if npl > 2:
            raise ValueError('Input plane range invalid format: {}'.format(pl))
        else:
            if not multi_plane:
                pl1 = pl[0]
                pl2 = pl[0]
                planes = [pl1,]
                nplanes = 1
            else:
                pl1 = pl[0]
                pl2 = pl[1]
                planes = range(pl1,pl2+1)
                nplanes = len(planes)

        if nfr > 2:
            raise ValueError('Input frame range invalid format: {}'.format(fr))
        else:
            if not multi_frame:
                fr1 = fr[0]
                fr2 = fr[0]
                frames = [fr1,]
                nframes = 1
            else:
                fr1 = fr[0]
                fr2 = fr[1]
                frames = range(fr1,fr2+1)
                nframes = len(frames)
        self.nframes = nframes
                
            
        # file data format parameters
        bytes_per_pixel = {
            1:1,
            2:2,
            3:4,
            4:4
        }
        struct_flags = {
            1:'b',
            2:'h',
            3:'i',
            4:'f'
        }
        bpp = bytes_per_pixel[ps.data_type]
        sf = struct_flags[ps.data_type]

        # read data from file
        print('Reading image data...')
        img_file = open(self.filepath,'rb')
        matsize = ps.x_dimension*ps.y_dimension*nplanes
        pl_offset = pl[0]*(ps.x_dimension*ps.y_dimension)
        imgmat = []
        for ifr in frames:  
            fr_offset = ifr*(ps.x_dimension*ps.y_dimension*ps.z_dimension)
            img_file.seek(bpp*(fr_offset+pl_offset))
            frame_data = np.array(struct.unpack(sf*matsize,img_file.read(bpp*matsize)))
            imgmat.append(frame_data)
        imgmat = np.array(imgmat)
        imgmat = imgmat.swapaxes(0,1)
        img_file.close()
        
        # scale data
        if unscaled:
            self.img_data = imgmat
            self.scaled = False
        else:
            img_data = imgmat.reshape(nplanes,ps.x_dimension,ps.y_dimension,nframes)
            if multi_plane and (not multi_frame):
                imagemat = img_data[0:nplanes,:,:,0]
                imagemat1 = imagemat*ps.scale_factor[fr1]
            elif (not multi_plane) and multi_frame:
                imagemat = img_data[0,:,:,0:nframes]
                imagemat1 = imagemat*ps.scale_factor[fr1:fr2+1]
            elif (not multi_plane) and (not multi_frame):
                imagemat = img_data[0,:,:,0]
                imagemat1 = imagemat*ps.scale_factor[fr1]
            else: 
                imagemat = img_data[0:nplanes,:,:,0:nframes]      
                imagemat1 = imagemat*ps.scale_factor[fr1:fr2+1]
                     
            self.img_data = imagemat1.reshape(nplanes,ps.x_dimension,ps.y_dimension,nframes)
            self.scaled = True

        return