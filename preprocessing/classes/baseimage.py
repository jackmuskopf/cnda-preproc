import os
import sys
import struct
import numpy as np
import ntpath
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import warnings

from collections import namedtuple

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
        self.cuts = []
        self.scale_factor = None
        self.scaled = None
        self.bpp = None # bytes per pixel
        self.tempdir = None
        self.data_lim = 10**7  # 10 MB


    def submemmap(self, ix, data):
        if self.tempdir is None:
            raise ValueError('self.tempdir is None in self.sub_memmap.')
        fnpcs = self.filename.split('.')
        fnpcs[0] = fnpcs[0] + '_s{}'.format(ix)
        filename = '.'.join(fnpcs)
        img_temp_name = os.path.join(self.tempdir,'{}.dat'.format(filename.split('.')[0]))
        if os.path.exists(img_temp_name):
            os.remove(img_temp_name)
        dfile = np.memmap(img_temp_name, mode='w+', dtype='float32', shape=data.shape)
        dfile[:] = data[:]
        return filename, dfile



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
        def read_chunks(ifr):
            '''
            Trying to read data in chunks to handle HiResCt images
            '''
            to_read = bpp*matsize
            read_lim = self.data_lim
            print('Will read {0} {1}MB chunks.'.format(to_read/read_lim,int(read_lim/10**6)))
            ix = 0
            while to_read > read_lim:
                print('Reading new chunk; {}MB left'.format(int(to_read/10**6)))
                nbytes = read_lim
                npixels = int(nbytes/bpp)
                chunk = np.array(struct.unpack(sf*npixels,img_file.read(nbytes)))
                imgmat[ifr][ix:ix+npixels] = chunk
                to_read -= read_lim
                ix+=npixels

            print('Reading new chunk; {}MB left'.format(int(to_read/10**6)))
            nbytes = to_read
            npixels = int(nbytes/bpp)
            chunk = np.array(struct.unpack(sf*npixels,img_file.read(nbytes)))
            imgmat[ifr][ix:ix+npixels] = chunk



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
        self.bpp = bpp
        sf = self.struct_flags[ps.data_type]

        # read data from file
        print('Reading image data...')
        
        img_file = open(self.filepath,'rb')
        matsize = ps.x_dimension*ps.y_dimension*nplanes
        pl_offset = pl[0]*(ps.x_dimension*ps.y_dimension)

        # make tempfile for whole image
        img_temp_name = os.path.join(self.tempdir,'{}.dat'.format(self.filename.split('.')[0]))
        imgmat = np.memmap(img_temp_name,mode='w+',dtype='float32',shape=(nframes,matsize))
        
        for ifr in frames:  
            fr_offset = ifr*(ps.x_dimension*ps.y_dimension*ps.z_dimension)
            img_file.seek(bpp*(fr_offset+pl_offset))
            read_chunks(ifr)
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


    def save_cuts(self,path):


        def write_chunks(data, dfile):
            '''
            Trying to read data in chunks to handle HiResCt images
            '''
            if self.bpp is None:
                raise ValueError('self.bpp not defined in self.save_cuts')
            bpp = self.bpp

            total_pixels = len(data)
            bytes_to_write = total_pixels*bpp
            write_lim = self.data_lim
            print('Will read {0} {1}MB chunks.'.format(bytes_to_write/write_lim,int(write_lim/10**6)))
            ix = 0
            while bytes_to_write > write_lim:
                print('Writing new chunk; {}MB left'.format(int(bytes_to_write/10**6)))
                nbytes = write_lim
                npixels = int(nbytes/bpp)
                chunk = data[ix:ix+npixels]
                dfile.write(struct.pack(npixels*sf, *chunk))
                bytes_to_write -= write_lim
                ix += npixels

            print('Writing new chunk; {}MB left'.format(int(bytes_to_write/10**6)))
            nbytes = bytes_to_write
            npixels = int(nbytes/bpp)
            chunk = data[ix:ix+npixels]
            dfile.write(struct.pack(npixels*sf, *chunk))
            return



        print('Saving files...')
        if not self.cuts:
            raise ValueError('Image has not been cut in BaseImage.save_cuts()')
        if path is None:
            raise ValueError('Path not specified')
        sf  = self.struct_flags[self.params.data_type]

        hdr_file = open(self.header_file, 'r')
        hdr_string = hdr_file.read()
        hdr_lines = hdr_string.split('\n')
        for i,cut_img in enumerate(self.cuts):
            cut_hdr_lines = hdr_lines
            for dim in ['x_dimension','y_dimension','z_dimension']:
                for j,line in enumerate(cut_hdr_lines):
                    if line.strip().startswith(dim):
                        cut_hdr_lines[j] = ' '.join([dim,str(getattr(cut_img,dim))])
                        break
            cut_filename = cut_img.filename
            cut_hdr_name = cut_filename+'.hdr'
            cut_hdr_str = '\n'.join(cut_hdr_lines)

            with open(os.path.join(path,cut_hdr_name),'w') as hf:
                hf.write(cut_hdr_str)

            out_data = cut_img.img_data
            out_data = out_data.reshape(cut_img.xdim*cut_img.ydim*cut_img.zdim,cut_img.nframes)
            # out_data.resize((cut_img.xdim*cut_img.ydim*cut_img.zdim,cut_img.nframes),refcheck=False)
            if self.scaled:
                inv = lambda x: 1/x
                v_inv = np.vectorize(inv)
                inv_scale_factor = v_inv(self.scale_factor)
                out_data = out_data*inv_scale_factor

            # prepare data to write out
            out_data = out_data.swapaxes(0,1).flatten()
            
            # make sure data is int if it is supposed to be
            if sf in ['i','B','h']:
                out_data = out_data.astype(int)

            with open(os.path.join(path,cut_filename),'wb') as dfile:
                write_chunks(out_data,dfile)
                # dfile.write(struct.pack(nd*sf,*out_data))
            print('File saved.')

    def clean_cuts(self):
        '''
        remove existing cuts
        '''
        for cut in self.cuts:
            try:
                delattr(cut,'img_data')
            except AttributeError:
                pass
            fn = '{}.dat'.format(cut.filename.split('.')[0])
            fp = os.path.join(self.tempdir,fn)
            if os.path.exists(fp):
                os.remove(fp)

    def get_axis(self,axis):
        '''
        converts axis x,y,z to 2,1,0 for use with numpy
        '''
        if axis not in ['x', 'y', 'z'] + list(range(3)):
            raise ValueError('Invalid axis input: {}\nUse axis in ["x","y",z",1,2,3].'.format(axis))
        try:
            axis = self.ax_map[axis]
        except KeyError:
            pass
        return axis

    def check_data(self):
        if self.img_data is None:
            raise ValueError('self.img_data has not been intialized. Use image.load_image()')
   
    def check_collapse_method(self,method):
        if method not in ['sum','mean','max']:
            raise ValueError('Unrecognized input collapse method: {}'.format(method))


    def get_frame(self,n):
        
        self.check_data()
       
        if self.frame_range is None:
            raise ValueError('self.frame_range has not been declared in self.get_frame()')

        f1,f2 = tuple(self.frame_range)
        if n not in range(f1,f2+1):
            raise IndexError('Specified frame {0} is not in loaded range {1}'.format(n,self.frame_range))
        return self.img_data[:,:,:,f1-n]

    def collapse_frame(self,axis,frame=None,method='sum'):
        if frame is None:
            matrix = self.img_data
        else:
            matrix = self.get_frame(frame)
        ax = self.get_axis(axis)
        self.check_collapse_method(method)
        cmatrix = getattr(matrix,method)(axis=ax)
        return cmatrix

    def collapse_over_frames(self,method,matrix=None):
        if matrix is None:
            matrix = self.img_data
        self.check_collapse_method(method)
        return getattr(self.img_data,method)(axis=3)

    def rotate_on_axis(self, axis):
        self.check_data()
        axis = self.get_axis(axis)
        axes_to_flip = [0,1,2]
        axes_to_flip.remove(axis)
        self.img_data = np.flip(self.img_data,axes_to_flip[0])
        self.img_data = np.flip(self.img_data,axes_to_flip[1])

    def split_on_axis(self,matrix,axis):
        axis = self.get_axis(axis)
        mats = np.split(matrix, matrix.shape[axis], axis=axis)
        mats = [np.squeeze(m) for m in mats]
        return mats


