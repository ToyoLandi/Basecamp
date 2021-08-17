# Basecamp 0.3 BETA
# Written by Collin Spears, Network TSE

'''
Welcome to Basecamp.py, I hope you like what we have done with the place.
Executing this file will start the Application UI, AND the SQLite3 DB. If
this is your first time, this file will also create the initial dirs and
log files using this file location as "root".

Read some comments, read some code - email me at "Collin_Spears@mcafee.com" if you
have any questions!

-Made with love in Durango, Colorado!
'''

'''
NOTES FOR DEVS!
    [File Structure]
        # Basecamp.py -  This is the main framework file which connects the various
        "bcamp_x' modules together. Containing the UI and nessicary logic. When a user
        interacts with "CaseData", this file leverages the 'bcamp_api' to do so in a
        thread-safe way.

        # bcamp_setup.py-  Handles the installation process, and automatically
        generates a "config.json" file to store user preferences.

        # bcamp_extensions.py - The '_extensions' module contains two main classes,
        'Unpackers' and 'Workpanes'. These classes are responsible for checking
        the /../example.py signature of an "extension" safely importing the code 
        written within.

    [Database Info]
        # Basecamp used SQLite3 to store CaseData such as file metadata or notes.
        Please keep the following in mind because of this...
            > Leverage the bcamp_api methods to query content safely, many formatted
            and open-ended methods are available to query every table.

            > SQLite3 *ONLY* stores values as strings. Example, the None datatype is
            saved as "None".

            > SQLite3 is a local instance ran ONLY when Basecamp is running.
'''

# Private imports
import bcamp_api
import bcamp_setup
import bcamp_extensions

# Public Imports
import io
import os
import stat
import json
import queue
import pprint
import shutil
import socket
import pickle
import pathlib
import logging
import webbrowser
import datetime
import threading
import subprocess
import tkinter as tk
import tkinter.font as tk_font
from tkinter import ttk, colorchooser, filedialog, dnd

#ROOT PATH CONSTANT FOR INSTALL DIR.
ROOTPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]

'''Registers Var as a callback method. Used for 'events' throughout the UI.'''
class callbackVar:
    '''
    When the assigned variable is changed, a callback command can be called.
    '''

    def __init__(self, initial_value=""):
        self._value = initial_value
        self._callbacks = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self._notify_observers(new_value)

    def _notify_observers(self, new_value):
        for callback in self._callbacks:
            callback(new_value)

    def register_callback(self, callback):
        self._callbacks.append(callback)


'''Main UI Class'''
class Gui(tk.Tk):
    '''
    This class contains Ttk.Frame, Ttk.Toplevel and other Tk/Ttk sub-classes 
    and required UI/UX logic for the primitive Tk Object to behave. You will
    often see that sub-classes are NOT recommened in Python due to loss of 
    scope, however I chose this design explictly as this helps organize the
    Tk.Widgets drawn in each "Frame". Keeping the GUI modular, and easily
    configurable.

    Further Reading...
    - https://docs.python.org/3/library/tk.html
    - https://docs.python.org/3/library/tk.ttk.html#module-tk.ttk

    '''
    # Defined outside of __init__ with intent... and a little Python spite. :)
    # Import Menu results Python Dict.
    import_item = callbackVar()
    # Tuples of priority number (int) and SR number.
    CaseViewer_index = []
    refresh_CaseView = callbackVar()
    # Filebrowser Progress Raw Poll result - for copy/unpack UI updates
    # Formatted result of 'fb_progress_val' - see *update_fb_prog()*
    fb_progress_val = callbackVar()
    fb_progress_string = callbackVar()
    fb_queue_string = callbackVar()


    def __init__(self, automations_manager):
        super().__init__()
        # Root Path of install CONSTANT.
        self.RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]

        # Attaching UI to intialized classes from "Basecamp.py"
        self.automations_man = automations_manager

        # Register callback for fb_progress_val updates that will
        # come from *self.file_queue*.
        Gui.fb_progress_val.register_callback(self.update_fb_prog)

        # Starting Queue Daemons - See "bcamp_api.py' for details.
        self.file_queue = bcamp_api.FileOpsQueue(self)

        # Register Callback method for "Gui.import_item" changes to 
        # "import_handler()". These will be dictionary objects from
        # the Tk_ImportMenu
        Gui.import_item.register_callback(self.import_handler)

        # Intializing Main Tk/Ttk Classes
        self.BottomBar = Tk_BottomBar()
        self.MasterPane = Tk_MasterPane(self)
        self.Workbench = Tk_WorkspaceTabs(self.MasterPane, self.file_queue)
        self.CaseViewer = Tk_CaseViewer(self.MasterPane, self.Workbench)
        #self.TodoList = Tk_TodoList(self.MasterPane)
        Gui.refresh_CaseView.register_callback(self.CaseViewer.update_CaseViewer_tiles)

        # Configuring Tk ELements for Main Window.
        self.config_widgets()
        self.config_grid()
        self.config_window()
        self.config_binds()

        # Configuring UI based on user-config in DB.
        self.render_initial_config()
        

        # STARTING TK/TTK UI
        self.configure(background="black")
        self.start_ui()
        # Nothing should be past "start_ui()" - The UI wont care about it :)

    # Tk/UI Methods
    def config_widgets(self):
        '''
        Tk Widgets NOT drawn by Tk_MasterPane are defined here.

        This also contains ttk.Style def's for Notebook and Treeview
        '''
        # Top Menu
        self.top_menu = tk.Menu(self, tearoff=0)

        # File Dropdown Menu
        self.tm_file = tk.Menu(self.top_menu, tearoff=0)
        self.tm_file.add_command(
            label="New Import                Ctrl+N", command=self.render_new_import)
        self.tm_file.add_command(
            label="Settings Menu            Ctrl+,", command=self.open_settings_menu)
        #self.tm_file.add_command(label="Open Theme Wizard", command=self.Tk_ThemeWizard)
        self.tm_file.add_command(
            label="Reveal Install Folder   Ctrl+I", command=self.reveal_install_loc)

        # View Dropdown Menu
        self.tm_view = tk.Menu(self.top_menu, tearoff=0)
        self.tm_view.add_command(
            label="Show Top Menu              Left Alt", command=self.toggle_top_menu)
        self.tm_view.add_separator()
        self.tm_view.add_command(
            label="Show CaseViewer            Ctrl+B", command=self.toggle_CaseViewer)
        self.tm_view.add_command(
            label="Move CaseViewer Left", command=lambda 
                pos='left': self.update_caseviewer_pos(pos))
        self.tm_view.add_command(
            label="Move CaseViewer Right", command=lambda 
                pos='right': self.update_caseviewer_pos(pos))
        
        # Adding "SubMenus" to Top_Menu widget.
        self.top_menu.add_cascade(label="File", menu=self.tm_file)
        self.top_menu.add_cascade(label="View", menu=self.tm_view)

        # Empty Top Menu - For disabling if user chooses.
        self.empty_menu = tk.Menu(self)

        # Ttk Styles from here...
        self.def_font = tk_font.Font(
            family="Segoe UI", size=12, weight="normal", slant="roman")

        # BUGFIX FOR tk TREEVIEW COLORS 
        def fixed_map(option):
            # Fix for setting text colour for tk 8.6.9
            # From: https://core.tcl.tk/tk/info/509cafafae
            #
            # Returns the style map for 'option' with any styles starting with
            # ('!disabled', '!selected', ...) filtered out.

            # style.map() returns an empty list for missing options, so this
            # should be future-safe.
            return [elm for elm in style.map('Treeview', query_opt=option) if
                    elm[:2] != ('!disabled', '!selected')]

        # Defining Treeview header color style.
        style = ttk.Style()
        style.theme_use('clam')
        style.element_create(
            "Custom.Treeheading.border", "from", "default")
        style.layout("Custom.Treeview.Heading", [
            ("Custom.Treeheading.cell", {'sticky': 'nswe'}),
            ("Custom.Treeheading.border", {'sticky': 'nswe', 'children': [
                ("Custom.Treeheading.padding", {'sticky': 'nswe', 'children': [
                    ("Custom.Treeheading.image", {
                        'side': 'right', 'sticky': ''}),
                    ("Custom.Treeheading.text", {'sticky': 'we'})
                ]})
            ]}),
        ])
        style.layout("Custom.Treeview", [('Custom.Treeview.treearea', {'sticky': 'nswe'})])
        style.configure("Custom.Treeview.Heading",
                        background="#212121", foreground="white", relief="flat")
        style.map("Custom.Treeview.Heading",
                    relief=[('active', 'groove'), ('pressed', 'flat')])
        style.map('Custom.Treeview',
                  foreground=fixed_map('foreground'),
                  background=fixed_map('background'),
                  )
        style.configure("Custom.Treeview",
                        fieldbackground="#0a0a0a", 
                        background="#0a0a0a", 
                        foreground="#fdfdfd",
                        relief='flat',
                        highlightthickness=0,
                        bd=0,)
        
        # Defining Scrollbar Styles.
        style.configure("Vertical.TScrollbar", gripcount=0,
                background="#717479", darkcolor="gray", lightcolor="gray",
                troughcolor="#1E1F21", bordercolor="black", arrowcolor="black")
        style.configure("Horizontal.TScrollbar", gripcount=0,
                background="#717479", darkcolor="gray", lightcolor="gray",
                troughcolor="#1E1F21", bordercolor="black", arrowcolor="black")



        # Defining the Notebook style colors for "Worktabs".
        myTabBarColor = "#05070F"
        myTabBackgroundColor = "#090B13"
        myTabForegroundColor = "#B2B6BC"
        myActiveTabBackgroundColor = "#1E1F21"
        myActiveTabForegroundColor = "#D5A336"



        style.map("TNotebook.Tab", background=[("selected", myActiveTabBackgroundColor)], foreground=[("selected", myActiveTabForegroundColor)]);
        # Import the Notebook.tab element from the default theme
        style.element_create('Plain.Notebook.tab', "from", 'clam')
        # Redefine the TNotebook Tab layout to use the new element
        style.layout("TNotebook.Tab",
            [('Plain.Notebook.tab', {'children':
                [('Notebook.padding', {'side': 'top', 'children':
                    [('Notebook.focus', {'side': 'top', 'children':
                        [('Notebook.label', {'side': 'top', 'sticky': ''})],
                    'sticky': 'nswe'})],
                'sticky': 'nswe'})],
            'sticky': 'nswe'})])
        
        #%%ass
        style.configure("TNotebook", background=myTabBarColor, borderwidth=0, bordercolor=myTabBarColor, focusthickness=40)
        style.configure("TNotebook.Tab", background=myTabBackgroundColor, foreground=myTabForegroundColor,
                                            lightcolor=myTabBackgroundColor, borderwidth=0, bordercolor=myTabBarColor)

    def config_grid(self):
        '''
        Initalized Frames and "config_widgets" content is added to the UI 
        geometry manager here. - using tk.grid().
        '''
        #self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        #self.TopBar.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.MasterPane.grid(row=1,
            column=2, 
            #columnspan=5, 
            sticky='nsew')
        self.BottomBar.grid(row=6, 
            column=0, 
            columnspan=3, 
            sticky="sew")

    def config_window(self):
        '''
        This method defines the *Master* TK window settings, such as the
        default render size, or "top menu" configuration.
        '''
        # Misc
        self.title("Basecamp")
        titlebar_photo = tk.PhotoImage(file=self.RPATH + "\\core\\bcamp.gif")
        self.iconphoto(False, titlebar_photo)

    def config_binds(self):
        self.bind('<Control-i>', self.reveal_install_loc)
        self.bind('<Control-,>', self.open_settings_menu)
        self.bind('<Control-n>', self.Workbench.import_tab)
        self.bind('<Control-b>', self.toggle_CaseViewer)
        self.bind('<Alt_L>', self.toggle_top_menu)

    def update_widgets(self):
        '''
        If any Widget config needs to be updated after other UI events, with
        an element besides a tk.Var() it should be defined here.
        '''
        self.update()
        # DO NOT WRITE ABOVE THIS COMMENT
        # BottomBar Remote Share connectivity Poll
        if os.access(bcamp_api.get_config("remote_root"), os.R_OK):
            self.BottomBar.bb_remote_canvas.itemconfigure(self.BottomBar.bb_remote_off, state='hidden')
            self.BottomBar.bb_remote_canvas.itemconfigure(self.BottomBar.bb_remote_on, state='normal')
        else:
            # Make the DOT red if DEAD.
            self.BottomBar.bb_remote_canvas.itemconfigure(self.BottomBar.bb_remote_on, state='hidden')
            self.BottomBar.bb_remote_canvas.itemconfigure(self.BottomBar.bb_remote_off, state='normal')

        # BottomBar Telemetry connectivity Poll
        if os.access(bcamp_api.get_config("remote_root"), os.R_OK):
            self.BottomBar.bb_telemen_canvas.itemconfigure(self.BottomBar.bb_telemen_off, state='hidden')
            self.BottomBar.bb_telemen_canvas.itemconfigure(self.BottomBar.bb_telemen_on, state='normal')
        else:
            # Make the DOT red if DEAD.
            self.BottomBar.bb_telemen_canvas.itemconfigure(self.BottomBar.bb_telemen_on, state='hidden')
            self.BottomBar.bb_telemen_canvas.itemconfigure(self.BottomBar.bb_telemen_off, state='normal')        

        # DO NOT WRITE BELOW THIS COMMENT
        self.after(2000, self.update_widgets)

    def start_ui(self):
        '''
        Calling update_widgets and then starting the Tk Mainloop.

        If the mainloop crashes, or is interuppted, the UI will hang with a 
        "Not Responding" message.
        '''
        self.update_widgets()
        self.mainloop()

    def render_initial_config(self):
        '''
        Using the UI values stored in the Basecamp.config table, this method
        populates the UI Window and "MasterPane". These values can be adjusted
        by users for a more personalized config.
        '''
        # First, Get values from config table and store as Vars
        start_res = bcamp_api.get_config('ui_start_res')
        render_top_menu = bcamp_api.get_config('ui_render_top_menu')
        caseviewer_pos = bcamp_api.get_config('ui_caseviewer_location')
        render_caseviewer = bcamp_api.get_config('ui_render_caseviewer')

        # [Resolution]
        self.geometry(start_res)

        # [Caseviewer/Workbench] location
        if render_caseviewer == "True":
            if caseviewer_pos == 'left':
                self.MasterPane.add(self.CaseViewer, sticky='nsew', width=250)
                self.MasterPane.add(self.Workbench, sticky='nsew') # Always rendered @ launch
            elif caseviewer_pos == 'right':
                # Resize Workbench First,
                self.MasterPane.update_idletasks()
                MasterPane_width = self.MasterPane.winfo_width()
                Workbench_width = MasterPane_width - 250 #= default width
                self.MasterPane.paneconfig(self.Workbench, width=Workbench_width)
                # Then Add CaseViewer
                self.MasterPane.add(self.CaseViewer, sticky='nsew', after=self.Workbench, width=250)
        elif render_caseviewer == "False":
            pass # Do not add to MasterPane.

        
        # [Top Menu] Enabled/Disabled
        if render_top_menu == 'True':
            self.config(menu=self.top_menu)
        elif render_top_menu == 'False':
            self.config(menu=self.empty_menu)

    def update_caseviewer_pos(self, pos):
        # First, check if Caseviewer is rendered.
        if bcamp_api.get_config('ui_render_caseviewer') == "True":
            # If so, remove it, and move it!
            self.MasterPane.forget(self.CaseViewer)

        # Now render based on pos and update DB.
        if pos == "left":
            self.MasterPane.add(self.CaseViewer, sticky='nsew', before=self.Workbench, width=250)
            bcamp_api.update_config('ui_caseviewer_location', 'left')
            bcamp_api.update_config('ui_render_caseviewer', 'True')   
        if pos == "right":
            self.MasterPane.add(self.CaseViewer, sticky='nsew', after=self.Workbench, width=250)
            bcamp_api.update_config('ui_caseviewer_location', 'right')
            bcamp_api.update_config('ui_render_caseviewer', 'True')
            # Resize self.Workbench
            MasterPane_width = self.MasterPane.winfo_width()
            Workbench_width = MasterPane_width - 250 #= default width
            self.MasterPane.paneconfig(self.Workbench, width=Workbench_width)

    # Create Imported themes.
    def create_themes(self):
        '''
        Creates the ttk style themes.

        Further Reading...
        https://docs.python.org/3/library/tkinter.ttk.html#ttk-styling
        '''

        style = ttk.Style()
        # TODO - For Theme in theme folder...
        style.theme_create('test-Alpine', parent='clam') # TODO - ?Add settings here for for loop?
        ###
        style.theme_settings('test-Alpine', {

        })

    # Keyboard-Binding Methods
    def open_settings_menu(self, event=None):
        Tk_SettingsMenu()

    def reveal_install_loc(self, event=None):
        '''
        Button and Keyboard Bind command to open the Root install location for
        Basecamp.
        '''
        RPATH = str(pathlib.Path(__file__).parent.absolute()
                    ).rpartition('\\')[0]
        os.startfile(RPATH)

    def render_new_import(self, event=None):
        self.Workbench.import_tab()

    def toggle_CaseViewer(self, event=None):
        '''
        Button and Keyboard Bind command to toggle the CaseViewer Pane, on the
        left of the UI.
        '''
        if bcamp_api.get_config('ui_render_caseviewer') == "False":
            # Last setting was "hidden" - Render Caseviewer...
            if bcamp_api.get_config('ui_caseviewer_location') == 'left':
                self.MasterPane.add(self.CaseViewer, sticky='nsew', before=self.Workbench, width=250)
            elif bcamp_api.get_config('ui_caseviewer_location') == 'right':
                self.MasterPane.add(self.CaseViewer, sticky='nsew', after=self.Workbench, width=250)
            # and update the DB
            bcamp_api.update_config('ui_render_caseviewer', "True")

        elif bcamp_api.get_config('ui_render_caseviewer') == "True":
            # Last Setting was "shown" - Remove Caseviewer...
            self.MasterPane.forget(self.CaseViewer)
            # and update DB.
            bcamp_api.update_config('ui_render_caseviewer', "False")

    def toggle_top_menu(self, event=None):
        # Assigning top_menu to "master" Window
        if bcamp_api.get_config("ui_render_top_menu") == "False":
            self.config(menu=self.top_menu)
            bcamp_api.update_config('ui_render_top_menu', "True")
        else:
            empty_menu = tk.Menu(self)
            self.config(menu=empty_menu)
            bcamp_api.update_config('ui_render_top_menu', "False")

    # DB & Config Integration Methods
    def import_handler(self, new_import_data):
        '''
        This method is called whenever "Gui.import_item" is modified. The
        expected input is a dictionary with the following syntax...

        new_import_data = {
            'sr_number': sr_number,
            'tags_list': tags_list,
            'account_string': account_string,
            'customs_list': customs_list,
            'product_string': product_string,
            'workspace_string': workspace_string,
            'important_bool': important_bool
        }

        If this is the first time a user has imported a SR Number. This will 
        only store the inital CaseData Object for 'new_value'. 

        If 'new_value' is an SR number that exist within CaseData, 'new_value'
        is simply passed to the intialized "Tk_Workspace.new_tab" method.
        '''

        # Unpacking SR key_value from import Dict.
        import_key_value = new_import_data['sr_number']
        print("IMPORT: Caught new_value <" + import_key_value + ">")

        # SR Numbers are 13 characters long.
        if len(import_key_value) == 13:
            if not bcamp_api.query_case_exist(import_key_value):
                bcamp_api.new_import(new_import_data)
                self.CaseViewer.update_CaseViewer_tiles()
                self.Workbench.render_workspace(import_key_value)
                # Create local 'downloads' folder.
                try:
                    os.mkdir(self.RPATH + "\\downloads\\" + import_key_value)
                except:
                    print("ERROR - Unable to create 'downloads' folder for ", import_key_value)
            else:
                self.Workbench.render_workspace(import_key_value)

    # UI Callbacks
    def update_fb_prog(self, new_fileops_val):
        '''
        Callback method whenever *Gui.fb_progress_val* var is modified.

        Parses the 'new_fileops_val' dictionary which contains a default
        'mode' value, and any other info provided from the API scripts
        for progress string formatting, which is done here!

        All Tk-Filebrowser instances will read the Gui.fb_progress_string
        updated by this class.
        '''
        def calc_percentage(cursize, totalsize):
            # Converts Totalsize/cursize to a rounded percentage.
            raw_percent = cursize / totalsize
            formated_percent = "{:.0%}".format(raw_percent)
            return formated_percent

        if new_fileops_val['mode'] == None:
            # Set when reset by FileOps Worker Thread
            Gui.fb_progress_string.value = ""
            
        if new_fileops_val['mode'] == 'download':
            # convert bytes to kB
            cur_kb = new_fileops_val['curbytes'] / 100
            total_kb = new_fileops_val['totalbytes'] / 100
            # Get percentage
            prog_percentage = calc_percentage(cur_kb, total_kb)
            # Get name and sr
            fname = os.path.basename(new_fileops_val['srcpath'])
            sr = new_fileops_val['sr']
            formatted_string = (
                "DOWNLOADING "
                + "[" 
                + prog_percentage 
                + "] ./"
                + sr
                + "/" + fname

            )
            Gui.fb_progress_string.value = formatted_string

        if new_fileops_val['mode'] == 'automation':
            def progress_string(base_msg, dots):
                # Simple method to generate automationing progress strings for UI.
                Gui.fb_progress_string.value = base_msg + dots

            # Base Message wth vars from *new_fileops_val* dictionary.
            automation_path = new_fileops_val['srcpath']
            automation_sr = new_fileops_val['sr']

            # TODO - Complete base MSG? 
            #base_msg = "automationing"


            fname = os.path.basename(new_fileops_val['srcpath'])
            sr = new_fileops_val['sr']
            base_msg = (
                "AUTOMATION - "
                + sr
                + "/" + fname

            )

            # Checking if 'automation' already complete since recursive call.
            if Gui.fb_progress_val.value['mode'] == 'automation':
                # Modify progress string with *self.after* - measured in ms
                Gui.fb_progress_string.value = base_msg
                self.after(1000, progress_string, base_msg, ".")
                self.after(2000, progress_string, base_msg, "..")
                self.after(3000, progress_string, base_msg, "...")

            # Recursive Call back to *self* with og new_fileops_val to loop
            # the progress dots.
            if Gui.fb_progress_val.value['mode'] == 'automation' and Gui.fb_progress_val.value['srcpath'] == automation_path:
                self.after(4000, self.update_fb_prog, new_fileops_val)
            else:
                # Jobs Done! - *Gui.fb_progress_val* cleared by FileopsQueue.
                # Manually clearing here so we dont have to wait for the 
                # threads to sync.
                Gui.fb_progress_string.value = ""
                

'''Sub-classed Tk/TcL Classes with Custom behavior for use in UI.'''
class CustomTk_ButtonHover(ttk.Button):
    def __init__(self, master, **kw):
        tk.Button.__init__(self, master=master, **kw)
        self.defaultBackground = self["background"]
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['background'] = self['activebackground']

    def on_leave(self, e):
        self['background'] = self.defaultBackground


class CustomTk_CreateToolTip(object):
        '''
        create a tooltip for a given widget, originally from Stack.

        https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tk
        '''

        def __init__(self, widget, text='widget info'):
            self.waittime = 500  # miliseconds
            self.wraplength = 180  # pixels
            self.widget = widget
            self.text = text
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.leave)
            self.widget.bind("<ButtonPress>", self.leave)
            self.id = None
            self.tw = None

        def enter(self, event=None):
            self.schedule()

        def leave(self, event=None):
            self.unschedule()
            self.hidetip()

        def schedule(self):
            self.unschedule()
            self.id = self.widget.after(self.waittime, self.showtip)

        def unschedule(self):
            id = self.id
            self.id = None
            if id:
                self.widget.after_cancel(id)

        def showtip(self, event=None):
            x = y = 0
            try:
                x, y, cx, cy = self.widget.bbox("insert")
            except:
                pass
            x += self.widget.winfo_rootx() + 0
            y += self.widget.winfo_rooty() + 0
            # creates a toplevel window
            self.tw = tk.Toplevel(self.widget)
            # Leaves only the label and removes the app window
            self.tw.wm_overrideredirect(True)
            self.tw.wm_geometry("+%d+%d" % (x, y))


            #%%hex
            label = tk.Label(self.tw, text=self.text, justify='center',
                             background="#ffffff", relief='solid', borderwidth=1,
                             wraplength=self.wraplength)


            
            label.pack(ipadx=1)

        def hidetip(self):
            tw = self.tw
            self.tw = None
            if tw:
                tw.destroy()


class CustomTk_autoEntry(ttk.Entry):
    """
    Subclass of tk.Entry that features autocompletion.
    To enable autocompletion use set_completion_list(list) to define 
    a list of possible strings to hit.
    To cycle through hits use down and up arrow keys.
    """
    tk_umlauts=['odiaeresis', 'adiaeresis', 'udiaeresis', 'Odiaeresis', 'Adiaeresis', 'Udiaeresis', 'ssharp']

    def set_completion_list(self, completion_list):
        self._completion_list = completion_list
        self._hits = []
        self._hit_index = 0
        self.position = 0
        self.bind('<KeyRelease>', self.handle_keyrelease)               

    def autocomplete(self, delta=0):
        """autocomplete the Entry, delta may be 0/1/-1 to cycle through possible hits"""
        if delta: # need to delete selection otherwise we would fix the current position
            self.delete(self.position, tk.END)
        else: # set position to end so selection starts where textentry ended
            self.position = len(self.get())
        # collect hits
        _hits = []
        for element in self._completion_list:
            #if element.startswith(self.get().lower()):
            if element.startswith(self.get()):
                _hits.append(element)
        # if we have a new hit list, keep this in mind
        if _hits != self._hits:
            self._hit_index = 0
            self._hits=_hits
        # only allow cycling if we are in a known hit list
        if _hits == self._hits and self._hits:
            self._hit_index = (self._hit_index + delta) % len(self._hits)
        # now finally perform the auto completion
        if self._hits:
            self.delete(0,tk.END)
            self.insert(0,self._hits[self._hit_index])
            self.select_range(self.position,tk.END)
                        
    def handle_keyrelease(self, event):
        """event handler for the keyrelease event on this widget"""
        if event.keysym == "BackSpace":
            self.delete(self.index(tk.INSERT), tk.END) 
            self.position = self.index(tk.END)
        if event.keysym == "Left":
            if self.position < self.index(tk.END): # delete the selection
                self.delete(self.position, tk.END)
            else:
                self.position = self.position-1 # delete one character
                self.delete(self.position, tk.END)
        if event.keysym == "Right":
            self.position = self.index(tk.END) # go to end (no selection)
        if event.keysym == "Down":
            self.autocomplete(1) # cycle to next hit
        if event.keysym == "Up":
            self.autocomplete(-1) # cycle to previous hit
        # perform normal autocomplete if event is a single key or an umlaut
        if len(event.keysym) == 1 or event.keysym in CustomTk_autoEntry.tk_umlauts:
            self.autocomplete()


