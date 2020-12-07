import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from PIL import ImageTk
from PIL import Image
import math
import warnings
import argparse
import sys
import os
import pdb
from tkinter import ttk
import csv
#global listoffiles

dirname = os.path.dirname(__file__)


class AutoScrollbar(ttk.Scrollbar):
    """ A scrollbar that hides itself if it's not needed. Works only for grid geometry manager """
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError('Cannot use pack with the widget ' + self.__class__.__name__)

    def place(self, **kw):
        raise tk.TclError('Cannot use place with the widget ' + self.__class__.__name__)


class CanvasImage:
    """ Display and zoom image """
    def __init__(self, placeholder, path):
        """ Initialize the ImageFrame """
        self.imscale = 1.0  # scale for the canvas image zoom, public for outer classes
        self.__delta = 1.3  # zoom magnitude
        self.__filter = Image.ANTIALIAS  # could be: NEAREST, BILINEAR, BICUBIC and ANTIALIAS
        self.__previous_state = 0  # previous state of the keyboard
        self.path = path  # path to the image, should be public for outer classes
        # Create ImageFrame in placeholder widget
        self.__imframe = ttk.Frame(placeholder)  # placeholder of the ImageFrame object
        # Vertical and horizontal scrollbars for canvas
        hbar = AutoScrollbar(self.__imframe, orient='horizontal')
        vbar = AutoScrollbar(self.__imframe, orient='vertical')
        hbar.grid(row=1, column=0, sticky='we')
        vbar.grid(row=0, column=1, sticky='ns')
        # Create canvas and bind it with scrollbars. Public for outer classes
        self.canvas = tk.Canvas(self.__imframe, highlightthickness=0,
                                xscrollcommand=hbar.set, yscrollcommand=vbar.set,width = 1300, height = 800)
        self.canvas.grid(row=0, column=0, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        hbar.configure(command=self.__scroll_x)  # bind scrollbars to the canvas
        vbar.configure(command=self.__scroll_y)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', lambda event: self.__show_image())  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.__move_from)  # remember canvas position
        self.canvas.bind('<B1-Motion>',     self.__move_to)  # move canvas to the new position
        self.canvas.bind('<MouseWheel>', self.__wheel)  # zoom for Windows and MacOS, but not Linux
        self.canvas.bind('<Button-5>',   self.__wheel)  # zoom for Linux, wheel scroll down
        self.canvas.bind('<Button-4>',   self.__wheel)  # zoom for Linux, wheel scroll up
        # Handle keystrokes in idle mode, because program slows down on a weak computers,
        # when too many key stroke events in the same time
        self.canvas.bind('<Key>', lambda event: self.canvas.after_idle(self.__keystroke, event))
        # Decide if this image huge or not
        self.__huge = False  # huge or not
        self.__huge_size = 14000  # define size of the huge image
        self.__band_width = 1024  # width of the tile band
        Image.MAX_IMAGE_PIXELS = 1000000000  # suppress DecompressionBombError for the big image
        with warnings.catch_warnings():  # suppress DecompressionBombWarning
            warnings.simplefilter('ignore')
            self.__image = Image.open(self.path)  # open image, but down't load it
        self.imwidth, self.imheight = self.__image.size  # public for outer classes
        if self.imwidth * self.imheight > self.__huge_size * self.__huge_size and \
           self.__image.tile[0][0] == 'raw':  # only raw images could be tiled
            self.__huge = True  # image is huge
            self.__offset = self.__image.tile[0][2]  # initial tile offset
            self.__tile = [self.__image.tile[0][0],  # it have to be 'raw'
                           [0, 0, self.imwidth, 0],  # tile extent (a rectangle)
                           self.__offset,
                           self.__image.tile[0][3]]  # list of arguments to the decoder
        self.__min_side = min(self.imwidth, self.imheight)  # get the smaller image side
        # Create image pyramid
        self.__pyramid = [self.smaller()] if self.__huge else [Image.open(self.path)]
        # Set ratio coefficient for image pyramid
        self.__ratio = max(self.imwidth, self.imheight) / self.__huge_size if self.__huge else 1.0
        self.__curr_img = 0  # current image from the pyramid
        self.__scale = self.imscale * self.__ratio  # image pyramide scale
        self.__reduction = 2  # reduction degree of image pyramid
        w, h = self.__pyramid[-1].size
        while w > 512 and h > 512:  # top pyramid image is around 512 pixels in size
            w /= self.__reduction  # divide on reduction degree
            h /= self.__reduction  # divide on reduction degree
            self.__pyramid.append(self.__pyramid[-1].resize((int(w), int(h)), self.__filter))
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle((0, 0, self.imwidth, self.imheight), width=0)
        self.__show_image()  # show image on the canvas
        self.canvas.focus_set()  # set focus on the canvas
    
    def setnewimage(self,path):
        #pdb.set_trace()
        self.path=path
        with warnings.catch_warnings():  # suppress DecompressionBombWarning
            warnings.simplefilter('ignore')
            self.__image = Image.open(self.path)  # open image, but down't load it
        self.imwidth, self.imheight = self.__image.size  # public for outer classes
        if self.imwidth * self.imheight > self.__huge_size * self.__huge_size and \
           self.__image.tile[0][0] == 'raw':  # only raw images could be tiled
            self.__huge = True  # image is huge
            self.__offset = self.__image.tile[0][2]  # initial tile offset
            self.__tile = [self.__image.tile[0][0],  # it have to be 'raw'
                           [0, 0, self.imwidth, 0],  # tile extent (a rectangle)
                           self.__offset,
                           self.__image.tile[0][3]]  # list of arguments to the decoder
        self.__min_side = min(self.imwidth, self.imheight)  # get the smaller image side
        # Create image pyramid
        self.__pyramid = [self.smaller()] if self.__huge else [Image.open(self.path)]
        # Set ratio coefficient for image pyramid
        self.__ratio = max(self.imwidth, self.imheight) / self.__huge_size if self.__huge else 1.0
        self.__curr_img = 0  # current image from the pyramid
        self.__scale = self.imscale * self.__ratio  # image pyramide scale
        self.__reduction = 2  # reduction degree of image pyramid
        w, h = self.__pyramid[-1].size
        while w > 512 and h > 512:  # top pyramid image is around 512 pixels in size
            w /= self.__reduction  # divide on reduction degree
            h /= self.__reduction  # divide on reduction degree
            self.__pyramid.append(self.__pyramid[-1].resize((int(w), int(h)), self.__filter))
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.__show_image()
        #self.canvas.focus_set()

    def smaller(self):
        """ Resize image proportionally and return smaller image """
        w1, h1 = float(self.imwidth), float(self.imheight)
        w2, h2 = float(self.__huge_size), float(self.__huge_size)
        aspect_ratio1 = w1 / h1
        aspect_ratio2 = w2 / h2  # it equals to 1.0
        if aspect_ratio1 == aspect_ratio2:
            image = Image.new('RGB', (int(w2), int(h2)))
            k = h2 / h1  # compression ratio
            w = int(w2)  # band length
        elif aspect_ratio1 > aspect_ratio2:
            image = Image.new('RGB', (int(w2), int(w2 / aspect_ratio1)))
            k = h2 / w1  # compression ratio
            w = int(w2)  # band length
        else:  # aspect_ratio1 < aspect_ration2
            image = Image.new('RGB', (int(h2 * aspect_ratio1), int(h2)))
            k = h2 / h1  # compression ratio
            w = int(h2 * aspect_ratio1)  # band length
        i, j, n = 0, 1, round(0.5 + self.imheight / self.__band_width)
        while i < self.imheight:
            print('\rOpening image: {j} from {n}'.format(j=j, n=n), end='')
            band = min(self.__band_width, self.imheight - i)  # width of the tile band
            self.__tile[1][3] = band  # set band width
            self.__tile[2] = self.__offset + self.imwidth * i * 3  # tile offset (3 bytes per pixel)
            self.__image.close()
            self.__image = Image.open(self.path)  # reopen / reset image
            self.__image.size = (self.imwidth, band)  # set size of the tile band
            self.__image.tile = [self.__tile]  # set tile
            cropped = self.__image.crop((0, 0, self.imwidth, band))  # crop tile band
            image.paste(cropped.resize((w, int(band * k)+1), self.__filter), (0, int(i * k)))
            i += band
            j += 1
        print('\r' + 30*' ' + '\r', end='')  # hide printed string
        return image

    def redraw_figures(self):
        """ Dummy function to redraw figures in the children classes """
        pass

    def grid(self, **kw):
        """ Put CanvasImage widget on the parent widget """
        self.__imframe.grid(**kw)  # place CanvasImage widget on the grid
        self.__imframe.grid(sticky='nswe')  # make frame container sticky
        self.__imframe.rowconfigure(0, weight=1)  # make canvas expandable
        self.__imframe.columnconfigure(0, weight=1)

    def pack(self, **kw):
        """ Exception: cannot use pack with this widget """
        raise Exception('Cannot use pack with the widget ' + self.__class__.__name__)

    def place(self, **kw):
        """ Exception: cannot use place with this widget """
        raise Exception('Cannot use place with the widget ' + self.__class__.__name__)

    # noinspection PyUnusedLocal
    def __scroll_x(self, *args, **kwargs):
        """ Scroll canvas horizontally and redraw the image """
        self.canvas.xview(*args)  # scroll horizontally
        self.__show_image()  # redraw the image

    # noinspection PyUnusedLocal
    def __scroll_y(self, *args, **kwargs):
        """ Scroll canvas vertically and redraw the image """
        self.canvas.yview(*args)  # scroll vertically
        self.__show_image()  # redraw the image

    def __show_image(self):
        """ Show image on the Canvas. Implements correct image zoom almost like in Google Maps """
        box_image = self.canvas.coords(self.container)  # get image area
        box_canvas = (self.canvas.canvasx(0),  # get visible area of the canvas
                      self.canvas.canvasy(0),
                      self.canvas.canvasx(self.canvas.winfo_width()),
                      self.canvas.canvasy(self.canvas.winfo_height()))
        box_img_int = tuple(map(int, box_image))  # convert to integer or it will not work properly
        # Get scroll region box
        box_scroll = [min(box_img_int[0], box_canvas[0]), min(box_img_int[1], box_canvas[1]),
                      max(box_img_int[2], box_canvas[2]), max(box_img_int[3], box_canvas[3])]
        # Horizontal part of the image is in the visible area
        if  box_scroll[0] == box_canvas[0] and box_scroll[2] == box_canvas[2]:
            box_scroll[0]  = box_img_int[0]
            box_scroll[2]  = box_img_int[2]
        # Vertical part of the image is in the visible area
        if  box_scroll[1] == box_canvas[1] and box_scroll[3] == box_canvas[3]:
            box_scroll[1]  = box_img_int[1]
            box_scroll[3]  = box_img_int[3]
        # Convert scroll region to tuple and to integer
        self.canvas.configure(scrollregion=tuple(map(int, box_scroll)))  # set scroll region
        x1 = max(box_canvas[0] - box_image[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(box_canvas[1] - box_image[1], 0)
        x2 = min(box_canvas[2], box_image[2]) - box_image[0]
        y2 = min(box_canvas[3], box_image[3]) - box_image[1]
        if int(x2 - x1) > 0 and int(y2 - y1) > 0:  # show image if it in the visible area
            if self.__huge and self.__curr_img < 0:  # show huge image
                h = int((y2 - y1) / self.imscale)  # height of the tile band
                self.__tile[1][3] = h  # set the tile band height
                self.__tile[2] = self.__offset + self.imwidth * int(y1 / self.imscale) * 3
                self.__image.close()
                self.__image = Image.open(self.path)  # reopen / reset image
                self.__image.size = (self.imwidth, h)  # set size of the tile band
                self.__image.tile = [self.__tile]
                image = self.__image.crop((int(x1 / self.imscale), 0, int(x2 / self.imscale), h))
            else:  # show normal image
                image = self.__pyramid[max(0, self.__curr_img)].crop(  # crop current img from pyramid
                                    (int(x1 / self.__scale), int(y1 / self.__scale),
                                     int(x2 / self.__scale), int(y2 / self.__scale)))
            #
            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1)), self.__filter))
            imageid = self.canvas.create_image(max(box_canvas[0], box_img_int[0]),
                                               max(box_canvas[1], box_img_int[1]),
                                               anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection

    def __move_from(self, event):
        """ Remember previous coordinates for scrolling with the mouse """
        self.canvas.scan_mark(event.x, event.y)

    def __move_to(self, event):
        """ Drag (move) canvas to the new position """
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.__show_image()  # zoom tile and show it on the canvas

    def outside(self, x, y):
        """ Checks if the point (x,y) is outside the image area """
        bbox = self.canvas.coords(self.container)  # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            return False  # point (x,y) is inside the image area
        else:
            return True  # point (x,y) is outside the image area

    def __wheel(self, event):
        """ Zoom with mouse wheel """
        x = self.canvas.canvasx(event.x)  # get coordinates of the event on the canvas
        y = self.canvas.canvasy(event.y)
        if self.outside(x, y): return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        #pdb.set_trace()
        if event.num == 5 or event.delta == -1:  # scroll down, smaller
            if round(self.__min_side * self.imscale) < 30: return  # image is less than 30 pixels
            self.imscale /= self.__delta
            scale        /= self.__delta
        if event.num == 4 or event.delta == 1:  # scroll up, bigger
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height()) >> 1
            if i < self.imscale: return  # 1 pixel is bigger than the visible area
            self.imscale *= self.__delta
            scale        *= self.__delta
        # Take appropriate image from the pyramid
        k = self.imscale * self.__ratio  # temporary coefficient
        self.__curr_img = min((-1) * int(math.log(k, self.__reduction)), len(self.__pyramid) - 1)
        self.__scale = k * math.pow(self.__reduction, max(0, self.__curr_img))
        #
        self.canvas.scale('all', x, y, scale, scale)  # rescale all objects
        # Redraw some figures before showing image on the screen
        self.redraw_figures()  # method for child classes
        self.__show_image()

    def __keystroke(self, event):
        """ Scrolling with the keyboard.
            Independent from the language of the keyboard, CapsLock, <Ctrl>+<key>, etc. """
        if event.state - self.__previous_state == 4:  # means that the Control key is pressed
            pass  # do nothing if Control key is pressed
        else:
            self.__previous_state = event.state  # remember the last keystroke state
            # Up, Down, Left, Right keystrokes
            #pdb.set_trace()
            if event.keycode in [68, 40, 102]:  # scroll right, keys 'd' or 'Right'
                self.__scroll_x('scroll',  1, 'unit', event=event)
            elif event.keycode in [65, 38, 100]:  # scroll left, keys 'a' or 'Left'
                self.__scroll_x('scroll', -1, 'unit', event=event)
            elif event.keycode in [87, 25, 104]:  # scroll up, keys 'w' or 'Up'
                self.__scroll_y('scroll', -1, 'unit', event=event)
            elif event.keycode in [83, 39, 98]:  # scroll down, keys 's' or 'Down'
                self.__scroll_y('scroll',  1, 'unit', event=event)

    def crop(self, bbox):
        """ Crop rectangle from the image and return it """
        if self.__huge:  # image is huge and not totally in RAM
            band = bbox[3] - bbox[1]  # width of the tile band
            self.__tile[1][3] = band  # set the tile height
            self.__tile[2] = self.__offset + self.imwidth * bbox[1] * 3  # set offset of the band
            self.__image.close()
            self.__image = Image.open(self.path)  # reopen / reset image
            self.__image.size = (self.imwidth, band)  # set size of the tile band
            self.__image.tile = [self.__tile]
            return self.__image.crop((bbox[0], 0, bbox[2], band))
        else:  # image is totally in RAM
            return self.__pyramid[0].crop(bbox)

    def destroy(self):
        """ ImageFrame destructor """
        self.__image.close()
        map(lambda i: i.close, self.__pyramid)  # close all pyramid images
        del self.__pyramid[:]  # delete pyramid list
        del self.__pyramid  # delete pyramid variable
        self.canvas.destroy()
        self.__imframe.destroy()

