import os, sys
if sys.platform == 'darwin':
    import matplotlib
    matplotlib.use('TkAgg')
import ntpath
import atexit
import gc
import tkinter as tk
import tempfile
import traceback
import inspect
import shutil
import numpy as np
from tkinter import Tk
from collections import defaultdict                
from tkinter import font  as tkfont 
from tkinter.filedialog import askopenfilename, askdirectory
from preprocessing.classes.baseimage import PETImage, CTImage, SubImage
from preprocessing.classes.imageviewer import ImageEditor

TEMPLOG = 'templog.txt'

def check_img_data(ie):
    try:
        getattr(ie.image,'img_data')
        print('Yes img_data')
    except AttributeError:
        print('No img_data')

class SplashScreen(tk.Toplevel):
    def __init__(self, parent, text, yn=False):
        self.__name__ = 'LoadScreen'
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        w = 530 # width for the Tk root
        h = 250 # height for the Tk root

        # get screen width and height
        ws = self.winfo_screenwidth() # width of the screen
        hs = self.winfo_screenheight() # height of the screen

        # calculate x and y coordinates for the Tk root window
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)

        # set the dimensions of the screen 
        # and where it is placed
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.title("Image Preprocessing")

        # size buttons
        sz = 18 if not yn else 11
        label = tk.Label(self, text=text, font=tkfont.Font(family='Helvetica', size=sz, weight="bold", slant="italic"))
        label.pack(side="top", fill="x", pady=10)

        if yn:
            tk.Button(self, text="Yes",command=lambda:self.return_yn(True)).pack(side=tk.RIGHT, fill="x", padx=(0,120))
            tk.Button(self, text="No",command=lambda:self.return_yn(False)).pack(side=tk.LEFT, fill="x", padx=(120,0))
        
        ## required to make window show before the program gets to the mainloop
        self.update()


    def return_yn(self,yn):
        print('Setting splash_yn: {}'.format(yn))
        self.parent.splash_yn = yn
        self.parent.stop_splash()