class CustomTk_Textbox(tk.Text):
    '''
    Same as the native Tk Text class, with the added proxy method when text is
    modified. 
    
    Notes from stack...
        "The proxy in this example does three things:

        First it calls the actual widget command, passing in all of the arguments it received.
        Next it generates an event for every insert and every delete
        Then it then generates a virtual event
        And finally it returns the results of the actual widget command
        You can use this widget exactly like any other Text widget, with the added benefit that you can bind to <<TextModified>>."

    https://stackoverflow.com/questions/40617515/python-tkinter-text-modified-callback
    '''
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

        # create a proxy for the underlying widget
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, command, *args):
        cmd = (self._orig, command) + args
        try:
            result = self.tk.call(cmd)
        except Exception:
            return None

        if command in ("insert", "delete", "replace"):
            self.event_generate("<<TextModified>>")

        return result


class CustomTk_ScrolledFrame(tk.Frame):
    def __init__(self, parent, vertical=True, horizontal=False):
        super().__init__(parent)

        # canvas for inner frame
        self._canvas = tk.Canvas(
            self,
            bd=0,
            highlightthickness=0,
        )
        self._canvas.grid(row=0, column=0, sticky='nsew') # changed

        # create right scrollbar and connect to canvas Y
        self._vertical_bar = ttk.Scrollbar(self, orient='vertical', command=self._canvas.yview)
        if vertical:
            self._vertical_bar.grid(row=0, column=1, sticky='ns')
        self._canvas.configure(yscrollcommand=self._vertical_bar.set)

        # create bottom scrollbar and connect to canvas X
        self._horizontal_bar = ttk.Scrollbar(self, orient='horizontal', command=self._canvas.xview)
        if horizontal:
            self._horizontal_bar.grid(row=1, column=0, sticky='we')
        self._canvas.configure(xscrollcommand=self._horizontal_bar.set)

        # inner frame for widgets
        self.inner = tk.Frame(self._canvas)
        self._canvas.create_window((0, 0), window=self.inner, anchor='nw', tags="inner")

        # autoresize inner frame
        self.columnconfigure(0, weight=1) # changed
        self.rowconfigure(0, weight=1) # changed

        # resize when configure changed
        self.inner.bind('<Configure>', self.resize)
        
        # resize inner frame to canvas size
        self.resize_width = False
        self.resize_height = False
        self._canvas.bind('<Configure>', self.inner_resize)

        # Bind Mousewheel to scroll.
        self._canvas.bind('<MouseWheel>', 
            lambda event: self._canvas.yview_scroll(
                int(-1*(event.delta/120)),
                "units")
        )

    def resize(self, event=None):
        #print(self._canvas.bbox('all'))
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def inner_resize(self, event):
        # resize inner frame to canvas size
        if self.resize_width:
            self._canvas.itemconfig("inner", width=event.width)
        if self.resize_height:
            self._canvas.itemconfig("inner", height=event.height)


'''Basecamp Tk/TcL Frames Rendered in the UI.'''
class Tk_MasterPane(tk.PanedWindow):
    '''
    This is the "Master Pane" that contains all main Widget frames such as
    "Tk_WorkspaceTabs" or "Tk_CaseViewer" - Allowing them to be resized
    via Sash grips.
    '''
    def __init__(self, master):
        super().__init__(master)
        self.configure(
            handlesize=16,
            handlepad=100,
            sashwidth=10,
            background="#141414"
        )


