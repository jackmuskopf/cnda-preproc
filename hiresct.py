import os
import sys
import struct
import numpy as np
import ntpath
from collections import namedtuple
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import warnings


class BaseImage:

    def __init__(self, filepath=None, img_data=None, frame_range=None):
        self.filepath = filepath
        self.img_data = img_data
        self.ax_map = {'z':0,'y':1,'x':2}
        self.struct_flags = {
                                1:'B',
                                2:'h',
                                3:'i',
                                4:'f'
                            }
        self.frame_range = frame_range
        if filepath is not None:
            self.filename = ntpath.basename(filepath)
            fpcs = self.filename.split('_')
            if len(fpcs) >= 4:
                self.subject_id = fpcs[0] + fpcs[3].split('.')[0]
            else:
                self.subject_id = fpcs[0]
        self.cuts = None
        self.scale_factor = None
        self.scaled = None


    def load_header(self):
        '''
        parses parameters from header file; checks line by line if line starts with keyword;
        uses first instance of keyword unless keyword in per_frame (in which case uses np.array)
        '''
        hdr_file = open(self.header_file, 'r')
        hdr_string = hdr_file.read()
        hdr_lines = hdr_string.split('\n')

        kwrds = self.keywords
        integers = self.integers
        per_frame = self.per_frame
        params = {kw : None for kw in kwrds}

        for kw in kwrds:
            for line in hdr_lines:
                kv = params[kw]
                try:
                    if kw == line.strip()[0:len(kw)]:
                        if kw in per_frame:
                            if kv is None:
                                params[kw] = np.array([])
                            params[kw] = np.append(params[kw], float(line.strip().split(' ')[1]))
                        elif kv is None:
                            ks = line.strip().split(' ')[1]
                            if kw in integers:
                                params[kw] = int(ks)
                            else:
                                params[kw] = float(ks)
                except IndexError:
                    pass

        failed = [kw for kw in kwrds if params[kw] is None]
        if any(failed):
            raise ValueError('Failed to parse parameters: {}'.format(', '.join(failed)))
        hdr_file.close()
    
        Parameters = namedtuple('Parameters',' '.join(kwrds))
        self.params = Parameters(**params)
        return


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
        x,y,z,fs = self.params.x_dimension,self.params.y_dimension,self.params.z_dimension,self.params.total_frames
        print('File dimensions: ({},{},{},{})'.format(x,y,z,fs))
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

        
        # some calcs with params
        if self.type == 'pet':
            axial_fov=ps.axial_blocks*ps.axial_crystals_per_block*ps.axial_crystal_pitch+ps.axial_crystal_pitch
            Iz_size=ps.z_dimension
            Iz_pixel=axial_fov/ps.z_dimension
            aspect=Iz_pixel/ps.pixel_size
            calib_scale_factor=ps.scale_factor*(ps.calibration_factor/ps.isotope_branching_fraction);
            
        
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

        bpp = bytes_per_pixel[ps.data_type]
        sf = self.struct_flags[ps.data_type]

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
            imgmat = imgmat.reshape(nplanes,ps.x_dimension,ps.y_dimension,nframes)
            if multi_plane and (not multi_frame):
                imgmat = imgmat[0:nplanes,:,:,0]
                self.scale_factor = ps.scale_factor[fr1]
            elif (not multi_plane) and multi_frame:
                imgmat = imgmat[0,:,:,0:nframes]
                self.scale_factor = ps.scale_factor[fr1:fr2+1]
            elif (not multi_plane) and (not multi_frame):
                imgmat = imgmat[0,:,:,0]
                self.scale_factor = ps.scale_factor[fr1]
            else: 
                imgmat = imgmat[0:nplanes,:,:,0:nframes]      
                self.scale_factor = ps.scale_factor[fr1:fr2+1]
            imgmat = imgmat*self.scale_factor
            self.img_data = imgmat.reshape(nplanes,ps.y_dimension,ps.x_dimension,nframes)
            self.scaled = True

        return