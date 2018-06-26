import os, sys
from tkinter import Tk, Label, Button



class ImageGUI:
    def __init__(self, master):
        self.master = master
        master.title("A simple GUI")

        self.pet_files,self.ct_files = self.list_files()

        self.pet_buttons = []
        for pet in self.pet_files:
            self.pet_buttons.append(Button(master,text=pet, command=lambda pet=pet: self.open_pet(pet)))
            self.pet_buttons[-1].pack()

        self.close_button = Button(master, text="Close", command=master.quit)
        self.close_button.pack()


    def new_window(self,event=None):
        new = Tk.Toplevel(self)
        new.title("window %d"%len(self.windows))
        tmp_label = Tk.Label(new,text="here is the label")
        tmp_label.grid() 
        #it is only temporary because reference is lost when the function finishes, it would be much preferable to have a separate class
        self.windows.append(new)

    def del_window(self,event=None):
        self.windows.pop().destroy()

    def open_pet(self,fname):
        print('opening image: {}'.format(fname))
        self.new_window()


    def list_files(self, folder='data'):
        folder = folder.strip('/').strip()
        pet_path = os.path.join(folder,'pet')
        ct_path = os.path.join(folder,'ct')
        pet_files = [f for f in os.listdir(pet_path) if not f.endswith('.hdr')]
        ct_files = [f for f in os.listdir(ct_path) if not f.endswith('.hdr')]
        return pet_files,ct_files




root = Tk()
root.geometry("500x500")
my_gui = ImageGUI(root)
root.mainloop()