class Tk_CaseViewer(tk.Frame):
    '''
    The CaseViewer is the Sidebar that contains the Case "Tiles". This class
    sources data from the local SQLite basecamp.db file and renders the Tiles
    using the "CaseTile_Template" Subclass for reference.
    '''
    def __init__(self, master, workspace_manager):
        super().__init__(master)
        # For starting new tabs in Workspace
        self.workspace_man = workspace_manager
        self.frame_state = "on"
        self.RPATH = str(pathlib.Path(
            __file__).parent.absolute()).rpartition('\\')[0]
        
        self.configure(background="#090B13")
        self.config_widgets()
        self.config_grid()
        #self.config_bindings()
        # Draw Current tiles on init...
        self.update_CaseViewer_tiles()

    def config_widgets(self):
        # Creating Canvas widget to contain the Case Tiles, enabling a
        # scrollbar if the user has a lot of cases imported.
        self.master_frame = CustomTk_ScrolledFrame(
            self,
        )
        self.master_frame.resize_width = True # Enable resize of inner canvas
        self.master_frame.resize_height = False
        self.master_frame._canvas.configure(
            background="#090B13"
        )
        self.master_frame.inner.configure(
            background="#090B13"
        )

    def config_grid(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        #self.master_frame.rowconfigure(0, weight=1),
        #self.master_frame.columnconfigure(0, weight=1)
        self.master_frame.grid(row=0, column=0, sticky="nsew")
        #self.master_frame.inner.grid(sticky="nsew")
        #self.master_frame.inner.rowconfigure(0, weight=1),
        #self.master_frame.inner.columnconfigure(0, weight=1)        

    def render_tile(self, key_value):
        '''
        Creates a case_template Tk.Frame for 'key_value' based on the
        global CaseViewer_index.
        '''
        index = [item for item in Gui.CaseViewer_index if key_value in item]
        self.CaseTile_template(self.master_frame.inner, index[0][0], key_value, self.workspace_man)

    def update_CaseViewer_tiles(self, *refresh_caller):
        '''
        This method appends new "key_values" to the UI's CaseViewer found
        in the collapsable left window. Ran at runtime, and when a new import occurs.
        '''
        sr_tuple = bcamp_api.query_cases("sr_number")
        max_index = len(sr_tuple) - 1 #offset for loop
        start_index = 0
        while start_index <= max_index:
            if sr_tuple[start_index][0] not in Gui.CaseViewer_index:
                try:
                    # Creating record...
                    record = (len(Gui.CaseViewer_index), sr_tuple[start_index][0], False)
                    # appending it to CaseViewer_index
                    Gui.CaseViewer_index.append(record)
                    # Passing sr_number to render_tile method
                    self.render_tile(sr_tuple[start_index][0])
                except tk.TclError as e:  # Thrown for dupes...
                    print(e)
                    pass
            # increase index counter
            start_index += 1

    #TK Definitions for CaseTile
    class CaseTile_template(tk.Frame):
        '''
        Template for each "Case Tab" in CaseViewer

        index_num determines the tk.Grid placement for this template. This
        is the value determines what is shown (>0) and in what order (0-X)
        '''
        def __init__(self, master, index_num, key_value, workspace_man):
            super().__init__()
            self.master = master
            self.index_num = index_num
            self.key_value = key_value
            self.workspace_man = workspace_man
            self.RPATH = str(pathlib.Path(
                __file__).parent.absolute()).rpartition('\\')[0]
            
            # Font Config
            self.sr_font = tk_font.Font(
                family="Consolas", size=14, weight="bold", slant="roman")
            self.mini_font = tk_font.Font(
                family="Consolas", size=8, weight="bold", slant="italic")
            self.sub_font = tk_font.Font(
                family="Consolas", size=10, weight="normal", slant="roman")

            # Tk Vars
            self.sub_frame_state = tk.BooleanVar()
            self.sub_frame_state.set(False)
            self.sr_id = self.key_value
            self.tag_obj_list = []
            self.account_var = tk.StringVar()
            self.product_var = tk.StringVar()
            self.last_ran_var = tk.StringVar()
            self.imported_var = tk.StringVar()
            self.bug_var = tk.StringVar()
            self.sr_local_path = tk.StringVar()
            self.sr_remote_path = tk.StringVar()
            self.pin_unpin_var = tk.StringVar()
            self.open_create_local_var = tk.StringVar()

            # Geting vals for SR. 
            self.sr_vals = bcamp_api.query_all_sr(self.key_value)
            self.remote_path = self.sr_vals[1]
            self.local_path = self.sr_vals[2]
            self.pinned = self.sr_vals[3]
            self.product = self.sr_vals[4]
            self.account = self.sr_vals[5]
            self.bug_id = self.sr_vals[7]
            # FUTURE IF NEEDED notes [6]
            # FUTURE IF NEEDED workspace [8]
            # FUTURE IF NEEDED files_table [9]

            # Determine if local path exist... for right click menu.
            if os.access(self.local_path, os.R_OK):
                self.open_create_local_var.set("Open Local Folder")
            else:
                self.open_create_local_var.set("Create Local Folder")
            self.sr_remote_path.set(self.remote_path)

            # Determine if SR is "important"... for right click menu.
            if self.pinned == 1: # True/False NA in SQLite3
                self.pin_unpin_var.set("Un-Pin SR")
            else:
                self.pin_unpin_var.set("Pin SR")

            # Colors...
            self.blk100 = "#EFF1F3"
            self.blk300 = "#B2B6BC"
            self.blk400 = "#717479"
            self.blk500 = "#1E1F21" ##
            self.blk600 = "#15171C"
            self.blk700 = "#0F1117"
            self.blk900 = "#05070F"
            self.act300 = "#D5A336"

            self.config_widgets()
            self.config_grid()
            self.config_bindings()
            self.refresh_tkVars() # update Record
            # Get tags, and pass to "render_tags" method.
            raw_tags = bcamp_api.query_tags(self.key_value)
            self.tag_tk_objs = self.render_tags(raw_tags)

        def config_widgets(self):
            # Colors
            self.configure(background="red")
            self.master_frame = tk.Frame(
                self.master,
                background=self.blk500,
            )
            self.sr_label = tk.Label(
                self.master_frame,
                text=self.sr_id,
                anchor="center",
                font=self.sr_font,
                background=self.blk500,
                foreground=self.blk300,
            )
            self.detail_frame = tk.Frame(
                self.master_frame,
                background=self.blk500,
            )
            self.account_label = tk.Label(
                self.detail_frame,
                textvariable=self.account_var,
                anchor="w",
                font=self.mini_font,
                background=self.blk500,
                foreground=self.blk400
            )
            self.product_label = tk.Label(
                self.detail_frame,
                textvariable=self.product_var,
                anchor="w",
                font=self.mini_font,
                background=self.blk500,
                foreground=self.act300
            )
            self.options_button = tk.Button(
                self.master_frame,
                text="☰",
                command=self.render_right_click_menu,
                relief='flat',
                #font=self.sub_font,
                background=self.blk500,
                foreground=self.blk400,
                cursor="hand2"      
            )
            self.dropdown_button = tk.Button(
                self.master_frame,
                text="˅",
                command=self.render_sub_frame,
                relief='flat',
                font=self.sub_font,
                background=self.blk500,
                foreground=self.blk400,
                cursor="hand2"                
            )
            # Frame "drop_down" when expanded.
            self.sub_frame = tk.Frame(
                self.master_frame,
                background=self.blk600,
            )
            self.tag_label = tk.Label(
                self.sub_frame,
                text="Tags:",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400
            )
            self.tags_frame = tk.Frame(
                self.sub_frame,
                #background="orange"
                background=self.blk600,
            )
            self.bug_label = tk.Label(
                self.sub_frame,
                text="JIRA:",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400
            )
            self.bug_button= tk.Button(
                self.sub_frame,
                textvariable=self.bug_var,
                background=self.blk600,
                foreground="yellow",
                relief='flat',
                command=self.launch_jira_browser
            )
            self.last_ran_label = tk.Label(
                self.sub_frame,
                text="Last Ran:",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400
            )
            self.last_ran_time_label = tk.Label(
                self.sub_frame,
                textvariable=self.last_ran_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400
            )
            self.pinned_label = tk.Label(
                self.sub_frame,
                text="Imported:",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400
            )
            self.pinned_time_label = tk.Label(
                self.sub_frame,
                textvariable=self.imported_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400
            )

            # Right-Click Menu
            self.right_click_menu = tk.Menu(
                self,
                relief='flat',
                tearoff=False,
                background=self.blk700,
                foreground=self.blk300,
                borderwidth=0,
            )

            self.right_click_menu.add_command(
                label="Open Workspace",
                command=self.right_click_open
            )
            
            # TODO - complete export methods.
            #self.right_click_menu.add_command(
            #    label="Export Workspace",
            #    command=self.right_click_export
            #)

            self.right_click_menu.add_separator()

            self.right_click_menu.add_command(
                label=self.pin_unpin_var.get(),
                command=self.right_click_pin_sr
            )
            self.right_click_menu.add_command(
                label="Edit SR Record",
                command=self.right_click_edit_sr_record
            )
            self.right_click_menu.add_separator()

            self.right_click_menu.add_command(
                label="Open Remote Folder",
                command=self.right_click_reveal_remote
            )
            self.right_click_menu.add_command(
                label=self.open_create_local_var.get(),
                command=self.right_click_reveal_local
            )
            self.right_click_menu.add_separator()

            self.right_click_menu.add_command(
                label="Copy SR to Clipboard",
                command=self.right_click_copy_sr
            )

            self.right_click_menu.add_command(
                label="Copy Remote Path to Clipboard",
                command=self.right_click_copy_remote
            )

            self.right_click_menu.add_command(
                label="Copy Local Path to Clipboard",
                command=self.right_click_copy_local
            )

            self.right_click_menu.add_separator()
            self.right_click_menu.add_command(
                label="Save ALL Notes to File",
                command=self.right_click_save_all_notes
            )
            self.right_click_menu.add_command(
                label="Save Case Notes to File",
                command=self.right_click_save_case_notes
            )
            self.right_click_menu.add_command(
                label="Copy Case Notes to Clipboard",
                command=self.right_click_clipboard_case_notes
            )

            self.right_click_menu.add_separator()
            self.right_click_menu.add_command(
                label="Delete",
                command=self.right_click_delete
            )

        def config_grid(self):
            #self.columnconfigure(0, weight=1)
            #self.columnconfigure(1, weight=1)
            self.master.columnconfigure(0, weight=1)
            #self.master.columnconfigure(1, weight=1)
            # Defining Grid...
            self.master_frame.grid(row=self.index_num, column=0, padx=2,
                pady=1, sticky='nsew')
            self.master_frame.columnconfigure(0, weight=1)
            self.sub_frame.columnconfigure(0, weight=1)
            self.sub_frame.columnconfigure(1, weight=1)
            # Master_Frame Content.
            self.sr_label.grid(row=0, column=0, columnspan=2,
                padx=5, sticky="nsew")
            self.detail_frame.grid(row=1, column=0, columnspan=2,
                padx=5, pady=3, sticky="w")
            self.options_button.grid(row=0, column=1, padx=3, pady=3,
                sticky="e")
            self.dropdown_button.grid(row=1, column=1, padx=5, pady=3,
                sticky="e")
            # Detail Frame Content.
            self.product_label.grid(row=0, column=0, sticky="w")
            self.account_label.grid(row=0, column=1, sticky="w")
            # Sub_frame Content.
            self.sub_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
            self.sub_frame.grid_remove()
            self.tag_label.grid(row=0, column=0)
            self.tags_frame.grid(row=0, column=1, sticky='nsew', pady=3,
                padx=1)
            # Tag frame grid for resize.
            self.tags_frame.rowconfigure(0, weight=1)
            self.bug_label.grid(row=1, column=0)
            self.bug_button.grid(row=1, column=1, stick='nsew')
            self.last_ran_label.grid(row=2, column=0)
            self.last_ran_time_label.grid(row=2, column=1)
            self.pinned_label.grid(row=3, column=0)
            self.pinned_time_label.grid(row=3, column=1)

        def config_bindings(self):
            # Bindings to show dropdown...
            self.master_frame.bind('<Shift-Button-1>', self.render_sub_frame)
            self.sr_label.bind('<Shift-Button-1>', self.render_sub_frame)
            self.product_label.bind('<Shift-Button-1>', self.render_sub_frame)
            self.account_label.bind('<Shift-Button-1>', self.render_sub_frame)
            self.master_frame.bind('<Button-3>', self.draw_menu)
            self.sr_label.bind('<Button-3>', self.draw_menu)
            self.product_label.bind('<Button-3>', self.draw_menu)
            self.account_label.bind('<Button-3>', self.draw_menu)
            self.tags_frame.bind('<Configure>', self.update_tag_grid)
            self.master_frame.bind('<Double-1>', self.right_click_open)
            self.sr_label.bind('<Double-1>', self.right_click_open)
            self.product_label.bind('<Double-1>', self.right_click_open)
            self.account_label.bind('<Double-1>', self.right_click_open)

            # LEGACY - Hover Dropdown Binds for *sub_frame*
                #self.master_frame.bind('<Enter>', self.enter_sub_frame)
                #self.sr_label.bind('<Enter>', self.enter_sub_frame)
                #self.product_label.bind('<Enter>', self.enter_sub_frame)
                #self.account_label.bind('<Enter>', self.enter_sub_frame)
                #self.sub_frame.bind('<Enter>', self.enter_sub_frame)
                #self.last_ran_label.bind('<Enter>', self.enter_sub_frame)
                #self.last_ran_time_label.bind('<Enter>', self.enter_sub_frame)
                #self.master_frame.bind('<Leave>',  self.leave_sub_frame)
                #self.sr_label.bind('<Leave>', self.leave_sub_frame)
                #self.product_label.bind('<Leave>', self.leave_sub_frame)
                #self.account_label.bind('<Leave>', self.leave_sub_frame)

            # ~~~

        def refresh_tkVars(self):
            '''
            Gets an updated Datastore record and updates the TK vars.
            '''
            new_sr_vals = bcamp_api.query_all_sr(self.key_value)
            new_remote_path = new_sr_vals[1]
            new_local_path = new_sr_vals[2]
            self.pinned_state = new_sr_vals[3]
            new_product = new_sr_vals[4]
            new_account = new_sr_vals[5]
            new_bug = new_sr_vals[7]
            new_import_time = new_sr_vals[10]
            new_last_ran_time = new_sr_vals[11]

            self.account_var.set(new_account)
            self.product_var.set(new_product)
            self.sr_local_path.set(new_local_path)
            self.sr_remote_path.set(new_remote_path)
            self.bug_var.set(new_bug)
            if self.bug_var.get() != "None":
                self.bug_button.configure(
                    cursor='hand2'
                )
            else:
                self.bug_button.configure(
                    state=tk.DISABLED
                )

            # Formatting Time Vals from DB.
            conv_import_timeobj = datetime.datetime.strptime(new_import_time, "%Y-%m-%d %H:%M:%S.%f")
            formated_import_time = conv_import_timeobj.strftime("%m/%d/%Y %H:%M:%S")
            conv_ran_timeobj = datetime.datetime.strptime(new_last_ran_time, "%Y-%m-%d %H:%M:%S.%f")
            formated_ran_time = conv_ran_timeobj.strftime("%m/%d/%Y %H:%M:%S")
            self.last_ran_var.set(formated_ran_time)
            self.imported_var.set(formated_import_time)
            
            # Determine if local path exist... for right click menu.
            if os.access(new_local_path, os.R_OK):
                self.open_create_local_var.set("Open Local Folder")
            else:
                self.open_create_local_var.set("Create Local Folder")
            self.sr_remote_path.set(new_remote_path)
            # Determine if SR is "important"
            if self.pinned_state == 1:
                self.pin_unpin_var.set("Un-Pin SR")
            else:
                self.pin_unpin_var.set("Pin SR")

            # Update Color Scheme based on new vals.
            # Removing labels if 'None'
            if self.account_var.get() == "None":
                self.account_label.configure(
                    foreground="#303030"
                )
            if self.product_var.get() == "None":
                self.product_label.configure(
                    foreground="#303030"
                )

        def render_tags(self, raw_tags):
            '''
            Generates Tag widgets per tag in "raw_tags"
            '''
            tag_labels = []
            ## Creating Tag TK objects
            if raw_tags != None:
                for tag in raw_tags:
                    if tag not in self.tag_obj_list and tag != '':
                        # Add to tag objects
                        self.tag_obj_list.append(tag)
                        index_root = len(self.tag_obj_list)
                        tag_label = tk.Label(
                            self.tags_frame,
                            text=tag,
                            font=self.sub_font,
                            background="#007B84",
                            foreground="#ffffff", # For now, want to chose from pallete I think.
                        )
                        tag_label.bind("<Button-1>", self.tag_clicked)
                        tag_labels.append(tag_label)
                        # Update
                        tag_label.update_idletasks()
            return tag_labels

        def update_tag_grid(self, event=None):
            self.tags_frame.update_idletasks()
            self.smart_grid(self.tags_frame, *self.tag_tk_objs, pady=1, padx=3)

        def smart_grid(self, parent, *args, **kwargs): # *args are the widgets!
            divisions   = kwargs.pop('divisions', 100)
            force_f     = kwargs.pop('force', False)
            if 'sticky' not in kwargs:
                kwargs.update(sticky='w')
            try:
                parent.win_width
            except:
                parent.win_width = -1
            winfo_width = parent.winfo_width()
            if 1 < winfo_width != parent.win_width or force_f:
                parent.win_width = winfo_width
                row = col = width = 0
                argc = len(args)
                for i in range(argc):
                    widget_width = (args[i].winfo_width() + 10)
                    columns = max(1, int(widget_width * float(divisions) / winfo_width))
                    width += widget_width
                    if width > winfo_width:
                        width = widget_width
                        row += 1
                        col = 0
                    args[i].grid(row=row, column=col, columnspan=columns, **kwargs)
                    col += columns
                parent.update_idletasks() # update() # 
                return row + 1
                    
        def tag_clicked(self, event):
            print("you clicked", (event.widget).cget('text'))

        # LEGACY - Hover Dropdown Methods for *sub_frame*: Future user option?
        def enter_sub_frame(self, event=None):
            self.after(80, self.sub_frame.grid())
            #self.sub_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        def leave_sub_frame(self, event=None):
            self.after(0, self.sub_frame.grid_remove())
        # ~~~

        # NEW - Shift-LeftClick for Dropdown for *sub_frame*
        def render_sub_frame(self, event=None):
            ''' 
            Renders or hides the Case Tiles Sub Frame based on the classes
            *sub_frame_state* Tk BooleanVar. Default is False.
            '''
            if self.sub_frame_state.get() == False:
                self.sub_frame.grid()
                self.sub_frame_state.set(True)
            elif self.sub_frame_state.get() == True:
                self.sub_frame.grid_remove()
                self.sub_frame_state.set(False)

        def render_right_click_menu(self):
            # Get current edge of Tile...
            self.master_frame.update_idletasks()
            x = self.master_frame.winfo_rootx()
            y = self.master_frame.winfo_rooty()
            frame_w = self.master_frame.winfo_width()
            # Render Menu at edge
            self.right_click_menu.post(x + frame_w, y + 0)

        def draw_menu(self, event):
            # Check SR record before posting menu
            # Make sure commands shown are "available"
            print("this is", self.sr_id)
            # check if local folder exist.
            self.right_click_menu.post(
                    event.x_root + 10, event.y_root + 10)

        def launch_jira_browser(self, event=None):
            '''
            Launches the default OS webbrowser with a preformatted link using
            *bug_var*.
            '''
            if self.bug_var.get() != "None":
                jira_url = "https://jira-lvs.prod.mcafee.com/browse/" + self.bug_var.get()
                webbrowser.open_new(jira_url)

        def right_click_open(self, event=None):
            # Calling the init. Workspace Manager class Render method.
            self.workspace_man.render_workspace(self.sr_id)
            # Update Last ran time in DB.
            new_ran_time = datetime.datetime.now()
            new_ran_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            bcamp_api.update_sr(self.sr_id, "last_ran_time", new_ran_time)
            # Update TK vars in tile.
            self.refresh_tkVars()

        def right_click_export(self, event=None):
            pass
            # Future Feature

        def right_click_pin_sr(self, event=None):
            '''
            Needs to handle pinning and unpinning based on
            self.pin_unpin_var.get() result.

            PINNED
                self.pin_unpin_var.set("Un-Pin SR")
            else:
                self.pin_unpin_var.set("Pin SR")
            '''
            print(self.pinned_state)
            if self.pinned_state == 1: # Pinned
                # change var, and update DB
                self.pinned_state = 0
                self.pin_unpin_var.set("Pin SR")
                bcamp_api.update_sr(self.key_value, 'pinned', 0)
            else: # Unpinned
                self.pinned_state = 1
                self.pin_unpin_var.set("Un-Pin SR")
                bcamp_api.update_sr(self.key_value, 'pinned', 1)
            self.right_click_menu.update_idletasks()

        def right_click_copy_sr(self, event=None):
            threading.Thread(target=bcamp_api.to_win_clipboard,
                args=[self.sr_id]).start()

        def right_click_copy_remote(self, event=None):
            # Get path of remote content from datastore.json
            path = self.remote_path
            threading.Thread(target=bcamp_api.to_win_clipboard,
                args=[path]).start()

        def right_click_copy_local(self, event=None):
            # Get path of remote content from datastore.json
            path = self.local_path
            threading.Thread(target=bcamp_api.to_win_clipboard,
                args=[path]).start()

        def right_click_reveal_remote(self, event=None):
            # Get path of remote content from datastore.json
            os.startfile(self.sr_remote_path.get())

        def right_click_reveal_local(self, event=None):
            '''
            Opens the local folder. If it does not exist, creates it! 
            '''
            # Get path of remote content from datastore.json
            if os.access(self.sr_local_path.get(), os.R_OK):
                os.startfile(self.sr_local_path.get())
            else:
                print("Local File Missing, creating it...")
                os.mkdir(self.sr_local_path.get())
                os.startfile(self.sr_local_path.get())

        def right_click_edit_sr_record(self):
            self.master_frame.update_idletasks()
            x = self.master_frame.winfo_rootx()
            y = self.master_frame.winfo_rooty()
            frame_w = self.master_frame.winfo_width()
            edit_menu = Tk_EditCaseMenu(self.key_value)
            edit_menu.update_idletasks()
            w = edit_menu.winfo_width()
            h = edit_menu.winfo_height()
            edit_menu.geometry("%dx%d+%d+%d" % (w, h, x + frame_w + 2, y + 0))

            # Open SubFrame to prevent Geometry glitches.
            if self.sub_frame_state.get() == False:
                self.sub_frame.grid()
                self.sub_frame_state.set(True)

        def right_click_delete(self, event=None):
            # Remove DB records
            bcamp_api.drop_sr(self.key_value)
            # Next remove *downloads* folder
            try:
                os.removedirs((self.RPATH + "\\downloads\\" + self.key_value))
            except:
                print("ERROR - Unable to delete *downloads* dir for " + self.key_value)
            # Last, remove Frames
            self.master_frame.destroy()
            self.sub_frame.destroy()

        def right_click_save_all_notes(self, event=None):
            # Define result string
            save_file = filedialog.asksaveasfile(
                initialdir="/",
                title="Basecamp - ALL Notes Exporter",
                initialfile=("allnotes_" + self.key_value),
                defaultextension=".txt"
            )
            #Case Notes Stack
            save_file.write("-- Case Notes --")
            save_file.write("\n")
            # Getting saved case notes in DB.
            casenotes_val = bcamp_api.query_sr(self.key_value, 'notes')
            # Writing to save_file
            if casenotes_val != None:
                casenotes_linesplit = casenotes_val.splitlines()
                for newline in casenotes_linesplit:
                    save_file.write("\t" + newline + "\n")
            else:
                save_file.write("\tn/a")
                save_file.write("\n")

            #File Notes Stack
            save_file.write("\n")    
            save_file.write("\n")    
            save_file.write("-- File Notes --")
            save_file.write("\n")    
            # Get a list of tuples containing all file details, with "notes"
            filenotes_dump = bcamp_api.query_dump_notes(self.key_value, "*")
            # Format ouput for each file.
            for file_details in filenotes_dump:
                fname = file_details[0]
                fmod_time = datetime.datetime.fromtimestamp(float(file_details[5])).strftime('%H:%M:%S %m/%d/%Y') #TODO FORMAT
                fpath = file_details[2]
                fnotes = file_details[9]
                save_file.write("\t" + fname)
                save_file.write("\n")                
                save_file.write("\t\tLast Modified (24 Hour): " + fmod_time)
                save_file.write("\n")
                save_file.write("\t\tPath: " + fpath)
                save_file.write("\n")
                save_file.write("\t\tNotes: ")
                save_file.write("\n")

                fnotes_linesplit = fnotes.splitlines()
                for newline in fnotes_linesplit:
                    save_file.write("\t\t\t" + newline + "\n")
                save_file.write("\n")
            # Saving and closing resulting file!
            save_file.close()

        def right_click_save_case_notes(self, event=None):
            # Define result string
            save_file = filedialog.asksaveasfile(
                initialdir="/",
                title="Basecamp - Case Notes Exporter",
                initialfile=("casenotes_" + self.key_value),
                defaultextension=".txt"
            )
            #Case Notes Stack
            save_file.write("-- Case Notes --")
            save_file.write("\n")
            # Getting saved case notes in DB.
            casenotes_val = bcamp_api.query_sr(self.key_value, 'notes')
            # Writing to save_file
            if casenotes_val != None:
                casenotes_linesplit = casenotes_val.splitlines()
                for newline in casenotes_linesplit:
                    save_file.write("\t" + newline + "\n")
            else:
                save_file.write("\tn/a")
                save_file.write("\n")

        def right_click_clipboard_case_notes(self, event=None):
            casenotes_val = bcamp_api.query_sr(self.key_value, 'notes')
            threading.Thread(target=bcamp_api.to_win_clipboard,
                args=[casenotes_val]).start()


        class tag_template(tk.Frame):
            '''
            Tag "label" frame created for each tag in an SR.
            '''
            def __init__(self, master, tag_id, row, index, bg_color, fg_color):
                super().__init__()
                # Saving Tab string from 'render_tags'
                self.master = master
                self.tag_id = tag_id
                self.row = row
                self.index = index
                # Wrapping by updating grid once index > 5
                self.bg = bg_color
                self.fg = fg_color
                # Setting font for widget...


                #%%f
                self.def_font = tk_font.Font(
                    family="Consolas", size=10, weight="normal", slant="roman")

                # Calling methods
                self.config_widgets()
                #self.config_grid()

            def config_widgets(self):

                self.tag_label = tk.Label(
                    self.master,
                    text=self.tag_id,
                    font=self.def_font,
                    background="#007B84",
                    foreground=self.fg, # For now, want to chose from pallete I think.
                )
                self.bind("<Button-1>", self.tag_clicked)
                self.tag_label.bind("<Button-1>", self.tag_clicked)
            
            #def config_grid(self):
            #    self.tag_label.grid(row=self.row, column=self.index, padx=5, pady=2)

            def tag_clicked(self, event=None):
                print("you clicked :)", self.tag_id)

            def smart_grid(parent, *args, **kwargs): # *args are the widgets!
                divisions   = kwargs.pop('divisions', 100)
                force_f     = kwargs.pop('force', False)
                if 'sticky' not in kwargs:
                    kwargs.update(sticky='w')
                try:
                    parent.win_width
                except:
                    parent.win_width = -1
                winfo_width = parent.winfo_width()
                if 1 < winfo_width != parent.win_width or force_f:
                    parent.win_width = winfo_width
                    row = col = width = 0
                    argc = len(args)
                    for i in range(argc):
                        widget_width = args[i].winfo_width()
                        columns = max(1, int(widget_width * float(divisions) / winfo_width))
                        width += widget_width
                        if width > winfo_width:
                            width = widget_width
                            row += 1
                            col = 0
                        args[i].grid(row=row, column=col, columnspan=columns, **kwargs)
                        col += columns
                    parent.update_idletasks() # update() # 
                    return row + 1


class Tk_EditCaseMenu(tk.Toplevel):
    '''
    Similar to the "ImportMenu" - but to edit exisiting Case records.
    '''
    def __init__(self, key_value):
        super().__init__()
        self.key_value = key_value

        #%%hex
        self.blk100 = "#EFF1F3"
        self.blk300 = "#B2B6BC"
        self.blk400 = "#717479"
        self.blk500 = "#1E1F21" ##
        self.blk600 = "#15171C"
        self.blk700 = "#0F1117"
        self.blk900 = "#05070F"
        self.act300 = "#D5A336"

        #%%f
        self.sr_font = tk_font.Font(
            family="Consolas", size=14, weight="bold", slant="roman")
        self.mini_font = tk_font.Font(
            family="Consolas", size=8, weight="bold", slant="italic")
        self.sub_font = tk_font.Font(
            family="Consolas", size=10, weight="normal", slant="roman")

        #self.attributes('-topmost', 'true')
        #self.resizable(False, False)
        self.wm_overrideredirect(True) # Hide windows title_bar
        self.resizable = False
        self.chkbtn_fav_var = tk.IntVar()
        self.config_widgets()
        # Populate widgets with current vals from DB
        self.populate_cur_vals()
        self.config_grid()
        # Taking Focus**
        self.focus_set()

        # "destroy" TopLevel when focus lost.
        self.bind("<FocusOut>", self.on_focus_out)
        
    def on_focus_out(self, event):
        '''
        "destroy" TopLevel when focus is not a child widget of toplevel.
        '''
        if event.widget not in self.winfo_children():
            print((event.widget).winfo_name())
            self.destroy()
            
    def config_widgets(self):
        self.configure(
            background=self.blk300,
        )
        self.label_sr = ttk.Label(
            self,
            text="Adjusting " + self.key_value + "...",
            anchor="w",
            background=self.blk500,
            foreground=self.blk100,
        )
        self.label_favorite = ttk.Label(
            self,
            text="Mark as Important",
            background=self.blk300,
            foreground="black"
        )
        chk_style = ttk.Style()
        chk_style.configure('cust.TCheckbutton', background=self.blk300)
        self.chkbtn_favorite = ttk.Checkbutton(
            self,
            variable=self.chkbtn_fav_var,
            state='!selected',
            style='cust.TCheckbutton'
        )
        self.label_tags = ttk.Label(
            self,
            text="Tag(s) :",
            background=self.blk300,
            foreground="black"
        )
        self.entry_tags = ttk.Entry(
            self,
            width=29,
        )
        self.label_product = ttk.Label(
            self,
            text="Product :",
            background=self.blk300,
            foreground="black"
        )
        self.entry_product = CustomTk_autoEntry(self)
        self.entry_product.configure(
            width=29
        )
        self.label_account = ttk.Label(
            self,
            text="Account :",
            background=self.blk300,
            foreground="black"
        )
        self.entry_account = CustomTk_autoEntry(self)
        self.entry_account.configure(
            width=29
        )
        self.label_bug = ttk.Label(
            self,
            text="JIRA/Bug ID :",
            background=self.blk300,
            foreground="black"
        )
        self.entry_bug = ttk.Entry(
            self,
            width=29,
        )
        self.label_workspace = ttk.Label(
            self,
            text="Default Workspace :",
        )
        self.entry_workspace = ttk.Entry(
            self,
            width=26
        )
        self.label_customs = ttk.Label(
            self,
            text="Custom Path(s):"
        )
        self.label_hint1 = ttk.Label(
            self,
            text="Hint - Use ',' to seperate multiple values,",
            anchor=tk.CENTER
        )
        self.label_hint2 = ttk.Label(
            self,
            text="such as in the 'Tag(s)' field.",
            anchor=tk.CENTER
        )
        self.entry_customs = ttk.Entry(
            self,
            width=29
        )
        self.buttons_frame = tk.Frame(
            self,
            background=self.blk300,
        )
        self.btn_save = tk.Button(
            self.buttons_frame,
            text="Save",
            command=self.save_changes,
            background=self.blk500,
            foreground="#ffffff",
            width=12,
            relief='flat'
        )
        self.btn_cancel = tk.Button(
            self.buttons_frame,
            text="Cancel",
            command=self.destroy,
            background=self.blk500,
            foreground="#ffffff",
            relief='flat'
        )
        # Setting auto-complete list
        account_autofill = bcamp_api.query_cases_distinct('account')
        product_autofill = bcamp_api.query_cases_distinct('product')
        self.entry_account.set_completion_list(tuple(account_autofill))
        self.entry_product.set_completion_list(tuple(product_autofill))

    def config_grid(self):
        '''
        Defines Grid layout for Tk.Widgets defined in init.
        '''
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Main Widgets
        self.label_sr.grid(row=0, column=0, columnspan=2, rowspan=2, ipady=10, sticky="nsew")
        self.label_favorite.grid(
            row=2, column=0, padx=4, pady=2, sticky="e")
        self.chkbtn_favorite.grid(
            row=2, column=1, padx=4, pady=2, sticky="w")
        self.label_tags.grid(row=3, column=0, padx=4, pady=2, sticky="e")
        self.entry_tags.grid(row=3, column=1, padx=4, pady=2, sticky="w")
        self.label_product.grid(
            row=4, column=0, padx=4, pady=2, sticky="e")
        self.entry_product.grid(
            row=4, column=1, padx=4, pady=2, sticky="w")
        self.label_account.grid(
            row=5, column=0, padx=4, pady=2, sticky="e")
        self.entry_account.grid(
            row=5, column=1, padx=4, pady=2, sticky="w")
        self.label_bug.grid(row=6, column=0, padx=4, pady=2, sticky="e")
        self.entry_bug.grid(row=6, column=1, padx=4, pady=2, sticky="w")
        #self.label_workspace.grid(
        #    row=7, column=0, padx=4, pady=2, sticky="e")
        #self.entry_workspace.grid(
        #    row=7, column=1, padx=4, pady=2, sticky="w")
        #self.label_customs.grid(
        #    row=8, column=0, padx=4, pady=2, sticky="e")
        #self.entry_customs.grid(
        #    row=8, column=1, padx=4, pady=2, sticky="w")
        self.buttons_frame.grid(row=7, column=0, columnspan=2, sticky='ew')
        self.buttons_frame.columnconfigure(0, weight=1)
        self.btn_cancel.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_save.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

    def populate_cur_vals(self):
        # Getting SR vals from SQLite3
        cur_sr_vals = bcamp_api.query_all_sr(self.key_value)
        cur_pinned =  cur_sr_vals[3]
        cur_product = cur_sr_vals[4]
        cur_account = cur_sr_vals[5]
        cur_bug = cur_sr_vals[7]
        cur_tags = bcamp_api.query_tags(self.key_value)
        #cur_workspace = cur_sr_vals[8]

        # Inserting values into tk.Entries
        self.chkbtn_fav_var.set(cur_pinned) #????
        if cur_tags != None:
            for tag in cur_tags: # tags are stored as a list
                if tag != '':
                    self.entry_tags.insert(0, (tag + ", "))
        if cur_product != None:
            self.entry_product.insert(0, cur_product)
        if cur_account != None:
            self.entry_account.insert(0, cur_account)
        if cur_bug != None:
            self.entry_bug.insert(0, cur_bug)
        #if cur_workspace != None:
        #    self.combox_workspace.insert(0, cur_workspace)
        #if cur_customs != None:
        #    self.entry_customs.insert(0, cur_customs)

    def save_changes(self, event=None):
        # Getting Values from GUI
        tags_list = self.get_tags()
        account_string = self.get_account()
        #customs_list = self.get_customs()
        product_string = self.get_product()
        bug_string = self.get_bug()
        #workspace_string = self.get_workspace()
        important_bool = self.get_important()

        # Creating "import_item" Dictionary
        new_sr_dict = {
            'tags_list': tags_list,
            'account_string': account_string,
            'product_string': product_string,
            'bug_string': bug_string,
            'important_bool': important_bool
            #'workspace_string': workspace_string,
            #'customs_list': customs_list,
        }

        # Updating "import_item" -> Gui.import_handler(new_import_dict)
        bcamp_api.update_case_record(self.key_value, new_sr_dict)
        # Refresh Caseview Tiles.
        Gui.refresh_CaseView.value = self.key_value

        # Closing window...
        self.destroy()

    # Advanced Options "Get" methods
    def get_tags(self):
        '''
        Returns list of [Tags] from the UI, seperated by ','

        If the ImportMenu entry is not populated, this will return None
        '''
        raw_tags = str(self.entry_tags.get())
        prepped_tags = raw_tags.replace(", ", ",")
        tags_list = prepped_tags.split(",")
        # Remove empty tag artifact
        while '' in tags_list:
            print("removing ''")
            tags_list.remove('')
            # Return Vals
        if raw_tags != "":
            return_val = tags_list
        else:
            return_val = None

        return return_val

    def get_account(self):
        '''
        Returns provided account name as a "string".

        If the ImportMenu entry is not populated, this will return None
        '''
        account_val = self.entry_account.get()
        return_val = None
        if account_val != "":
            return_val = account_val

        return return_val

    def get_customs(self):
        '''
        Returns list of <os.abspath Objects>, seperated by ','

        If the ImportMenu entry is not populated, this will return None
        '''
        raw_paths = str(self.entry_customs.get())
        paths_list = raw_paths.split(",")
        return_val = None
        if raw_paths != "":
            return_val = paths_list

        return return_val

    def get_product(self):
        '''
        Returns provided Product as a "string".

        If the ImportMenu entry is not populated, this will return None
        '''
        product_val = self.entry_product.get()
        return_val = None
        if product_val != "":
            return_val = product_val

        return return_val

    def get_workspace(self):
        '''
        Returns provided Workspace as a "string". 

        If the ImportMenu entry is not populated, this will return 'basic'
        '''
        workspace_val = self.combox_workspace.get()
        return_val = None
        if workspace_val != "":
            return_val = workspace_val

        return return_val

    def get_important(self):
        '''
        Returns bool if the favorite checkbox is checked or not.
        '''
        chkbtn_val = self.chkbtn_fav_var.get()
        return chkbtn_val

    def get_bug(self):
        workspace_val = self.entry_bug.get()
        return_val = None
        if workspace_val != "":
            return_val = workspace_val

        return return_val


class Tk_SettingsMenu(tk.Toplevel):
    '''
    This is the UI menu where users can update the 'config.json' file,
    which contains various CONSTANTS and variables used throughout 
    the Application.

    TODO : Unpacker exe's dont save when changed.
    TODO : Enabling an unpacker requires a restart before the unpacker
        is detected.
    '''

    def __init__(self, event=None):
        super().__init__()
        self.title("Basecamp Settings")
        self.attributes('-topmost', 'true')
        self.resizable(False, False)
        self.mode_str = tk.StringVar()
        self.selected_menu = tk.IntVar()

        #%%hex
        self.configure(background="#111111")

        # TK methods
        self.config_widgets()
        self.config_grid()
        self.get_mode()
        # Render Default Msg
        self.Tk_DefaultMsg(self.base_menu_frame)

    def config_widgets(self):
        #%%hex
        self.base_btn_frame = tk.Frame(
            self,
            background="#111111",
            width=50
        )
        self.base_menu_frame = tk.Frame(
            self,
            background="#303030"
        )
        self.paths_menu = tk.Button(
            self.base_btn_frame,
            text="Main Paths      ▷",
            anchor='center',
            command=self.render_paths,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.workpanes_menu = tk.Button(
            self.base_btn_frame,
            text="Workpanes      ▷",
            anchor='center',
            command=self.render_workpanes,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.automations_menu = tk.Button(
            self.base_btn_frame,
            text="Automations    ▷",
            anchor='center',
            command=self.render_automations,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.unpacker_menu = tk.Button(
            self.base_btn_frame,
            text="Unpackers       ▷",
            anchor='center',
            command=self.render_unpackers,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.json_menu = tk.Button(
            self.base_btn_frame,
            text="JSON Viewer    ▷",
            anchor='center',
            command=self.render_json,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.json_menu.bind('<Quadruple-1>', self.enable_dev_mode)
        self.dev_mode_label = tk.Label(
            self.base_btn_frame,
            textvariable=self.mode_str,
            background="#111111",
            foreground="#525258"
        )

    def config_grid(self):
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)
        self.columnconfigure(1, weight=1)
        # Btn Frame Config
        self.base_btn_frame.grid(
            row=0, column=0, padx=3, pady=5, sticky="nsew")
        self.paths_menu.grid(row=0, column=0, padx=1, pady=1, sticky='ew')
        #self.unpacker_menu.grid(
        #    row=1, column=0, padx=1, pady=1, sticky='ew')
        self.automations_menu.grid(
            row=2, column=0, padx=1, pady=1, sticky='ew')
        self.json_menu.grid(row=3, column=0, padx=1, pady=1, sticky='ew')
        self.dev_mode_label.grid(
            row=4, column=0, padx=3, pady=3, sticky="sw")
        # Menu Frame Config
        # Row and Column config found in Nested Frame class...
        self.base_menu_frame.grid(
            row=0, column=1, padx=3, pady=5, sticky="nsew")

    def render_paths(self):
        # self.base_menu_frame()
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_Paths(self.base_menu_frame)

    def render_json(self):
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_JsonViewer(self.base_menu_frame)

    def render_unpackers(self):
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_Unpackers(self.base_menu_frame)

    def render_workpanes(self):
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_Workpanes(self.base_menu_frame, self.workpane_man)

    def render_automations(self):
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_Automations(self.base_menu_frame)

    def get_mode(self):
        if bcamp_api.get_config('dev_mode') == "True":
            self.mode_str.set("DevMode 😈")
        else:
            self.mode_str.set("Howdy, Engineer 😎")

    def enable_dev_mode(self, event=None):
        bcamp_api.update_config('dev_mode', "True")
        self.mode_str.set("DevMode 😈")


    class Tk_DefaultMsg(tk.Frame):
        '''
        Intial Frame rendered when settings is launched! 
        '''

        def __init__(self, master):
            super().__init__()
            self.master = master  # Nested so we use master

            # Tk Methods
            self.config_widgets()
            self.config_grid()

        def config_widgets(self):




            #%%hex
            self.msg_label = tk.Label(
                self.master,
                text="Welcome to the Settings Menu!\n\nSelect something to configure to the left,\n\nor don't, I wont tell anyone...",
                background='#303030',
                foreground='#969696'
            )





        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.master.rowconfigure(0, weight=1)
            self.master.columnconfigure(0, weight=1)
            self.msg_label.grid(row=0, column=0, padx=10,
                                pady=10, sticky='nsew')


    class Tk_Paths(tk.Frame):
        '''
        Paths Setting Menu Frame for Remote and Local Paths
        '''

        def __init__(self, master):
            super().__init__()
            self.master = master
            RPATH = str(pathlib.Path(__file__).parent.absolute()
                        ).rpartition('\\')[0]
            # Getting values from config.json
            open_config = open((RPATH + "\\core\\config.json"), "r")
            self.conv_config = json.load(open_config)
            open_config.close()
            self.remote_strVar = tk.StringVar()
            self.remote_strVar.set(self.conv_config['remote_path'])
            self.local_strVar = tk.StringVar()
            self.local_strVar.set(self.conv_config['local_path'])

            # Tk Methods
            self.config_widgets()
            self.config_grid()

        def config_widgets(self):
            self.local_label = tk.Label(
                self.master,
                text="Local Downloads (Path)",
                background="#303030",
                foreground='#f5f5f5'
            )
            self.local_entry = tk.Entry(
                self.master,
                width=70,
                textvariable=self.local_strVar,
                background="#222222",
                foreground='#f5f5f5'
            )
            self.local_browse = tk.Button(
                self.master,
                text="Browse",
                command=self.explorer_browser,
                background="#222222",
                foreground='#f5f5f5',
                relief='flat'
            )
            self.remote_label = tk.Label(
                self.master,
                text="Network Folder (Path) - Fixed Value",
                background="#303030",
                foreground='#f5f5f5'
            )
            self.remote_entry = tk.Entry(
                self.master,
                width=70,
                textvariable=self.remote_strVar,
                state='disabled',
                background="#222222",
                foreground='#f5f5f5'
            )
            self.remote_browse = tk.Button(
                self.master,
                text="Browse",
                command=self.r_explorer_browser,
                relief='flat',
                background="#222222",
                foreground='#f5f5f5',
                state="disabled"
            )
            self.spacer = tk.Label(
                self.master,
                text="You shouldnt see this message... :)",
                background="#303030",
                foreground="#303030",
            )
            self.save_bar = tk.Frame(
                self.master,
                background="#212121"
            )
            self.save_btn = tk.Button(
                self.save_bar,
                text="Save and Apply",
                background='#badc58',
                foreground='#111111',
                relief="flat",
                command=self.save_settings
            )

        def config_grid(self):
            self.local_label.grid(
                row=0, column=0, padx=3, pady=3, sticky='nsew')
            self.local_entry.grid(
                row=1, column=0, padx=3, pady=2, ipady=2, sticky='new')
            self.local_browse.grid(row=1, column=1, padx=3, sticky='new')
            self.remote_label.grid(
                row=2, column=0, padx=3, pady=3, sticky='nsew')
            self.remote_entry.grid(
                row=3, column=0, padx=3, pady=2, ipady=2, sticky='new')
            self.remote_browse.grid(
                row=3, column=1, padx=3, pady=0, sticky='new')
            self.spacer.grid(row=4, column=0, columnspan=2, sticky="nsew")
            self.save_bar.grid(row=8, column=0, columnspan=2, sticky="sew")
            self.save_bar.columnconfigure(0, weight=1)
            self.save_btn.grid(row=0, column=0, padx=1, pady=1, sticky='e')

        def explorer_browser(self):
            filename = filedialog.askdirectory(
                initialdir="/",
                title="Select a Folder",
            )
            print("New path> ", filename)
            self.local_strVar.set(filename)

        def r_explorer_browser(self):
            filename = filedialog.askdirectory(
                initialdir="//dnvcorpvf2.corp.nai.org/nfs_dnvspr",
                title="Select a Folder",
            )
            print("New path> ", filename)
            self.remote_strVar.set(filename)

        def clear_widgets(self):
            self.remote_label.grid_forget()
            self.remote_entry.grid_forget()
            self.remote_browse.grid_forget()
            self.local_label.grid_forget()
            self.local_entry.grid_forget()
            self.local_browse.grid_forget()

        def save_settings(self):
            # JSON Goodies
            config_path = self.RPATH + "\\core\\config.json"
            with open(config_path, "r") as read_file:
                new_config = json.load(read_file)
                new_config['local_path'] = self.local_strVar.get()
            with open(config_path, "w") as write_file:
                json.dump(new_config, write_file, indent=4)


    class Tk_JsonViewer(tk.Frame):
        '''
        TODO - REMOVE THIS POST SQL MIGRATION FOR CONFIG.
        
        JSON Viewer Setting Menu Frame to view Raw 'config.json'
        '''

        def __init__(self, master):
            super().__init__()
            self.master = master  # Nested so we use master
            RPATH = str(pathlib.Path(__file__).parent.absolute()
                        ).rpartition('\\')[0]
            # Getting values from config.json
            open_config = open((RPATH + "\\core\\config.json"), "r")
            self.conv_config = json.load(open_config)
            open_config.close()

            # Tk Methods
            self.config_widgets()
            self.config_grid()

        def config_widgets(self):





            #%%hex
            self.textbox = tk.Text(
                self.master,
                background="#222222",
                foreground="#ffcf69",
                wrap='word',
            )







            self.textbox.insert('1.0', pprint.pformat(self.conv_config))

        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.textbox.grid(row=0, column=0, sticky='nsew')


    class Tk_Automations(tk.Frame):
        '''
        Configure the Enabled "Automations" found in "extension/automations"
        and update the config.json file for newly enabled modules.
        '''

        def __init__(self, master):
            super().__init__()
            self.master = master
            self.RPATH = str(pathlib.Path(
                __file__).parent.absolute()).rpartition('\\')[0]
            # Getting values from config.json
            open_config = open((self.RPATH + "\\core\\config.json"), "r")
            self.conv_config = json.load(open_config)
            open_config.close()
            self.enabled_list = self.get_enabled_list()
            self.automation_path_list = self.get_automations_list()
            self.enable_bar_str = tk.StringVar()
            self.info_str = tk.StringVar()
            self.extension_str = tk.StringVar()
            self.author_str = tk.StringVar()
            self.config_widgets()
            self.config_grid()

        def config_widgets(self):
            self.lframe_automations = tk.LabelFrame(
                self.master,
                text="Disable/Enable Automations"
            )
            self.automation_listbox = tk.Listbox(
                self.lframe_automations,
                width=40,
                selectmode=tk.SINGLE,
                relief="flat",
            )
            self.automation_listbox.bind(
                '<<ListboxSelect>>', self.get_selected_info)
            
            self.enable_bar = tk.Button(
                self.lframe_automations,
                textvariable=self.enable_bar_str,
                background='#939393',
                foreground='#111111',
                relief="flat",
                command=self.toggle_automation
            )
            self.enabled_listbox = tk.Listbox(
                self.lframe_automations,
                width=40,
                relief="flat",
                selectmode=tk.SINGLE
            )
            self.enabled_listbox.bind(
                '<<ListboxSelect>>', self.get_selected_info)
            # Get all content in './extension/automations'
            self.fill_automation_list()
            self.fill_enabled_list()

            self.lframe_info = tk.LabelFrame(
                self.master,
                text="Selected Details"
            )
            self.label_info = tk.Label(
                self.lframe_info,
                text="Description:",
                anchor='w'
            )
            self.info_text = tk.Label(
                self.lframe_info,
                textvariable=self.info_str,
                width=40,
                wraplength=250,
                justify=tk.LEFT
            )
            self.label_extensions = tk.Label(
                self.lframe_info,
                text="Supported File Types:",
                anchor='w'
            )
            self.extensions_text = tk.Label(
                self.lframe_info,
                textvariable=self.extension_str,
                justify=tk.CENTER
            )
            self.label_author = tk.Label(
                self.lframe_info,
                text="Created By:",
                anchor='w'
            )
            self.author_text = tk.Label(
                self.lframe_info,
                textvariable=self.author_str
            )

            self.save_bar = tk.Frame(
                self.master,
                background='#212121',
            )
            self.open_folder_btn = tk.Button(
                self.save_bar,
                text="Open Folder",
                background='#939393',
                foreground='#111111',
                relief="flat",
                command=self.open_folder
            )
            self.save_btn = tk.Button(
                self.save_bar,
                text="Save and Apply",
                background='#badc58',
                foreground='#111111',
                relief="flat",
                command=self.save_settings
            )

        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.lframe_automations.grid(
                row=0, column=0, pady=4,  sticky='nsew')
            self.lframe_info.grid(row=1, column=0, pady=4, sticky='nsew')
            # lframe_automations grid
            self.lframe_automations.rowconfigure(0, weight=1)
            self.lframe_automations.columnconfigure(0, weight=1)
            self.automation_listbox.grid(row=0, column=0, sticky='nsew')
            self.enable_bar.grid(row=0, column=1, sticky='ns')
            self.enabled_listbox.grid(row=0, column=2, sticky='nsew')
            # lframe_info grid
            self.lframe_info.rowconfigure(0, weight=1)
            self.lframe_info.columnconfigure(1, weight=1)
            self.label_info.grid(row=0, column=0, sticky='w')
            self.info_text.grid(row=1, column=0, rowspan=4, sticky='nsw')
            self.label_extensions.grid(row=0, column=1, sticky='w')
            self.extensions_text.grid(row=1, column=1, sticky='nsw')
            self.label_author.grid(row=2, column=1, sticky='w')
            self.author_text.grid(row=3, column=1, sticky='nsw')
            # SaveBar
            self.save_bar.grid(row=8, column=0, ipady=2, sticky="sew")
            self.save_bar.columnconfigure(0, weight=1)
            self.open_folder_btn.grid(row=0, column=0, padx=3, pady=1, sticky='e')
            self.save_btn.grid(row=0, column=1, padx=3, pady=1, sticky='e')

        def get_automations_list(self):
            #Check /extensions/automations is readable
            automation_path = (self.RPATH + "\\extensions\\automations")
            # Store raw os.DirEntries
            automation_list = []
            if os.access(automation_path, os.R_OK):
                with os.scandir(automation_path) as scanner:
                    for dirEntry in scanner:
                        if dirEntry.is_dir() and dirEntry.name not in self.enabled_list:
                            test_properties_path = str(
                                dirEntry.path) + "\\properties.json"
                            if os.access(test_properties_path, os.R_OK):
                                automation_list.append(dirEntry.path)
            return automation_list

        def get_enabled_list(self):
            return_list = []
            automation_list = self.conv_config['automations']
            for automation in automation_list:
                return_list.append(automation['name'])
            print(return_list)
            return return_list

        def fill_automation_list(self):
            for path in self.automation_path_list:
                path_name = str(path).rpartition("\\")[2]
                self.automation_listbox.insert(tk.END, path_name)

        def fill_enabled_list(self):
            for automation in self.enabled_list:
                self.enabled_listbox.insert(tk.END, automation)

        def get_selected_info(self, event=None):
            try:
                if self.automation_listbox.get(self.automation_listbox.curselection()) != "":
                    selected = self.automation_listbox.get(
                        self.automation_listbox.curselection())
                    self.enable_bar_str.set(">")
            except:
                if self.enabled_listbox.get(self.enabled_listbox.curselection()) != "":
                    selected = self.enabled_listbox.get(
                        self.enabled_listbox.curselection())
                    self.enable_bar_str.set("<")

                pass
            properties_path = (
                self.RPATH + "\\extensions\\automations\\" + selected + "\\properties.json")
            with open(properties_path, "r") as read_file:
                conv_properties = json.load(read_file)
                # Setting StringVars for Info Pane
                self.info_str.set(conv_properties['description'])
                self.extension_str.set(conv_properties['extensions'])
                self.author_str.set(conv_properties['author'])

        def toggle_automation(self, event=None):
            # Try for Enabling
            try:
                og_selected = self.automation_listbox.get(
                    self.automation_listbox.curselection())
                # Removing from "automation" list
                self.automation_listbox.delete(
                    self.automation_listbox.curselection())
                # And inserting into enabled list
                self.enabled_listbox.insert(0, og_selected)
                test_selected = self.enabled_listbox.get(1)
                print(test_selected)
            except tk.TclError:
                # Thrown when disabling cause "automation_list"
                # selection is empty
                selected = self.enabled_listbox.get(
                    self.enabled_listbox.curselection())
                self.enabled_listbox.delete(
                    self.enabled_listbox.curselection())
                self.automation_listbox.insert(0, selected)

        def open_folder(self, event=None):
            '''
            Launches the "automations" folder for easy import!
            '''
            automation_dir_path = self.RPATH + "\\extensions\\automations"
            print("slutbug>", automation_dir_path)
            os.startfile(automation_dir_path)

        def save_settings(self):
            # Get current items in 'enabled list'.
            enabled_items = self.enabled_listbox.get(0, tk.END)
            final_automations_list = []
            for automation in enabled_items:
                properties_path = (
                    self.RPATH + "\\extensions\\automations\\" + automation + "\\properties.json")
                with open(properties_path, "r") as read_file:
                    conv_properties = json.load(read_file)
                    # Storing to config.json style dict
                    automation_config = {
                        'name': automation,
                        'extensions': [conv_properties['extensions']],
                        "exe": conv_properties['exe'],
                        'downloadFirst': conv_properties['downloadFirst']
                    }
                    final_automations_list.append(automation_config)
            # JSON Goodies
            config_path = self.RPATH + "\\core\\config.json"
            with open(config_path, "r") as read_file:
                new_config = json.load(read_file)
                new_config['automations'] = final_automations_list
            with open(config_path, "w") as write_file:
                json.dump(new_config, write_file, indent=4)

        def direct_import_broswer(self):
            filename = filedialog.askopenfilename(
                initialdir="/",
                title="Select a target .exe",
            )
            return filename


    class Tk_Unpackers(tk.Frame):
        '''
        Configure the Enabled "Unpackers" found in "extension/unpackers"
        and update the config.json file for newly enabled modules.
        '''

        def __init__(self, master):
            super().__init__()
            self.master = master
            self.RPATH = str(pathlib.Path(
                __file__).parent.absolute()).rpartition('\\')[0]
            # Getting values from config.json
            open_config = open((self.RPATH + "\\core\\config.json"), "r")
            self.conv_config = json.load(open_config)
            open_config.close()
            self.enabled_list = self.get_enabled_list()
            self.unpacker_path_list = self.get_unpackers_list()
            self.enable_bar_str = tk.StringVar()
            self.info_str = tk.StringVar()
            self.extension_str = tk.StringVar()
            self.author_str = tk.StringVar()
            self.config_widgets()
            self.config_grid()

        def get_unpackers_list(self):
            #Check /extensions/unpackers is readable
            unpacker_path = (self.RPATH + "\\extensions\\unpackers")
            # Store raw os.DirEntries
            unpacker_list = []
            if os.access(unpacker_path, os.R_OK):
                with os.scandir(unpacker_path) as scanner:
                    for dirEntry in scanner:
                        if dirEntry.is_dir() and dirEntry.name not in self.enabled_list:
                            test_properties_path = str(
                                dirEntry.path) + "\\properties.json"
                            if os.access(test_properties_path, os.R_OK):
                                unpacker_list.append(dirEntry.path)
            return unpacker_list

        def get_enabled_list(self):
            return_list = []
            unpacker_list = self.conv_config['unpackers']
            for unpacker in unpacker_list:
                return_list.append(unpacker['name'])
            print(return_list)
            return return_list

        def config_widgets(self):
            self.lframe_unpackers = tk.LabelFrame(
                self.master,
                text="Manage Unpackers"
            )
            self.unpacker_listbox = tk.Listbox(
                self.lframe_unpackers,
                width=40,
                selectmode=tk.SINGLE,
                relief="flat",
            )
            self.unpacker_listbox.bind(
                '<<ListboxSelect>>', self.get_selected_info)
            
            self.enable_bar = tk.Button(
                self.lframe_unpackers,
                textvariable=self.enable_bar_str,
                background='#939393',
                foreground='#111111',
                relief="flat",
                command=self.toggle_unpacker
            )
            self.enabled_listbox = tk.Listbox(
                self.lframe_unpackers,
                width=40,
                relief="flat",
                selectmode=tk.SINGLE
            )
            self.enabled_listbox.bind(
                '<<ListboxSelect>>', self.get_selected_info)
            # Get all content in './extension/unpackers'
            self.fill_unpacker_list()
            self.fill_enabled_list()

            self.lframe_info = tk.LabelFrame(
                self.master,
                text="Unpacker Details"
            )
            self.label_info = tk.Label(
                self.lframe_info,
                text="Description:",
                anchor='w'
            )
            self.info_text = tk.Label(
                self.lframe_info,
                textvariable=self.info_str,
                width=40,
                wraplength=250,
                justify=tk.LEFT
            )
            self.label_extensions = tk.Label(
                self.lframe_info,
                text="Supported File Types:",
                anchor='w'
            )
            self.extensions_text = tk.Label(
                self.lframe_info,
                textvariable=self.extension_str,
                justify=tk.CENTER
            )
            self.label_author = tk.Label(
                self.lframe_info,
                text="Created By:",
                anchor='w'
            )
            self.author_text = tk.Label(
                self.lframe_info,
                textvariable=self.author_str
            )

            self.save_bar = tk.Frame(
                self.master,
                background='#212121',
            )
            self.open_folder_btn = tk.Button(
                self.save_bar,
                text="Open Folder",
                background='#939393',
                foreground='#111111',
                relief="flat",
                command=self.open_folder
            )
            self.save_btn = tk.Button(
                self.save_bar,
                text="Save and Apply",
                background='#badc58',
                foreground='#111111',
                relief="flat",
                command=self.save_settings
            )

        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.lframe_unpackers.grid(
                row=0, column=0, pady=4,  sticky='nsew')
            self.lframe_info.grid(row=1, column=0, pady=4, sticky='nsew')
            # lframe_unpackers grid
            self.lframe_unpackers.rowconfigure(0, weight=1)
            self.lframe_unpackers.columnconfigure(0, weight=1)
            self.unpacker_listbox.grid(row=0, column=0, sticky='nsew')
            self.enable_bar.grid(row=0, column=1, sticky='ns')
            self.enabled_listbox.grid(row=0, column=2, sticky='nsew')
            # lframe_info grid
            self.lframe_info.rowconfigure(0, weight=1)
            self.lframe_info.columnconfigure(1, weight=1)
            self.label_info.grid(row=0, column=0, sticky='w')
            self.info_text.grid(row=1, column=0, rowspan=4, sticky='nsw')
            self.label_extensions.grid(row=0, column=1, sticky='w')
            self.extensions_text.grid(row=1, column=1, sticky='nsw')
            self.label_author.grid(row=2, column=1, sticky='w')
            self.author_text.grid(row=3, column=1, sticky='nsw')
            # SaveBar
            self.save_bar.grid(row=8, column=0, ipady=2, sticky="sew")
            self.save_bar.columnconfigure(0, weight=1)
            self.open_folder_btn.grid(row=0, column=0, padx=3, pady=1, sticky='e')
            self.save_btn.grid(row=0, column=1, padx=3, pady=1, sticky='e')

        def fill_unpacker_list(self):
            for path in self.unpacker_path_list:
                path_name = str(path).rpartition("\\")[2]
                self.unpacker_listbox.insert(tk.END, path_name)

        def fill_enabled_list(self):
            for unpacker in self.enabled_list:
                self.enabled_listbox.insert(tk.END, unpacker)

        def get_selected_info(self, event=None):
            try:
                if self.unpacker_listbox.get(self.unpacker_listbox.curselection()) != "":
                    selected = self.unpacker_listbox.get(
                        self.unpacker_listbox.curselection())
                    self.enable_bar_str.set(">")
            except:
                if self.enabled_listbox.get(self.enabled_listbox.curselection()) != "":
                    selected = self.enabled_listbox.get(
                        self.enabled_listbox.curselection())
                    self.enable_bar_str.set("<")

                pass
            properties_path = (
                self.RPATH + "\\extensions\\unpackers\\" + selected + "\\properties.json")
            with open(properties_path, "r") as read_file:
                conv_properties = json.load(read_file)
                # Setting StringVars for Info Pane
                self.info_str.set(conv_properties['description'])
                self.extension_str.set(conv_properties['extensions'])
                self.author_str.set(conv_properties['author'])

        def toggle_unpacker(self, event=None):
            # Try for Enabling
            try:
                og_selected = self.unpacker_listbox.get(
                    self.unpacker_listbox.curselection())
                # Removing from "unpacker" list
                self.unpacker_listbox.delete(
                    self.unpacker_listbox.curselection())
                # And inserting into enabled list
                self.enabled_listbox.insert(0, og_selected)
                test_selected = self.enabled_listbox.get(1)
                print(test_selected)
            except tk.TclError:
                # Thrown when disabling cause "unpacker_list"
                # selection is empty
                selected = self.enabled_listbox.get(
                    self.enabled_listbox.curselection())
                self.enabled_listbox.delete(
                    self.enabled_listbox.curselection())
                self.unpacker_listbox.insert(0, selected)

        def open_folder(self, event=None):
            '''
            Launches the "Unpackers" folder for easy import!
            '''
            unpacker_dir_path = self.RPATH + "\\extensions\\unpackers"
            print("slutbug>", unpacker_dir_path)
            os.startfile(unpacker_dir_path)

        def save_settings(self):
            # Get current items in 'enabled list'.
            enabled_items = self.enabled_listbox.get(0, tk.END)
            final_unpackers_list = []
            for unpacker in enabled_items:
                properties_path = (
                    self.RPATH + "\\extensions\\unpackers\\" + unpacker + "\\properties.json")
                with open(properties_path, "r") as read_file:
                    conv_properties = json.load(read_file)
                    # Storing to config.json style dict
                    unpacker_config = {
                        'name': unpacker,
                        'extensions': [conv_properties['extensions']],
                        "exe": conv_properties['exe']
                    }
                    final_unpackers_list.append(unpacker_config)
            # JSON Goodies
            config_path = self.RPATH + "\\core\\config.json"
            with open(config_path, "r") as read_file:
                new_config = json.load(read_file)
                new_config['unpackers'] = final_unpackers_list
            with open(config_path, "w") as write_file:
                json.dump(new_config, write_file, indent=4)


    class Tk_Workpanes(tk.Frame):
        '''
        *Removed for now... 

        Configure the Enabled "workpanes" found in "extension/workpanes"
        and update the config.json file for newly enabled modules.

        This will use lf_extension_manager to determine which Workpanes
        to "import" or show as available.
        '''

        def __init__(self, master, workpane_manager):
            super().__init__()
            # Extension Managers from lf_extension_man...
            self.workpane_man = workpane_manager
            self.master = master
            self.RPATH = str(pathlib.Path(
                __file__).parent.absolute()).rpartition('\\')[0]
            # Getting values from config.json
            open_config = open((self.RPATH + "\\core\\config.json"), "r")
            self.conv_config = json.load(open_config)
            open_config.close()
            self.enabled_list = self.get_enabled_list()
            self.workpane_list = self.workpane_man.get()
            self.enable_bar_str = tk.StringVar()
            self.info_str = tk.StringVar()
            self.dependencies_str = tk.StringVar()
            self.author_str = tk.StringVar()
            self.config_widgets()
            self.config_grid()

        def config_widgets(self):
            self.lframe_workpanes = ttk.LabelFrame(
                self.master,
                text="Manage workpanes"
            )
            self.workpane_listbox = tk.Listbox(
                self.lframe_workpanes,
                width=40,
                selectmode=tk.SINGLE
            )
            self.workpane_listbox.bind(
                '<<ListboxSelect>>', self.get_selected_info)
            self.enable_bar = tk.Button(
                self.lframe_workpanes,
                textvariable=self.enable_bar_str,
                relief="flat",
                command=self.toggle_unpacker
            )
            self.enabled_workpane = tk.Listbox(
                self.lframe_workpanes,
                width=40,
                selectmode=tk.SINGLE
            )
            self.enabled_workpane.bind(
                '<<ListboxSelect>>', self.get_selected_info)
            # Get all content in './extension/workpanes'
            self.fill_unpacker_list()
            self.fill_enabled_list()

            self.lframe_info = ttk.LabelFrame(
                self.master,
                text="Unpacker Details"
            )
            self.label_info = tk.Label(
                self.lframe_info,
                text="Description:",
                anchor='w'
            )
            self.info_text = tk.Label(
                self.lframe_info,
                textvariable=self.info_str,
                width=40,
                wraplength=250,
                justify=tk.LEFT
            )
            self.label_dependencies = tk.Label(
                self.lframe_info,
                text="Dependencies:",
                anchor='w'
            )
            self.dependencies_text = tk.Label(
                self.lframe_info,
                textvariable=self.dependencies_str,
                justify=tk.CENTER
            )
            self.label_author = tk.Label(
                self.lframe_info,
                text="Created By:",
                anchor='w'
            )
            self.author_text = tk.Label(
                self.lframe_info,
                textvariable=self.author_str
            )



            #%%hex
            self.save_bar = tk.Frame(
                self.master,
                background="#212121"
            )
            self.save_btn = tk.Button(
                self.save_bar,
                text="Save and Apply",
                background='#badc58',
                foreground='#111111',
                relief="flat",
                command=self.save_settings
            )

        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.lframe_workpanes.grid(
                row=0, column=0, pady=4,  sticky='nsew')
            self.lframe_info.grid(row=1, column=0, pady=4, sticky='nsew')
            # lframe_workpanes grid
            self.lframe_workpanes.rowconfigure(0, weight=1)
            self.lframe_workpanes.columnconfigure(0, weight=1)
            self.workpane_listbox.grid(row=0, column=0, sticky='nsew')
            self.enable_bar.grid(row=0, column=1, sticky='ns')
            self.enabled_workpane.grid(row=0, column=2, sticky='nsew')
            # lframe_info grid
            self.lframe_info.rowconfigure(0, weight=1)
            self.lframe_info.columnconfigure(1, weight=1)
            self.label_info.grid(row=0, column=0, sticky='w')
            self.info_text.grid(row=1, column=0, rowspan=4, sticky='nsw')
            self.label_dependencies.grid(row=0, column=1, sticky='w')
            self.dependencies_text.grid(row=1, column=1, sticky='nsw')
            self.label_author.grid(row=2, column=1, sticky='w')
            self.author_text.grid(row=3, column=1, sticky='nsw')
            # SaveBar
            self.save_bar.grid(row=8, column=0, columnspan=1, sticky="sew")
            self.save_bar.columnconfigure(0, weight=1)
            self.save_btn.grid(row=0, column=0, padx=1, pady=1, sticky='e')

        def get_enabled_list(self):
            return_list = []
            unpacker_list = self.conv_config['workpanes']
            for unpacker_dict in unpacker_list:
                return_list.append(unpacker_dict['name'])
            print(return_list)
            return return_list

        def fill_unpacker_list(self):
            for path in self.workpane_list:
                # Dont show dupes that are already enabled
                if path not in self.enabled_list:
                    path_name = str(path).rpartition("\\")[2]
                    self.workpane_listbox.insert(tk.END, path_name)

        def fill_enabled_list(self):
            for unpacker in self.enabled_list:
                self.enabled_workpane.insert(tk.END, unpacker)

        def get_selected_info(self, event=None):
            try:
                if self.workpane_listbox.get(self.workpane_listbox.curselection()) != "":
                    selected = self.workpane_listbox.get(
                        self.workpane_listbox.curselection())
                    self.enable_bar_str.set(">")
            except:
                if self.enabled_workpane.get(self.enabled_workpane.curselection()) != "":
                    selected = self.enabled_workpane.get(
                        self.enabled_workpane.curselection())
                    self.enable_bar_str.set("<")

                pass
            properties_path = (
                self.RPATH + "\\extensions\\workpanes\\" + selected + "\\properties.json")
            with open(properties_path, "r") as read_file:
                conv_properties = json.load(read_file)
                # Setting StringVars for Info Pane
                self.info_str.set(conv_properties['description'])
                self.dependencies_str.set(conv_properties['dependencies'])
                self.author_str.set(conv_properties['author'])

        def toggle_unpacker(self, event=None):
            # Try for Enabling
            try:
                og_selected = self.workpane_listbox.get(
                    self.workpane_listbox.curselection())
                # Removing from "unpacker" list
                self.workpane_listbox.delete(
                    self.workpane_listbox.curselection())
                # And inserting into enabled list
                self.enabled_workpane.insert(0, og_selected)
                test_selected = self.enabled_workpane.get(1)
                print(test_selected)
            except tk.TclError:
                # Thrown when disabling cause "unpacker_list"
                # selection is empty
                selected = self.enabled_workpane.get(
                    self.enabled_workpane.curselection())
                self.enabled_workpane.delete(
                    self.enabled_workpane.curselection())
                self.workpane_listbox.insert(0, selected)

        def save_settings(self):
            # Get current items in 'enabled list'.
            enabled_items = self.enabled_workpane.get(0, tk.END)
            final_workpanes_list = []
            for unpacker in enabled_items:
                properties_path = (
                    self.RPATH + "\\extensions\\workpanes\\" + unpacker + "\\properties.json")
                with open(properties_path, "r") as read_file:
                    conv_properties = json.load(read_file)
                    # Storing Name-Keyed Dict to config.json
                    pane_dict = {
                        'name': unpacker,
                        'dependencies': conv_properties['dependencies']
                    }
                    print(__name__, pane_dict)
                    final_workpanes_list.append(pane_dict)
            # JSON Goodies
            config_path = self.RPATH + "\\core\\config.json"
            with open(config_path, "r") as read_file:
                new_config = json.load(read_file)
                new_config['workpanes'] = final_workpanes_list
            with open(config_path, "w") as write_file:
                json.dump(new_config, write_file, indent=4)


class Tk_ImportMenu(tk.Frame):
    '''

    The standard Import Menu that allows users to query via SR Numbers, or
    direct file/dir imports. This Ttk.Frame also includes methods to 
    return various user entries for inital CaseData generation. Notably,
    if a user does not populate the "Advanced Settings" during import
    the applicable CaseData entry will be set to "None"

    - get_tags() : Returns list of [Tags] from the UI, seperated by ','
    - get_account() : Returns provided account name as a "string".
    - get_customs() : Returns list of <os.abspath Objects>, seperated by ','
    - get_product() : Returns provided Product as a "string".
    - get_workspace() : Returns provided Workspace as a "string".
    '''

    def __init__(self, master, Tk_WorkspaceTabs, import_string, event=None):
        super().__init__(master=master)
        #self.title("Basecamp Importer")
        #self.attributes('-topmost', 'true')
        #self.resizable(False, False)
        #self.resizable = False
        self.Tk_WorkspaceTabs = Tk_WorkspaceTabs
        self.import_string = import_string # Used to define what tab to remove
        self.advanced_opts_state = "off"
        self.notes_frame_state = "off"
        self.chkbtn_fav_var = tk.IntVar()
        self.direct_import = False
        self.config_widgets()
        self.config_grid()

        # Taking Focus of window...
        self.focus_force()
        self.entry_sr.focus_force()

        # Binding <enter> to SR entry for keyboard traversal.
        self.entry_sr.bind('<Return>', self.start_import)

        # Auto-Fill entry if clipboard is SR number
        try:
            win_clipboard = self.clipboard_get()
            if len(win_clipboard) == 13 and "4-" in win_clipboard:
                self.entry_sr.insert(tk.END, win_clipboard)
        except:
            print("Tk_ImportMenu failed to import Clipboard contents.")

    def config_widgets(self):
        bg_0 = "#111111"
        bg_1 = "#333333"
        bg_2 = "#202020"
        fg_0 = "#FFFFFF"
        grn_0 = "#badc58"

        # Main Widgets
        self.config(
            background=bg_0
        )
        self.label_sr = tk.Label(
            self,
            text="SR Number to Import",
            relief='flat',
            background=bg_0,
            foreground=fg_0
        )
        self.entry_sr = tk.Entry(
            self,
            width=29,
            relief='flat'
        )
        #self.chkbtn_show_adv_opts = ttk.Checkbutton(
        #    self,
        #    command=self.show_advanced_opts,
        #    onvalue=(self.advanced_opts_state == "on"),
        #    offvalue=(self.advanced_opts_state == "off"),
        #    state='!selected'
        #
        self.label_favorite = tk.Label(
            self,
            text="Important?",
            relief='flat',
            background=bg_0,
            foreground=fg_0            
        )
        self.chkbtn_favorite = tk.Checkbutton(
            self,
            variable=self.chkbtn_fav_var,
            background=bg_0,
            foreground=fg_0
        )
        self.bulk_hint = tk.Label(
            self,
            text="""Hint: Bulk imports should be a text file that is one SR per line, with the below format.\n
            4-11211211211, NSP, DurangoJoes\n
            <SR Number>, <Product>, <Account>""",
            anchor=tk.CENTER,
            background=bg_0,
            foreground="#555555"
        )

        # Bottom Bar Buttons
        self.bottom_bar_frame = tk.Frame(
            self,
            background="#5b6366",
            relief='flat'
        )
        self.btn_browse = tk.Button(
            self.bottom_bar_frame,
            text="Bulk Import",
            command=self.direct_import_broswer,
            relief='flat'
        )
        self.btn_start = tk.Button(
            self.bottom_bar_frame,
            text="Import",
            command=self.start_import,
            relief='flat',
            background=grn_0,
            foreground=bg_0
        )

        # CaseNotes Block
        self.show_notes_btn = tk.Button(
            self,
            text="Case Notes",
            command=self.show_notes,
            relief='flat',
            background=bg_1,
            foreground=fg_0
        )
        self.notes_frame = tk.Frame(
            self,
            background=bg_2,
            relief='flat'
        )
        self.text_notes = tk.Text(
            self.notes_frame,
            relief='flat',
            height=20,
            background=bg_2,
            foreground="#EEEEEE",
            insertbackground="#EEEEEE",
            wrap='word',
        )

        # Advanced Options Tk Widgets
        self.label_adv_opts = tk.Button(
            self,
            text="Extra Options",
            command=self.show_advanced_opts,
            relief='flat',
            background=bg_1,
            foreground=fg_0
        )
        self.ext_opts_frame = tk.Frame(
            self,
            background=bg_2,
            relief='flat'
        )
        self.label_tags = tk.Label(
            self.ext_opts_frame,
            text="Tag(s) :",
            background=bg_2,
            foreground=fg_0
        )
        self.entry_tags = tk.Entry(
            self.ext_opts_frame,
            width=29,
        )
        self.label_product = tk.Label(
            self.ext_opts_frame,
            text="Product :",
            background=bg_2,
            foreground=fg_0
        )
        self.combox_product = CustomTk_autoEntry(
            self.ext_opts_frame,
            width=29,
            background=bg_2,
        )
        self.label_account = tk.Label(
            self.ext_opts_frame,
            text="Account :",
            background=bg_2,
            foreground=fg_0
        )
        self.combox_account = CustomTk_autoEntry(
            self.ext_opts_frame,
            width=29,
            background=bg_2,
        )
        self.label_bug = tk.Label(
            self.ext_opts_frame,
            text="JIRA/Bug ID :",
            background=bg_2,
            foreground=fg_0
        )
        self.entry_bug = tk.Entry(
            self.ext_opts_frame,
            width=29,
        )
        self.label_workspace = tk.Label(
            self.ext_opts_frame,
            text="Default Workspace :",
            background=bg_2,
            foreground=fg_0
        )
        self.combox_workspace = ttk.Combobox(
            self.ext_opts_frame,
            width=26,
            background=bg_2,
            foreground=fg_0
        )
        self.label_customs = tk.Label(
            self.ext_opts_frame,
            text="Custom Path(s):",
            background=bg_2,
            foreground=fg_0
        )
        self.label_hint1 = tk.Label(
            self.ext_opts_frame,
            text="Hint - Use ',' to seperate multiple values,",
            anchor=tk.CENTER,
            background=bg_2,
            foreground=fg_0
        )
        self.label_hint2 = tk.Label(
            self.ext_opts_frame,
            text="such as in the 'Tag(s)' field.",
            anchor=tk.CENTER,
            background=bg_2,
            foreground=fg_0
        )
        self.entry_customs = tk.Entry(
            self,
            width=29,
            background=bg_2,
            foreground=fg_0
        )

    def config_grid(self):
        '''
        Defines Grid layout for Tk.Widgets defined in init.
        '''
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Main Widgets
        self.label_sr.grid(
            row=0, column=0, padx=4, pady=4, sticky="e", ipady=10)
        self.entry_sr.grid(
            row=0, column=1, padx=4, pady=2, sticky="w")
        self.label_favorite.grid(
            row=2, column=0, padx=4, pady=2, sticky="e")
        self.chkbtn_favorite.grid(
            row=2, column=1, padx=4, pady=2, sticky="w")
        self.bulk_hint.grid(
            row=3, column=0, columnspan=2, padx=4, pady=5, sticky="ew")
        # Browse/Start Buttons
        self.bottom_bar_frame.grid(
            row=10, column=0, columnspan=2, padx=4, pady=4, sticky="ew")
        self.bottom_bar_frame.columnconfigure(0, weight=1)
        self.btn_browse.grid(
            row=0, column=0, padx=4, pady=4, sticky="e")
        self.btn_start.grid(
            row=0, column=1, padx=4, pady=4, sticky="w")

        # CaseNotes Block
        self.show_notes_btn.grid(
            row=4, column=0, columnspan=2, padx=4, pady=2, sticky="ew")            
        self.notes_frame.grid(
            row=5, column=0, columnspan=2, padx=4, pady=2, sticky="nsew")
        self.notes_frame.grid_remove()
        self.notes_frame.columnconfigure(0, weight=1)
        self.text_notes.grid(
            row=0, column=0, columnspan=2, padx=4, pady=2, sticky="nsew")

        # Advanced options Block
        self.label_adv_opts.grid(
            row=6, column=0, columnspan=2, padx=4, pady=2, sticky="nsew")
        self.ext_opts_frame.grid(
            row=7, column=0, columnspan=2, padx=4, pady=2, sticky="nsew")
        self.ext_opts_frame.grid_remove()
        self.ext_opts_frame.columnconfigure(0, weight=1)
        self.ext_opts_frame.columnconfigure(1, weight=1)
        self.label_tags.grid(
            row=4, column=0, padx=4, pady=2, sticky="e")
        self.entry_tags.grid(
            row=4, column=1, padx=4, pady=2, sticky="w")
        self.label_product.grid(
            row=5, column=0, padx=4, pady=2, sticky="e")
        self.combox_product.grid(
            row=5, column=1, padx=4, pady=2, sticky="w")
        self.label_account.grid(
            row=6, column=0, padx=4, pady=2, sticky="e")
        self.combox_account.grid(
            row=6, column=1, padx=4, pady=2, sticky="w")
        self.label_bug.grid(
            row=7, column=0, padx=4, pady=2, sticky="e")
        self.entry_bug.grid(
            row=7, column=1, padx=4, pady=2, sticky="w")
        #self.label_workspace.grid(
        #    row=8, column=0, padx=4, pady=2, sticky="e")
        #self.label_workspace.grid_remove()
        #self.combox_workspace.grid(
        #    row=8, column=1, padx=4, pady=2, sticky="w")
        #self.combox_workspace.grid_remove()
        #self.label_customs.grid(
        #    row=9, column=0, padx=4, pady=2, sticky="e")
        #self.label_customs.grid_remove()
        #self.entry_customs.grid(
        #    row=9, column=1, padx=4, pady=2, sticky="w")
        #self.entry_customs.grid_remove()
        self.label_hint1.grid(
            row=10, column=0, columnspan=2, padx=4, pady=2, sticky="nsew")
        self.label_hint2.grid(
            row=11, column=0, columnspan=2, padx=4, sticky="nsew")
        
    # Tk.Widgets "commands"
    def show_advanced_opts(self):
        if self.advanced_opts_state == "on":
            self.ext_opts_frame.grid_remove()
            self.advanced_opts_state = "off"
        else:
            self.ext_opts_frame.grid()
            self.advanced_opts_state = "on"

    def show_notes(self):
        if self.notes_frame_state == "on":
            self.notes_frame.grid_remove()
            self.notes_frame_state = "off"
        else:
            self.notes_frame.grid()
            self.notes_frame_state = "on"

    def direct_import_broswer(self):
        filename = filedialog.askopenfilename(
            initialdir="/",
            title="Select a File",
            filetypes=(("Text files",
                        "*.txt*"),
                        ("all files",
                        "*.*")))

        # Change label contents
        self.label_sr.configure(text="Importing >")
        self.entry_sr.insert(0, filename)
        self.direct_import = True

    def start_import(self, event=None):
        # Creating "import_item" Dictionary
        new_import_dict = {
            'sr_number': self.entry_sr.get(),
            'pinned': self.chkbtn_fav_var.get(),
            'product': self.get_product(),
            'account': self.get_account(),
            'bug_id': self.get_bug(),
            'workspace': self.get_workspace(),
            'tags_list': self.get_tags(),
            'customs_list': self.get_customs(),
            'notes': self.get_notes()
        }

        # Updating "import_item" -> Gui.import_handler(new_import_dict)
        Gui.import_item.value = new_import_dict
        # Removing "import" from Tk_WorkspaceTabs.open_tabs
        pop_index = next((i for i, item in enumerate(self.Tk_WorkspaceTabs.open_tabs) if item[0] == self.import_string), None)
        del self.Tk_WorkspaceTabs.open_tabs[pop_index]
        # Closing window...
        self.destroy()

    # Advanced Options "Get" methods
    def get_tags(self):
        '''
        Returns list of [Tags] from the UI, seperated by ','

        If the ImportMenu entry is not populated, this will return None
        '''
        raw_tags = str(self.entry_tags.get())
        prepped_tags = raw_tags.replace(", ", ",")
        tags_list = prepped_tags.split(",")
        if raw_tags != "":
            return_val = tags_list
        else:
            return_val = None

        print("IMPORT: Tags set to <", tags_list, ">")
        return return_val

    def get_account(self):
        '''
        Returns provided account name as a "string".

        If the ImportMenu entry is not populated, this will return None
        '''
        account_val = self.combox_account.get()
        return_val = None
        if account_val != "":
            return_val = account_val
        print("IMPORT: Account set to <" + str(return_val) + ">")
        return return_val

    def get_customs(self):
        '''
        Returns list of <os.abspath Objects>, seperated by ','

        If the ImportMenu entry is not populated, this will return None
        '''
        raw_paths = str(self.entry_customs.get())
        paths_list = raw_paths.split(",")
        return_val = None
        if raw_paths != "":
            return_val = paths_list
        print("IMPORT: Tags set to <" + str(return_val) + ">")
        return return_val

    def get_product(self):
        '''
        Returns provided Product as a "string".

        If the ImportMenu entry is not populated, this will return None
        '''
        product_val = self.combox_product.get()
        return_val = None
        if product_val != "":
            return_val = product_val
        print("IMPORT: Product set to <" + str(return_val) + ">")
        return return_val

    def get_workspace(self):
        '''
        Returns provided Workspace as a "string". 

        If the ImportMenu entry is not populated, this will return 'basic'
        '''
        workspace_val = self.combox_workspace.get()
        return_val = None
        if workspace_val != "":
            return_val = workspace_val
        print("IMPORT: Workspace set to <" + str(return_val) + ">")
        return return_val

    def get_bug(self):
        '''
        Returns JIRA Issue Number for support issues as a string if
        defined during import.
        '''
        bug_val = self.entry_bug.get()
        return_val = None
        if bug_val != "":
            return_val = bug_val
        print("IMPORT: Bug set to <" + str(return_val) + ">")
        return return_val

    def get_notes(self):
        notes_val = self.text_notes.get("1.0",'end-1c')
        return_val = None
        if notes_val != "":
            return_val = notes_val
        print("IMPORT: Notes set to <" + str(return_val) + ">")
        return return_val


class Tk_ThemeWizard(tk.Toplevel):
    '''
    Colors, Fonts, and other styling for the UI is handled here. This
        includes...

    - UI Frame drawn when a user selects, "Options > Theme Manager"
    - Ttk Style Maps.
    - Variable binding for JSON elements.

    The actual color hexcodes, font families, .etc can be re-themed using
        a JSON file stored "./extension/themes/<theme_name>.json". 
    '''
    class Tk_StyleEditor(ttk.Frame):
        def __init__(self, master):
            super().__init__()
            self.master = master
            self.config_widgets()
            self.config_grid()

        def config_widgets(self):
            self.menu = tk.Menu(self.master)
            self.menu_options = tk.Menu(self.menu, tearoff=0)
            self.menu_options.add_command(
                label="Export Theme", command=self.export_theme)
            self.menu.add_cascade(label="File", menu=self.menu_options)
            # self.config(menu=self.menu)
            self.text_box = tk.Text(
                self.master,
                background="#333333",
                foreground="#ffffff",
                height=30,
                width=80
            )

        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.text_box.grid(row=0, column=0, sticky='nsew')

        def export_theme(self):
            print("Would launch filebrowser here to save file...")

    def __init__(self):
        super().__init__()
        self.config_frames()
        self.config_grid()

    def config_frames(self):
        self.editor_frame = self.Tk_StyleEditor(self)

    def config_grid(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.editor_frame.grid(row=0, column=1, sticky='nse')


class Tk_BottomBar(tk.Frame):
    def __init__(self):
        super().__init__()
        self.config_widgets()
        self.config_grid()

        #%%hex
        self.configure(
            background="#111111"
        )

    def config_widgets(self):

        self.bb_ver = ttk.Label(
            self,
            text=bcamp_api.get_config('version'),
            background="#111111",
            foreground="#777777"
        )
        self.bb_remote_canvas = tk.Canvas(
            self,
            width=12,
            height=12,
            background="#111111",
            highlightthickness=0,
        )
        self.remote_oval = self.bb_remote_canvas.create_oval(
            0, 0, 10, 10, fill='#000000', outline='#333333')

        self.bb_telemen_canvas = tk.Canvas(
            self,
            width=12,
            height=12,
            background="#111111",
            highlightthickness=0
        )
        self.bb_telemen_on = self.bb_telemen_canvas.create_oval(
            0, 0, 10, 10, fill='#22a6b3', outline='#333333')
        self.bb_telemen_off = self.bb_telemen_canvas.create_oval(
            0, 0, 10, 10, fill='#a10000', outline='#333333')

        self.bb_remote_on = self.bb_remote_canvas.create_oval(
            0, 0, 10, 10, fill='#6ab04c', outline='#333333')
        self.bb_remote_off = self.bb_remote_canvas.create_oval(
            0, 0, 10, 10, fill='#a10000', outline='#333333')

        bb_telemen_tip = CustomTk_CreateToolTip(
            self.bb_telemen_canvas, "Telemetry Server Connectivity")
        bb_remote_tip = CustomTk_CreateToolTip(
            self.bb_remote_canvas, "Remote Folder Connectivity")

    def config_grid(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.bb_ver.grid(row=0, column=0, sticky='se', padx=5)
        self.bb_remote_canvas.grid(row=0, column=1, padx=2)
        self.bb_telemen_canvas.grid(row=0, column=2, padx=2)


class Tk_TodoList(tk.Frame):
    '''
    This class defines the TK Frame for the TodoList. This class is init. in
    Gui, and is "add"ed as a child frame of the "Tk_MasterPane" - Allowing
    users to resize this Frame, and other contents added to "Tk_MasterPane".

    This initial implementation is simplified but will be added to later.
    '''
    def __init__(self, master):
        super().__init__(master)
        # Class Vars
        self.todo_list = []
        # Tk def Methods.
        self.config_widgets()
        self.config_grid()

    def config_widgets(self):
        self.list_frame = tk.Frame(
            self,
        )
        self.add_button = tk.Button(
            self,
            text="+",
            command=self.create_todo_object
        )
    
    def config_grid(self):
        self.rowconfigure(0 ,weight=1)
        self.columnconfigure(0, weight=1)
        self.list_frame.grid(
            row=0, column=0, sticky='nsew'
        )
        self.add_button.grid(
            row=1, column=0, sticky='e'
        )

    def create_todo_object(self):
        '''
        Renders/intializes a new TodoObject and adds the resulting frame to
        the *self.list_frame* widget.
        '''
        print("Creating new Todo Object")
        newObj = self.TodoObject(self.list_frame)
        # Now add to *self.todo_list
        self.todo_list.append(newObj)
        # Get current length of todo_list to determine GRID placement.
        curLen = len(self.todo_list)
        # Add to Grid of *self.list_frame
        newObj.grid(
            row=curLen, column=0, sticky='nsew'
        )

    class TodoObject(tk.Frame):
        def __init__(self, master):
            super().__init__(master)
            # Tk Vars
            self.created_time_stringVar = tk.StringVar()
            # Set time for "created_time" Var
            datetimeObj = datetime.datetime.now()
            f_timestamp = datetimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
            self.created_time_stringVar.set(f_timestamp)
            # Tk Methods
            self.config_widgets()
            self.config_grid()


        def config_widgets(self):
            self.todo_text = tk.Text(
                self,
            )
            self.created_time_label = tk.Label(
                self,
                textvariable=self.created_time_stringVar
            )
            self.edit_button = tk.Button(
                self,
                text="✎",
                command=self.enable_edit
            )
            self.remove_button = tk.Button(
                self,
                text="✓",
                command=self.remove_todo
            )
        
        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.rowconfigure(1, weight=1)
            self.columnconfigure(0, weight=1)
            self.created_time_label.grid(
                row=0, column=0, sticky='w'
            )
            self.edit_button.grid(
                row=0, column=1, sticky="e"
            )
            self.remove_button.grid(
                row=0, column=2, sticky="e"
            )
            self.todo_text.grid(
                row=1, column=0, columnspan=3, sticky='nsew'
            )

        def enable_edit(self):
            print("$would enable_edit")

        def remove_todo(self):
            print("$would remove Item.")
        

'''Basecamp Workpane Tk/Tcl Frames'''
class Tk_WorkspaceTabs(tk.Frame):
    '''
    This renders the default, and new workspace tabs when a user imports new
    data, or recalls a previously worked item (Sr Number, Path, etc.) through
    the "Case Data" pane.

    Example.) Getting file_paths from <SR> for Treeview Rendering.
    '''
    # Tk_WorkspaceTabs Methods...
    def __init__(self, master, file_queue):
        super().__init__(master)
        self.file_queue = file_queue
        self.RPATH = str(pathlib.Path(
            __file__).parent.absolute()).rpartition('\\')[0]
        self.tab_id = tk.StringVar()
        self.open_tabs = ['+']
        # Rendering Tk Elements
        self.config_widgets()
        self.config_grid()
        self.focus_set()
        self.configure(
            background="#111111"
        )

    # Ttk Config Methods
    def config_widgets(self):
        # Building "Notebook" for multiple SR's to tab through...

                #%%hex
        self.blk100 = "#EFF1F3"
        self.blk300 = "#B2B6BC"
        self.blk400 = "#717479"
        self.blk500 = "#1E1F21" ##
        self.blk600 = "#15171C"
        self.blk700 = "#0F1117"
        self.blk900 = "#05070F"
        self.act300 = "#D5A336"

        self.tab_notebook = ttk.Notebook(
            self,
            width=400,
            height=320,
            cursor="hand2"
        )
        self.tab_notebook.bind('<Button-3>', self.popup_menu)
        self.tab_notebook.bind('<Control-1>', self.ctrl_click_close)
        self.default_tab(Tk_DefaultTab, self, "➕")

        #%%hex
        self.right_click_menu = tk.Menu(
            self,
            relief='flat',
            tearoff=False,
            background=self.blk700,
            foreground=self.blk300,
            bd=-2
        )
        self.right_click_menu.add_command(
            label="Close Tab        ",
            command=self.right_click_close
        )
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(
            label="Show/Hide Filebrowser",
            command=lambda widget='default_filebrowser': self.update_case_template(widget)
        )
        self.right_click_menu.add_command(
            label="Show/Hide LogView",
            command=lambda widget='default_logview': self.update_case_template(widget)
        )
        self.right_click_menu.add_command(
            label="Show/Hide Case Notes",
            command=lambda widget='default_casenotes': self.update_case_template(widget)
        )
        self.right_click_menu.add_command(
            label="Show/Hide File Notes",
            command=lambda widget='default_filenotes': self.update_case_template(widget)
        )

    def config_grid(self):
        # Grid Layout
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tab_notebook.grid(row=0, column=0, sticky='nsew')

    def popup_menu(self, event):
        clicked_tab = self.tab_notebook.tk.call(
            self.tab_notebook._w, "identify", "tab", event.x, event.y)
        self.tab_id.set(clicked_tab)
        self.right_click_menu.post(event.x_root + 10, event.y_root + 10)

    def right_click_close(self):
        self.tab_notebook.forget(self.tab_id.get())
        self.open_tabs.pop(int(self.tab_id.get()))

    def ctrl_click_close(self, event):
        clicked_tab = self.tab_notebook.tk.call(
            self.tab_notebook._w, "identify", "tab", event.x, event.y)
        self.tab_notebook.forget(clicked_tab)
        self.open_tabs.pop(clicked_tab)

    def update_case_template(self, widget):
        case_index = int(self.tab_id.get())
        target_case = self.open_tabs[case_index][1]
        # Get dictionary object of target Case & Widget.
        for col_dict in target_case.template.value:
            pane_index = -1 # Offset from 0
            for workpane in col_dict["workpanes"]:
                pane_index += 1
                if workpane[0] == widget:
                    col_index = col_dict["index"]
                    # Create a copy of self.template
                    target_pane = target_case.template.value[col_index]['workpanes'][pane_index]
                    # Flip the bool for target_pane[1] to show/hide 
                    print(target_pane[1])
                    if target_pane[1]: # True
                        new_pane_set = (target_pane[0], False)
                    else: # False
                        new_pane_set = (target_pane[0], True)
                    # Update self.template.value with changes...
                    temp_template = target_case.template.value
                    temp_template[col_index]['workpanes'][pane_index] = new_pane_set
                    # Update template.value...
                    # which calls targets init Tk_CaseMasterFrame.render_panes"
                    target_case.template.value = temp_template

        # Update applicable widget textvariable for popup menu!
        #print("widget? > ", widget)

    # Called by Import_handler or opening a CaseView Tab
    def render_workspace(self, key_value):
        '''
        On new imports, or recalling previous SR's via the search pane, 
        the render_workspace method is called, intializing the Tk_CaseMasterFrame
        class, and adding the frame to the "tab_notebook" widget.

        The open_tabs objects have the following format...

        ['+', ,('4-11111111111', <__main__.Tk_CaseMasterFrame object 
            .!tk_casemasterframe>, False)]
        '''
        # First, check if SR is already open in open_tabs - increment 
        # open_tab_counter if so.
        open_tab_counter = 0
        open_index = 0 # Defines target tab to select if already open later.
        for item in self.open_tabs:
            if item == key_value:
                open_tab_counter += 1
                break
            try:
                if item[0] == key_value:
                    open_tab_counter += 1
                    break
            except IndexError as e:
                print("DEBUG PASSING>", e)
            # Increment open_index as nothing has matched key_val yet.
            open_index += 1

        # If open_tab_counter is zero - Render NEW Workspace. 
        if open_tab_counter == 0:
            # Key-Value passed to Tk_CaseMasterFrame instance to render "Workspace" template.
            new_tab_frame = Tk_CaseMasterFrame(self.tab_notebook, key_value, self, self.file_queue)
            # Add Tab with new Workpane
            self.tab_notebook.add(
                new_tab_frame,
                text=key_value, # Tab Header
                padding=2
            )
            # "Jumping" to imported SR
            self.tab_notebook.select(new_tab_frame)

            # Adding "key_value" to "open_tabs" list.
            tab_tuple = (key_value, new_tab_frame, False)
            self.open_tabs.append(tab_tuple)
        # If key_value is already open/open_tab_counter >=1, jump to open tab.
        else:
            # Get index of open_tabs - matches tab id index.
            #index = self.open_tabs.index(key_value)
            self.tab_notebook.select(open_index)

    def default_tab(self, target_frame, Tk_WorkspaceTabs, header):
        '''
        Creates a the default import tab when a new session is rendered.
        '''
        f_newtab = ttk.Frame(self.tab_notebook)
        # Intialzing Default Tab Class with Args
        target_frame(f_newtab, Tk_WorkspaceTabs)
        self.tab_notebook.add(
            f_newtab,
            text=header
        )

    def import_tab(self, event=None):
        '''
        Renders a new "<importing>" tab when prompted by a user.
        '''
        # Calc. Import Index Number
        import_cnt = 0
        for item in self.open_tabs:
            if isinstance(item, tuple):
                if item[2] == True: # Check is import flag is True
                    import_cnt += 1
        final_import_cnt = import_cnt + 1
        import_string = "<Import " + str(final_import_cnt) + ">"

        # Intialize new Import Menu
        new_tab_frame = Tk_ImportMenu(self.tab_notebook, self, import_string)

        # Adding "key_value" to "open_tabs" list.
        tab_tuple = (import_string, new_tab_frame, True)
        self.open_tabs.append(tab_tuple)

        # Add Tab with new Workpane
        self.tab_notebook.add(
            new_tab_frame,
            text=import_string, # Tab Header
            padding=2
        )
        # "Jumping" to imported SR
        self.tab_notebook.select(new_tab_frame)


class Tk_DefaultTab(ttk.Frame):
    '''
    The Default "import" tab. If no other workspaces are rendered,
    users will be presented with this Widget first.
    '''

    def __init__(self, master, Tk_WorkspaceTabs):
        super().__init__(master)
        self.Tk_WorkspaceTabs = Tk_WorkspaceTabs
        self.def_font = tk_font.Font(
            family="Consolas", size=10, weight="normal", slant="roman")

        self.btn_big = tk.Button(
            self.master,
            text="Click anywhere here to Import a new Case.\n\nYou can also use <CTRL> + <n>.\n\n Or <CTRL> + <Click> to import a 'list.txt' of Cases here." ,
            command=self.render_import_menu,
            font=self.def_font,
            background="#0F1117",
            foreground="#717479",
            cursor="plus"
        )

        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.btn_big.grid(row=0, column=0, sticky="nsew")
        self.btn_big.bind('<Control-1>', self.direct_import_broswer)
        self.btn_big.bind('<Control-Motion>', self.bulk_cursor)
        self.btn_big.bind('<Motion>', self.default_cursor)

    def render_import_menu(self):
        '''
        Renders the Import Menu within a new WorkspaceTabs Tab.
        '''
        self.Tk_WorkspaceTabs.import_tab()

    def direct_import_broswer(self, event=None):
        # Prompt User for file to import
        filename = filedialog.askopenfilename(
            initialdir="/",
            title="Basecamp Bulk Importer - Select a file to import!",
            filetypes=[("Text files",
                        "*.txt*")])
        # Open resulting file
        print("IMPORT FILE:", filename)
        ifile = open(filename, 'r')
        ifile_content = ifile.readlines()
        # Read lines of "ifile" and import one, by one.
        for line in ifile_content:
            print("-->", line)
            # Splitting string to parse for account, and product vals.
            split_line = line.split(', ')
            # Order -> Sr_Num, Product, Account 
            self.start_bulk_import(split_line[0], split_line[1], split_line[2])

    def start_bulk_import(self, sr_num, product, account):
        # Creating "import_item" Dictionary
        new_import_dict = {
            # Required Dict Vals
            'sr_number': sr_num,
            #'remote_path': None,  # Set in Finalize...
            #'local_path': None, # Set in Finalize...
            'pinned': 0, # Default = !Pinned
            # Import/Calculated Values
            'product': product.strip(),
            'account': account.strip(),
            #'import_time': None,
            #'last_ran_time': None,
            # Untouched Dict Vals for bulk
            'bug_id': None,
            'workspace': None,
            'notes': None,
            'tags_list': None,
            'customs_list': None
        }
        # Updating "import_item" -> Gui.import_handler(new_import_dict)
        Gui.import_item.value = new_import_dict

    def bulk_cursor(self, event=None):
        self.btn_big['cursor'] = 'top_side'

    def default_cursor(self, event=None):
        self.btn_big['cursor'] = 'plus'


class Tk_CaseMasterFrame(tk.Frame):
    '''
    The Main Frame that contains all Workpanes, for a target SR.

    This class also contains the default Workpane template for new imports, 
    and the methods to Hide/Show Workpanes when a user interacts with the UI.
    '''
    # Tk_CaseMasterFrame Methods...

    def __init__(self, master, key_value, WorkspaceTabs, file_queue):
        super().__init__()
        # Vars
        self.master = master
        self.key_value = key_value
        self.WorkspaceTabs = WorkspaceTabs
        self.file_queue = file_queue
        self.RPATH = str(pathlib.Path(
            __file__).parent.absolute()).rpartition('\\')[0]
        self.frame_list = []
        self.open_panes = []
        self.fb_cur_sel = callbackVar()

        # DEFINING DEFAULT WORKSPACE
        self.default_template = [
                {
                    'index': 0,
                    'workpanes': [('default_filebrowser', True)]
                },
                {
                    'index': 1,
                    'workpanes': [('default_logview', False)]
                },
                {
                    'index': 2,
                    'workpanes': [('default_casenotes', True), ('default_filenotes', False)]
                },
            ]

        # Methods
        self.config_widgets()
        self.config_grid()
        self.config_bindings()
        self.template = callbackVar()
        self.template.register_callback(self.render_panes)
        self.template.value = self.get_template()

    # Tk Methods
    def config_widgets(self):
        # Panedwindow
        self.main_pane = tk.PanedWindow(
            self,
            background="#bfbeb0",
            bd=0,
            #sashwidth=8,
            #showhandle=True
        )

        # NOTE - When attempting to render the template within a loop,
        # performance was impacted after 15 cycles, likely due to a memory
        # leak or some other error in the [Python -> Tk/Tcl -> C] transfer
        # Programmer included :). As a result, I am "hardcoding" the
        # Workbench to 3 columns.

        self.main_col0 = tk.PanedWindow(
            self.main_pane,
            background="black",
            bd=0,
            orient='vertical'
            #sashwidth=8,
            #showhandle=True
        )
        self.main_col1 = tk.PanedWindow(
            self.main_pane,
            background="black",
            bd=0,
            orient='vertical'
            #sashwidth=8,
            #showhandle=True
        )            
        self.main_col2 = tk.PanedWindow(
            self.main_pane,
            background="black",
            bd=0,
            orient='vertical'
            #sashwidth=8,
            #showhandle=True
        )
        # Intializing Frames
        self.tk_file_browser = Tk_FileBrowser(self.main_col0, self.key_value, self.file_queue, self)
        self.tk_log_viewer = Tk_LogViewer(self.main_col1, self.key_value, self.file_queue, self)
        self.tk_case_notes = Tk_CaseNotes(self.main_col2, self.key_value)                    
        self.tk_file_notes = Tk_FileNotes(self.main_col2, self.key_value, self.file_queue, self, None)
        # "Adding" to Panedwindow - Similar to Grid or Pack in TcL/Tk
        self.main_col0.add(self.tk_file_browser, stretch="always")
        self.main_col1.add(self.tk_log_viewer, stretch="always")
        self.main_col2.add(self.tk_case_notes, stretch="always")
        self.main_col2.add(self.tk_file_notes, stretch="always")
            
    def config_grid(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.main_pane.grid(
            row=0, column=0, columnspan=2, sticky='nsew')

    def config_bindings(self):
        self.main_pane.bind("<Double-1>", self.auto_resize_pane)

    def get_template(self):
        db_template = bcamp_api.query_sr(self.key_value, 'workspace')
        if db_template == None:  # Not specified on import.
            return self.default_template
        else:
            #Deserialize 'pickle' Binary Object back to python Dict.
            return pickle.loads(db_template)

    def render_panes(self, template):
        '''
        This method translates the datastore "workspace" template
        and renders the actual horizontal panes, vertical panes.

        Any assigned Workpanes will also be rendered here if available
        in the template.
        '''
        # NOTE - When attempting to render the template using the legacy loop,
        # performance was impacted after 15 cycles, likely due to a memory
        # leak or some other error in the [Python -> Tk/Tcl -> C] pipeline.
        # Programmer included :). As a result, I am "hardcoding" the
        # Workbench to 3 columns.

        # Render Vert Panes based on template
        for pane_dict in template:
            workpanes = pane_dict['workpanes']
            index = pane_dict['index']
            #print("**", index)
            if index == 0:
                columnpane = self.main_col0
            if index == 1:
                columnpane = self.main_col1
            elif index == 2:
                columnpane = self.main_col2

            # Adding children, if configured.
            if workpanes != None:
                hidden_pane_count = 0
                # Renders in order of left to right in list.
                for pane_class in workpanes:
                    # Intializing Workpane Class
                    if pane_class[0] == 'default_filebrowser':
                        rendered_pane = self.tk_file_browser
                    if pane_class[0] == 'default_casenotes':
                        rendered_pane = self.tk_case_notes                     
                    if pane_class[0] == 'default_filenotes':
                        rendered_pane = self.tk_file_notes
                    if pane_class[0] == 'default_logview':
                        rendered_pane = self.tk_log_viewer

                    if pane_class[1] == True:
                        columnpane.paneconfigure(rendered_pane, hide=False, stretch="always")
                    else:
                        columnpane.paneconfigure(rendered_pane, hide=True)
                        hidden_pane_count += 1
                    
                # "Place" columnpane now with rendered frame, into
                # the *main_pane* Panedwindow. Note indent.
                #print("Hidden Cnt >", hidden_pane_count)
                if hidden_pane_count == len(columnpane.winfo_children()): # All panes are hidden
                    self.main_pane.paneconfigure(columnpane, hide=True)
                else:
                    # First, get size of main_pane
                    main_pane_width = self.main_pane.winfo_width()
                    print("$", main_pane_width)
                    self.main_pane.paneconfigure(columnpane, hide=False)
                    self.main_pane.add(columnpane, stretch='always', minsize=10)

        # Save new template into Sqlite3 DB
        print("Saving template changes to DB for", self.key_value)
        binary_template = pickle.dumps(template)
        bcamp_api.update_sr(self.key_value, 'workspace', binary_template)

    def show_workpane(self, target_workpane):
        '''
        Updates the *target_workpane* bool in self.template - Showing the target
        workpane in the SR's Tab.
        '''
        # Get dictionary object of target Case & Widget.
        for col_dict in self.template.value:
            pane_index = -1 # Offset from 0
            for workpane in col_dict["workpanes"]:
                pane_index += 1
                if workpane[0] == target_workpane:
                    col_index = col_dict["index"]
                    # Create a copy of self.template
                    target_pane = self.template.value[col_index]['workpanes'][pane_index]
                    new_pane_set = (target_pane[0], True)
                    # Update self.template.value with changes...
                    temp_template = self.template.value
                    temp_template[col_index]['workpanes'][pane_index] = new_pane_set
                    # Update template.value - which calls target Frame's "update_panes"
                    self.template.value = temp_template

    def auto_resize_pane(self, event):
        print("YOU CLICKED ON THE PANE - GOOD BOY")
        print("event>", event)

        ident = self.main_pane.identify(event.x, event.y)
        print(ident)

        if ident[1] == 'sash': #User pressed sash
            # First determine total Main_pane size.
            main_pane_width = self.main_pane.winfo_width()

            # Second, determine how many child columns rendered.
            rendered_cols = 0
            for column in self.template.value:
                for item in column['workpanes']:
                    if item[1] == True:
                        rendered_cols += 1

            # Third, resize columns based on data from above.
            columns = self.main_pane.panes()
            new_width = main_pane_width/rendered_cols
            resize_counter = 0
            while resize_counter <= rendered_cols:
                self.main_pane.paneconfig(columns[resize_counter], width=new_width)
                resize_counter += 1
                

class Tk_FileBrowser(tk.Frame):
    '''
    A Default Workpane that displays files found in the remote and
    local folders. This also contains the "Favorites" tree, and 
    the "QueueManager" for unpack and download operations against
    files in the trees.

    TODO - *RANGE* scanning for .log or .dbg* files needs to be complete. - On hold for beta.
    '''

    def __init__(self, master, key_value, file_queue, Tk_CaseMasterFrame):
        super().__init__(master=master)
        self.master = master
        self.key_value = key_value
        self.file_queue = file_queue
        self.case_frame = Tk_CaseMasterFrame
        self.progress_strVar = tk.StringVar()
        self.queue_strVar = tk.StringVar()
        Gui.fb_progress_string.register_callback(self.update_progess_string)
        Gui.fb_queue_string.register_callback(self.update_queue_string)

        # Getting install dir path...
        self.RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]

        # Get time_format from config
        self.time_zone = bcamp_api.get_config('time_zone')
        self.time_format = bcamp_api.get_config('time_format')
        
        # Get Remote root path for 'key_value'
        self.sr_remote_path = bcamp_api.query_sr(self.key_value, "remote_path")
        self.sr_local_path = bcamp_api.query_sr(self.key_value, "local_path")

        # Toggle for Workflow Frame
        self.frame_label_queue_state = "off"

        # Building Tk Elements
        self.config_widgets()
        self.config_bindings()
        self.config_grid()


        # MOVE THIS
        # Inserting local tree if local_path exist and contains files.
        #self.local_tree = self.sr_local_path
        #if os.access(self.sr_local_path, os.R_OK):
        #    # Now check for contents, insert if !0
        #    if len(os.listdir(self.sr_local_path)) != 0:
        #        self.file_tree.insert('', '0', iid='local_filler_space', tags=('default'))
        #        self.file_tree.insert('', '0', iid=self.local_tree, text="Local Files (Downloads)", tags=('dir_color'))

        # Rendering File's via refresh threads
        #self.render_snapshot(self.key_value)
        threading.Thread(
            target=self.refresh_file_record,
            args=['remote']).start()
        threading.Thread(
            target=self.refresh_file_record,
            args=['local']).start()

    def config_widgets(self):
        # Colors...
        self.blk100 = "#EFF1F3"
        self.blk300 = "#B2B6BC"
        self.blk400 = "#717479"
        self.blk500 = "#1E1F21" ##
        self.blk600 = "#15171C"
        self.blk700 = "#0F1117"
        self.blk900 = "#05070F"
        self.act300 = "#D5A336"

        self.configure(
            background="#111111",
            relief='flat'
        )
        self.trees_pane = tk.PanedWindow(
            self,
            orient='vertical',
            background="#101010",
            sashwidth=12,
            bd=0,
            borderwidth=0
        )

        # Building Treeview for SR Content
        self.file_tree = ttk.Treeview(self.trees_pane, columns=(
            "date", "size"), style="Custom.Treeview")
        #self.file_tree = ttk.Treeview(self.trees_pane, columns=(
        #    "date", "size", "range"), style="Custom.Treeview")
        # LEGACY SCROLLBAR OMISSIONS
        #self.tree_ysb = ttk.Scrollbar(
        #    self.master, orient='vertical', command=self.file_tree.yview)
        #self.tree_xsb = ttk.Scrollbar(
        #    self.master, orient='horizontal', command=self.file_tree.xview)
        #self.file_tree.configure(
        #    yscroll=self.tree_ysb.set, xscroll=self.tree_xsb.set, show="tree headings")

        # fonts
        self.def_font = tk_font.Font(
            family="Consolas", size=11, weight="normal", slant="roman")
        self.dir_font = tk_font.Font(
            family="Consolas", size=11, weight="bold", slant="roman")

        # Treeview Tags
        self.file_tree.tag_configure('debug',  background="#0a0a0a", foreground="#ff7979", font=self.def_font)
        self.file_tree.tag_configure('default',  background="#0a0a0a", foreground="#fdfdfd", font=self.def_font)
        self.file_tree.tag_configure('log_color', background="#0a0a0a", foreground="#a9e34b", font=self.def_font)
        self.file_tree.tag_configure('zip_color', background="#0a0a0a", foreground="#ffd43b", font=self.def_font)
        self.file_tree.tag_configure('dir_color', background="#0F0F0F", foreground="#fdfdfd", font=self.dir_font)
        # Move to custom place??
        self.file_tree.tag_configure('enc_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)
        self.file_tree.tag_configure('bin_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)

        # Treeview Column Config
        self.file_tree.heading('#0', text="Name",)
        self.file_tree.heading('date', text="Creation Time", anchor='center')
        self.file_tree.heading('size', text="Size", anchor='center')
        #self.file_tree.heading('range', text="Range", anchor='center')
        self.file_tree.column('#0', minwidth=100, width=260, anchor='e')
        self.file_tree.column("date", anchor="center", minwidth=10, width=40)
        self.file_tree.column("size", anchor="e", minwidth=9, width=10)
        #self.file_tree.column("range", anchor="center", minwidth=10, width=40)

        #Favorites Frame
        self.fav_tree = ttk.Treeview(self.trees_pane, columns=("date", "size"), style="Custom.Treeview")
        self.fav_tree.heading('#0', text="Favorites",)
        self.fav_tree.heading('date', text="", anchor='center')
        self.fav_tree.heading('size', text="", anchor='center')
        #self.fav_tree.heading('range', text="Range", anchor='center')
        self.fav_tree.column('#0', minwidth=100, width=260, anchor='e')
        self.fav_tree.column("date", anchor="center", minwidth=10, width=40)
        self.fav_tree.column("size", anchor="e", minwidth=9, width=10)
        #self.fav_tree.column("range", anchor="center", minwidth=10, width=40)

        # fav_tree Tags
        self.fav_tree.tag_configure('default',  background="#0a0a0a", foreground="#fdfdfd", font=self.def_font)
        self.fav_tree.tag_configure('log_color', background="#0a0a0a", foreground="#a9e34b", font=self.def_font)
        self.fav_tree.tag_configure('zip_color', background="#0a0a0a", foreground="#ffd43b", font=self.def_font)
        self.fav_tree.tag_configure('dir_color', background="#0F0F0F", foreground="#fdfdfd", font=self.dir_font)
        # Move to custom place??
        self.fav_tree.tag_configure('enc_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)
        self.fav_tree.tag_configure('bin_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)


        # Context Menu when "Right-Click"ing.
        self.right_click_menu = tk.Menu(self)
        self.fav_right_click_menu = tk.Menu(self)
        self.local_right_click_menu = tk.Menu(self)
        self.automations_menu = tk.Menu(self)
        self.fav_automations_menu = tk.Menu(self)

        # Main Tree Right-Click Menu Content
        self.right_click_menu.configure(
            relief='flat',
            tearoff=False,
            background=self.blk700,
            foreground=self.blk300,
            borderwidth=0,
        )
        self.right_click_menu.add_command(
            label="Open",
            command=self.right_click_open_local
        )
        self.right_click_menu.add_command(
            label="Open in Default App",
            command=self.right_click_open
        )
        self.right_click_menu.add_command(
            label="Open in TextEditor",
            command=self.right_click_open_local
        )
        self.right_click_menu.add_command(
            label="Copy",
            command=self.right_click_open_local
        )
        self.right_click_menu.add_command(
            label="Copy Filename",
            command=self.right_click_open_local
        )
        self.right_click_menu.add_command(
            label="Copy File Path",
            command=self.right_click_open_local
        )
        self.right_click_menu.add_command(
            label="Reveal in Explorer",
            command=self.right_click_reveal_in_explorer
        )
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(
            label="Download",
            command=self.right_click_download
        )
        self.right_click_menu.add_cascade(
            label="Automations",
            menu=self.automations_menu
        )
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(
            label="Add to 'Favorites'",
            command=self.right_click_favorite
        )
        # Automations menu
        self.automations_menu.configure(
            relief='flat',
            tearoff=False,
            background=self.blk700,
            foreground=self.blk300,
            borderwidth=0,
        )
        self.fav_automations_menu.configure(
            relief='flat',
            tearoff=False,
            background=self.blk700,
            foreground=self.blk300,
            borderwidth=0,
        )
        enabled_autos = self.get_automations_list()
        for automation in enabled_autos:
            self.automations_menu.add_command(
                label=automation,
                command= lambda target=automation: self.launch_automation(target)
            )
            self.fav_automations_menu.add_command(
                label=automation,
                command= lambda target=automation: self.fav_launch_automation(target)
            )

        #lambda widget='default_filebrowser': self.update_case_template(widget)

        # Favorite Tree Right-Click Menu Content
        self.fav_right_click_menu.configure(
            relief='flat',
            tearoff=False,
            background=self.blk700,
            foreground=self.blk300,
            borderwidth=0,
        )
        self.fav_right_click_menu.add_command(
            label="Open",
            command=self.fav_right_click_open_local
        )
        self.fav_right_click_menu.add_command(
            label="Open in Windows",
            command=self.fav_right_click_open
        )
        self.fav_right_click_menu.add_command(
            label="Reveal in Explorer",
            command=self.fav_right_click_reveal_in_explorer
        )
        self.fav_right_click_menu.add_separator()
        self.fav_right_click_menu.add_command(
            label="Download",
            command=self.fav_right_click_download
        )
        self.fav_right_click_menu.add_cascade(
            label="Automations",
            menu=self.fav_automations_menu
        )
        self.fav_right_click_menu.add_separator()
        self.fav_right_click_menu.add_command(
            label="Remove from 'Favorites'",
            command=self.fav_right_click_unfavorite
        )

        # Main Tree Right-Click Menu Content
        self.local_right_click_menu.configure(
            relief='flat',
            tearoff=False,
            background=self.blk700,
            foreground=self.blk300,
            borderwidth=0,
        )
        self.local_right_click_menu.add_command(
            label="Open",
            command=self.right_click_open_local
        )
        self.local_right_click_menu.add_command(
            label="Open in Windows",
            command=self.right_click_open
        )        
        self.local_right_click_menu.add_command(
            label="Reveal in Explorer",
            command=self.right_click_reveal_in_explorer
        )
        self.local_right_click_menu.add_separator()
        self.local_right_click_menu.add_command(
            label="Upload",
            command=self.right_click_upload
        )
        self.local_right_click_menu.add_cascade(
            label="Automations",
            menu=self.automations_menu
        )
        self.local_right_click_menu.add_separator()
        self.local_right_click_menu.add_command(
            label="Add to 'Favorites'",
            command=self.right_click_favorite
        )
        self.local_right_click_menu.add_command(
            label="Delete from Local Disk",
            command=self.right_click_delete_local
        )
        # Queue Manager
        self.fileops_frame = tk.Frame(
            self,
            background="#202020",
        )
        self.progress_label = tk.Label(
            self.fileops_frame,
            textvariable=self.progress_strVar,
            background="#202020",
            foreground="#757575"
        )
        self.queue_label = tk.Label(
            self.fileops_frame,
            textvariable=self.queue_strVar,
            background="#202020",
            foreground="#757575",
            relief="flat"
        )
        self.btn_show_queue = tk.Button(
            self.fileops_frame,
            text="˅",
            command=self.show_QueueManager,
            background="#202020",
            foreground="#757575",
            relief="flat"
        )
        self.queue_frame = tk.LabelFrame(
            self.fileops_frame,
            text="Workflow Queue",
            background="#111111",
        )
        self.listbox_dnd = tk.Listbox(self.queue_frame)
        self.listbox_dnd.insert(0, "example-Thread")
        self.listbox_dnd.insert(0, "random-Thread")
        self.listbox_dnd.insert(0, "Upload-Thread")

        self.dnd_cur_index = None

        # GRID
        self.queue_frame.columnconfigure(0, weight=1)

    def config_grid(self):
        # GRID
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        # Adding Trees to 'self.trees_pane'
        self.trees_pane.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky='nsew')
        self.trees_pane.add(self.file_tree, height=500, sticky='nsew')
        self.trees_pane.add(self.fav_tree, height=200, sticky='nsew')

        # "Progress-Bar" & Queue Manager.
        self.fileops_frame.grid(row=7, column=0, columnspan=4, sticky='nsew')
        self.fileops_frame.rowconfigure(0, weight=1)
        self.fileops_frame.columnconfigure(0, weight=1)
        self.progress_label.grid(row=0, column=0, sticky='nsw')
        self.queue_label.grid(
            row=0, column=1, columnspan=3, sticky='sew')
        #self.btn_show_queue.grid(
        #    row=0, column=1, columnspan=3, sticky='sew')
        self.listbox_dnd.grid(row=0, column=0, columnspan=3, sticky='nsew')

    def config_bindings(self):
        # File Treeview Command Bindings
        self.file_tree.bind("<ButtonRelease-3>", self.popup)
        self.file_tree.bind("<Double-Button-1>", self.on_double_click)
        self.file_tree.bind("<Return>", self.right_click_open)
        self.file_tree.bind("<<TreeviewSelect>>", self.toggle_trees_focus)
        
        # Favorite Treeview Command Bindings
        self.fav_tree.bind("<ButtonRelease-3>", self.fav_popup)
        self.fav_tree.bind("<Double-Button-1>", self.on_double_click)
        self.fav_tree.bind("<Return>", self.fav_right_click_open)
        self.fav_tree.bind("<<TreeviewSelect>>", self.toggle_trees_focus)

        # Queue Manager Bindings
        self.listbox_dnd.bind('<Button-1>', self.dnd_set_current)
        self.listbox_dnd.bind('<B1-Motion>', self.dnd_shift_selection)

    # Content Methods
    def get_automations_list(self):
        # Getting values from config.json
        open_config = open((self.RPATH + "\\core\\config.json"), "r")
        conv_config = json.load(open_config)
        open_config.close()
        return_list = []
        automation_list = conv_config['automations']
        for automation in automation_list:
            return_list.append(automation['name'])
        print(return_list)
        return return_list

    def _LEGACY_render_snapshot(self, key_value):
        '''
        TODO - THIS NEEDS TO BE RE-ADDED :)

        Called when Filebrowser is first rendered. 
        This does not do any rescursive scanning into directories. This 
        trades off depth on render for an instant load time. Because the
        'refresh_file_tree' is a generator, the sub-directories of any
        directories present in the root (dnvshare\\4-123...) will be rendered
        in *order of depth*. This is to optimize time-to-work on import.

        ** The Subdirs of 'FILE1' and 'FILE2' will be inserted into Tree
        before the Sub/Subdirs of 'FILE1' are inserted.
        '''

        # Inserting local tree test
        # if local files present
        if os.access(self.sr_local_path, os.R_OK):
            self.file_tree.insert('', '0', iid='local_space', tags=('default'))
            self.file_tree.insert('', '0', iid='local_root', text="Local Files (Downloads)", tags=('dir_color'))

        cur_filestable = bcamp_api.query_all_files(key_value)
        #pprint.pprint(cur_filestable)
        for row in cur_filestable:
            print("\n**~**~**")
            print("depth:", row[10])
            print("path", row[2])
        return 
        for file_tup in cur_filestable:
            #print("***", file_tup[2], file_tup[10])
            # Saving raw vars from SQLite3 DB 
            file_path = file_tup[2]
            file_type = file_tup[3]
            file_raw_size = int(file_tup[4])    # Stored as str in SQLite3
            file_raw_ctime = float(file_tup[5]) # Stored as str in SQLite3
            file_date_range = file_tup[7]

            # Converting Time to readable format from config.json
            tree_ctime = (datetime.datetime.fromtimestamp(
                file_raw_ctime)).strftime(self.time_format)

            # Converting File Size - Omiting Dirs for now...
            format_size = "{size:.3f} MB"
            if file_type != 'dir':
                tree_size = format_size.format(size=file_raw_size / (1024*1024))
            else:
                tree_size = "..."

            # Setting Range

            # Defining Color Tags based on User config - TO BE DEFINED IN CONFIG.JSON
            # Resetting Tag from prev file in loop
            tree_tag = 'default'
            if file_type == 'dir':
                tree_tag = 'dir_color'
            if file_type == ".enc":
                tree_tag = 'enc_color'
            if file_type == ".bin":
                tree_tag = 'bin_color'
            if file_type == ".zip":
                tree_tag = 'zip_color'
            if file_type == ".log":
                tree_tag = 'log_color'

            '''
            #try:
            #    self.file_tree.insert('', 'end', iid=file_path, text=file_tup[0], values=(
            #        tree_ctime, tree_size), tags=(tree_tag,))
            #except tk.TclError as e:
            #    print("PASS" + str(file_tup[0]) + " - Already exist")
            #    pass
            '''
            split_path = os.path.split(file_tup[2])
            possible_parent = split_path[0] # Head/Path sans filename
            #print("\n***", file_tup[0], file_tup[10])

            # TESTING
            if file_tup[1] == 'remote':
                tree_root = ''
            else:
                tree_root = 'local_root'

            # Inserting Files into *self.file_tree*
            if self.file_tree.exists(possible_parent): 
                # Insert as child of *possible_parent*
                print("*posparent*", possible_parent)
                try:
                    self.file_tree.insert(possible_parent, 
                        'end', 
                        iid=file_tup[2], 
                        text=file_tup[0],
                        values=(tree_ctime, tree_size, file_date_range),
                        tags=(tree_tag))
                except tk.TclError:
                    # Passing - Error thrown on dupes which is expected.
                    #print(mode, "Passing " + os.path.basename(_path) + " : Already in Tree")
                    pass

            else:
                # Create New Parent Row
                print("\n*parent MISSING*\n", "path:", file_tup[2], "\n parent:", possible_parent,
                    "\n depth:", file_tup[10],)
                try:
                    self.file_tree.insert(
                        tree_root, 
                        'end', 
                        iid=file_tup[2], 
                        text=file_tup[0],
                        values=(tree_ctime, tree_size, file_date_range),
                        tags=('debug'))
                except tk.TclError as e:
                    print(e)

        #pprint.pprint(bcamp_api.query_all_files(key_value))
                    
    def refresh_file_record(self, mode):
        '''
        Threaded generator that scans the either the remote, 
        local paths in order of nested dir "depth"*. The
        *mode* var determines the target path, and location of found
        files.

        mode('remote') - Starts scanning from 'self.remote_path'
        mode('local') - Starts scanning from 'self.local_path'

        ** The Subdirs of 'FILE1' and 'FILE2' will be inserted 
        into Tree before the Sub/Sub/dirs of 'FILE1' are inserted.
        '''
        def tree_gen(depth_index):
            # Temp Container for dir_paths @ 'depth_index'
            temp_dirs = []
            # For paths at this *depth_index*
            for path in dir_depth_list[depth_index]:
                with os.scandir(path) as scanner:
                    for dirEntry in scanner:
                        # Add any dirs paths to temp_dirs
                        if dirEntry.is_dir():
                            # Save to temp_dirs for next iteration
                            temp_dirs.append(dirEntry.path)
                            # Create record in stream, effort to reduce N*
                            create_record(dirEntry.path, depth_index)
                        if dirEntry.is_file():
                            create_record(dirEntry.path, depth_index)

            # Prevent adding empty temp_dir list for infin loop.
            if len(temp_dirs) != 0:
                dir_depth_list.append(temp_dirs)
                yield temp_dirs

        def create_record(_path, depth_index):
            '''
            Used by *tree_gen* to create a dictionary record for
            Dir paths found.
            '''
            # Get os.stat values for *path*
            file_stats = os.stat(_path)
            # Set 'type'
            if stat.S_ISDIR(file_stats.st_mode):
                _type = "dir"
            else:
                _type = os.path.splitext(_path)[1]
                # TODO if type is '.1' or '.2', etc, see if its actually .log here...
            # Enough data for tree record now, insert here...
            insert_to_tree(_path, file_stats, _type)

            # Determine if file is "favorited"
            #if self.config_record['favorites'] != None:
            #    if os.path.basename(_path) in self.config_record['favorites']:
            #        # Pass to 'insert_to_favtree' with vars
            #        insert_to_favtree(_path, file_stats, _type)


            # Create record using *file_stats*
            record = {
                os.path.basename(_path): {
                        'location': mode,
                        'path': _path,
                        'type': _type,
                        'size': file_stats.st_size,
                        'creation_time': file_stats.st_ctime,
                        'modified_time': file_stats.st_mtime,
                        'date_range': None, # Set in "finalize"    
                        'favorite': False,  # Set in "finalize"
                        'notes': None,      # Set in "finalize"
                        'depth_index': depth_index
                    }
            }
            updated_file_record.update(record)
            return record
        
        def insert_to_tree(_path, _stats, _type):
            # Build Var's for Treeview insert
            # Check *_path* (head,) string via os.path.split
            split_path = os.path.split(_path)
            possible_parent = split_path[0] # Head
            tree_text = split_path[1] # Tail/name

            # formated size string
            format_size = "{size:.3f} MB"
            if _type != 'dir':
                tree_size = format_size.format(size=_stats.st_size / (1024*1024))
            else:
                tree_size = "..."

            # Formating time String
            tree_ctime = (datetime.datetime.fromtimestamp(
                    _stats.st_ctime)).strftime(time_format)

            # Formating Range based on _type
            #tree_range = "" # Default 
            #if _type in self.config_record['range_extensions']:
            #    #print("Supported range ext", tree_text)
            #    #TODO calculate range of files...
            #    pass

            # Setting Tree 'tag' based on type...
            tree_tag = 'default'
            if _type == 'dir':
                tree_tag = 'dir_color'
            if _type == ".enc":
                tree_tag = 'enc_color'
            if _type == ".bin":
                tree_tag = 'bin_color'
            if _type == ".zip":
                tree_tag = 'zip_color'
            if _type == ".log":
                tree_tag = 'log_color'

            # Determine "root" path for tree based on mode.
            if mode == 'remote':
                tree_root = ''
            elif mode == 'local':
                # Download tree created during __init__ if dir !empty.
                # Creating it here if it is missing - ex first local file.
                if self.file_tree.exists(self.local_tree):
                    tree_root = self.local_tree
                else:
                    self.file_tree.insert('', '0', iid='local_filler_space', tags=('default'))
                    self.file_tree.insert('', '0', iid=self.local_tree, text="Downloads/Unpacks", tags=('dir_color'))
                    tree_root = self.local_tree
            
            # Inserting Files into *self.file_tree*
            #dbg("file_tree", self.file_tree) 
            try:
                if self.file_tree.exists(possible_parent): 
                    # Insert as child of *possible_parent*
                    try:
                        self.file_tree.insert(possible_parent, 
                            'end', 
                            iid=_path, 
                            text=tree_text,
                            values=(tree_ctime, tree_size, tree_range),
                            tags=(tree_tag))
                    except tk.TclError:
                        # Passing - Error thrown on dupes which is expected.
                        #print(mode, "Passing " + os.path.basename(_path) + " : Already in Tree")
                        pass

                else:
                    # Create New Parent Row
                    try:
                        self.file_tree.insert(
                            tree_root, 
                            'end', 
                            iid=_path, 
                            text=tree_text, 
                            values=(tree_ctime, tree_size, tree_range), 
                            tags=(tree_tag))
                    except tk.TclError:
                        #print(mode, "Passing " + os.path.basename(_path) + " : Already in Tree")
                        pass
            except tk.TclError:
                pass
                #print("No file_tree yo!")

        def insert_to_favtree(_path, _stats, _type):
            '''
            Very Similar to 'insert_to_tree' with edits to comply
            with expected "favorites" format from generators.
            '''
            # Build Var's for Treeview insert
            split_path = _path.split(self.key_value + "\\", 1)
            parent = split_path[1].rsplit("\\", 1)
            
            # formated size string
            format_size = "{size:.3f} MB"
            if _type != 'dir':
                tree_size = format_size.format(size=_stats.st_size / (1024*1024))
            else:
                tree_size = "..."

            # Formating time String
            tree_ctime = (datetime.datetime.fromtimestamp(
                    _stats.st_ctime)).strftime(time_format)

            # Formating Range based on _type
            #tree_range = "" # Default 
            #if _type in self.config_record['range_extensions']:
            #    # TODO Is this needed here?
            #    #print("Supported range ext", parent[1])
            #    pass

            # Setting Tree 'tag' based on type...
            tree_tag = 'default'
            if _type == 'dir':
                tree_tag = 'dir_color'
            if _type == ".enc":
                tree_tag = 'enc_color'
            if _type == ".bin":
                tree_tag = 'bin_color'
            if _type == ".zip":
                tree_tag = 'zip_color'
            if _type == ".log":
                tree_tag = 'log_color'

            if len(parent) == 2:
                #print("**result**", "\n", "parent_tree:", parent[0], "\n", "fav_tree_text:", parent[1], "\n", "fav_tree_iid:", _path, "\n")
                # Inserting Files into *self.fav_tree*
                try:
                    self.fav_tree.insert(
                        os.path.dirname(_path), 
                        'end', 
                        iid=_path, 
                        text=parent[1],
                        values=(tree_ctime, tree_size, tree_range),
                        tags=(tree_tag))
                except tk.TclError as e:
                    try:
                        self.fav_tree.insert(
                            '', 
                            'end', 
                            iid=os.path.dirname(_path), 
                            text=parent[0],
                            tags=('dir_color'),
                            open=True)
                        self.fav_tree.insert(
                            os.path.dirname(_path), 
                            'end', 
                            iid=_path, 
                            text=parent[1],
                            values=(tree_ctime, tree_size, tree_range),
                            tags=(tree_tag))
                    except tk.TclError:
                        #print(mode, "Passing " + os.path.basename(_path) + " : Already in Tree")
                        pass

            else:
                #print("**result**", "\n", "parent_tree:", 'none/root', "\n", "fav_tree_text:", parent[0], "\n", "fav_tree_iid:", _path, "\n")
                # Create New Parent Row
                try:
                    self.fav_tree.insert(
                        '', 
                        'end', 
                        iid=_path, 
                        text=parent[0], 
                        values=(tree_ctime, tree_size, tree_range), 
                        tags=(tree_tag))
                except tk.TclError:
                    #print(mode, "Passing " + os.path.basename(_path) + " : Already in Tree")
                    pass
                
        def finalize_mode_record(mode, updated_record):
            '''
            Iterates through the *updated_record*, determining
            'location' and other misc. values per File. Once
            complete, the *finalized_record* is written to
            'datastore.json'

            Called with *update_record* once 'tree_gen' throws
            an StopIter for EOF.

            You wanna parse files after unpack? Call it here :)
            '''
            print("\n   $ *** FINALIZING RECORD ***")


            def timestamp_parser():
                '''
                Testing regex-based parser for Timestamp extraction from log 
                files found in the remote or local dirs.

                For files that contain a timestamp for each-line ("True Logs")
                a DB record should be created that saves... 

                [Filename, Line Num, Timestamp in below format]
                    (Hour:Minute:Second:MS DAY 00/MONTH 00 /YEAR 0000)
                '''

                def datetime_parse(string, line_num, format_str):
                    '''
                    string = Line from opened file.
                    format_str = datetime format string to parse 'string' against.

                    See > https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
                    
                    '''
                    timestamp = datetime.datetime.strptime(
                        string, format_str) 
                    print(line_num, ">", timestamp)


                for item in updated_record:
                    # DEBUG IF
                    if updated_record[item]['type'] == ".dbg":
                        print("\n    $regex_timestamp_parse 'item' >  ", item)
                        # Getting Path of item to open file using recursion.
                        f_path = updated_record[item]['path']
                        print("    path:", f_path, "\n")
                        # Opening file/Creating File Object
                        file = open(f_path, 'r')
                        # Ierating through each line.
                        line_number = 0
                        for line in file:
                            line_number += 1
                            # Try to strip timestamp string using datetime
                            # [DATETIME METHOD ONE] "%b  %d %H:%M:$S"
                            '''ex.) Dec  7 08:35:35'''
                            try:
                                datetime_parse(line, line_number, "%b  %d %H:%M:$S")
                            except ValueError as e:
                                pass
                                #print("    $debug :", e, "\nAttempting next method...\n")

                            # [DATETIME METHOD TWO]
                            '''ex.) 2020-12-16T15:01:04.800390-06:00'''
                            try:
                                datetime_parse(line, line_number, "%Y-%m-%dT%H:%M:$S.%f%z")
                            except ValueError as e:
                                pass
                                #print("    $debug :", e, "\nAttempting next method...\n")





            
            def find_favorites():
                '''
                Crawl 'updated_record' here, and find file records that
                have same name as favorites in config.json. Remember
                this will be specific to each 'mode' i.e 'remote'
                'local' and 'cust'. The results from here need to be
                combined from all modes before we save the datastore
                record.
                '''
                cur_favorites = bcamp_api.get_file_favs()
                # Search 'updated_record' for each string in 
                # 'cur_favorites'
                if cur_favorites != None:
                    for filename in cur_favorites:
                        search_result = bcamp_api.findkeys(updated_record, filename)
                        for result in search_result:
                            pass
                            #print(result)
                
            # RUN METHODS
            #timestamp_parser() -> Performane OPT needed.

            # SAVE RESULTS TO DB.
            '''
            'path': _path,
            'type': _type,
            'size': file_stats.st_size,
            'creation_time': file_stats.st_ctime,
            'modified_time': file_stats.st_mtime,
            'date_range': None, # Set in "finalize"    
            'favorite': False,  # Set in "finalize"
            'notes': None,      # Set in "finalize"
            '''
            # Refresh files to DB as a thread.
            threading.Thread(target=bcamp_api.update_files, 
                args=(self.key_value, updated_record)).start()

        # Determine root path pased on *mode*
        if mode == 'remote':
            if os.access(self.sr_remote_path, os.R_OK):
                dir_depth_list = [[self.sr_remote_path]]
        if mode == 'local':
            if os.access(self.sr_local_path, os.R_OK):
                dir_depth_list = [[self.sr_local_path]]
            else:
                return

        updated_file_record = {}
        depth_index = -1
        time_format = self.time_format

        if not os.access(self.sr_remote_path, os.R_OK):
            print("ERROR - UNABLE TO LOCATE REMOTE FOLDER. CHECK VPN AND TRY AGAIN?")
            return #exit method
        
        # Generator Loop to iterate through files in order of Depth.
        while True:
            data = tree_gen(depth_index)
            depth_index += 1
            # Recursive call here, if EOF, stopIter thrown.
            try:
                next(tree_gen(depth_index))
            except StopIteration:
                #print(mode, "Jobs Done!")
                threading.Thread(
                    target=finalize_mode_record,
                    args=[mode, updated_file_record]).start()
                return




    # General Treeview Methods
    def toggle_trees_focus(self, event):
        '''
        Allows for only one element from either File or Fav tree to be
        selected at a time. 
        '''
        # Select/Deselect Events from File Tree
        if event.widget == self.file_tree:
            # Determine if File-tree item was selected
            if len(self.file_tree.selection()) > 0:
                self.case_frame.fb_cur_sel.value = self.file_tree.selection()[0]

                # Determine if *fav_tree* has Selections and remove if found.
                if len(self.fav_tree.selection()) > 0:
                    for item in self.fav_tree.selection():
                            self.fav_tree.selection_remove(item)

        # Select/Deselect Events from Favorite Tree
        if event.widget == self.fav_tree:
            # Determine if Favorite-tree item was selected
            if len(self.fav_tree.selection()) > 0:
                self.case_frame.fb_cur_sel.value = self.fav_tree.selection()[0]
                # Determine if *file_tree* has Selections and remove if found.
                if len(self.file_tree.selection()) > 0:
                    for item in self.file_tree.selection():
                            self.file_tree.selection_remove(item)

    def on_double_click(self, event):
        '''
        "Global" Doubleclick handler for All treeviews.
        '''
        treeview = event.widget
        column = treeview.identify_column(event.x)
        region = treeview.identify("region", event.x, event.y)
        #print("\n*debug-region*:", region)
        if region == "heading":
            print("Clicked on heading of", treeview)

        if region == "separator":
            # Column '#0' - TEXT
            if column == '#0':
                data_lst = []
                for child in treeview.get_children():
                    all_vals = treeview.item(child)['text']
                    try:
                        data_lst.append(all_vals)
                    except IndexError:
                        # Thrown for LocalFolder tree item, AND empty space.
                        pass
                # Send to *resize_tree_col* method to handle resizing.
                self.resize_tree_col(treeview, '#0', data_lst)

            # Column '#1' - Date
            if column == '#1':
                # Generate List of all *date* vals.
                data_lst = []
                for child in treeview.get_children():
                    all_vals = treeview.item(child)['values']
                    try:
                        data_lst.append(all_vals[0])
                    except IndexError:
                        # Thrown for LocalFolder tree item, AND empty space.
                        pass
                # Send to *resize_tree_col* method to handle resizing.
                self.resize_tree_col(treeview, '#1', data_lst)

            # Column '#2' - Size
            if column == '#2':
                data_lst = []
                for child in treeview.get_children():
                    all_vals = treeview.item(child)['values']
                    try:
                        data_lst.append(all_vals[1])
                    except IndexError:
                        # Thrown for LocalFolder tree item, AND empty space.
                        pass
                # Send to *resize_tree_col* method to handle resizing.
                self.resize_tree_col(treeview, '#2', data_lst)

            # Column '#3' - Range
            if column == '#3':
                data_lst = []
                for child in treeview.get_children():
                    all_vals = treeview.item(child)['values']
                    try:
                        data_lst.append(all_vals[2])
                    except IndexError:
                        # Thrown for LocalFolder tree item, AND empty space.
                        pass
                # Send to *resize_tree_col* method to handle resizing.
                self.resize_tree_col(treeview, '#3', data_lst)
        else:
            print("Clicked *ITEM*")
            self.right_click_open_local(event=None)

    def resize_tree_col(self, tree_widget, column, data_lst):
        # Calculate which is string longest using max()
        longest_str = max(data_lst, key = len)
        str_length = len(longest_str)
        print ("***\nString ->", longest_str, "\nCharCnt ->", str_length)

        # Calculate true pixel width of *longest_str*
        # NOTE - self.def_font is used in tree. If this changes,
        # make sure this val is updated HERE also.
        print("Tk-Width ->", self.def_font.measure(longest_str))
        raw_pixel_cnt = self.def_font.measure(longest_str)
        padding = (self.def_font['size'] * 2) + 20 #Treeview Leftover Space
        new_column_width = raw_pixel_cnt + padding
        tree_widget.column(column, width=new_column_width)

    # File Tree "Right-Click" Menu
    def popup(self, event):
        """action in event of button 3 on tree view"""
        # select row under mouse
        iid = self.file_tree.identify_row(event.y)
        if iid:
            # mouse pointer over item
            self.file_tree.selection_set(iid)
            # Configuring menu based on IID...
            if self.sr_local_path in iid:
                self.local_right_click_menu.post(
                    event.x_root + 10, event.y_root + 10)
            else:
                self.right_click_menu.post(
                    event.x_root + 10, event.y_root + 10)
        else:
            # mouse pointer not over item
            # occurs when items do not fill frame
            # no action required
            pass

    def right_click_open_local(self, event=None):
        iid = self.file_tree.selection()[0]
        # Check if LogViewer is "open" - Open if closed
        curTemplate = self.case_frame.template.value 
        # TEMPORARY - Updates LogViewer val manually, will need to be adjusted
        # when Workpanes can be dynamically placed.
        logViewer_shown = (curTemplate[1])['workpanes'][0][1]
        if not logViewer_shown:
            self.case_frame.show_workpane('default_logview')
        # Update self.case_frame.main_col1 Width for Logviewer.
        self.case_frame.main_col1.paneconfig(self.case_frame.tk_log_viewer, stretch="always")

    def right_click_open(self, event=None):
        iid = self.file_tree.selection()[0]
        try:
            os.startfile(iid)
        except OSError:
            print("ERROR - NO APPLICATION ASSOCIATED.")
        # FUTURE - Multiple Selection -> [0] removed and should handle tuple
        self.file_tree.selection_remove(self.file_tree.selection()[0])

    def right_click_download(self):
        iid = self.file_tree.selection()[0]
        print("DOWNLOAD> ", iid)
        # Add download to threaded Queue.
        self.file_queue.add_download(self.key_value, iid)
        remote_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['remote'],
            name=(self.key_value + "::remote_refresh")
            )
        local_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['local'],
            name=(self.key_value + "::local_refresh")
            )
        # Local refresh first because you download to local :)
        self.file_queue.put(local_refresh)
        # REMOVED for Optimization -> self.file_queue.put(remote_refresh)
        # FUTURE - Multiple Selection -> [0] removed and should handle tuple
        self.file_tree.selection_remove(self.file_tree.selection()[0])

    def right_click_upload(self):
        iid = self.file_tree.selection()[0]
        print("UPLOAD> ", iid)
        # Add download to threaded Queue.
        self.file_queue.add_upload(self.key_value, iid)
        remote_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['remote'],
            name=(self.key_value + "::remote_refresh")
            )
        local_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['local'],
            name=(self.key_value + "::local_refresh")
            )
        # Remote refresh first because you upload to remote :)
        self.file_queue.put(remote_refresh)
        # REMOVED for Optimization -> self.file_queue.put(local_refresh)
        # FUTURE - Multiple Selection -> [0] removed and should handle tuple
        self.file_tree.selection_remove(self.file_tree.selection()[0])
        
    def right_click_reveal_in_explorer(self):
        iid = self.file_tree.selection()[0]
        print("would reveal... " + iid)
        subprocess.Popen((r'explorer /select,' + iid))
        self.file_tree.selection_remove(self.file_tree.selection()[0])

    def right_click_favorite(self):
        '''
        Using the 'file name' as a key, this file is added to the
        users config.json 'favorite' record. When this file name
        is seen during 'finalize_mode_record', it will be 
        automatically appended to the 'self.fav_tree' during
        future scans for ANY product.
        '''
        # iid is full path of 'x' in tree
        iid = self.file_tree.selection()[0]

        cur_favorites = bcamp_api.get_fav_files()
        print("$cur_favorites", cur_favorites)

        bcamp_api.add_fav_file(self.key_value, iid)


        # Finally, insert results into treeview
        threading.Thread(
            target=self.refresh_file_record,
            args=['remote']).start()
        threading.Thread(
            target=self.refresh_file_record,
            args=['local']).start()

    def right_click_delete_local(self):
        # iid is full path of 'x' in tree
        iid = self.file_tree.selection()[0]
        print("Deleting", iid)
        try:
            shutil.rmtree(iid)
        except:
            os.remove(iid)
        print(iid, "deleted!")
        # Check if count of local files, may need to remove root path
        if len(os.listdir(self.sr_local_path)) > 1:
            # Drop IID from tree only
            self.file_tree.delete(iid)
            # TODO Keep Tree open on removal
            self.file_tree.item(self.local_tree, open=True)
        else:
            # Drop IID and ROOT local Tree items
            self.file_tree.delete('local_filler_space')
            self.file_tree.delete(self.local_tree)

        # Local refresh only, only change.
        local_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['local'],
            name=(self.key_value + "::local_refresh")
            )
        #local_refresh.start()
        self.file_queue.put(local_refresh)

    def launch_automation(self, targetAuto):
        iid = self.file_tree.selection()[0]

        # Starting thread to prevent UI from hanging...
        self.file_queue.add_automation(self.key_value, iid, targetAuto)
        # Put refresh threads into queue after - will run once unpacked.
        remote_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['remote'],
            name=(self.key_value + "::remote_refresh")
            )
        local_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['local'],
            name=(self.key_value + "::local_refresh")
            )
        # Local refresh first because you unpack to local :)
        self.file_queue.put(local_refresh)
        self.file_queue.put(remote_refresh)
        self.file_tree.selection_remove(self.file_tree.selection()[0])

    # Fav Tree "Right-Click" Menu Methods
    def fav_popup(self, event):
        """action in event of button 3 on tree view"""
        # select row under mouse
        iid = self.fav_tree.identify_row(event.y)
        if iid:
            # mouse pointer over item
            self.fav_tree.selection_set(iid)
            # Configuring menu based on IID...
            self.fav_right_click_menu.post(
                event.x_root + 10, event.y_root + 10)
        else:
            # mouse pointer not over item
            # occurs when items do not fill frame
            # no action required
            pass

    def fav_right_click_open_local(self, event=None):
        iid = self.fav_tree.selection()[0]
        # Check if LogViewer is "open" - Open if closed
        curTemplate = self.case_frame.template.value 
        # TEMPORARY - Updates LogViewer val manually, will need to be adjusted
        # when Workpanes can be dynamically placed.
        logViewer_shown = (curTemplate[1])['workpanes'][0][1]
        if not logViewer_shown:
            self.case_frame.show_workpane('default_logview')
        # Update self.case_frame.main_col1 Width for Logviewer.
        self.case_frame.main_col1.paneconfig(self.case_frame.tk_log_viewer, width=(self.winfo_width()/2.2))

    def fav_right_click_open(self, event):
        iid = self.fav_tree.selection()[0]
        try:
            os.startfile(iid)
        except OSError:
            print("ERROR - NO APPLICATION ASSOCIATED.")
        
        # FUTURE - Multiple Selection -> [0] removed and should handle tuple
        self.fav_tree.selection_remove(self.fav_tree.selection()[0])

    def fav_right_click_download(self):
        iid = self.fav_tree.selection()[0]
        print("DOWNLOAD> ", iid)
        self.file_queue.add_download(self.key_value, iid)
        remote_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['remote'],
            name=(self.key_value + "::remote_refresh")
            )
        local_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['local'],
            name=(self.key_value + "::local_refresh")
            )
        # Local refresh first because you download to local :)
        self.file_queue.put(local_refresh)
        self.file_queue.put(remote_refresh)

    def fav_right_click_reveal_in_explorer(self):
        iid = self.fav_tree.selection()[0]
        print("would reveal... " + iid)
        subprocess.Popen((r'explorer /select,' + iid))

    def fav_right_click_unfavorite(self):
        iid = self.fav_tree.selection()[0]
        print("unfavorite... " + iid)
        # Remove from tree
        self.fav_tree.detach(iid)
        # Remove from "favorite_files" table
        bcamp_api.remove_fav_file(iid)

    def fav_launch_automation(self, targetAuto):
        iid = self.fav_tree.selection()[0]

        # Starting thread to prevent UI from hanging...
        self.file_queue.add_automation(self.key_value, iid, targetAuto)
        # Put refresh threads into queue after - will run once unpacked.
        remote_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['remote'],
            name=(self.key_value + "::remote_refresh")
            )
        local_refresh = threading.Thread(
            target=self.refresh_file_record,
            args=['local'],
            name=(self.key_value + "::local_refresh")
            )
        # Local refresh first because you unpack to local :)
        self.file_queue.put(local_refresh)
        self.file_queue.put(remote_refresh)
        self.file_tree.selection_remove(self.file_tree.selection()[0])

    # FileOps Queue Methods
    def update_progess_string(self, new_string):
        '''
        Called when Gui.progress_string.value is updated,
        which is passed to this method as *new_string*

        Updates progress_strVar Tk Var which automatically
        updates the Progress label.
        '''
        self.progress_strVar.set(new_string)

    def update_queue_string(self, new_string):
        '''
        Called when Gui.queue_string.value is updated,
        which is passed to this method as *new_string*

        Updates queue_strVar Tk Var which automatically
        updates the Progress label.
        '''
        self.queue_strVar.set(new_string)

    def dnd_set_current(self, event):
        self.listbox_dnd.dnd_cur_index = self.listbox_dnd.nearest(
            self.event.y)

    def dnd_shift_selection(self, event):
        i = self.listbox_dnd.nearest(self.event.y)
        if i < self.listbox_dnd.dnd_cur_index:
            x = self.listbox_dnd.get(i)
            self.listbox_dnd.delete(i)
            self.listbox_dnd.insert(i+1, x)
            self.listbox_dnd.dnd_cur_index = i
        elif i > self.listbox_dnd.dnd_cur_index:
            x = self.listbox_dnd.get(i)
            self.listbox_dnd.delete(i)
            self.listbox_dnd.insert(i-1, x)
            self.listbox_dnd.dnd_cur_index = i

    def show_QueueManager(self, event=None):
        if self.frame_label_queue_state == "on":
            self.queue_frame.grid_remove()
            self.frame_label_queue_state = "off"
            self.btn_show_queue['text'] = "˅"
        else:
            self.queue_frame.grid(
                row=4,
                column=0,
                columnspan=3,
                sticky="nsew"
            )
            self.frame_label_queue_state = "on"
            self.btn_show_queue['text'] = "^"


