import os, sys
if sys.platform == 'darwin':
    import matplotlib
    matplotlib.use('TkAgg')
import ntpath
import tkinter as tk                
from tkinter import font  as tkfont 
from preprocessing.classes.baseimage import *
from preprocessing.classes.imageviewer import *
from preprocessing.settings import *



def is_pet(fname):
    if 'pet' in fname and '.ct' not in fname and fname.endswith('.img'):
        return True
    else:
        return False

class ImageGUI(tk.Tk):

    def __init__(self, folder='data'):
        tk.Tk.__init__(self)
        w = 500 # width for the Tk root
        h = 500 # height for the Tk root

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
        # self.pet_path =  os.path.join(folder,'pet')
        # self.ct_path = os.path.join(folder,'ct')
        self.escale = 14.0
        self.view_ax = 'z'
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


    def list_files(self):
        fnames = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.folder) for f in filenames]
        pet_files =  [f for f in fnames if is_pet(f)]
        ct_files = [f for f in fnames if f.endswith('.ct.img')]
        return pet_files,ct_files
        


    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()

        try:
            frame.re_init()
        except Exception as e:
            print(e)

    def start_pet(self,filepath):
        self.img_type = 'pet'
        self.filepath = filepath
        self.image_editor = ImageEditor(PETImage(filepath),escale=self.escale)
        self.image_editor.image.load_image()
        self.show_frame("ImageRotator")


    def get_escaler(self, frame):
        escaler = tk.Scale(frame, from_=1, to=100, resolution=.05, orient=tk.HORIZONTAL, label='Exposure', command=self.adjust_escale)
        escaler.set(self.escale)
        return escaler


    def adjust_escale(self,escale):
        if self.image_editor is not None:
            self.image_editor.escale = float(escale)
        self.escale = float(escale)

    def get_img_info(self,frame):
        fname = ntpath.basename(self.filepath)
        nframes = self.image_editor.image.nframes
        nmice = self.nmice if self.nmice is not None else '?'
        text = '\n'.join(['File : {}',
                        'Number of frames : {}',
                        'Number of mice : {}'
            ]).format(fname,nframes,nmice)
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
        label.pack(side="top", fill="x", pady=10)

        self.pet_files,self.ct_files = self.controller.list_files()

        self.pet_buttons = []
        for pet in self.pet_files:
            self.pet_buttons.append(tk.Button(self, text=ntpath.basename(pet), command=lambda pet=pet: controller.start_pet(pet)))
            self.pet_buttons[-1].pack()

        self.close_button = tk.Button(self, text="Close", command=controller.quit)
        self.close_button.pack()