class ImageGUI(tk.Tk):

    def __init__(self, folder='data'):
        tk.Tk.__init__(self)
        self.__name__ = 'ImageGUI'
        self.title("Image Preprocessing")
        w = 500 # width for the Tk root
        h = 550 # height for the Tk root

        # get screen width and height
        ws = self.winfo_screenwidth() # width of the screen
        hs = self.winfo_screenheight() # height of the screen

        # calculate x and y coordinates for the Tk root window
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)

        # set the dimensions of the screen 
        # and where it is placed
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))

        self.img_type = None
        self.filepath = None
        self.image_editor = None
        self.nmice = None
        self.folder = folder.strip('/').strip('\\').strip()
        self.tempdirs = []

        # default exposure scale
        self.escale = 14.0
        self.str_scale = tk.StringVar()

        # escaler coords
        self.escaler_x,self.escaler_y = 360,245
        
        # view axis
        self.view_ax = 'z'
        
        # image info coords
        self.iicoords = (20,140)

        # attribute to hold splash screen
        self.splash = None

        # attribute to hold which frame is raised
        self.raised_frame = None

        # attribute to hold which frame was raised last
        self.last_frame = None

        # attribute to hold result from splash y/n var
        self.splash_yn = None

        # title font var
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold", slant="italic")

        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (ImageSelector, ImageRotator, ImageCutter, CutViewer, HeaderUI, ConfirmSave):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame

            # put all of the pages in the same location;
            # the one on the top of the stacking order
            # will be the one that is visible.
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("ImageSelector")


    def get_files(self):
        
        fnames = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.folder) for f in filenames]
        pet_files =  [PETImage(f) for f in fnames if is_pet(f)]
        ct_files = [CTImage(f) for f in fnames if f.endswith('.ct.img')]
        all_files = pet_files+ct_files
        all_files.sort(key=lambda x: x.subject_id)
        groups = defaultdict(list)
        for img in all_files:
            groups[img.subject_id].append(img)
        img_pairs = groups.values()
        return img_pairs
        


    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        self.last_frame = self.raised_frame
        self.raised_frame = frame.__name__
        frame.tkraise()

        try:
            frame.re_init()
        except AttributeError as e:
            print_error(e)

    def make_splash(self,text='Loading...',yn=False):
        self.withdraw()
        self.splash = SplashScreen(self,text=text,yn=yn)

    def stop_splash(self):
        self.splash.destroy()
        self.deiconify()

    def load_image(self):
        tdir = tempfile.mkdtemp()
        log_temp_dir(tdir)
        self.image_editor.image.tempdir = tdir
        self.image_editor.image.load_image()


    def start_img(self,img):
        self.make_splash()       
        self.image_editor = ImageEditor(img,escale=self.escale)
        self.load_image()
        self.tempdirs.append(self.image_editor.image.tempdir)
        self.stop_splash()
        self.show_frame("ImageRotator")

    def init_escaler(self, frame):
        self.adjust_escale(frame)
        try:
            frame.escaler.destroy()
        except:
            pass
        frame.escaler = self.make_escale(frame)
        frame.escaler.place(x=self.escaler_x,y=self.escaler_y)

        if frame.escale_label is None:
            frame.escale_label = tk.Label(frame, text="Exposure Scale:",justify=tk.LEFT).place(x=self.escaler_x,y=self.escaler_y-30)
        if frame.escale_apply is None:
            frame.escale_apply = tk.Button(frame, text="Apply",command=frame.re_init).place(x=self.escaler_x+30,y=self.escaler_y+30)

    def make_escale(self, frame):
        self.str_scale.set(str(self.escale))
        escaler = tk.Entry(frame,textvariable=self.str_scale)
        return escaler


    def adjust_escale(self,frame):
        if frame.escaler is not None:
            try:
                self.escale = float(self.str_scale.get())
            except ValueError:
                print('Cannot interpret input {} exposure scale as a float.'.format(frame.str_scale.get()))
                return
            if self.image_editor is not None:
                self.image_editor.escale = self.escale


    def get_img_info(self,frame):
        fname = self.image_editor.image.filename
        nmice = self.nmice if self.nmice is not None else '?'
        z,y,x,frames = self.image_editor.image.img_data.shape
        text = '\n'.join(['File : {}'.format(fname),
                        'Number of frames : {}'.format(frames),
                        'Frame dimensions : ({0}, {1}, {2})'.format(x,y,z),
                        'Number of mice : {}'.format(nmice)
            ])
        label = tk.Label(frame,text=text,font=tkfont.Font(family='Helvetica', size=9),justify=tk.LEFT)
        return label

    def init_img_info(self,frame,coords=None):
        if frame.img_info is not None:
            frame.img_info.destroy()
        frame.img_info = self.get_img_info(frame)
        if coords is None:
            coords = self.iicoords
        frame.img_info.place(x=coords[0],y=coords[1])

    def remove_temp_dirs(self):
        self.clean_memmaps()
        for directory in self.tempdirs:
            try:
                shutil.rmtree(directory)
                print('Removed tempdir: {}'.format(directory))
                self.tempdirs.remove(directory)
            except Exception as e:
                print('Failed to remove tempdir: {0}\n{1}'.format(directory,e))
        
    def clean_memmaps(self):
        if self.image_editor is not None:
            if self.image_editor.image is not None:
                self.image_editor.image.clean_cuts()
                try:
                    delattr(self.image_editor.image,'img_data')
                except AttributeError:
                    pass
                fn = '{}.dat'.format(self.image_editor.image.filename.split('.')[0])
                fp = os.path.join(self.image_editor.image.tempdir,fn)
                if os.path.exists(fp):
                    os.remove(fp)
        self.image_editor = None
        gc.collect()