class Tk_CaseNotes(tk.Frame):
    '''
    Welcome to 'default_notepad'! A Default Workpane that provides a simple
    notepad contextual to each SR. Please use this as an example if you wish to
    create your own Workspace pane - and read some Tk/Tcl Docs ;)

    Further Reading...
    - https://docs.python.org/3/library/tkinter.html
    - https://docs.python.org/3/library/tkinter.ttk.html#module-tkinter.ttk
    '''

    def __init__(self, master, key_value):
        super().__init__(master=master)
        # ROOT Install Path
        global ROOTPATH
        self.RPATH = ROOTPATH
        #self.master = master
        self.key_value = key_value
        self.title = tk.StringVar()
        self.title.set("CaseNotes")
        # Saving SQLite Notes Val for Case.
        self.notes_val = bcamp_api.query_sr(self.key_value, 'notes')
        if self.notes_val == None:
            self.notes_val = ""

        # Setting Fonts for text_box

        self.def_font = tk_font.Font(
            family="Consolas", size=10, weight="normal", slant="roman")
        self.icon_font = tk_font.Font(
            family="Consolas", size=16, weight="normal", slant="roman")
        self.text_font = tk_font.Font(
            family="Consolas", size=12, weight="normal", slant="roman")
        #TK Methods
        self.config_widgets()
        self.config_bindings()
        self.config_grid()

        #Binding Keyboard shortcuts
        self.bind('<Control-s>', self.save_button)

    def config_widgets(self):
        self.notepad_top_frame = tk.Frame(
            self,
            background='#404b4d',
        )
        self.save_button = tk.Button(
            self.notepad_top_frame,
            background='#404b4d',
            foreground='#5b6366',
            text="🖿",
            font=self.def_font,
            relief="flat",
            command=self.save_notes
        )
        self.search_text = tk.Entry(
            self.notepad_top_frame,
            background='#333333',
            foreground="#777777",
            relief="flat",
            width=60,
        )
        self.search_text_btn = tk.Button(
            self.notepad_top_frame,
            background='#161616',
            foreground="#777777",
            relief="flat",
            text='>'
        )
        self.title_label = tk.Label(
            self.notepad_top_frame,
            textvariable=self.title,
            background='#404b4d',
            foreground="#888888",
            relief="flat",
            anchor="center",
        )
        self.text_box = CustomTk_Textbox(
            self,
            background="#1e2629",
            foreground="#fdfdfd",
            insertbackground="#ffffff", #Cursor, ugh TK Naming conventions...
            padx=10,
            pady=10,
            wrap='word',
            undo=True,
            font=self.text_font,
            relief='flat'
        )
        #Getting notes from datastore
        self.text_box.insert('1.0', self.notes_val)
    
    def config_grid(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='ew')
        #top_frame_grid
        self.notepad_top_frame.columnconfigure(0, weight=1)
        self.title_label.grid(row=0, column=0, padx=5, pady=3, sticky='ew')
        self.save_button.grid(row=0, column=1, padx=3, pady=3, sticky='e')
        #self.search_text.grid(row=0, column=1, sticky='e')
        #self.search_text_btn.grid(row=0, column=2, sticky='e')
        #/top_frame_grid
        self.text_box.grid(row=1, column=0, sticky='nsew')

    def config_bindings(self):
        self.text_box.bind("<FocusIn>", self.set_focusIn_colors)
        self.text_box.bind("<FocusOut>", self.set_focusOut_colors)
        self.text_box.bind("<<TextModified>>", self.save_notify)

    def set_focusIn_colors(self, event):
        if self.title.get() == "⬤ Case Notes":
            self.save_button.config(
                background='#404b4d',
                foreground='#badc58',
            )
        else:
            self.save_button.config(
                background='#404b4d',
                foreground='#ffffff',
            )
        self.title_label.config(
            foreground="#CCCCCC",
        )

    def set_focusOut_colors(self, event):
        self.save_button.config(
            background='#404b4d',
            foreground='#5b6366',
        )
        self.title_label.config(
            foreground="#888888",
        )

    def save_notify(self, event):
        self.title.set("⬤ CaseNotes")
        self.save_button.config(
            background='#404b4d',
            foreground='#badc58',
        )

    def save_notes(self):
        new_notes = self.text_box.get('1.0', tk.END)
        bcamp_api.update_sr(self.key_value, 'notes', new_notes)
        self.title.set("CaseNotes")
        self.save_button.config(
            background='#404b4d',
            foreground='#ffffff',
        )


