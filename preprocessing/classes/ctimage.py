import os
import sys
import struct
import numpy as np
from collections import namedtuple
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import warnings
from .BaseImage.py import BaseImage

class CTImage(BaseImage):

	def __init__(self, filepath, img_data=None):
		BaseImage.__init__(self, filepath=filepath, img_data=img_data)
		self.type = 'ct'
		self.params = None
		self.header_file = filepath+'.hdr'
		self.load_header()



	def load_header(self):
        '''
        parses parameters from header file; checks line by line if line starts with keyword;
        uses first instance of keyword unless keyword in per_frame (in which case uses np.array)
        '''
        hdr_file = open(self.header_file, 'r')
        hdr_string = hdr_file.read()
        hdr_lines = hdr_string.split('\n')

        kwrds = ['axial_blocks',
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

        integers = ['data_type','z_dimension','total_frames','x_dimension','y_dimension']

        per_frame = ['scale_factor','frame_duration'] 

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