class ImageSelector(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.__name__ = 'ImageSelector'
        self.controller = controller
        self.controller.remove_temp_dirs()
        label = tk.Label(self, text="Select Image", font=controller.title_font)
        label.grid(row=0,column=1,columnspan=2,padx=(30,0),pady=(0,20))
        
        self.petcol = 1
        self.ctcol = 2

        # pad space
        tk.Label(self,text=' '*25).grid(column=0)

        ## labels for displayed image types
        # col_title_font = tkfont.Font(family='Helvetica', size=14)
        # tk.Label(self, text="PET Images", font=col_title_font).grid(row=2,column=self.petcol)
        # tk.Label(self, text="CT Images", font=col_title_font).grid(row=2,column=self.ctcol)

        # browse for file
        tk.Button(self, text='Browse', command=self.browse_file).grid(row=1,column=1,columnspan=1,padx=(30,0),pady=(0,20))
        tk.Button(self, text='Quit', command=lambda app=self.controller:exit_fn(app)).grid(row=1,column=2,columnspan=1,padx=(30,0),pady=(0,20))

        self.make_buttons()



    def re_init(self):
        self.controller.remove_temp_dirs() # do this when we select new file
        self.controller.nmice=None
        for b in self.buttons:
            b.destroy()
        self.make_buttons()

    def make_buttons(self):
        img_pairs = self.controller.get_files()

        self.buttons = []
        for i,pair in enumerate(img_pairs):
            try:
                im1,im2 = pair
            except:
                im1,im2 = pair[0],None
            for im in [im1,im2]:
                if im is not None:
                    column = self.petcol if im.type == 'pet' else self.ctcol
                    b = tk.Button(self,
                        text=im.filename,
                        command = lambda im=im: self.controller.start_img(im))
                    b.grid(row=i+3,column=column)
                    self.buttons.append(b)

    def browse_file(self):
        Tk().withdraw()
        fpath = askopenfilename()
        if fpath:
            if fpath.endswith('.hdr'):
                fpath = '.'.join(fpath.split('.')[:-1])
            fname = ntpath.basename(fpath)
            if is_pet(fname):
                img = PETImage(fpath)
            else:
                img = CTImage(fpath)
            self.controller.start_img(img)




class ImageRotator(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.__name__ = 'ImageRotator'
        self.controller = controller
        self.img_info = None
        
        # title
        label = tk.Label(self, text="Image Rotator", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        
        # reminder to specify nmice
        self.nmice_msg = None

        # rotator instructions
        tk.Label(self, 
            text="\n".join([
                'Notes on rotation:',
                'x-axis: belly should be up, head to right',
                'y-axis: head should be up, heart on right']), 
            font=tkfont.Font(family='Helvetica', size=9),
            justify=tk.LEFT
            ).place(x=20,y=320)

        # next, back
        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self,text="Next",command=self.next_page).place(x=nbbx+180,y=nbby)
       
        # exposure scale
        self.escale_label = None
        self.escale_apply = None
        self.escaler = None
        self.controller.init_escaler(self)

        # nmice selector
        self.rbx,self.rby = 20,240
        tk.Label(self, text="Number of mice:").place(x=self.rbx,y=self.rby-20)
        self.R1,self.R2,self.R3,self.tknmice = None,None,None,None
        self.init_nmice_select()
 

        rotbx,rotby = 200,220
        tk.Button(self, text="Rotate on x axis", command=lambda : self.rotate_on_axis('x')).place(x=rotbx,y=rotby)
        tk.Button(self, text="Rotate on y axis", command=lambda : self.rotate_on_axis('y')).place(x=rotbx,y=rotby+30)
        tk.Button(self, text="Rotate on z axis", command=lambda : self.rotate_on_axis('z')).place(x=rotbx,y=rotby+60)
        

    def re_init(self):
        self.controller.init_img_info(self)
        self.controller.init_escaler(self)
        self.init_nmice_select()
        self.init_ani()


    def init_ani(self):
        self.animate_axes()

    def init_nmice_select(self):
        if self.controller.nmice is None:
            self.tknmice = tk.IntVar()      
            for r in [self.R1,self.R2,self.R3]:
                if r is not None:
                    r.destroy()
            self.R1 = tk.Radiobutton(self, text="1 mouse", variable=self.tknmice, value=1, command=self.set_nmice)
            self.R2 = tk.Radiobutton(self, text="2 mice", variable=self.tknmice, value=2, command=self.set_nmice)
            self.R3 = tk.Radiobutton(self, text="3 or 4 mice", variable=self.tknmice, value=4, command=self.set_nmice)
            self.R1.place(x=self.rbx,y=self.rby)
            self.R2.place(x=self.rbx,y=self.rby+20)
            self.R3.place(x=self.rbx,y=self.rby+40)

    def back(self):
        self.controller.image_editor.stop_animation()
        self.controller.show_frame('ImageSelector')

    def animate_axes(self):
        self.controller.image_editor.stop_animation()
        self.controller.image_editor.animate_axes()

    def rotate_on_axis(self,ax):
        self.controller.image_editor.image.rotate_on_axis(ax)
        self.animate_axes()

    def next_page(self):
        if self.controller.image_editor.nmice is not None:
            self.controller.image_editor.stop_animation()
            if self.controller.image_editor.nmice == 1:
                self.controller.view_ax = 'x'
                im = self.controller.image_editor.image
                fpcs = im.filename.split('.')
                if not fpcs[0].endswith('_s1'):
                    fpcs[0]+='_s1'
                self.controller.image_editor.image.filename = '.'.join(fpcs)
                self.controller.image_editor.image.cuts = [self.controller.image_editor.image] #[SubImage(parent_image=im,img_data=im.img_data,filename='.'.join(fpcs))]
                self.controller.show_frame('CutViewer')
            else:
                self.controller.show_frame('ImageCutter')
        else:
            self.nmice_warn()
            print('Specify number of mice before continuing.')

    def set_nmice(self):
        nmice = self.tknmice.get()
        if nmice is not None:
            self.controller.image_editor.nmice = self.tknmice.get()
            self.controller.nmice = self.tknmice.get()

    def nmice_warn(self):
        if self.nmice_msg:
            self.nmice_msg.destroy()
        color = np.random.choice(["blue","red","green","purple","orange","maroon","cyan","indigo","yellow","violet","pink","turquoise"])
        self.nmice_msg = tk.Label(self, 
            text="Number of mice must be indicated before continuing.", 
            font=tkfont.Font(family='Helvetica', size=12, weight="bold"),
            fg=color)
        self.nmice_msg.pack(side="top",fill="x",pady=15)


class ImageCutter(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.__name__ = 'ImageCutter'
        self.controller = controller
        self.img_info = None

        # title
        label = tk.Label(self, text="Image Cutter", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        # recenter crosshairs
        rbx,rby = 200,340
        tk.Button(self,text="Recenter",command=self.recenter).place(x=rbx,y=rby)

        # choose cutter
        tk.Label(self,text='Choose cutter:').place(x=20,y=220)
        cbx,cby = 20,240
        tk.Button(self,text="Cross",command=lambda:self.set_cutter('cross')).place(x=cbx,y=cby)
        tk.Button(self,text="Up T",command=lambda:self.set_cutter('up_T')).place(x=cbx,y=cby+30)
        tk.Button(self,text="Down T",command=lambda:self.set_cutter('down_T')).place(x=cbx,y=cby+60)
        tk.Button(self,text="Horizontal",command=lambda:self.set_cutter('horizontal')).place(x=cbx,y=cby+90)
        tk.Button(self,text="Vertical",command=lambda:self.set_cutter('vertical')).place(x=cbx,y=cby+120)

        # exposure scale
        self.escale_label = None
        self.escale_apply = None
        self.escaler = None
        self.controller.init_escaler(self)

        # back, next
        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self,text="Cut Image",command=self.do_cut).place(x=nbbx+180,y=nbby)

        # # view axes
        # vbx, vby = 200,220
        # viewy = tk.Button(self,text="View collapsed y-axis",command=lambda:self.change_ax('y')).place(x=vbx,y=vby)
        # viewz = tk.Button(self,text="View collapsed z-axis",command=lambda:self.change_ax('z')).place(x=vbx,y=vby+30)
        
    def recenter(self):
        self.controller.image_editor.cx, self.controller.image_editor.cy = self.controller.image_editor.cx_def, self.controller.image_editor.cy_def
        self.init_ani()


    def re_init(self):
        self.controller.init_img_info(self)
        self.controller.view_ax = 'z'
        self.controller.init_escaler(self)
        self.init_ani()

    def back(self):
        self.controller.image_editor.stop_animation()
        self.controller.show_frame('ImageRotator')

    def init_ani(self):
        self.start_cutter()

    def start_cutter(self):
        self.controller.image_editor.stop_animation()
        self.controller.image_editor.animated_cutter(view_ax=self.controller.view_ax)

    def change_ax(self,ax):
        self.controller.view_ax = ax
        self.start_cutter()

    def set_cutter(self,cutter):
        self.controller.image_editor.cutter=cutter
        self.re_init()

    def do_cut(self):
        self.controller.image_editor.cut_image()
        self.controller.show_frame('CutViewer')


class CutViewer(tk.Frame):

    def __init__(self, parent, controller):
        
        tk.Frame.__init__(self, parent)
        self.__name__ = 'CutViewer'
        self.controller = controller
        self.view_ax = 'z'

        self.img_info = None
        

        label = tk.Label(self, text="Review", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        # back, next
        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self, text="Next",command=self.next).place(x=nbbx+180,y=nbby)

        # view axes
        vbx, vby = 200,220
        tk.Button(self,text="View collapsed x-axis",command=lambda:self.change_ax('x')).place(x=vbx,y=vby)
        tk.Button(self,text="View collapsed y-axis",command=lambda:self.change_ax('y')).place(x=vbx,y=vby+30)
        tk.Button(self,text="View collapsed z-axis",command=lambda:self.change_ax('z')).place(x=vbx,y=vby+60)
        
        # exposure scale
        self.escale_label = None
        self.escale_apply = None
        self.escaler = None
        self.controller.init_escaler(self)
        

    def re_init(self):
        self.controller.init_img_info(self)
        self.controller.init_escaler(self)
        self.init_ani()

    def init_ani(self):
        self.animate_cuts()

    def back(self):
        self.controller.image_editor.stop_animation()
        if self.controller.image_editor.nmice == 1:
            self.controller.show_frame('ImageRotator')
        else:
            self.controller.show_frame('ImageCutter')

    def next(self):
        self.controller.image_editor.stop_animation()
        self.controller.show_frame('HeaderUI')

    def animate_cuts(self):
        self.controller.image_editor.stop_animation()
        if self.controller.image_editor.nmice == 1:
            self.controller.image_editor.animate_collapse(self.controller.view_ax)
        else:
            self.controller.image_editor.animate_cuts(view_ax=self.controller.view_ax)

    def change_ax(self,ax):
        self.controller.view_ax = ax
        self.animate_cuts()





class HeaderUI(tk.Frame):

    def __init__(self, parent, controller):

        self.__name__ = 'HeaderUI'
        
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.controller = controller
        self.img_info = None

        # local image editor for controlling animation of each cut
        self.ie = None
        self.cut = None
        self.title = None

        # pad space
        tk.Label(self,text=' '*30).grid(column=0)  

        # exposure scale
        self.escale_label = None
        self.escale_apply = None
        self.escaler = None

        


    def re_init(self):
        self.reset_attrs()
        self.cut_ix = 0 if self.controller.last_frame == 'CutViewer' else len(self.controller.image_editor.image.cuts)-1
        
        # coords for placing entry boxes and labels
        self.er,self.ec = 1,1
        self.hdr_attrs = ['filename','animal_number','subject_weight']

        # input file info
        if self.controller.image_editor.image.type == 'ct':
            pass
        elif self.controller.image_editor.image.type == 'pet':
            self.hdr_attrs += ['dose','injection_time']
        else:
            raise ValueError('Unexpected image type: {}'.format(self.controller.image_editor.image.type))


        try:
            self.destroy_buttons()
        except AttributeError:
            pass

        self.controller.init_img_info(self,coords=(30,self.controller.escaler_y))
        self.controller.init_escaler(self)

        er,ec = self.er,self.ec
        for i,attr in enumerate(self.hdr_attrs):
            setattr(self,attr,tk.StringVar(value=''))
            entry = tk.Entry(self,textvariable=getattr(self,attr),width=40)
            entry_attr = attr+'_entry'
            setattr(self,entry_attr,entry)
            getattr(self,entry_attr).grid(row=er+i,column=ec+1)
            label_attr = attr+'_label'
            setattr(self,label_attr,tk.Label(self,text=get_label(attr)))
            getattr(self,label_attr).grid(row=er+i,column=ec)

        # add title
        self.update_title()

        # back, next
        nbbx,nbby = 135,400
        self.back_button = tk.Button(self, text="Back",command=self.back)
        self.back_button.place(x=nbbx,y=nbby)
        self.next_button = tk.Button(self, text="Next",command=self.increment_cut)
        self.next_button.place(x=nbbx+180,y=nbby)

        self.cut = self.controller.image_editor.image.cuts[0]
        self.init_cut()


    def update_title(self):
        if self.title is not None:
            self.title.destroy()
        self.title = tk.Label(self, text="Cut {} Header Information".format(self.cut_ix+1), font=self.controller.title_font, justify=tk.LEFT)
        self.title.grid(row=0,column=1,columnspan=2,padx=(0,0),pady=(10,20))



    def increment_cut(self):
        self.update_cut()
        self.cut_ix += 1
        if self.cut_ix < len(self.controller.image_editor.image.cuts):
            self.update_title()
            self.cut = self.controller.image_editor.image.cuts[self.cut_ix]
            self.init_cut()
        else:
            self.destroy_buttons()
            self.controller.image_editor.stop_animation()
            self.reset_attrs()
            self.controller.show_frame('ConfirmSave')


    def decrement_cut(self):
        self.cut_ix -= 1
        self.update_title()
        self.cut = self.controller.image_editor.image.cuts[self.cut_ix]
        self.init_cut()


    def init_cut(self):
        self.init_entries()
        self.init_ani()

    def init_ani(self):
        self.controller.image_editor.stop_animation()
        self.ie = ImageEditor(self.cut, escale=self.controller.image_editor.escale)
        self.ie.animate_axes()

    def init_entries(self):
        for attr in self.hdr_attrs:
            if (not attr=='filename'):
                _ = getattr(self.cut.params,attr)
                if _ is not None:
                    getattr(self,attr).set(_)

        self.filename.set(self.cut.filename)

    def update_cut(self):
        for attr in self.hdr_attrs:
            entry_attr = attr+'_entry'
            entry = getattr(self,entry_attr)
            val = entry.get().strip()
            if attr=='filename':
                self.cut.filename = val
            else:
                setattr(self.cut.params, attr, val)

    def destroy_buttons(self):
        
        for attr in self.hdr_attrs:
            entry_attr = attr+'_entry'
            label_attr = attr+'_label'
            getattr(self,entry_attr).destroy()
            getattr(self,label_attr).destroy()
        self.next_button.destroy()
        self.back_button.destroy()

    def reset_attrs(self):
        self.ie = None
        self.cut = None
        gc.collect()


    def back(self):
        self.update_cut()
        if self.cut_ix > 0:
            self.decrement_cut()
        else:
            self.destroy_buttons()
            self.controller.image_editor.stop_animation()
            self.reset_attrs()
            self.controller.show_frame('CutViewer')



class ConfirmSave(tk.Frame):

    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.__name__ = 'ConfirmSave'


    def re_init(self):
        # pad space
        tk.Label(self,text=' '*30).grid(column=0)
        
        # title
        label = tk.Label(self, text="Confirm", font=self.controller.title_font)
        label.grid(row=0,column=0,columnspan=2,padx=(30,0),pady=(0,20))        

        params_to_display = ['animal_number','injection_time','dose','subject_weight','filename']
        for i,cut in enumerate(self.controller.image_editor.image.cuts):
            for j,param in enumerate(params_to_display):
                jx=j+1
                if param == 'filename':
                    val = cut.filename
                else:
                    try:
                        val = getattr(cut.params,param)
                    except AttributeError:
                        val = None
                if val is not None:
                    r,c = jx+(i//2)*len(params_to_display),i%2
                    r = r+1 if i>1 else r
                    px = c*10+5
                    tk.Label(self,text='{0} : {1}'.format(get_label(param),val)).grid(row=r,column=c,padx=(px,0))
        
        # space
        tk.Label(self,text=' '*50).grid(row=6,column=0,columnspan=2)
        tk.Label(self,text=' '*50).grid(row=12,column=0,columnspan=2)

        brow = len(params_to_display)*2+3
        self.back_button = tk.Button(self, text="Back",command=self.back)
        self.back_button.grid(column=0,row=brow)
        self.save_button = tk.Button(self, text="Save",command=self.save_cuts)
        self.save_button.grid(column=1,row=brow)
        self.init_ani()

    def init_ani(self):
        self.controller.image_editor.animate_cuts()


    def clear_widgets(self):
        for widget in self.winfo_children():
            widget.destroy()

    def back(self):
        self.controller.image_editor.stop_animation()
        self.controller.show_frame('HeaderUI')

    def check_paths(self, path):
        new_files = [os.path.join(path,cut.filename) for cut in self.controller.image_editor.image.cuts]
        for f in new_files:
            overwrite = [tf for tf in (f,f+'.hdr') if os.path.exists(tf)]
            if overwrite:
                ow_msg = '\n'.join(['The following files will be overwritten:']+overwrite+['Do you want to continue?'])
                self.controller.make_splash(text=ow_msg, yn=True)
                print('Returning {}'.format(self.controller.splash_yn))
                return self.controller.splash_yn
            else:
                return True




    def save_cuts(self):
        Tk().withdraw()
        save_path = askdirectory()
        if save_path:
            ok_save = self.check_paths(save_path)
            if ok_save:
                self.controller.make_splash(text='Saving images...')
                self.controller.image_editor.image.save_cuts(path=save_path)
                self.controller.stop_splash()
                self.controller.image_editor.stop_animation()
                self.controller.remove_temp_dirs()
                self.controller.frames['ImageSelector'].re_init()   # don't need to do this?
                self.controller.show_frame('ImageSelector')




# functions

def check_memmap(data):
    refs = gc.get_referrers(*[data])
    print("{} referrers: [{}]".format(len(refs),' ,'.join([str(type(r)) for r in refs])))
    for r in refs:
        if type(r) is type(sys._getframe()):
            print('FRAME: {}'.format(inspect.getframeinfo(r)))

def get_label(attr_name):
    if attr_name == 'dose':
        return 'Injection Dose'
    elif attr_name == 'injection_time':
        return 'Injection Datetime'
    else:
        return attr_name.replace('_',' ').title()


def is_pet(fname):
    if 'pet' in fname and '.ct' not in fname and fname.endswith('.img'):
        return True
    else:
        return False

def clean_temp_dirs():
    if os.path.exists(TEMPLOG):
        with open(TEMPLOG,'r') as tlog:
            tlog_txt = tlog.read()
        tdirs = list(set([d for d in tlog_txt.split('\n') if d]))
        for d in tdirs:
            try:
                shutil.rmtree(d)
                print('Removed tempdir: {}'.format(d))
                tdirs.remove(d)
            except Exception as e:
                if not os.path.exists(d):
                    tdirs.remove(d)
                else:
                    print('Failed to remove tempdir: {0}\n{1}'.format(d,e))
        with open(TEMPLOG,'w') as tlog:
            tlog.write('\n'.join(tdirs))


def log_temp_dir(directory):
    if os.path.exists(TEMPLOG):
        ap_wr = 'a'
    else:
        ap_wr = 'w'

    tlog = open(TEMPLOG, ap_wr)
    tlog.write('\n{}'.format(directory))
    tlog.close()


def exit_fn(app):
    if app.image_editor is not None:
        app.image_editor.stop_animation()
        if app.image_editor.image is not None:
            for i,cut in enumerate(app.image_editor.image.cuts):
                del cut.img_data
            del app.image_editor.image.img_data
    app.destroy()
    del app
    gc.collect()
    clean_temp_dirs()
    sys.exit(0)


def print_error(e):
    exc_info = sys.exc_info()
    exc_type, exc_obj, exc_tb = exc_info
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    traceback.print_exception(*exc_info)
    print('{}\n'.format(e),exc_type, fname, exc_tb.tb_lineno)
    


if __name__ == "__main__":
    gc.collect()
    clean_temp_dirs()
    data_folder = os.path.join('data','pcds')
    app = ImageGUI(folder=data_folder)
    app.protocol("WM_DELETE_WINDOW", lambda app=app:exit_fn(app))
    app.mainloop()