class SubImage(BaseImage):

    def __init__(self, parent_image, img_data, filename):

        # make tempfile
        self.filename = filename

        BaseImage.__init__(self, filepath='./{}'.format(self.filename), img_data=img_data)
        self.type = parent_image.type
        self.parent_image = parent_image
        self.frame_range = parent_image.frame_range
        self.plane_range = parent_image.plane_range
        self.scaled = parent_image.scaled
        shape = self.img_data.shape
        self.zdim, self.ydim, self.xdim, self.nframes = shape
        self.x_dimension,self.y_dimension,self.z_dimension = self.xdim,self.ydim,self.zdim
        self.bounds={0 : (self.ydim, self.xdim), 
                    1 : (self.xdim, self.zdim),
                    2 : (self.zdim, self.ydim)}



# make so can initialize with np matrix
class PETImage(BaseImage):

    def __init__(self, filepath, img_data=None):
        '''
        Needs header file and data file in same directory
        '''
        BaseImage.__init__(self, filepath, img_data)
        self.type = 'pet'

        # for header file info
        self.params = None
        self.keywords = ['axial_blocks',
                'axial_crystals_per_block',
                'axial_crystal_pitch',
                'data_type',
                'z_dimension',
                'x_dimension',
                'y_dimension',
                'pixel_size',
                'total_frames',
                'calibration_factor',
                'scale_factor',
                'isotope_branching_fraction',
                'frame_duration']
        self.integers = ['data_type','z_dimension','total_frames','x_dimension','y_dimension']
        self.per_frame = ['scale_factor','frame_duration'] 


        self.header_file = filepath+'.hdr'

        self.load_header()  # initialize params
        self.xdim = self.params.x_dimension
        self.ydim = self.params.y_dimension
        self.zdim = self.params.z_dimension
        self.x_dimension,self.y_dimension,self.z_dimension = self.xdim,self.ydim,self.zdim

        self.frame_range = None
        self.plane_range = None
        self.nframes = None

        self.bounds={0 : (self.ydim, self.xdim), 
                    1 : (self.xdim, self.zdim),
                    2 : (self.zdim, self.ydim)}
        self.scaled = None

        




class CTImage(BaseImage):

    def __init__(self, filepath, img_data=None):
        BaseImage.__init__(self, filepath=filepath, img_data=img_data)
        self.type = 'ct'
        self.params = None
        self.header_file = filepath+'.hdr'

        self.keywords = [
                'data_type',
                'z_dimension',
                'x_dimension',
                'y_dimension',
                'pixel_size',
                'total_frames',
                'calibration_factor',
                'scale_factor',
                'frame_duration']

        self.integers = ['data_type','z_dimension','total_frames','x_dimension','y_dimension']
        self.per_frame = ['scale_factor','frame_duration'] 
        self.load_header()
        self.xdim = self.params.x_dimension
        self.ydim = self.params.y_dimension
        self.zdim = self.params.z_dimension
        self.x_dimension,self.y_dimension,self.z_dimension = self.xdim,self.ydim,self.zdim

        self.frame_range = None
        self.plane_range = None
        self.nframes = None

        self.bounds={0 : (self.ydim, self.xdim), 
                    1 : (self.xdim, self.zdim),
                    2 : (self.zdim, self.ydim)}
        self.scaled = None