class Tk_FileNotes(tk.Frame):
    '''
    A workpane similar to *CaseNotes*, but only shows the selected file Notes.
    '''
    def __init__(self, master, key_value, root_path, case_frame, log_viewer):
        super().__init__(master=master)
        #self.master = master
        self.key_value = key_value
        self.log_viewer = log_viewer #shown in LogViewer or indepent.
        self.selected_file = ""
        self.title = tk.StringVar()
        self.title.set("*Select a file first* - FileNotes")
        self.case_frame = case_frame
        self.case_frame.fb_cur_sel.register_callback(self.get_file_notes)

        # Getting values from core/datastore.json
        self.RPATH = root_path

        # Setting Fonts for text_box
        self.def_font = tk_font.Font(
            family="Consolas", size=10, weight="normal", slant="roman")
        self.text_font = tk_font.Font(
            family="Consolas", size=12, weight="normal", slant="roman")
        
        #TK Methods
        self.config_widgets()
        self.config_bindings()
        self.config_grid()

        #Binding Keyboard shortcuts
        self.bind('<Control-s>', self.save_button)

    def config_widgets(self):
        self.notepad_top_frame = tk.Frame(
            self,
            background='#404b4d',
        )
        self.save_button = tk.Button(
            self.notepad_top_frame,
            background='#404b4d',
            foreground='#5b6366',
            text="🖿",
            font=self.def_font,
            relief="flat",
            command=self.save_notes
        )
        if self.log_viewer != None:
            self.hide_button = tk.Button(
                self.notepad_top_frame,
                background='#404b4d',
                foreground='#5b6366',
                text="^",
                font=self.def_font,
                relief="flat",
                command=self.log_viewer.show_file_notes
            )
        self.search_text = tk.Entry(
            self.notepad_top_frame,
            background='#333333',
            foreground="#777777",
            relief="flat",
            width=60,
        )
        self.search_text_btn = tk.Button(
            self.notepad_top_frame,
            background='#161616',
            foreground="#777777",
            relief="flat",
            text='>'
        )
        self.title_label = tk.Label(
            self.notepad_top_frame,
            textvariable=self.title,
            background='#404b4d',
            foreground="#888888",
            relief="flat",
            anchor="center",
        )
        self.text_box = CustomTk_Textbox(
            self,
            background="#1e2629",
            foreground="#fdfdfd",
            insertbackground="#ffffff", #Cursor, ugh TK Naming conventions...
            padx=10,
            pady=10,
            wrap='word',
            undo=True,
            font=self.text_font,
            relief='flat'
        )

    def config_grid(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='ew')
        #top_frame_grid
        self.notepad_top_frame.columnconfigure(1, weight=1)
        if self.log_viewer != None:
            self.hide_button.grid(row=0, column=0, padx=3, pady=3, sticky='w')
        self.title_label.grid(row=0, column=1, padx=5, sticky='ew')
        self.save_button.grid(row=0, column=2, padx=3, pady=3, sticky='e')
        #self.search_text_btn.grid(row=0, column=2, sticky='e')
        #/top_frame_grid
        self.text_box.grid(row=1, column=0, sticky='nsew')

    def config_bindings(self):
        self.text_box.bind("<FocusIn>", self.set_focusIn_colors)
        self.text_box.bind("<FocusOut>", self.set_focusOut_colors)
        self.text_box.bind("<<TextModified>>", self.save_notify)

    def set_focusIn_colors(self, event):
        if self.title.get() == "⬤ " + self.selected_file:
            self.save_button.config(
                background='#404b4d',
                foreground='#badc58',
            )
        else:
            self.save_button.config(
                background='#404b4d',
                foreground='#ffffff',
            )
        self.title_label.config(
            foreground="#CCCCCC",
        )

    def set_focusOut_colors(self, event):
        self.save_button.config(
            background='#404b4d',
            foreground='#5b6366',
        )
        self.title_label.config(
            foreground="#888888",
        )

    def save_notify(self, event):
        # Get current file_selected
        new_val = "⬤ " + os.path.basename(self.selected_file)
        self.title.set(new_val)
        self.save_button.config(
            background='#404b4d',
            foreground='#badc58',
        )

    def get_file_notes(self, fb_cur_sel):
        '''
        Using the 'Selected File' Value from the FileBroswer, this method
        querys the DB for the notes record, and inserts it into the TextField.
        '''
        # Update Class var for "selected file"
        self.selected_file = fb_cur_sel
        # Query Notes for File
        notes_val = bcamp_api.query_file(self.key_value, 'notes', fb_cur_sel)
        if notes_val == None:
            notes_val = ""
        # Refresh TextBox Widget
        self.text_box.delete('1.0', tk.END)
        self.text_box.insert('1.0', notes_val)
        # Update Title
        trimmed_fname = (os.path.basename(fb_cur_sel))
        self.title.set(trimmed_fname + " - FileNotes")

    def save_notes(self):
        '''
        Saves the content from *self.text_box* into the Sqlite3 DB.
        '''
        new_notes = self.text_box.get('1.0', tk.END)
        bcamp_api.update_file(self.key_value, 'notes', self.selected_file, new_notes)
        self.title.set(os.path.basename(self.selected_file))
        self.save_button.config(
            background='#404b4d',
            foreground='#ffffff',
        )


