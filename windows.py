
import os
import tkinter as tk                
from tkinter import font  as tkfont 
from preprocessing.classes.BaseImage import *
from preprocessing.classes.ImageViewer import *
from preprocessing.settings import *

class ImageGUI(tk.Tk):

    def __init__(self, folder='data'):
        tk.Tk.__init__(self)

        self.geometry("500x500")

        self.img_type = None
        self.fileprefix = None
        self.image_editor = None
        self.folder = folder
        self.pet_path =  os.path.join(folder,'pet')
        self.ct_path = os.path.join(folder,'ct')
        self.escale_default = 14.0
        self.view_ax = 'z'

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


    def list_files(self, folder='data'):
        folder = folder.strip('/').strip()
        pet_files = [f for f in os.listdir(self.pet_path) if not f.endswith('.hdr')]
        ct_files = [f for f in os.listdir(self.ct_path) if not f.endswith('.hdr')]
        return pet_files,ct_files
        


    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()
        try:
            frame.init_ani()
        except:
            pass

    def start_pet(self,fileprefix):
        self.img_type = 'pet'
        self.fileprefix = fileprefix.split('.')[0]
        self.image_editor = ImageEditor(PETImage(self.fileprefix,self.pet_path),escale=self.escale_default)
        self.image_editor.image.load_image()
        self.show_frame("ImageRotator")


    def adjust_escale(self,escale):
        if self.image_editor is not None:
            self.image_editor.escale = float(escale)


class ImageSelector(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Select Image", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        self.pet_files,self.ct_files = self.controller.list_files()

        self.pet_buttons = []
        for pet in self.pet_files:
            self.pet_buttons.append(tk.Button(self,text=pet, command=lambda pet=pet: controller.start_pet(pet)))
            self.pet_buttons[-1].pack()

        self.close_button = tk.Button(self, text="Close", command=controller.quit)
        self.close_button.pack()



class ImageRotator(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        label = tk.Label(self, text="Image Rotator", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        

        back = tk.Button(self, text="Back",command=lambda: controller.show_frame("ImageSelector"))
        back.pack()

        escaler = tk.Scale(self, from_=1, to=100, resolution=.05, orient=tk.HORIZONTAL, command=self.controller.adjust_escale)
        escaler.set(self.controller.escale_default)

        escaler.pack()
        
        applyb = tk.Button(self, text="Apply",command=self.animate_axes)
        applyb.pack()

        self.tknmice = tk.IntVar()
        R1 = tk.Radiobutton(self, text="1 mouse", variable=self.tknmice, value=1,
                          command=self.set_nmice)
        R1.pack( anchor = tk.W )
        R2 = tk.Radiobutton(self, text="2 mice", variable=self.tknmice, value=2,
                          command=self.set_nmice)
        R2.pack( anchor = tk.W )
        R3 = tk.Radiobutton(self, text="3 or 4 mice", variable=self.tknmice, value=4,
                          command=self.set_nmice)
        R3.pack( anchor = tk.W)

        rotxb = tk.Button(self, text="rotate on x axis", command=lambda : self.rotate_on_axis('x'))
        rotyb = tk.Button(self, text="rotate on y axis", command=lambda : self.rotate_on_axis('y'))
        rotzb = tk.Button(self, text="rotate on z axis", command=lambda : self.rotate_on_axis('z'))
        nextb = tk.Button(self,text="Next",command=self.next_page)
        for b in [rotxb, rotyb, rotzb, nextb]:
            b.pack()

    def init_ani(self):
        self.animate_axes()

    def back(self):
        self.controller.image_editor.stop_animation()
        self.show_frame('ImageSelector')

    def animate_axes(self):
        self.controller.image_editor.stop_animation()
        self.controller.image_editor.animate_axes()

    def rotate_on_axis(self,ax):
        self.controller.image_editor.image.rotate_on_axis(ax)
        self.animate_axes()

    def next_page(self):
        if self.controller.image_editor.nmice is not None:
            self.controller.image_editor.stop_animation()
            self.controller.show_frame('ImageCutter')
        else:
            print('Specify number of mice before continuing.')

    def set_nmice(self):
        self.controller.image_editor.nmice = self.tknmice.get()


class ImageCutter(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Image Cutter", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)

        escaler = tk.Scale(self, from_=1, to=100, resolution=.05, orient=tk.HORIZONTAL, command=self.controller.adjust_escale)
        escaler.set(self.controller.escale_default)

        escaler.pack()
        applyb = tk.Button(self,text="apply",command=self.start_cutter)
        applyb.pack()
        backb = tk.Button(self, text="back",command=self.back)
        viewx = tk.Button(self,text="view collapsed x axis",command=lambda:self.change_ax('x'))
        viewy = tk.Button(self,text="view collapsed y axis",command=lambda:self.change_ax('y'))
        viewz = tk.Button(self,text="view collapsed z axis",command=lambda:self.change_ax('z'))
        docut = tk.Button(self,text="do cut",command=self.docut)

        for b in [backb,viewx,viewy,viewz,docut]:
            b.pack()

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

    def docut(self):
        self.controller.image_editor.cut_image()
        self.controller.show_frame('CutViewer')


class CutViewer(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.view_ax = 'z'
        label = tk.Label(self, text="Review Cut", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        backb = tk.Button(self, text="back",command=self.back)
        viewx = tk.Button(self,text="view collapsed x axis",command=lambda:self.change_ax('x'))
        viewy = tk.Button(self,text="view collapsed y axis",command=lambda:self.change_ax('y'))
        viewz = tk.Button(self,text="view collapsed z axis",command=lambda:self.change_ax('z'))

        escaler = tk.Scale(self, from_=1, to=100, resolution=.05, orient=tk.HORIZONTAL, command=self.controller.adjust_escale)
        escaler.set(self.controller.escale_default)

        escaler.pack()

        for b in [backb,viewx,viewy,viewz]:
            b.pack()

    def init_ani(self):
        self.animate_cuts()

    def back(self):
        self.controller.image_editor.stop_animation()
        self.controller.show_frame('ImageCutter')

    def animate_cuts(self):
        self.controller.image_editor.stop_animation()
        self.controller.image_editor.animate_cuts(self.controller.view_ax)

    def change_ax(self,ax):
        self.controller.view_ax = ax
        self.animate_cuts()

if __name__ == "__main__":
    app = ImageGUI()
    app.mainloop()