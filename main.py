import os, sys
if sys.platform == 'darwin':
    import matplotlib
    matplotlib.use('TkAgg')
import ntpath
import tkinter as tk
from collections import defaultdict                
from tkinter import font  as tkfont 
from preprocessing.classes.baseimage import *
from preprocessing.classes.imageviewer import *
from preprocessing.settings import *






class LoadScreen(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        w = 500 # width for the Tk root
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
        label = tk.Label(self, text="Loading Image...", font=tkfont.Font(family='Helvetica', size=18, weight="bold", slant="italic"))
        label.pack(side="top", fill="x", pady=10)

        ## required to make window show before the program gets to the mainloop
        self.update()





class ImageGUI(tk.Tk):

    def __init__(self, folder='data'):
        tk.Tk.__init__(self)
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

        # default exposure scale
        self.escale = 14.0
        self.str_scale = tk.StringVar()

        # escaler coords
        self.escaler_x,self.escaler_y = 360,245
        
        # view axis
        self.view_ax = 'z'
        
        # image info coords
        self.iicoords = (20,140)

        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold", slant="italic")

        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (ImageSelector, ImageRotator, ImageCutter, CutViewer):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame

            # put all of the pages in the same location;
            # the one on the top of the stacking order
            # will be the one that is visible.
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("ImageSelector")


    def get_files(self):

        def is_pet(fname):
            if 'pet' in fname and '.ct' not in fname and fname.endswith('.img'):
                return True
            else:
                return False
        
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
        frame.tkraise()

        try:
            frame.re_init()
        except Exception as e:
            print(e)


    def start_img(self,img):
        self.withdraw()
        splash = LoadScreen(self)        
        self.image_editor = ImageEditor(img,escale=self.escale)
        self.image_editor.image.load_image()
        splash.destroy()
        self.deiconify()
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

    def init_img_info(self,frame):
        if frame.img_info is not None:
            frame.img_info.destroy()
        frame.img_info = self.get_img_info(frame)
        coords = self.iicoords
        frame.img_info.place(x=coords[0],y=coords[1])



class ImageSelector(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Select Image", font=controller.title_font)
        label.grid(row=0,column=1,columnspan=2,padx=(30,0),pady=(0,20))
        
        petcol = 1
        ctcol = 2

        # pad space
        tk.Label(self,text=' '*25).grid(column=0)

        col_title_font = tkfont.Font(family='Helvetica', size=14)
        tk.Label(self, text="PET Images", font=col_title_font).grid(row=1,column=petcol)
        tk.Label(self, text="CT Images", font=col_title_font).grid(row=1,column=ctcol)


        img_pairs = self.controller.get_files()
        for i,pair in enumerate(img_pairs):
            try:
                im1,im2 = pair
            except:
                im1,im2 = pair[0],None
            for im in [im1,im2]:
                if im is not None:
                    column = petcol if im.type == 'pet' else ctcol
                    tk.Button(self,
                        text=im.filename,
                        command = lambda im=im: controller.start_img(im)).grid(row=i+2,column=column)


        # self.pet_buttons = []
        # for i,pet in enumerate(self.pet_files):
        #     self.pet_buttons.append(
        #         tk.Button(self, 
        #         text=pet.filename,
        #         anchor='e',
        #         command=lambda pet=pet: controller.start_img(pet)))
        #     self.pet_buttons[-1].grid(row=i+1,column=1,padx=40)
        # self.ct_buttons = []
        # for i,ct in enumerate(self.ct_files):
        #     self.ct_buttons.append(
        #         tk.Button(self,
        #             text=ct.filename,
        #             anchor='w',
        #             command=lambda ct=ct: controller.start_img(ct)
        #             ))
        #     self.ct_buttons[-1].grid(row=i+1,column=3)


    def re_init(self):
        self.controller.nmice=None



class ImageRotator(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.img_info = None
        
        # title
        label = tk.Label(self, text="Image Rotator", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        
        # indicate nmice reminder
        tk.Label(self, 
            text="Number of mice must be indicated before continuing.", 
            font=tkfont.Font(family='Helvetica', size=12, weight="bold"),
            fg='red'
            ).pack(side="top",fill="x",pady=15)

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
        tk.Button(self, text="rotate on x axis", command=lambda : self.rotate_on_axis('x')).place(x=rotbx,y=rotby)
        tk.Button(self, text="rotate on y axis", command=lambda : self.rotate_on_axis('y')).place(x=rotbx,y=rotby+30)
        tk.Button(self, text="rotate on z axis", command=lambda : self.rotate_on_axis('z')).place(x=rotbx,y=rotby+60)
        

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
                self.controller.show_frame('CutViewer')
            else:
                self.controller.show_frame('ImageCutter')
        else:
            print('Specify number of mice before continuing.')

    def set_nmice(self):
        nmice = self.tknmice.get()
        if nmice is not None:
            self.controller.image_editor.nmice = self.tknmice.get()
            self.controller.nmice = self.tknmice.get()


class ImageCutter(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.img_info = None

        # title
        label = tk.Label(self, text="Image Cutter", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        # recenter crosshairs
        rbx,rby = 20,240
        tk.Button(self,text="Recenter",command=self.recenter).place(x=rbx,y=rby)

        # exposure scale
        self.escale_label = None
        self.escale_apply = None
        self.escaler = None
        self.controller.init_escaler(self)

        # back, next
        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self,text="Cut Image",command=self.do_cut).place(x=nbbx+180,y=nbby)

        # view axes
        vbx, vby = 200,220
        viewy = tk.Button(self,text="View collapsed y-axis",command=lambda:self.change_ax('y')).place(x=vbx,y=vby)
        viewz = tk.Button(self,text="View collapsed z-axis",command=lambda:self.change_ax('z')).place(x=vbx,y=vby+30)
        
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

    def do_cut(self):
        self.controller.image_editor.cut_image()
        self.controller.show_frame('CutViewer')


class CutViewer(tk.Frame):

    def __init__(self, parent, controller):
        
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.view_ax = 'z'

        self.img_info = None
        

        label = tk.Label(self, text="Review", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        # back, next
        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self, text="Save",command=self.save_cuts).place(x=nbbx+180,y=nbby)

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

    def animate_cuts(self):
        self.controller.image_editor.stop_animation()
        if self.controller.image_editor.nmice == 1:
            self.controller.image_editor.animate_collapse(self.controller.view_ax)
        else:
            self.controller.image_editor.animate_cuts(self.controller.view_ax)

    def change_ax(self,ax):
        self.controller.view_ax = ax
        self.animate_cuts()

    def save_cuts(self):
        self.controller.image_editor.image.save_cuts()

if __name__ == "__main__":
    data_folder = os.path.join('data','pcds')
    app = ImageGUI(folder=data_folder)
    app.mainloop()