class Tk_LogViewer(tk.Frame):
    '''
    Renders supported text file types common to product logs.

    Also contains a "FileNotes" subFrame for a wider range of Engineer 
    workflows
    '''
    # Defining supported file extensions to render in textbox!
    SUPPORTED_FILE_EXT = [".log", ".dbg", ".txt", ".0", ".1", ".2", ".3",
        ".4", ".5", ".6", ".7", ".8", ".9", ".10", ".11", ".12", ".13",
        ".14", ".15", ".16", ".properties", ".xml"]
    IMG_FILE_EXT = [".jpeg", ".png", ".gif", ".JPEG", ".PNG", ".GIF"]
    
    def __init__(self, master, key_value, root_path, case_frame):
        super().__init__(master=master)
        #self.master = master
        self.key_value = key_value
        self.show_notes_intvar = tk.IntVar()
        self.wordwrap_intvar = tk.IntVar() 
        self.show_search_intvar = tk.IntVar() 
        self.show_ysb_intvar = tk.IntVar()
        self.show_notes_intvar.set(0) # Default: start notes pane.
        self.wordwrap_intvar.set(1) # Default: Enable Wrap
        self.show_search_intvar.set(0) # Default: Hidden
        self.selected_file = ""
        self.title = tk.StringVar()
        self.title.set("*Select a file first* - LogViewer 0.1")
        self.case_frame = case_frame
        self.case_frame.fb_cur_sel.register_callback(self.open_selected_file)
        self.RPATH = root_path

        # Setting Fonts for text_box.
        self.def_font = tk_font.Font(
            family="Consolas", size=10, weight="normal", slant="roman")
        self.text_font = tk_font.Font(
            family="Consolas", size=12, weight="normal", slant="roman")
        
        #TK Methods
        self.config_widgets()
        self.config_bindings()
        self.config_grid()

    def config_widgets(self):
        self.notepad_top_frame = tk.Frame(
            self,
            background='#404b4d',
        )
        self.search_button = tk.Button(
            self.notepad_top_frame,
            background='#404b4d',
            foreground="#777777",
            relief="flat",
            text='⌕',
            command=self.toggle_search_bar
        )
        self.title_label = tk.Label(
            self.notepad_top_frame,
            textvariable=self.title,
            background='#404b4d',
            foreground="#888888",
            relief="flat",
            anchor="center",
        )

        self.options_button = tk.Button(
            self.notepad_top_frame,
            background='#404b4d',
            foreground="#777777",
            relief="flat",
            text='☰',
            command=self.render_options_menu
        )

        #self.file_notes_button = tk.Button(
        #    self.notepad_top_frame,
        #    text="Notes",
        #    background='#404b4d',
        #    foreground='#5b6366',
        #    font=self.def_font,
        #    command=self.show_file_notes,
        #    relief='flat',
        #)
        #self.wordwrap_button = tk.Button(
        #    self.notepad_top_frame,
        #    text="Wrap",
        #    background='#404b4d',
        #    foreground='#5b6366',
        #    font=self.def_font,
        #    command=self.toggle_wordwrap,
        #    relief='flat',
        #)
        self.text_pane = tk.PanedWindow(
            self,
            orient='vertical',
            bd=0,
            sashwidth=3
        )
        self.text_box_frame = tk.Frame(
            self.text_pane
        )
        self.text_box = CustomTk_Textbox(
            self.text_box_frame,
            background="#1e2629",
            foreground="#CCCCCC",
            insertbackground="#ffffff", #Cursor, ugh TK Naming conventions...
            padx=10,
            pady=10,
            wrap='word',
            undo=True,
            font=self.text_font,
            relief='flat',
        )
        self.text_box_xsb = ttk.Scrollbar(
            self.text_box_frame,
            orient='horizontal',
            command=self.text_box.xview
        )
        self.text_box_ysb = ttk.Scrollbar(
            self.text_box_frame,
            orient='vertical',
            command=self.text_box.yview
        )
        self.text_box.configure(
            xscrollcommand = self.text_box_xsb.set,
            yscrollcommand = self.text_box_ysb.set
        )
        self.file_notes_frame = tk.Frame(
            self.text_pane,
            background="#222222"
        )
        # Intialize Tk_CaseNotes
        self.file_notes = Tk_FileNotes(self.file_notes_frame, self.key_value, self.RPATH, self.case_frame, self)
        # Intialize Tk_LogSearchBar
        self.search_bar = Tk_LogSearchBar(self.notepad_top_frame, self.key_value, self.text_box)

    def config_grid(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='ew')
        self.text_pane.grid(row=1, column=0, sticky='nsew')

        # Notepad_top_frame_grid
        self.notepad_top_frame.rowconfigure(1, weight=1)
        self.notepad_top_frame.columnconfigure(0, weight=1)
        self.notepad_top_frame.columnconfigure(1, weight=1)
        self.title_label.grid(row=0, column=0, columnspan=2, padx=5, pady=3, sticky='ew')
        #self.file_notes_button.grid(row=0, column=1, sticky='e')
        #self.wordwrap_button.grid(row=0, column=2, padx=3, sticky='e')
        self.search_button.grid(row=0, column=2, padx=3, sticky='e')
        self.options_button.grid(row=0, column=3, padx=3, sticky='e')
        self.search_bar.grid(row=1, column=0, columnspan=4, sticky='ew')
        # Hiding SearchBar
        self.search_bar.grid_remove()

        # File Notes grid.
        self.file_notes_frame.rowconfigure(0, weight=1)
        self.file_notes_frame.columnconfigure(0, weight=1)
        self.file_notes.grid(row=0, column=0, sticky='nsew')

        # Text_box Frame
        self.text_box_frame.rowconfigure(0, weight=1)
        self.text_box_frame.columnconfigure(0, weight=1)
        self.text_box.grid(row=0, column=0, sticky='nsew')
        self.text_box_xsb.grid(row=1, column=0, sticky='ew')
        self.text_box_ysb.grid(row=0, column=1, rowspan=2, sticky='ns')
        # Hiding Scrollbars
        self.text_box_xsb.grid_remove()
        self.text_box_ysb.grid_remove()

        # Paned Window
        self.text_pane.add(self.text_box_frame, sticky="nsew", stretch="always")

        # Options Menu
        self.options_menu = tk.Menu(
            tearoff="false",
            background='#404b4d',
            foreground="#CCCCCC",
        )
        self.options_menu.add_command(
            label="Show/Hide Scrollbar",
            command=self.toggle_ysb
        )
        self.options_menu.add_command(
            label="Show/Hide File Notes",
            command=self.show_file_notes
        ) 
        self.options_menu.add_command(
            label="Toggle Word-Wrap",
            command=self.toggle_wordwrap
        )

    def config_bindings(self):
        pass
        #self.text_box.bind("<FocusIn>", self.set_focusIn_colors)
        #self.text_box.bind("<FocusOut>", self.set_focusOut_colors)
        #self.text_box.bind("<<TextModified>>", self.save_notify)
        #self.text_box.bind("<Key>", lambda e: "break") # Readonly textbox

    #def set_focusIn_colors(self, event):
    #    self.title_label.config(
    #        foreground="#CCCCCC",
    #    )
    #    if self.show_notes_intvar.get() == 1:
    #        self.file_notes_button.config(
    #            background='#404b4d',
    #            foreground='#D5A336',
    #        )
    #    else:
    #        self.file_notes_button.config(
    #            background='#404b4d',
    #            foreground='#ffffff',
    #        )
    #    if self.wordwrap_intvar.get() == 0:
    #        self.wordwrap_button.config(
    #            background='#404b4d',
    #            foreground='#D5A336',
    #        )
    #    else:
    #        self.wordwrap_button.config(
    #            background='#404b4d',
    #            foreground='#ffffff',
    #        )
    #
    #def set_focusOut_colors(self, event):
    #    self.title_label.config(
    #        foreground="#888888",
    #    )
    #    self.file_notes_button.config(
    #        background='#404b4d',
    #        foreground='#5b6366',
    #    )
    #    self.wordwrap_button.config(
    #        background='#404b4d',
    #        foreground='#5b6366',
    #    )        

    def open_selected_file(self, fb_cur_sel):
        '''
        Using the 'Selected File' Value from the FileBroswer, this method
        opens the ".log" or ".dbg" extension files and loaded them into
        the LogViewer text_box.

        Threaded-object to prevent UI hanging.
        '''
        def open_file_threadobj(): 
            print("Starting 'open' thread")
            # Update Title
            trimmed_fname = (os.path.basename(fb_cur_sel))
            self.selected_file = trimmed_fname
            self.title.set(trimmed_fname + " - LogViewer 0.1")
            # Clear TextBox Widget
            self.text_box.delete('1.0', tk.END)
            # Open File
            # Get file size, if less than *SIZE*, load at one,
            # otherwise, render line by line! For BIG log files...
            fsize = os.path.getsize(fb_cur_sel)
            print("File_Size >", fsize)
            if fsize <= 1024:
                # Will try "utf-8" and then "latin-1" encoding...
                #try:
                with open(fb_cur_sel, 'r', encoding='utf8') as f:
                    self.text_box.insert(tk.INSERT, f.read())
                #except:
                #    self.text_box.insert(tk.INSERT, "<Unsupported File Type>")
            else:
                with open(fb_cur_sel, 'rb') as f:
                    for line in f:
                        self.text_box.insert(tk.END, line)
                
            print("Finishing 'open' thread - SUCCESS!")
        
        # Defining thread Var to check
        # Check if *fb_cur_sel* is a supported file type.
        if os.path.splitext(fb_cur_sel)[1] in Tk_LogViewer.SUPPORTED_FILE_EXT:
            threading.Thread(target=open_file_threadobj, name=("fopen_" + os.path.basename(fb_cur_sel))).start()
        if os.path.splitext(fb_cur_sel)[1] in Tk_LogViewer.IMG_FILE_EXT:
            # Clear TextBox Widget
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert(tk.END, "An image file? Best I can do is this...\n\n"
                + '''
            ──────▄▀▄─────▄▀▄
            ─────▄█░░▀▀▀▀▀░░█▄
            ─▄▄──█░░░░░░░░░░░█──▄▄
            █▄▄█─█░░▀░░┬░░▀░░█─█▄▄█
                ''' + "\n\nHint: Hitting <Enter> will launch the default App defined by the OS.")
        else:
            # Clear TextBox Widget
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert(tk.END, "!Supported File Type\n\nHint: Hitting <Enter> will launch the default App defined by the OS.")           

    def show_file_notes(self):
        if self.show_notes_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_notes_intvar.set(1)
            self.text_pane.add(self.file_notes_frame, sticky="nsew", stretch="always")
            # Resizing pane of new notepad
            self.text_pane.paneconfig(self.file_notes_frame, height=(self.winfo_height()/2))
            # Changing color of ShowHide Icon
            self.file_notes_button.config(
                background='#404b4d',
                foreground='#D5A336',
            )
        elif self.show_notes_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_notes_intvar.set(0)
            self.text_pane.remove(self.file_notes_frame)
            self.file_notes_button.config(
                background='#404b4d',
                foreground='#ffffff',
            )

    def render_options_menu(self):
        # Get current edge of Tile...
        self.notepad_top_frame.update_idletasks()
        x = self.notepad_top_frame.winfo_rootx()
        y = self.notepad_top_frame.winfo_rooty()
        frame_w = self.notepad_top_frame.winfo_width()
        # Render Menu at edge
        self.options_menu.post(x + frame_w, y + 0)

    def toggle_ysb(self):
        if self.show_ysb_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_ysb_intvar.set(1)
            self.text_box_ysb.grid()
        elif self.show_ysb_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_ysb_intvar.set(0)
            self.text_box_ysb.grid_remove()

    def toggle_search_bar(self):
        if self.show_search_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_search_intvar.set(1)
            self.search_bar.grid()

        elif self.show_search_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_search_intvar.set(0)
            self.search_bar.grid_remove()
            self.file_notes_button.config(
                background='#404b4d',
                foreground='#ffffff',
            )

    def toggle_wordwrap(self):
        if self.wordwrap_intvar.get() == 0: # Disabled
            # Update IntVar, and ENABLE wordwrap
            self.wordwrap_intvar.set(1)
            self.text_box.configure(wrap=tk.WORD)
            # Remove Scrollbar
            self.text_box_xsb.grid_remove()


        elif self.wordwrap_intvar.get() == 1: # Enabled *Default Value
            # Update IntVar, and DISABLE wordwrap
            self.wordwrap_intvar.set(0)
            self.text_box.configure(wrap=tk.NONE)
            # Show Hori. Scrollbar
            self.text_box_xsb.grid()

    def legacy_render_search_frame(self):
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty()
        frame_w = self.winfo_width()
        search_bar = Tk_LogSearchBar(self, self.key_value, self.text_box)
        search_bar.update_idletasks()
        w = search_bar.winfo_width()
        h = search_bar.winfo_height()

        search_bar.place(width=w, height=h)

        #search_bar.place(("%dx%d+%d+%d" % (w, h, x + frame_w - 383, y + 32)))