class mdatastruct:
    'data structure for bouding box'
    def __init__(self,filename,general,genus,species,alive):
        self.general=general
        self.genus=genus
        self.species=species
        self.alive=alive
        self.filename=filename


class App:
    #currentimg=0
    #listoffiles=[]
    #fileID
    general='unk'
    genus='unk'
    species='unk'
    alive='unk'
    #fileID = open("openfile.csv", 'w')
    currentimage_name='unk'
    current_image_place=0
    listoffiles=[]

    
    def __init__(self, master):
        self.master = master
        self.majorlist=[]
        self.frame0 = tk.Frame(self.master)
        self.frame1 = tk.Frame(self.master, width = 1200, height = 1000)

        self.button0 = ttk.Button(self.frame0, text = 'Set Directory', width = 15, command = self.mset_directory)
        self.text0=tk.Label(self.frame0,width = 7, text="General", fg="#9C9C9C")
        self.text1=tk.Label(self.frame0,width = 7, text="Genus", fg="#9C9C9C")
        self.text2=tk.Label(self.frame0,width = 7, text="Species", fg="#9C9C9C")
        self.text3=tk.Label(self.frame0,width = 7, text="Alive", fg="#9C9C9C")

        self.tkvargen=tk.StringVar(self.master)
        self.generallist=["unk","bare","water","lichen","moss","forb","grass","shrub"]
        self.tkvargen.set(self.generallist[0])
        self.dropdownmenugeneral=ttk.Combobox(self.frame0,width=15,textvariable=self.tkvargen,values=self.generallist)

        self.entrygenus=tk.Entry(self.frame0, width = 15)

        self.entryspecies=tk.Entry(self.frame0, width = 15)

        self.tkvaralive=tk.StringVar(self.master)
        self.alivelist=["unk","yes","no"]
        self.tkvaralive.set(self.alivelist[0])
        self.dropdownmenualive=ttk.Combobox(self.frame0,textvariable=self.tkvaralive,values=self.alivelist, width = 15)
        
        self.savebutton=ttk.Button(self.frame0,text='Save',width = 15, command = self.savefile)

        self.button0.grid(row=0,column=1, columnspan=2, pady =30) # set directory
        self.text0.grid(row=1,column=0) # genera
        self.text1.grid(row=2,column=0) # genus
        self.text2.grid(row=3,column=0) # species
        self.text3.grid(row=4,column=0) # alive

        self.dropdownmenugeneral.grid(row=1,column=1, columnspan=2)
        self.entrygenus.grid(row=2,column=1, columnspan=2)
        self.entryspecies.grid(row=3,column=1, columnspan=2)
        self.dropdownmenualive.grid(row=4,column=1, columnspan=2)

        self.savebutton.grid(row=5,column=1, columnspan=2, pady=30)
        master.bind('<Control-s>', lambda event: self.savefile())
        
        self.button_prev = ttk.Button(self.frame0, text = '<', width = 7, command = self.prevfile)
        self.button_next = ttk.Button(self.frame0, text = '>', width = 7, command = self.nextfile)        
        master.bind('<Right>', lambda event: self.nextfile()) # key bind for next image
        master.bind('<Left>', lambda event: self.prevfile()) # key bind for prev image
        self.button_prev.grid(row=6,column=1, pady = 10)
        self.button_next.grid(row=6,column=2, pady =10)        


        self.frame0.grid(row=0,column=0)
        self.frame1.grid(row=0,column=1)

        # button to open reference image in new window
        # buttonref = ttk.Button(self.frame0, text='Common Plants of Nunavut', command=self.refimage, width=20)
        # master.bind('<space>', lambda event: self.refimage())
        # buttonref.grid(row=7,column=1, columnspan = 2)


    def refimage(self):
        nwin = tk.Toplevel()
        nwin.title("Common Plants of Nunavut")

        photo2 = tk.PhotoImage(file = os.path.join(dirname, 'refimage.gif'))
        lbl2 = tk.Label(nwin, image = photo2)
        lbl2.pack()
        nwin.wm_protocol("WM_DELETE_WINDOW", lambda: self.onDeleteChild(nwin))
        # exitb = ttk.Button(nwin, text="Close", command=lambda: self.onDeleteChild(nwin))
        nwin.bind('<space>', lambda event: self.onDeleteChild(nwin)) # key bind for closing reference image

        # function to exit just the reference window


        nwin.mainloop()

    def onDeleteChild(self, w):
        w.destroy()

    def quit(self):
        self.top.destroy()
    
    def __enter__(self):
        return self

    def __exit__(self,exc_type,exc_val,exc_tb):
        pass
        #self.fileID.close()
    def readfromfile(self):
        #self.fileID=open(self.directory+'/output.txt','r')
        #cont=self.fileID.readlines()
        #pdb.set_trace()
        #for line in cont:
        #    reader=csv.reader(line)
        #    row1=next(reader)
        #    self.majorlist.append(mdatastruct(row1[0],row1[1],row1[2],row1[3],row1[4]))
        #    self.majorlist.append(mdatastruct(self.wavefilelist[i],'unk','unk','unk','unk'))
        #pdb.set_trace()
        with open(self.directory+'/output.txt', newline='') as f:
            reader=csv.reader(f)
            for row1 in reader:
                self.majorlist.append(mdatastruct(row1[0],row1[1],row1[2],row1[3],row1[4]))
            self.wavefilelistlocation=0
            self.alive=self.majorlist[self.wavefilelistlocation].alive
            self.general=self.majorlist[self.wavefilelistlocation].general
            self.genus=self.majorlist[self.wavefilelistlocation].genus
            self.species=self.majorlist[self.wavefilelistlocation].species
            self.entrygenus.delete(0,tk.END)
            self.entrygenus.insert(0,self.genus)
            self.entryspecies.delete(0,tk.END)
            self.entryspecies.insert(0,self.species)
            #pdb.set_trace()
            self.dropdownmenugeneral.current(self.generallist.index(self.general))
            self.dropdownmenualive.current(self.alivelist.index(self.alive))    
        #pdb.set_trace()

        #    row1=next(reader)
        #    self.majorlist.append(mdatastruct(row1[0],row1[1],row1[2],row1[3],row1[4]))
        #    pdb.set_trace()    

 
    def savefile(self):
        self.fileID=open(self.directory+'/output.txt','w+')
        self.alive=self.tkvaralive.get()
        self.general=self.tkvargen.get()
        self.genus=self.entrygenus.get()
        self.species=self.entryspecies.get()
        self.majorlist[self.wavefilelistlocation].alive=self.alive
        self.majorlist[self.wavefilelistlocation].general=self.general
        self.majorlist[self.wavefilelistlocation].genus=self.genus
        self.majorlist[self.wavefilelistlocation].species=self.species
        for obj in self.majorlist:
            self.fileID.write(obj.filename+','+obj.general+','+obj.genus+','+obj.species+','+ obj.alive+'\n')
        self.fileID.close()    

    def nextfile(self):
        #pdb.set_trace()
        self.alive=self.tkvaralive.get()
        self.general=self.tkvargen.get()
        self.genus=self.entrygenus.get()
        self.species=self.entryspecies.get()
        self.majorlist[self.wavefilelistlocation].alive=self.alive
        self.majorlist[self.wavefilelistlocation].general=self.general
        self.majorlist[self.wavefilelistlocation].genus=self.genus
        self.majorlist[self.wavefilelistlocation].species=self.species
        if self.wavefilelistlocation < len(self.wavefilelist)-1:
            self.wavefilelistlocation=self.wavefilelistlocation+1
            self.setcanvasimage(self.directory+'/'+self.wavefilelist[self.wavefilelistlocation])
            try:
                #pdb.set_trace()
                self.alive=self.majorlist[self.wavefilelistlocation].alive
                self.general=self.majorlist[self.wavefilelistlocation].general
                self.genus=self.majorlist[self.wavefilelistlocation].genus
                self.species=self.majorlist[self.wavefilelistlocation].species
                self.entrygenus.delete(0,tk.END)
                self.entrygenus.insert(0,self.genus)
                self.entryspecies.delete(0,tk.END)
                self.entryspecies.insert(0,self.species)
                #pdb.set_trace()
                self.dropdownmenugeneral.current(self.generallist.index(self.general))
                self.dropdownmenualive.current(self.alivelist.index(self.alive))

                #pdb.set_trace()
                #self.dropdownmenugeneral.current
            except:
                print('didnt work')    
         

    def prevfile(self):
        #pdb.set_trace()
        self.alive=self.tkvaralive.get()
        self.general=self.tkvargen.get()
        self.genus=self.entrygenus.get()
        self.species=self.entryspecies.get()
        self.majorlist[self.wavefilelistlocation].alive=self.alive
        self.majorlist[self.wavefilelistlocation].general=self.general
        self.majorlist[self.wavefilelistlocation].genus=self.genus
        self.majorlist[self.wavefilelistlocation].species=self.species
        if 0<self.wavefilelistlocation:
            self.wavefilelistlocation=self.wavefilelistlocation-1
            self.setcanvasimage(self.directory+'/'+self.wavefilelist[self.wavefilelistlocation])
            try:
                #pdb.set_trace()
                self.alive=self.majorlist[self.wavefilelistlocation].alive
                self.general=self.majorlist[self.wavefilelistlocation].general
                self.genus=self.majorlist[self.wavefilelistlocation].genus
                self.species=self.majorlist[self.wavefilelistlocation].species
                self.entrygenus.delete(0,tk.END)
                self.entrygenus.insert(0,self.genus)
                self.entryspecies.delete(0,tk.END)
                self.entryspecies.insert(0,self.species)
                #pdb.set_trace()
                self.dropdownmenugeneral.current(self.generallist.index(self.general))
                self.dropdownmenualive.current(self.alivelist.index(self.alive))

                #pdb.set_trace()
                #self.dropdownmenugeneral.current
            except:
                print('didnt work')
            

    def setcanvasimage(self,mpath):
        #returnspectrogram(mpath)
        #pdb.set_trace()
        tempfile=mpath.split('.')
        #pdb.set_trace()
        load=Image.open(mpath)
        load=load.resize((800,800),Image.ANTIALIAS)
        #pdb.set_trace()
        image1=ImageTk.PhotoImage(load)
        self.image=image1
        #pdb.set_trace()
        #self.canvas1.create_image(0,0,image=image1,anchor='nw')
        self.canvas1.setnewimage(mpath)
        self.master.title(tempfile[0])

    def setcanvasimage_firsttime(self,mpath):
        #returnspectrogram(mpath)
        #pdb.set_trace()
        tempfile=mpath.split('.')
        #pdb.set_trace()
        load=Image.open(mpath)
        load=load.resize((800,800),Image.ANTIALIAS)
        #pdb.set_trace()
        image1=ImageTk.PhotoImage(load)
        self.image=image1
        #pdb.set_trace()
        self.canvas1=CanvasImage(self.frame1,mpath)
        self.canvas1.grid(row=0,column=0)
        #self.canvas1.create_image(0,0,image=image1,anchor='nw')
        self.master.title(tempfile[0])    
        
    def mset_directory(self):
        self.directory=tk.filedialog.askdirectory(initialdir=os.getcwd())
        self.wavefilelist=self.listofwavfilesindir(self.directory)
        if os.path.isfile(self.directory+'/output.txt'):
            self.readfromfile()

        else:
            for i in range(0,len(self.wavefilelist)):
                self.majorlist.append(mdatastruct(self.wavefilelist[i],'unk','unk','unk','unk'))

        #self.majorlist=[mdatastruct() for i in range(len(self.wavefilelist))]    
        #self.specieslist=self.getspecieslist(self.directory)
        #pdb.set_trace()
        self.wavefilelistlocation=0
        self.setcanvasimage_firsttime(self.directory+'/'+self.wavefilelist[self.wavefilelistlocation])
        #self.fileID=open(self.directory+'/output.txt','w+')
        #self.dirpath=
        #self.newWindow = tk.Toplevel(self.master)
        #self.app = Demo2(self.newWindow)  
        # 
        #
    def listofwavfilesindir(self,mpath):
        mlist=[]
        
        for f in os.listdir(mpath):
            if(f.split(".")[1]=="JPG" or "jpg"):
                mlist.append(f)
        #pdb.set_trace()        
        return mlist        


    def nextimage(self):
        pdb.set_trace()
        print('next image')
        #pdb.set_trace()
        #self.fileID.write(self.currentimage_name+','+self.general+','+self.genus+','+self.species+','+ self.alive+'\n')
        #pdb.set_trace()
        self.current_image_place=self.current_image_place+1
        load=Image.open("img_place/"+listoffiles[self.current_image_place])
        #pdb.set_trace()
        render=ImageTk.PhotoImage(load)
        self.label1.configure(image=render)
        self.label1.image=render
        self.general='unk'
        self.genus='unk'
        self.species='unk'
        self.alive='unk'
        #pdb.set_trace()
        #self.label1=tk.Label(self.root,image=self.image1,justify='right')
        #label1=render

    def previousimage(self):
        print('previous image')        

    def set_general(self, mvalue):
        self.general=mvalue
        

    def set_genus(self, mvalue):
        self.genus=mvalue

    def set_species(self, mvalue):
        self.species=mvalue

    def set_alive(self, mvalue):
        self.alive=mvalue

    def on_closing(self):
        self.fileID.close()
        self.root.destroy()
        #self.fileID.close()
        #if messagebox.askokcancel("Quit", "Do you want to quit?"):
        #    root.destroy()



def main():
    ##parser=argparse.ArgumentParser(description='not sure')
    ##parser.add_argument("--i", help='place to look for images')
    ##args=parser.parse_args()
    ##image_dir=args.i
    ##fileID=open
    ##pdb.set_trace()
    #global listoffiles
    #listoffiles=[]
    #for root, subdirs, mfiles in os.walk('img_place'):
    #    for name in mfiles:
    #        listoffiles.append(name)
    #    #for name in mfiles:
    #        #print(name)
    ##root= os.walk('img_place')       
    ##pdb.set_trace()
    root = tk.Tk() 
    #with App(root) as w:
    #    w.mainloop()
    P=App(root)
    #root.protocol("WM_DELETE_WINDOW",P.on_closing)
    root.mainloop()


if __name__=="__main__":
    main() 