class ImageRotator(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.img_info = None
        
        label = tk.Label(self, text="Image Rotator", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        
        tk.Label(self, 
            text="Number of mice must be indicated before continuing.", 
            font=tkfont.Font(family='Helvetica', size=12, weight="bold"),
            fg='red'
            ).pack(side="top",fill="x",pady=15)

        tk.Label(self, 
            text="\n".join([
                'Notes on rotation:',
                'x-axis: belly should be up, head to right',
                'y-axis: head should be up, heart on right']), 
            font=tkfont.Font(family='Helvetica', size=9),
            justify=tk.LEFT
            ).place(x=20,y=320)

        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self,text="Next",command=self.next_page).place(x=nbbx+180,y=nbby)
       
        
        self.scaler_x,self.scaler_y = 380,210
        tk.Button(self, text="Apply",command=self.re_init).place(x=self.scaler_x+30,y=self.scaler_y+60)
        self.init_escaler()

        rbx,rby = 20,240
        tk.Label(self, text="Number of mice:").place(x=rbx,y=rby-20)
        self.tknmice = tk.IntVar()
        R1 = tk.Radiobutton(self, text="1 mouse", variable=self.tknmice, value=1,command=self.set_nmice).place(x=rbx,y=rby)
        R2 = tk.Radiobutton(self, text="2 mice", variable=self.tknmice, value=2,command=self.set_nmice).place(x=rbx,y=rby+20)
        R3 = tk.Radiobutton(self, text="3 or 4 mice", variable=self.tknmice, value=4,command=self.set_nmice).place(x=rbx,y=rby+40)

        rotbx,rotby = 200,220
        tk.Button(self, text="rotate on x axis", command=lambda : self.rotate_on_axis('x')).place(x=rotbx,y=rotby)
        tk.Button(self, text="rotate on y axis", command=lambda : self.rotate_on_axis('y')).place(x=rotbx,y=rotby+30)
        tk.Button(self, text="rotate on z axis", command=lambda : self.rotate_on_axis('z')).place(x=rotbx,y=rotby+60)
        

    def re_init(self):
        self.controller.init_img_info(self)
        self.init_escaler()
        self.init_ani()

    def init_escaler(self):
        try:
            self.escaler.destroy()
        except:
            pass
        self.escaler = self.controller.get_escaler(self)
        self.escaler.place(x=self.scaler_x,y=self.scaler_y)

    def init_ani(self):
        self.animate_axes()

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

        label = tk.Label(self, text="Image Cutter", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        rbx,rby = 20,240
        tk.Button(self,text="Recenter",command=self.recenter).place(x=rbx,y=rby)

        self.scaler_x,self.scaler_y = 380,210
        tk.Button(self, text="Apply",command=self.init_ani).place(x=self.scaler_x+30,y=self.scaler_y+60)
        self.init_escaler()

        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self,text="Cut Image",command=self.do_cut).place(x=nbbx+180,y=nbby)

        vbx, vby = 200,220
        viewy = tk.Button(self,text="View collapsed y-axis",command=lambda:self.change_ax('y')).place(x=vbx,y=vby)
        viewz = tk.Button(self,text="View collapsed z-axis",command=lambda:self.change_ax('z')).place(x=vbx,y=vby+30)
        
    def recenter(self):
        self.controller.image_editor.cx, self.controller.image_editor.cy = self.controller.image_editor.cx_def, self.controller.image_editor.cy_def
        self.init_ani()


    def re_init(self):
        self.controller.init_img_info(self)
        self.controller.view_ax = 'z'
        self.init_escaler()
        self.init_ani()

    def back(self):
        self.controller.image_editor.stop_animation()
        self.controller.show_frame('ImageRotator')

    def init_escaler(self):
        try:
            self.escaler.destroy()
        except:
            pass
        self.escaler = self.controller.get_escaler(self)
        self.escaler.place(x=self.scaler_x,y=self.scaler_y)

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

        # back button
        nbbx,nbby = 135,400
        tk.Button(self, text="Back",command=self.back).place(x=nbbx,y=nbby)
        tk.Button(self, text="Save").place(x=nbbx+180,y=nbby)

        vbx, vby = 200,220
        tk.Button(self,text="View collapsed x-axis",command=lambda:self.change_ax('x')).place(x=vbx,y=vby)
        tk.Button(self,text="View collapsed y-axis",command=lambda:self.change_ax('y')).place(x=vbx,y=vby+30)
        tk.Button(self,text="View collapsed z-axis",command=lambda:self.change_ax('z')).place(x=vbx,y=vby+60)
        
        self.scaler_x,self.scaler_y = 380,210
        tk.Button(self, text="Apply",command=self.re_init).place(x=self.scaler_x+30,y=self.scaler_y+60)
        self.init_escaler()
        

    def re_init(self):
        self.controller.init_img_info(self)
        self.init_escaler()
        self.init_ani()


    def init_escaler(self):
        try:
            self.escaler.destroy()
        except:
            pass
        self.escaler = self.controller.get_escaler(self)
        self.escaler.place(x=self.scaler_x,y=self.scaler_y)

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

if __name__ == "__main__":
    data_folder = os.path.join('data','pcds')
    app = ImageGUI(folder=data_folder)
    app.mainloop()