class Tk_LogSearchBar(tk.Frame):
    '''
    Default search bar shared by various "Log" focused panes such as 
    "LogViewer" or "CaseNotes"
    '''
    def __init__(self, master, key_value, target_textbox):
        super().__init__(master=master)
        self.key_value = key_value
        self.target_textbox = target_textbox
        self.shown_match = 0
        self.total_match = 0
        self.match_count_stringvar = tk.StringVar()
        self.match_count_stringvar.set("No results") #Default/empty Val

        self.blk100 = "#EFF1F3"
        self.blk300 = "#B2B6BC"
        self.blk400 = "#717479"
        self.blk500 = "#1E1F21" ##
        self.blk600 = "#15171C"
        self.blk700 = "#0F1117"
        self.blk900 = "#05070F"
        self.act300 = "#D5A336"

        self.sr_font = tk_font.Font(
            family="Consolas", size=14, weight="bold", slant="roman")
        self.mini_font = tk_font.Font(
            family="Consolas", size=8, weight="bold", slant="italic")
        self.sub_font = tk_font.Font(
            family="Consolas", size=10, weight="normal", slant="roman")

        # ONLY for frames. 
        #self.wm_overrideredirect(True) # Hide windows title_bar
        ##self.attributes('-topmost', 'true')
        #self.resizable = False
        self.config_widgets()
        self.config_bindings()
        self.config_grid()
        # Taking Focus**
        self.focus_set()
        self.search_entry.focus_set()
        # TODO "destroy" TopLevel when focus lost.
        #self.bind("<FocusOut>", self.on_focus_out)
        
    def config_widgets(self):
        self.configure(
            background=self.blk400,
        )
        self.search_entry = tk.Entry(
            self,
            background=self.blk500,
            foreground="#eeeeee",
            insertbackground="#eeeeee",
            insertwidth=1,
            relief='flat'
        )
        self.match_count = tk.Label(
            self,
            background=self.blk400,
            foreground=self.blk500,
            textvariable=self.match_count_stringvar,
            relief='flat'
        )
        self.prev_match_button = tk.Button(
            self,
            background=self.blk400,
            foreground="#eeeeee",
            text="ᐱ",
            relief='flat',
            command=self.prev_match
        )
        self.next_match_button = tk.Button(
            self,
            background=self.blk400,
            foreground="#eeeeee",
            text="ᐯ",
            relief='flat',
            command=self.next_match       
        )
        self.exit_button = tk.Button(
            self,
            background=self.blk400,
            foreground="#eeeeee",
            text="X",
            relief='flat',
            command=self.exit
        )

    def config_bindings(self):
        self.search_entry.bind('<Return>', self.search_target_textbox)

    def config_grid(self):
        '''
        Defines Grid layout for Tk.Widgets defined in init.
        '''
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.grid(ipadx=2, ipady=2)

        # Main Widgets
        self.search_entry.grid(row=0, column=0, padx=5, ipadx=2, ipady=2, sticky='ew')
        self.match_count.grid(row=0, column=1, padx=2, sticky='ew')
        self.prev_match_button.grid(row=0, column=2, padx=2, sticky='ew')
        self.next_match_button.grid(row=0, column=3, padx=2, sticky='ew')
        self.exit_button.grid(row=0, column=4, padx=2, sticky='ew')

    def exit(self):
        '''
        Remove search bar TopLevel when focus is not a child widget of toplevel.
        '''
        self.grid_remove()

    def search_target_textbox(self, event=None):
        # Reset UI counters from previous search
        self.match_count_stringvar.set("...")
        self.shown_match = 0
        # Begin Search Algo.
        searchEntry = self.search_entry
        self.target_textbox.tag_delete("search")
        self.target_textbox.tag_configure("search", background="green")
        start="1.0"
        if len(searchEntry.get()) > 0:
            self.target_textbox.mark_set("insert", self.target_textbox.search(searchEntry.get(), start))
            self.target_textbox.see("insert")
            self.shown_match += 1

            while True:
                pos = self.target_textbox.search(searchEntry.get(), start, tk.END) 
                if pos == "": 
                    break       
                start = pos + "+%dc" % len(searchEntry.get()) 
                self.target_textbox.tag_add("search", pos, "%s + %dc" % (pos,len(searchEntry.get())))
        
        # Count results and update Counter
        match_string_count = len(self.target_textbox.tag_ranges('search'))/2
        self.total_match = "{:n}".format(match_string_count)
        self.match_count_stringvar.set(str(self.shown_match) + " of " + str(self.total_match))
        self.target_textbox.focus_set()

    def next_match(self, event=None):
        if self.match_count_stringvar.get() == "No results": # Default/Empty
            return

        # move cursor to end of current match
        while (self.target_textbox.compare(tk.INSERT, "<", tk.END) and
            "search" in self.target_textbox.tag_names(tk.INSERT)):
            self.target_textbox.mark_set(tk.INSERT, "insert+1c")

        # Update shown index
        if int(self.shown_match) < int(self.total_match):
            self.shown_match += 1
            self.match_count_stringvar.set(str(self.shown_match) + " of " + str(self.total_match))
        # find next character with the tag
        next_match = self.target_textbox.tag_nextrange("search", tk.INSERT)
        if next_match:
            self.target_textbox.mark_set(tk.INSERT, next_match[0])
            self.target_textbox.see(tk.INSERT)

        # prevent default behavior, in case this was called
        # via a key binding
        return "break"


    def prev_match(self, event=None):
        if self.match_count_stringvar.get() == "No results": # Default/Empty
            return

        # move cursor to end of current match
        while (self.target_textbox.compare(tk.INSERT, ">", tk.END) and
            "search" in self.target_textbox.tag_names(tk.INSERT)):
            self.target_textbox.mark_set(tk.INSERT, "insert+1c")

        # Update shown index
        if int(self.shown_match) > 0:
            self.shown_match -= 1
            self.match_count_stringvar.set(str(self.shown_match) + " of " + str(self.total_match))
        # find next character with the tag
        prev_match = self.target_textbox.tag_prevrange("search", tk.INSERT)
        if prev_match:
            self.target_textbox.mark_set(tk.INSERT, prev_match[0])
            self.target_textbox.see(tk.INSERT)

        # prevent default behavior, in case this was called
        # via a key binding
        return "break"


'''
LAUNCH!
'''
# Create Folder Structure
bcamp_setup.CreateDirs()

# Configuring main log...
RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
if os.access((RPATH + '\\logs\\main.log'), os.R_OK):
    logging.basicConfig(filename=(RPATH + '\\logs\\main.log'), encoding='utf-8', level=logging.DEBUG)
else:
    # create empty setup.log file
    file = open((RPATH + '\\logs\\main.log'), "w+")
    file.close()
    logging.basicConfig(filename=(RPATH + '\\logs\\main.log'), encoding='utf-8', level=logging.DEBUG)

# Creating "basecamp.db" if not available.
bcamp_setup.CreateDB()

# Intializing Extension Managers
automations_manager = bcamp_extensions.Automations()

# Starting UI
Gui(automations_manager)