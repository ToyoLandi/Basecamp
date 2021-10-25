# Basecamp 0.3 BETA
# Written by Collin Spears, Network TSE

'''
Welcome to Basecamp.py, I hope you like what we have done with the place.
This is the main file. Executing this file will start the Application UI, AND
the SQLite3 DB. If this is your first time, this file will also create the
initial dirs and log files using this file location as "root".

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

        # bcamp_setup.py -  Handles the installation process, and automatically
        generates the "basecamp.db" SQLite3 Database, containing various tables that
        store UI behavior, Case Data, and automation details.

        # bcamp_api.py - The "backend" of the Application, containing DB queries,
        Automation imports, and other shortcuts for common functionality needed
        through the UI.


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

# Public Imports
import io
import os
import stat
import atexit
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
BCAMP_ROOTPATH = bcamp_api.BCAMP_ROOTPATH

'''Root Tk/Tcl Class'''
class Gui(tk.Tk):
    '''
    Main Class of Basecamp UI

    This class renders the main UI window, and initializes the Tk/TtK classes
    used through out the application. The idea is for this class to be a 
    "framework" for the rest of the UI elements.

    Further Reading...
    - https://docs.python.org/3/library/tk.html
    - https://docs.python.org/3/library/tk.ttk.html#module-tk.ttk

    '''
    # ***[ GLOBAL CALLBACK VARIABLES ]***

    # Import Menu results Python Dict.
    import_item = bcamp_api.callbackVar()
    JIRA_ENABLED = bcamp_api.callbackVar()
    JIRA_ENABLED.value = False

    def __init__(self):
        super().__init__()
        # Root Path of install CONSTANT.
        self.RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]

        # Check for available "Automations" and update DB
        bcamp_api.Automations()

        # Starting Queue Daemons - See "bcamp_api.py' for details.
        self.FileOpsQ = bcamp_api.FileOpsQueue()
        self.CasePoll = bcamp_api.CasePollDaemon(self)
        self.ImportDaemon = bcamp_api.ImportDaemon(self)
        # Register Callback method for "Gui.import_item" changes to 
        # "import_handler()". These will be dictionary objects from
        # the Tk_ImportMenu
        Gui.import_item.register_callback(self.import_handler)

        # Register EXIT method
        atexit.register(self.on_exit)

        # Intializing Main Tk/Ttk Classes
        self.RootPane = Tk_RootPane(self)
        self.BottomBar = Tk_BottomBar(self)
        self.Workbench = Tk_WorkbenchTabs(self.RootPane.vertical_pane, self.FileOpsQ, self)

        # Fullscreen Var for <Alt-Enter>
        self.w_fullscreen = False

        # Configuring Tk ELements for Main Window.
        self.config_widgets()
        self.config_grid()
        self.config_window()
        self.config_binds()
        self.ttk_theme_changes()

        # Configuring UI based on user-config in DB.
        self.render_initial_config()
        
        # STARTING TK/TTK UI
        self.start_ui()
        # Nothing should be past "start_ui()" - The UI wont care about it :)

    # Tk/UI Methods
    def start_ui(self):
        '''
        Starting the Tk Mainloop.

        If the mainloop crashes, or is interuppted, the UI will hang with a 
        "Not Responding" message.
        '''
        self.mainloop()

    def config_widgets(self):
        '''
        Tk Widgets NOT drawn by Tk_RootPane are defined here.

        This also contains ttk.Style def's for Notebook and Treeview
        '''
        self.configure(background="black")

        # Top Menu
        self.top_menu = tk.Menu(self, tearoff=0)

        # File Dropdown Menu
        self.tm_file = tk.Menu(self.top_menu, tearoff=0)
        self.tm_file.add_command(
            label="New Import                               Ctrl+N", command=self.render_new_import)
        self.tm_file.add_command(
            label="New Bulk Import                      Ctrl+B", command=self.launch_bulk_importer)
        self.tm_file.add_command(label="Create BulkImport File", command=self.export_bulk_import_file)
        self.tm_file.add_command(
            label="Create Cases Backup               ", command=self.export_cases_backup)
        self.tm_file.add_command(
            label="Restore Cases Backup             ", command=self.import_cases_backup)
        self.tm_file.add_separator()
        self.tm_file.add_command(
            label="Open Downloads                     Ctrl+D", command=self.reveal_download_loc)
        self.tm_file.add_command(
            label="Open Install Dir.                       Ctrl+I", command=self.reveal_install_loc)

        self.tm_file.add_separator()
        self.tm_file.add_command(
            label="Settings Menu                          Ctrl+,", command=self.open_settings_menu)
        self.tm_file.add_separator()
        self.tm_file.add_command(
            label="Check SR Changes                        F5", command=self.start_CasePoll)
        #self.tm_file.add_command(label="Open Theme Wizard", command=self.Tk_ThemeWizard)

        # View Dropdown Menu
        self.tm_view = tk.Menu(self.top_menu, tearoff=0)
        self.tm_view.add_command(
            label="Show Top Menu              Left Alt", command=self.toggle_top_menu)
        self.tm_view.add_separator()
        ####
        self.tm_view.add_command(
            label="Show Side Bar            Ctrl+B", 
                command=self.toggle_sidebar
            )
        self.tm_view.add_command(
            label="Move Side Bar Left", command=lambda 
                pos='left': self.update_sidebar_pos(pos)
            )
        self.tm_view.add_command(
            label="Move Side Bar Right", command=lambda 
                pos='right': self.update_sidebar_pos(pos)
            )
        ####

        # Adding "SubMenus" to Top_Menu widget.
        self.top_menu.add_cascade(label="File", menu=self.tm_file)
        self.top_menu.add_cascade(label="View", menu=self.tm_view)

        # Empty Top Menu - For disabling if user chooses.
        self.empty_menu = tk.Menu(self)

    def config_grid(self):
        '''
        Initalized Frames and "config_widgets" content is added to the UI 
        geometry manager here. - using tk.grid().
        '''
        #self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        #self.TopBar.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.RootPane.grid(row=1,
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
        self.title("Basecamp Beta")
        # Removed for .py -> .exe conversion.
        #titlebar_photo = tk.PhotoImage(file=self.RPATH + "\\core\\bcamp.gif")
        #self.iconphoto(False, titlebar_photo)

    def config_binds(self):
        self.bind('<Control-i>', self.reveal_install_loc)
        self.bind('<Control-d>', self.reveal_download_loc)
        self.bind('<Control-,>', self.open_settings_menu)
        self.bind('<Control-n>', self.Workbench.import_tab)
        self.bind('<Control-b>', self.toggle_sidebar)
        self.bind('<Control-l>', self.launch_bulk_importer)
        #self.bind('<Control-x>', self.export_cases_backup)
        #self.bind('<Control-r>', self.import_cases_backup)
        self.bind('<Alt_L>', self.toggle_top_menu)
        self.bind('<Alt-Return>', self.make_fullscreen)
        self.bind('<F5>', self.start_CasePoll)

    def ttk_theme_changes(self):
        '''
        Container method to organize all Ttk theme changes used globally 
        throughout the UI.
        '''
        # Ttk Styles from here...
        self.def_font = tk_font.Font(
            family="Segoe UI", size=12, weight="normal", slant="roman")
        self.tab_font = tk_font.Font(
            family="Segoe UI", size=10, weight="bold", slant="roman")

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
        style.theme_use('default')
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
                        background="#212121",
                        activebackground="#313131",
                        foreground="white",
                        relief="flat")
        style.map("Custom.Treeview.Heading",
                    relief=[('active', 'flat'), ('pressed', 'flat')],
                    background=[('active', '#272822'), ('pressed', 'cyan')])
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
                background="#2B2B28", darkcolor="red", lightcolor="red",
                troughcolor="#161616", bordercolor="#161616", arrowcolor="#5E5E58",
                troughrelief='flat', borderwidth=1, relief='flat')
        style.map("Vertical.TScrollbar",
            background=[('disabled', "#101010")],
            arrowcolor=[('disabled', "#5E5E58")],
            relief=[('disabled', "flat")],
            troughrelief=[('disabled', "flat")],
        )
        style.configure("Horizontal.TScrollbar", gripcount=0,
                background="#2B2B28", darkcolor="red", lightcolor="red",
                troughcolor="#161616", bordercolor="#161616", arrowcolor="#5E5E58",
                troughrelief='flat', borderwidth=1, relief='flat')
        style.map("Horizontal.TScrollbar",
            background=[('disabled', "#101010")],
            arrowcolor=[('disabled', "#5E5E58")],
            relief=[('disabled', "flat")],
            troughrelief=[('disabled', "flat")],
        )

        # Defining the Notebook style colors for "Worktabs".
        myTabBarColor = "#10100B"
        myTabBackgroundColor = "#1D1E19"
        myTabForegroundColor = "#8B9798"
        myActiveTabBackgroundColor = "#414438"
        myActiveTabForegroundColor = "#FDFFD0" #"#FFE153"

        style.map("TNotebook.Tab", background=[("selected", myActiveTabBackgroundColor)], 
            foreground=[("selected", myActiveTabForegroundColor)], expand=[("selected", (0,1))]);
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
        
        #style.configure("TNotebook", background=myTabBarColor, borderwidth=0, bordercolor=myTabBarColor, focusthickness=40)
        style.configure("TNotebook", background='#1D1E19', borderwidth=0, bordercolor='red')
        style.configure("TNotebook.Tab", background=myTabBackgroundColor,
            foreground=myTabForegroundColor, lightcolor='#1D1E19',
            border=1, bordercolor='#11120F', font=self.tab_font)
        
        # DEFINING LOGVIEWER THEME
        # Defining the Notebook style colors for "Worktabs".
        logviewer_myTabBarColor = "#10100B"
        logviewer_myTabBackgroundColor = "#1D1E19"
        logviewer_myTabForegroundColor = "#8B9798"
        logviewer_myActiveTabBackgroundColor = 'cyan' #"#414438"
        logviewer_myActiveTabForegroundColor = "#FDFFD0" #"#FFE153"

        style.map("logveiwer.TNotebook.Tab", background=[("selected", logviewer_myActiveTabBackgroundColor)], 
            foreground=[("selected", myActiveTabForegroundColor)], expand=[("selected", (0,1))]);
        # Import the Notebook.tab element from the default theme
        style.element_create('Plain.Notebook.tab', "from", 'clam')
        # Redefine the TNotebook Tab layout to use the new element
        style.layout("logveiwer.TNotebook.Tab",
            [('Plain.Notebook.tab', {'children':
                [('Notebook.padding', {'side': 'top', 'children':
                    [('Notebook.focus', {'side': 'top', 'children':
                        [('Notebook.label', {'side': 'top', 'sticky': ''})],
                    'sticky': 'nswe'})],
                'sticky': 'nswe'})],
            'sticky': 'nswe'})])
        
        #style.configure("TNotebook", background=myTabBarColor, borderwidth=0, bordercolor=myTabBarColor, focusthickness=40)
        style.configure("logveiwer.TNotebook", background='#1D1E19', borderwidth=0, bordercolor='red')
        style.configure("logveiwer.TNotebook.Tab", background=myTabBackgroundColor,
            foreground=myTabForegroundColor, lightcolor='#1D1E19',
            border=1, bordercolor='#11120F', font=self.tab_font)

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

        # [Populate RootPane Panes]
        self.RootPane.vertical_pane.add(self.Workbench, 
            sticky='nsew', 
            hide=True, 
            stretch='always'
        )

        # [Intialize Sidebar Apps]
        self.RootPane.sidebar_pane.add_sidebar_app(Tk_CaseViewer,
            expand=True,
            active=True,
            title='CaseViewer', 
            container='frame',
            refresh_callback='sb_refresh' # Method found in TargetWidget
        )
        self.RootPane.sidebar_pane.add_sidebar_app(Tk_TodoList,
            expand=False,
            active=False, 
            title='TODO', 
            container='frame',
        )

        if render_caseviewer == "True":
            if caseviewer_pos == 'left':
                self.RootPane.vertical_pane.paneconfig(self.RootPane.sidebar_pane, hide=False, sticky='nsew')
                self.RootPane.vertical_pane.paneconfig(self.Workbench, hide=False, stretch='always')
            elif caseviewer_pos == 'right':
                # Resize Workbench First,
                self.MasterPane.update_idletasks()
                MasterPane_width = self.RootPane.horizontal_pane.winfo_width()
                Workbench_width = MasterPane_width - 300 #= default width
                self.RootPane.vertical_pane.paneconfig(self.Workbench, hide=False, width=Workbench_width, stretch='always')
                self.RootPane.vertical_pane.paneconfig(self.RootPane.sidebar_pane, hide=False, after=self.Workbench, sticky='nsew')
        elif render_caseviewer == "False":
            # Only render Workbench
            self.RootPane.vertical_pane.paneconfig(self.Workbench, hide=False)

        # [Top Menu] Enabled/Disabled
        if render_top_menu == 'True':
            self.config(menu=self.top_menu)
        elif render_top_menu == 'False':
            self.config(menu=self.empty_menu)

    def update_sidebar_pos(self, pos):
        # Now render based on pos and update DB.
        if pos == "left":
            self.RootPane.vertical_pane.paneconfigure(self.RootPane.sidebar_pane, 
                sticky='nsew', 
                width=300, 
                hide=False, 
                before=self.Workbench
            )
            bcamp_api.update_config('ui_caseviewer_location', 'left')
            bcamp_api.update_config('ui_render_caseviewer', 'True')   
        if pos == "right":
            MasterPane_width = self.RootPane.winfo_width()
            Workbench_width = MasterPane_width - 300 #= default width
            self.RootPane.vertical_pane.paneconfig(self.Workbench, 
                width=Workbench_width, 
                stretch='always'
            )
            self.RootPane.vertical_pane.paneconfigure(self.RootPane.sidebar_pane, 
                sticky='nsew', 
                width=300, 
                hide=False, 
                after=self.Workbench
            )
            bcamp_api.update_config('ui_caseviewer_location', 'right')
            bcamp_api.update_config('ui_render_caseviewer', 'True')
            # Resize self.Workbench

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

    def reveal_download_loc(self, event=None):
        '''
        Button and Keyboard Bind command to open the Root install location for
        Basecamp.
        '''
        RPATH = str(pathlib.Path(__file__).parent.absolute()
                    ).rpartition('\\')[0]
        os.startfile(RPATH + "\\downloads")

    def render_new_import(self, event=None):
        self.Workbench.import_tab()

    def toggle_sidebar(self, event=None):
        '''
        Button and Keyboard Bind command to toggle the CaseViewer Pane, on the
        left of the UI.
        '''
        if bcamp_api.get_config('ui_render_caseviewer') == "False":
            # Last setting was "hidden" - Render Caseviewer...
            if bcamp_api.get_config('ui_caseviewer_location') == 'left':
                self.RootPane.vertical_pane.paneconfig(self.RootPane.sidebar_pane, sticky='nsew', width=300, hide=False)
            elif bcamp_api.get_config('ui_caseviewer_location') == 'right':
                self.RootPane.vertical_pane.paneconfig(self.RootPane.sidebar_pane, sticky='nsew', width=300, hide=False, after=self.Workbench)
            # and update the DB
            bcamp_api.update_config('ui_render_caseviewer', "True")

        elif bcamp_api.get_config('ui_render_caseviewer') == "True":
            # Last Setting was "shown" - Remove Caseviewer...
            self.RootPane.vertical_pane.paneconfig(self.RootPane.sidebar_pane, hide=True)
            # and update DB.
            bcamp_api.update_config('ui_render_caseviewer', "False")

    def toggle_sidebar_search(self, event=None):
        '''
        Button and Keyboard Bind command to toggle the CaseViewer Pane, on the
        left of the UI.
        '''
        if bcamp_api.get_config('ui_render_caseviewer_search') == "False":
            # Update DB first as CaseViewer method reads from DB only.
            bcamp_api.update_config('ui_render_caseviewer_search', "True")
            # Last setting was "hidden" - Render Caseviewer Search...
            self.CaseViewer.update_search_pos()

        elif bcamp_api.get_config('ui_render_caseviewer_search') == "True":
            # Update DB first as CaseViewer method reads from DB only.
            bcamp_api.update_config('ui_render_caseviewer_search', "False")
            # Last Setting was "shown" - Remove Caseviewer Search...
            self.CaseViewer.update_search_pos()

    def toggle_top_menu(self, event=None):
        # Assigning top_menu to "master" Window
        if bcamp_api.get_config("ui_render_top_menu") == "False":
            self.config(menu=self.top_menu)
            bcamp_api.update_config('ui_render_top_menu', "True")
        else:
            empty_menu = tk.Menu(self)
            self.config(menu=empty_menu)
            bcamp_api.update_config('ui_render_top_menu', "False")

    def make_fullscreen(self, event=None):
        '''
        Makes the root TK window fullscreen.
        '''
        if self.w_fullscreen == False:
            self.w_fullscreen = True
            self.attributes('-fullscreen', True)
        elif self.w_fullscreen == True:
            self.w_fullscreen = False
            self.attributes('-fullscreen', False)

    def start_CasePoll(self, event=None):
        self.CasePoll.start_manual_poll()
    
    # Case Import/Export methods
    def import_handler(self, new_import_data):
        '''
        This method is called whenever "Gui.import_item" is modified. The
        expected input is a dictionary with the following syntax...

        new_import_data Schema: 
            {
            'type': --> 'single', 'bulk', 'backup'
            'case_data': --> {}, [{}]
            }

        Example case_data dictionary:
            {
                'sr_number': sr_number,
                'tags_list': tags_list,
                'account_string': account_string,
                'customs_list': customs_list,
                'product_string': product_string,
                'workspace_string': workspace_string,
                'important_bool': important_bool,
                'download_flag': 0 or 1
            }

        If this is the first time a user has imported a SR Number. This will 
        only store the inital CaseData Object for 'new_value'. 

        If 'new_value' is an SR number that exist within CaseData, 'new_value'
        is simply passed to the intialized "Tk_Workspace.new_tab" method.
        '''        
        # Pass 'new_import_data' to ImportDaemon for handling.
        _type = new_import_data['type']
        _case_data_lst = new_import_data['case_data']
        print('UI import_handler called!')
        self.ImportDaemon.add_import(_type, _case_data_lst)

    def export_cases_backup(self, event=None):
        bcamp_api.export_cases_backup()

    def import_cases_backup(self, event=None):
        bcamp_api.import_cases_backup(self)

    def export_bulk_import_file(self, event=None):
        bcamp_api.export_bulk_import_file()

    def launch_bulk_importer(self, event=None):
        bcamp_api.bulk_importer(Gui.import_item)

    # At Exit Method
    def on_exit(self):
        # Flush Environment Var
        print("Cleaning up...")
        os.environ['BCAMP'] = 'null'


'''Basecamp Settings Tk/Tcl TopLevel Frame'''
class Tk_SettingsMenu(tk.Toplevel):
    '''
    This is the UI menu where users can update the config DB file,
    which contains various CONSTANTS and variables used throughout 
    the Application.
    '''

    def __init__(self, event=None):
        super().__init__()
        self.title("Basecamp Settings")
        #self.attributes('-topmost', 'true')
        self.resizable(False, False)
        self.mode_str = tk.StringVar()
        self.selected_menu = tk.IntVar()

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
        self.general_menu = tk.Button(
            self.base_btn_frame,
            text="General Settings        ▷",
            anchor='center',
            command=self.render_general_settings,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.automations_menu = tk.Button(
            self.base_btn_frame,
            text="Automations             ▷",
            anchor='center',
            command=self.render_automations,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.parsing_menu = tk.Button(
            self.base_btn_frame,
            text="Parsing Rules            ▷",
            anchor='center',
            command=self.render_parsing_rules,
            width=30,
            relief='flat',
            background='#212121',
            foreground='#f5f5f5'
        )
        self.dev_mode_label = tk.Label(
            self.base_btn_frame,
            textvariable=self.mode_str,
            background="#111111",
            foreground="#525258"
        )
        self.dev_mode_label.bind('<Control-Button-3>', self.enable_dev_mode)

    def config_grid(self):
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(4, weight=1)
        self.columnconfigure(1, weight=1)
        # Btn Frame Config
        self.base_btn_frame.grid(
            row=0, column=0, padx=3, pady=5, sticky="nsew")
        self.general_menu.grid(row=0, column=0, padx=1, pady=1, sticky='ew')
        self.automations_menu.grid(
            row=2, column=0, padx=1, pady=1, sticky='ew')
        self.parsing_menu.grid(
            row=3, column=0, padx=1, pady=1, sticky='ew')
        self.dev_mode_label.grid(
            row=4, column=0, padx=3, pady=3, sticky="sw")
        # Menu Frame Config
        # Row and Column config found in Nested Frame class...
        self.base_menu_frame.grid(
            row=0, column=1, padx=3, pady=5, sticky="nsew")

    def render_general_settings(self):
        # self.base_menu_frame()
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_General(self.base_menu_frame)

    def render_automations(self):
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_Automations(self.base_menu_frame)

    def render_parsing_rules(self):
        for child in self.base_menu_frame.winfo_children():
            child.destroy()
        self.Tk_ParsingRules(self.base_menu_frame)

    def get_mode(self):
        '''
        Sets DevMode string in UI
        '''
        if bcamp_api.get_config('dev_mode') == "True":
            self.mode_str.set("DevMode 😈")
        else:
            self.mode_str.set("Howdy, Engineer 😎")

    def enable_dev_mode(self, event=None):
        '''
        Toggle method to enable or disable dev mode. 
        '''
        if bcamp_api.get_config('dev_mode') == "True":
            bcamp_api.set_devMode(False)
            self.mode_str.set("Howdy, Engineer 😎")

        elif bcamp_api.get_config('dev_mode') == "False":
            # Configuring extra params for DevMode - See API.
            bcamp_api.set_devMode(True)
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


    class Tk_General(tk.Frame): 
        '''
        Paths Setting Menu Frame for Remote and Local Paths
        '''
        def __init__(self, master):
            super().__init__()
            self.master = master
            RPATH = str(pathlib.Path(__file__).parent.absolute()
                        ).rpartition('\\')[0]
            self.remote_strVar = tk.StringVar()
            self.remote_strVar.set(bcamp_api.get_config('remote_root'))
            self.local_strVar = tk.StringVar()
            self.local_strVar.set(bcamp_api.get_config('download_root'))
            self.notepad_strVar = tk.StringVar()
            self.notepad_strVar.set(bcamp_api.get_config('notepad_path'))
            self.def_notepad_strVar = tk.StringVar()
            self.def_notepad_strVar.set(bcamp_api.get_config('user_texteditor'))

            # Tk Methods
            self.config_widgets()
            self.config_grid()

        def config_widgets(self):
            self.basebg = "#303030"
            self.basefg = "#f5f5f5"
            self.entry_bg = "#10100B"
            self.entry_fg = "#f5f5f5"

            # [Notepad Options]
            self.notepad_opts_frame = tk.LabelFrame(
                self.master,
                text='Default Text Editor',
                background=self.basebg,
                foreground=self.basefg
            )
            ### default notepad user pref
            self.def_notepad_label = tk.Label(
                self.notepad_opts_frame,
                text="Default Text Editor",
                background=self.basebg,
                foreground=self.basefg,
                anchor="w"
            )
            self.def_notepad_spinbox = tk.Spinbox(
                self.notepad_opts_frame,
                values=('Logviewer', 'Notepad++', 'Windows Default'),
                width=65,
                relief='flat',
                buttondownrelief='flat',
                buttonuprelief='flat',
                background=self.entry_bg,
                foreground=self.entry_fg,
                buttonbackground="#111111",
                justify="center",
                textvariable=self.def_notepad_strVar
            )
            ### notepad++ path to exe
            self.notepad_label = tk.Label(
                self.notepad_opts_frame,
                text="Notepad++ Path",
                background=self.basebg,
                foreground=self.basefg,
                anchor="w"
            )
            self.notepad_entry = tk.Entry(
                self.notepad_opts_frame,
                width=70,
                relief='flat',
                textvariable=self.notepad_strVar,
                background=self.entry_bg,
                foreground=self.entry_fg
            )
            self.notepad_browse = tk.Button(
                self.notepad_opts_frame,
                text="Browse",
                command=self.notepad_browser,
                relief='flat',
                background=self.entry_bg,
                foreground=self.entry_fg,
            )

            # [Main Paths]
            self.main_path_frame = tk.LabelFrame(
                self.master,
                text="Root Paths",
                background=self.basebg,
                foreground=self.basefg
            )
            self.local_label = tk.Label(
                self.main_path_frame,
                text="Local Downloads (Path)",
                background=self.basebg,
                foreground=self.basefg,
                anchor="w"
            )
            self.local_entry = tk.Entry(
                self.main_path_frame,
                width=70,
                relief='flat',
                textvariable=self.local_strVar,
                background="#222222",
                foreground='#f5f5f5'
            )
            self.local_browse = tk.Button(
                self.main_path_frame,
                text="Browse",
                command=self.explorer_browser,
                background=self.entry_bg,
                foreground=self.entry_fg,
                relief='flat'
            )
            self.remote_label = tk.Label(
                self.main_path_frame,
                text="Network Folder (Path) - Fixed Value",
                background=self.basebg,
                foreground=self.basefg,
                anchor="w"
            )
            self.remote_entry = tk.Entry(
                self.main_path_frame,
                width=70,
                textvariable=self.remote_strVar,
                state='disabled',
                background="#222222",
                foreground='#f5f5f5'
            )
            self.remote_browse = tk.Button(
                self.main_path_frame,
                text="Browse",
                command=self.r_explorer_browser,
                relief='flat',
                background=self.entry_bg,
                foreground=self.entry_fg,
                state='disabled'
            )

            # [BottomBar]
            self.bbar_frame = tk.Frame(
                self.master,
                background=self.basebg,
            )
            self.spacer = tk.Label(
                self.bbar_frame,
                text="You shouldnt see this message... :)",
                background="#303030",
                foreground="#303030",
            )
            self.save_bar = tk.Frame(
                self.bbar_frame,
                background="#111111"
            )
            self.save_btn = tk.Button(
                self.bbar_frame,
                text="Save and Apply",
                background='#badc58',
                foreground='#111111',
                relief="flat",
                command=self.save_settings
            )

        def config_grid(self):
            # [Notepad Options]
            self.notepad_opts_frame.grid(
                row=1, column=0, padx=3, pady=10, sticky='nsew'
            )
            self.notepad_opts_frame.grid_columnconfigure(1, weight=1)
            self.def_notepad_label.grid(
                row=0, column=0, padx=3, pady=3, sticky='nsew'
            )
            self.def_notepad_spinbox.grid(
                row=1, column=0, columnspan=2, padx=3, pady=3, sticky='nsew'
            )
            self.notepad_label.grid(
                row=2, column=0, padx=3, pady=3, sticky='nsew')
            self.notepad_entry.grid(
                row=3, column=0, padx=3, pady=2, ipady=2, sticky='new')
            self.notepad_browse.grid(
                row=3, column=1, padx=3, pady=0, sticky='new')
            
            # [Main Paths]
            self.main_path_frame.grid(
                row=2, column=0, padx=3, pady=10, sticky='nsew'
            )
            self.main_path_frame.grid_columnconfigure(1, weight=1)
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
            
            # [BottomBar]
            self.bbar_frame.grid(
                row=4, column=0, sticky='nsew'
            )
            self.bbar_frame.grid_columnconfigure(0, weight=1)
            self.spacer.grid(row=0, column=0, columnspan=2, sticky="nsew")
            self.save_bar.grid(row=1, column=0, columnspan=2, pady=(20,0), sticky="nsew")
            self.save_bar.columnconfigure(0, weight=1)
            self.save_btn.grid(row=1, column=0, padx=1, pady=(20,0), sticky='e')

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

        def notepad_browser(self):
            filename = filedialog.askdirectory(
                initialdir="/",
                title="Select the Notepad++.exe",
            )
            print("New path> ", filename)
            self.notepad_strVar.set(filename)

        def clear_widgets(self):
            self.remote_label.grid_forget()
            self.remote_entry.grid_forget()
            self.remote_browse.grid_forget()
            self.local_label.grid_forget()
            self.local_entry.grid_forget()
            self.local_browse.grid_forget()

        def save_settings(self):
            '''
            Updates DB values based on values stored in this menu.
            '''
            ### Notepad Default User Preference.
            # Get value of spinbox.
            def_notepad = self.def_notepad_spinbox.get()
            # Utilize API to update DB.
            bcamp_api.update_config('user_texteditor', def_notepad)


    class Tk_ParsingRules(tk.Frame):
        '''
        Menu to modify user-defined parsing rules for the "SimpleParser" 
        '''
        def __init__(self, master):
            super().__init__()
            self.master = master
            self.new_rule_frame_open = False
            self.refresh_tree_callback = bcamp_api.callbackVar()
            self.refresh_tree_callback.register_callback(self.update_ar_tree)
            self.total_rule_cnt = 0

            # Tk Methods
            self.config_widgets()
            self.config_grid()
            self.config_binds()
            self.update_ar_tree()

        def config_widgets(self):
            # [Active Rules Table]
            self.ar_frame = tk.Frame(
                self.master,
                background="#303030"
            )
            self.ar_label = tk.Label(
                self.master,
                text="Active Parsing Rules",
                background="#303030",
                foreground="#FFFFFF"
            )
            self.ar_tree = ttk.Treeview(
                self.ar_frame,
            )
            self.ar_tree_ysb = ttk.Scrollbar(
                self.ar_frame,
                orient='vertical',
                command=self.ar_tree.yview
            )
            self.ar_tree.configure(yscrollcommand=self.ar_tree_ysb)

            self.new_rule_btn = tk.Button(
                self.ar_frame,
                text="New Rule +",
                command=self.render_new_rule_config
            )
            self.import_rules_btn = tk.Button(
                self.ar_frame,
                text="Import Ruleset"
            )
            self.export_rules_btn = tk.Button(
                self.ar_frame,
                text="Export Ruleset"
            )

            # [Active Rules Tree Config]
            self.ar_tree.configure(
                height=20,
                style="Custom.Treeview",
                columns=('Type', 'Return', 'Target File', 'Rule Definition'),
                displaycolumns=('Type', 'Return', 'Target File', 'Rule Definition'),
                selectmode='browse',
            )
            self.ar_tree.column('#0', width=0, stretch=False)
            self.ar_tree.heading('Type', text="Type")
            self.ar_tree.heading('Return', text="Return", anchor='center')
            self.ar_tree.heading('Target File', text="Target File", anchor='center')
            self.ar_tree.heading('Rule Definition', text="Rule Definition", anchor='center')

            # [RightClick Menu]
            self.rc_menu = tk.Menu(
                self,
                bg="#272822",
                fg="#ffffff",
                tearoff=False
            )
            self.rc_menu.add_command(
                label="Edit Rule",
                command=self.edit_rule
            )
            self.rc_menu.add_command(
                label="Delete Rule",
                command=self.delete_rule
            )

        def config_grid(self):
            # [Active Rules Frame]
            self.ar_frame.grid(row=1, column=0, sticky="nsew")
            #self.ar_frame.rowconfigure(3, weight=0) 
            self.ar_label.grid(row=0, column=0, pady=5, sticky="nsew")
            self.ar_tree.grid(row=1, column=0, columnspan=2, rowspan=2, sticky="nsew")
            self.ar_tree_ysb.grid(row=1, column=2, rowspan=2, sticky="nse")
            self.new_rule_btn.grid(row=4, column=0, sticky="sw", padx=4, pady=4)
            #self.import_rules_btn.grid(row=2, column=1, sticky="nsew")
            #self.export_rules_btn.grid(row=2, column=2, sticky="nsew")

        def config_binds(self):
            self.ar_tree.bind("<ButtonRelease-3>", self.rc_popup)

        def rc_popup(self, event):
            """action in event of button 3 on tree view"""
            # select row under mouse
            iid = self.ar_tree.identify_row(event.y)
            if iid:
                # mouse pointer over item
                self.ar_tree.selection_set(iid)
                self.rc_menu.post(
                    event.x_root + 10, event.y_root + 10)
            else:
                # mouse pointer not over item
                # occurs when items do not fill frame
                # no action required
                pass

        def get_rulesets(self):
            '''
            Queries the DB for the parsing rules, and updates the 
            'total_rule_count' var for new rules!
            '''
            parser_ruleset = bcamp_api.dump_parser()

            # Updating total_rule_cnt value for new rule gen
            self.total_rule_cnt = 0
            for rule in parser_ruleset:
                self.total_rule_cnt += 1
            
            return parser_ruleset

        def save_settings(self):
            '''
            Takes configured rulesets and updates the DB.
            '''
            pass

        def render_new_rule_config(self):
            config_menu = self.Rule_Config_Menu(self.ar_frame, 'new', self)
            config_menu.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=2, pady=(0,5))
        
        def update_ar_tree(self, callback_var=None):
            '''
            Called when the self.refresh_tree_callback var is modified. This
            method renders the available rules from the DB into the active
            rules tree
            '''
            print("$update_ar_tree CALLED")
            # Call 'get_rulesets' to get new DB dump, and update
            # the total_rule_cnt val for new rules 
            p_rules = self.get_rulesets()
            # Iteratate through Parser rules dict to populate ar tree.
            for rule in p_rules:
                try:
                    self.ar_tree.insert('', 
                        'end', 
                        iid=rule,
                        values=(
                            p_rules[rule]['type'],
                            p_rules[rule]['return'],
                            p_rules[rule]['target'], 
                            p_rules[rule]['rule']),
                        #tags=(_tag)
                        )
                except tk.TclError:
                    pass

        def edit_rule(self):
            ruleid = self.ar_tree.selection()[0]
            config_menu = self.Rule_Config_Menu(self.ar_frame, ruleid, self)
            config_menu.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=2, pady=(0,5))            

        def delete_rule(self):
            # Remove item from tree
            ruleid = self.ar_tree.selection()[0]
            print(ruleid)
            self.ar_tree.delete(ruleid)
            # Remove item from DB
            bcamp_api.del_parser_rule(ruleid)


        class Rule_Config_Menu(tk.Frame):
            '''
            Template of widgets to create a "new" row/rule or to edit an
            exisiting rule.
            '''
            def __init__(self, master, rule_id, ParserMenu):
                super().__init__(master=master)
                self.master = master
                self.rule_id = rule_id
                self.ParserMenu = ParserMenu

                # Defining Tk Vars
                self.id_strVar = tk.StringVar()
                self.type_strVar = tk.StringVar()
                self.return_strVar = tk.StringVar()
                self.target_strVar = tk.StringVar()
                self.rule_strVar = tk.StringVar()

                self.set_vars()
                self.config_widgets()
                self.config_grid()

            def config_widgets(self):
                self.config(bg="#444444")
                self.top_frame = tk.Frame(
                    self,
                    bg="#272822"
                )
                self.top_label_frame = tk.Frame(
                    self.top_frame,
                    bg='#272822',
                )
                self.top_label = tk.Label(
                    self.top_label_frame,
                    text="Configuring ->",
                    bg='#272822',
                    fg='#717463',
                    relief='flat'
                )
                self.id_label = tk.Label(
                    self.top_label_frame,
                    textvariable=self.id_strVar,
                    bg='#272822',
                    fg='#717463',
                    relief='flat'
                )
                self.exit_menu_btn = tk.Button(
                    self.top_frame,
                    text="X",
                    command=self.close_menu,
                    bg='#272822',
                    fg='#717463',
                    relief='flat'
                )
                self.mid_frame = tk.Frame(
                    self,
                    bg="#444444"
                )

                self.type_label = tk.LabelFrame(
                    self.mid_frame,
                    text="Type:",
                    bd=0,
                    bg="#444444",
                    fg="#FFFFFF"
                )
                self.type_spinbox = tk.Spinbox(
                    self.type_label,
                    values=('LINE', 'KEYWORD', 'REGEX'),
                    textvariable=self.type_strVar
                )
                self.return_label = tk.LabelFrame(
                    self.mid_frame,
                    text="Return:",
                    bd=0,
                    bg="#444444",
                    fg="#FFFFFF"
                )
                self.return_spinbox = tk.Spinbox(
                    self.return_label,
                    values=('ALL', 'FIRST'),
                    textvariable=self.return_strVar
                )
                self.target_label = tk.LabelFrame(
                    self.mid_frame,
                    text="Target File:",
                    bd=0,
                    bg="#444444",
                    fg="#FFFFFF"
                )
                self.target_entry = tk.Entry(
                    self.target_label,
                    width=68,
                    textvariable=self.target_strVar
                )
                self.bottom_frame = tk.Frame(
                    self,
                    bg="#444444"
                )

                self.rule_label = tk.LabelFrame(
                    self.bottom_frame,
                    text="Rule Definition:",
                    bd=0,
                    bg="#444444",
                    fg="#FFFFFF"
                )
                self.rule_entry = tk.Entry(
                    self.rule_label,
                    width=126,
                    textvariable=self.rule_strVar
                )
                self.add_button = tk.Button(
                    self.bottom_frame,
                    text="Save Rule",
                    bg="#badc58",
                    fg="#111111",
                    command=self.update_ruleset,
                    relief='flat'  
                )
        
            def config_grid(self):
                #self.ruleid_label.grid(row=0, column=0)0
                self.columnconfigure(0, weight=1)
                self.top_frame.grid(row=0, column=0, sticky='nsew')
                self.top_frame.columnconfigure(0, weight=1)
                self.top_label_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsw')
                self.top_label.grid(row=0, column=0)
                self.id_label.grid(row=0, column=1)
                self.exit_menu_btn.grid(row=0, column=1, padx=5, pady=5, sticky='nse')
                self.mid_frame.grid(row=1, column=0, sticky='nsew', pady=4)
                self.type_label.grid(row=0, column=0, padx=10)
                self.type_spinbox.grid(row=0, column=0, padx=10, pady=10)
                self.return_label.grid(row=0, column=1, padx=10)
                self.return_spinbox.grid(row=0, column=0, padx=10, pady=10)
                self.target_label.grid(row=0, column=2, padx=10)
                self.target_entry.grid(row=0, column=0, padx=10, pady=10)
                self.bottom_frame.grid(row=2, column=0, sticky='nsew')
                self.bottom_frame.columnconfigure(0, weight=1)                
                self.rule_label.grid(row=0, column=0, sticky='w', padx=10)
                self.rule_entry.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
                self.add_button.grid(row=2, column=0, sticky='e', padx=10)

            def set_vars(self):
                if self.rule_id != 'new':
                    # Get values for ruleID from DB.
                    self.id_strVar.set(self.rule_id)
                    self.type_strVar.set(
                        bcamp_api.query_parser(self.rule_id, 'type'))
                    self.return_strVar.set(
                        bcamp_api.query_parser(self.rule_id, 'return'))
                    self.target_strVar.set(
                        bcamp_api.query_parser(self.rule_id, 'target'))
                    self.rule_strVar.set(
                        bcamp_api.query_parser(self.rule_id, 'rule'))
                else:
                    self.id_strVar.set("NEW RULE*")
                    self.type_strVar.set('line')
                    self.return_strVar.set('all')
                    self.target_strVar.set('')
                    self.rule_strVar.set('')

            def close_menu(self):
                '''
                Exit function to remove the config menu from the UI
                '''
                self.destroy()
            
            def update_ruleset(self):
                '''
                When a user either saves a new parsing rule, or edits a rule 
                in the Setting menu, this method is called by the "Save Rule"
                button being pressed.
                '''
                print("$updating ruleset")
                ruleid = self.id_strVar.get()
                newRule = False
                # Exception for new rules...
                if ruleid == "NEW RULE*":
                    print("$max", bcamp_api.get_max_prule())
                    # Calculate new rule_id from 'ParserMenu.total_rule_cnt'
                    if bcamp_api.get_max_prule() == None: # No rules in DB yet...
                        ruleid_index = -1
                    else:
                        ruleid_index = bcamp_api.get_max_prule()
                    newRule = True
                    ruleid = (int(ruleid_index) + 1)

                new_rule_dict = {
                    'id': ruleid,
                    'type': self.type_strVar.get(),
                    'return': self.return_strVar.get(),
                    'target': self.target_strVar.get(),
                    'rule': self.rule_strVar.get(),
                    }
                print("$new_rule_dict", new_rule_dict)

                if newRule:
                    # Updating DB with new rule!
                    bcamp_api.create_parser_rule(new_rule_dict)
                elif newRule == False:
                    bcamp_api.update_parser_rule(ruleid, new_rule_dict)

                # Triggering Callback method to refresh Active Rules Tree.
                self.ParserMenu.refresh_tree_callback.value = True


    class Tk_Automations(tk.Frame):
        '''
        Configure the Enabled "Automations" found in "extension/automations"
        and update the config DB file for newly enabled modules.
        '''
        def __init__(self, master):
            super().__init__()
            # Defining Vars
            self.master = master
            self.RPATH = str(pathlib.Path(
                __file__).parent.absolute()).rpartition('\\')[0]
            self.enable_bar_str = tk.StringVar()
            self.info_str = tk.StringVar()
            self.extension_str = tk.StringVar()
            self.author_str = tk.StringVar()
            self.save_data = {}

            # Rendering UI elements
            self.config_widgets()
            self.config_grid()
            # Populate UI based on DB record. 
            self.fill_automation_list()
            self.fill_enabled_list()

        def config_widgets(self):
            # Defining Fonts 
            def_font = tk_font.Font(
                family="Segoe UI", size=11, weight="normal", slant="roman")
            bold_mini_font = tk_font.Font(
                family="Segoe UI", size=10, weight="bold", slant="roman")
            bold_font = tk_font.Font(
                family="Segoe UI", size=12, weight="bold", slant="roman")

            self.lframe_automations = tk.LabelFrame(
                self.master,
                text="Disable/Enable Automations",
                bg="#444444",
                fg="#ffffff",
                padx=5,
                pady=5,
                font=bold_font
            )
            self.automation_listbox = tk.Listbox(
                self.lframe_automations,
                width=40,
                selectmode=tk.SINGLE,
                relief="flat",
                bg="#202020",
                fg="#ffffff",
                highlightthickness=0,
                font=def_font
            )
            self.automation_listbox.bind(
                '<<ListboxSelect>>', self.get_selected_info)
            
            self.enable_bar = tk.Button(
                self.lframe_automations,
                textvariable=self.enable_bar_str,
                background='#939393',
                foreground='#111111',
                relief="flat",
                command=self.toggle_automation,
            )
            self.enabled_listbox = tk.Listbox(
                self.lframe_automations,
                width=40,
                relief="flat",
                selectmode=tk.SINGLE,
                bg="#202020",
                fg="#ffffff",
                highlightthickness=0,
                font=def_font
            )
            self.enabled_listbox.bind(
                '<<ListboxSelect>>', self.get_selected_info
            )

            # Automation Details Frame
            self.lframe_info = tk.LabelFrame(
                self.master,
                text="",
                bg="#272822",
                fg="#ffffff",
                font=bold_font
            )
            self.label_info = tk.Label(
                self.lframe_info,
                text="Description:",
                anchor='w',
                bg="#272822",
                fg="#ffffff",
                font=bold_font
            )
            self.info_text = tk.Label(
                self.lframe_info,
                textvariable=self.info_str,
                width=40,
                wraplength=250,
                justify=tk.LEFT,
                bg="#272822",
                fg="#ffffff",
                font=def_font
            )
            self.label_extensions = tk.Label(
                self.lframe_info,
                text="Supported File Types:",
                anchor='w',
                bg="#272822",
                fg="#ffffff",
                font=bold_font
            )
            self.extensions_text = tk.Label(
                self.lframe_info,
                textvariable=self.extension_str,
                justify=tk.CENTER,
                bg="#272822",
                fg="#ffffff",
                font=def_font
            )
            self.label_author = tk.Label(
                self.lframe_info,
                text="Created By:",
                anchor='w',
                bg="#272822",
                fg="#ffffff",
                font=bold_font
            )
            self.author_text = tk.Label(
                self.lframe_info,
                textvariable=self.author_str,
                bg="#272822",
                fg="#ffffff",
                font=def_font
            )
            self.user_options_frame = tk.LabelFrame(
                self.lframe_info,
                bg="#272822",
                fg="#FFFFFF",
                text="User-Defined Options: ",
                padx=10,
                pady=10,
                font=bold_mini_font
            )

            # Bottom Bar Content.
            self.save_bar = tk.Frame(
                self.master,
                background='#212121',
            )
            self.open_folder_btn = tk.Button(
                self.save_bar,
                text="Open Automations Folder",
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
            self.info_text.grid(row=1, column=0, rowspan=3, sticky='nsw')
            self.label_extensions.grid(row=0, column=1, sticky='w')
            self.extensions_text.grid(row=1, column=1, sticky='nsw')
            self.label_author.grid(row=2, column=1, sticky='w')
            self.author_text.grid(row=3, column=1, sticky='nsw')
            self.user_options_frame.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=(15,0))
            self.user_options_frame.columnconfigure(0, weight=1)
            self.user_options_frame.grid_remove() # Keep hidden until needed.

            # SaveBar
            self.save_bar.grid(row=8, column=0, ipady=2, sticky="sew")
            self.save_bar.columnconfigure(0, weight=1)
            self.open_folder_btn.grid(row=0, column=0, padx=3, pady=1, sticky='e')
            self.save_btn.grid(row=0, column=1, padx=3, pady=1, sticky='e')

        def refresh_automations_list(self):
            '''
            Calls bcamp_api.Automations.get() to get a new list of available
            Automations that compile successfully and contain the correct file
            format.
            '''
            new_avail_autos = self.api_automations.get()
            print("$get_auto_list", new_avail_autos)
            return new_avail_autos

        def fill_automation_list(self):
            result = bcamp_api.get_automations()
            for item in result[1]:
                self.automation_listbox.insert(tk.END, item)

        def fill_enabled_list(self):
            result = bcamp_api.get_automations()
            for item in result[0]:
                self.enabled_listbox.insert(tk.END, item)

        def get_selected_info(self, event):
            '''
            This method is called, EVERYTIME an Automation is selected in 
            either in the enabled or disabled tree. This is responsible for
            populating the default 'info', 'extension' and 'description'
            fields based on values from in the DB (generated when auto. is 
            first seen on launch.)

            This method ALSO get the details of external EXE's needed for this
            automation to work (if any) to allow these paths to be defined
            within the UI. The results are passed to the "ren_exe_widgets()"
            methods to actually draw the UI elements to allow these paths to 
            be adjusted.
            '''
            # Configure Middle-bar arrow direction
            if self.automation_listbox.curselection() != ():
                selected = self.automation_listbox.get(
                    self.automation_listbox.curselection())
                self.enable_bar_str.set(">")
            elif self.enabled_listbox.curselection() != ():
                selected = self.enabled_listbox.get(
                    self.enabled_listbox.curselection())
                self.enable_bar_str.set("<")

            # Populate detail menus for 'selected'
            self.info_str.set(bcamp_api.query_automation(selected, 'description'))
            self.extension_str.set(bcamp_api.query_automation(selected, 'extensions'))
            self.author_str.set(bcamp_api.query_automation(selected, 'author'))

            # Get Automation User-Defined details
            b_user_opts_list = bcamp_api.query_automation(selected, 'user_options')
            py_user_opts_list = pickle.loads(b_user_opts_list) # convert Bin -> Py list
            self.ren_user_opts_widgets(selected, py_user_opts_list)

        def ren_user_opts_widgets(self, target_auto, exe_list):
            '''
            Iterating through the exe_list for a selected automation (provided
            by the "get_selected_info()" method) this method actually renders
            the "exe" sub menu in the UI.

            'exe_list' format > [{"name":"X_TOOL", "path":c:\pathto\exe"}, etc.]
                'name' = The UI string to represent this path.
                'path' = The path to the target exe to be used by the auto.

            * There can be multiple exe's in the list.
            '''
            # Clear the child_widgets before rendering new content.
            if exe_list != None:
                self.user_options_frame.grid()
                for child in self.user_options_frame.winfo_children():
                    child.destroy()
            elif exe_list == None:
                self.user_options_frame.grid_remove()

            # Check if exe-list is None
            if exe_list != None:
                # Iterate through exe_list
                row = 0 # used for Grid manager in the EXE template.
                #print("$.exe_lst", exe_list)
                for exe_spec in exe_list:
                    # Check User-Option Type here...
                        # >> Render Path Template.
                    if list(exe_spec)[1] == 'path':
                        # Render UI element under the 'user_options_frame'
                        self.Path_template(self.user_options_frame, target_auto, exe_spec['name'],
                            exe_spec['path'], row, exe_list)
                        # >> Render String Template.
                    if list(exe_spec)[1] == 'string':
                        # Render UI element under the 'user_options_frame'
                        self.String_template(self.user_options_frame, target_auto, exe_spec['name'],
                            exe_spec['string'], row, exe_list)                                
                    # Increment row by 1.
                    row += 1
            
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
            os.startfile(automation_dir_path)

        def save_settings(self):
            '''
            Based on the settings configured for the Automations in the
            'Enabled' Listbox on the right, these values are updated within
            the 'bcamp_automations' table in the DB.
            '''
            # Get current items in 'enabled list' and 'disabled list'.
            enabled_items = self.enabled_listbox.get(0, tk.END)
            disabled_items = self.automation_listbox.get(0, tk.END)
            # Update the DB 'enabled' value for each enabled_item.
            for item in enabled_items:
                bcamp_api.update_automation(item, 'enabled', "True")
            # And Update the column for the Disabled items.
            for item in disabled_items:
                bcamp_api.update_automation(item, 'enabled', "False")

        def direct_import_broswer(self):
            filename = filedialog.askopenfilename(
                initialdir="/",
                title="Select a target .exe",
            )
            return filename


        class Path_template(tk.Frame):
            '''
            Template class rendered for EACH exe defined for a selected 
            automation - allowing users to update paths for needed external
            applications within the UI.
            '''
            def __init__(self, master_frame, target_auto, path_name, path_string, row, exe_list):
                super().__init__(master=master_frame)
                self.target_auto = target_auto
                self.path_name = path_name
                self.path_string = path_string
                self.exe_list = exe_list # list passed for saving changes.
                self.row = row
                self.path_strVar = tk.StringVar()
                self.path_strVar.set(self.path_string)

                self.config_widgets()
                self.config_grid()
            
            def config_widgets(self):
                # Defining Fonts
                def_font = tk_font.Font(
                    family="Segoe UI", size=10, weight="normal", slant="roman")
                bold_font = tk_font.Font(
                    family="Segoe UI", size=10, weight="bold", slant="roman")

                self.configure(bg="#272822")
                self.name_label = tk.LabelFrame(
                    self,
                    text = self.path_name,
                    bg="#272822",
                    fg="#FFFFFF",
                    padx=5,
                    pady=5,
                    font=bold_font
                )
                self.path_entry = tk.Entry(
                    self.name_label,
                    textvariable=self.path_strVar,
                    bg="#101010",
                    fg="#FFFFFF",
                    font=def_font,
                    insertbackground="#FFFFFF"
                )
                self.browse_button = tk.Button(
                    self.name_label,
                    text="Browse",
                    command=self.explorer_browser,
                    bg="#717463",
                    fg="#101010",
                    relief='flat',
                    font=bold_font
                )
                self.save_button = tk.Button(
                    self.name_label,
                    text="Save",
                    bg="#717463",
                    fg="#101010",
                    relief='flat',
                    font=bold_font,
                    command=self.save_to_db,
                )

            def config_grid(self):
                # Allow root frame to expand to full *WIDTH*
                #self.columnconfigure(0, weight=1)
                
                # Defining Widget grid
                self.grid(row=self.row, column=0, sticky='ew')
                self.columnconfigure(0, weight=1)
                self.name_label.columnconfigure(0, weight=1)
                self.name_label.grid(row=0, column=0, pady=2, sticky="nsew")
                self.path_entry.grid(row=0, column=0, padx=2, sticky="nsew")
                self.browse_button.grid(row=0, column=1, padx=2, sticky="nse")
                self.save_button.grid(row=0, column=2, padx=2, sticky="nse")

            def flash_entry(self):
                '''
                Called when a user attempts to save a path value that is not
                accessable. This flashes the background of the entry field red
                to motivate users to update the value.
                '''
                def set_red():
                    self.path_entry['bg'] = 'red'
                
                def set_norm():
                    self.path_entry['bg'] = '#101010'

                self.after(000, set_red)
                self.after(100, set_norm)
                self.after(200, set_red)
                self.after(300, set_norm)
                self.after(400, set_red)
                self.after(500, set_norm)

            def explorer_browser(self):
                filename = filedialog.askopenfilename(
                    initialdir=self.path_string,
                    title=("Basecamp Automations - " + self.path_name + " Path"),
                )
                print("$$auto New path> ", os.path.abspath(filename))
                self.path_strVar.set(os.path.abspath(filename))

            def save_to_db(self):
                '''
                Saves the current self.path_strVar to the DB for the
                target automation.
                '''
                # First, test if path exist.
                if os.access(self.path_strVar.get(), os.R_OK):
                    realpath = True
                elif not os.access(self.path_strVar.get(), os.R_OK):
                    realpath = False
                
                if realpath:
                    # Create NEW automation exe list
                    updated_exe_list = self.exe_list
                    updated_exe_list[self.row] = {
                        'name':self.path_name, 
                        'path':self.path_strVar.get()
                        }
                    # Convert updated_exe_list to binary object w/ pickle.
                    b_updated_exe_list = pickle.dumps(updated_exe_list)
                    bcamp_api.update_automation(self.target_auto, 'user_options', b_updated_exe_list)
                if not realpath:
                    self.flash_entry()


        class String_template(tk.Frame):
            '''
            Template class rendered for EACH exe defined for a selected 
            automation - allowing users to update paths for needed external
            applications within the UI.
            '''
            def __init__(self, master_frame, target_auto, string_name, string_var, row, string_lst):
                super().__init__(master=master_frame)
                self.target_auto = target_auto
                self.string_name = string_name
                self.string_var = string_var
                self.string_lst = string_lst # list passed for saving changes.
                self.row = row
                self.string_strVar = tk.StringVar()
                self.string_strVar.set(self.string_var)

                self.config_widgets()
                self.config_grid()
            
            def config_widgets(self):
                # Defining Fonts
                def_font = tk_font.Font(
                    family="Segoe UI", size=10, weight="normal", slant="roman")
                bold_font = tk_font.Font(
                    family="Segoe UI", size=10, weight="bold", slant="roman")

                self.configure(bg="#272822")
                self.name_label = tk.LabelFrame(
                    self,
                    text = self.string_name,
                    bg="#272822",
                    fg="#FFFFFF",
                    padx=5,
                    pady=5,
                    font=bold_font
                )
                self.string_entry = tk.Entry(
                    self.name_label,
                    textvariable=self.string_strVar,
                    bg="#101010",
                    fg="#FFFFFF",
                    font=def_font,
                    insertbackground="#FFFFFF"
                )
                self.save_button = tk.Button(
                    self.name_label,
                    text="Save",
                    bg="#717463",
                    fg="#101010",
                    relief='flat',
                    font=bold_font,
                    command=self.save_to_db,
                )

            def config_grid(self):
                # Allow root frame to expand to full *WIDTH*
                #self.columnconfigure(0, weight=1)
                
                # Defining Widget grid
                self.grid(row=self.row, column=0, sticky='ew')
                self.columnconfigure(0, weight=1)
                self.name_label.columnconfigure(0, weight=1)
                self.name_label.grid(row=0, column=0, pady=2, sticky="nsew")
                self.string_entry.grid(row=0, column=0, padx=2, sticky="nsew")
                self.save_button.grid(row=0, column=1, padx=2, sticky="nse")

            def save_to_db(self):
                '''
                Saves the current self.path_strVar to the DB for the
                target automation.
                '''
                # Create NEW automation exe list
                updated_exe_list = self.string_lst
                updated_exe_list[self.row] = {
                    'name':self.string_name, 
                    'string':self.string_strVar.get()
                    }
                # Convert updated_exe_list to binary object w/ pickle.
                b_updated_exe_list = pickle.dumps(updated_exe_list)
                bcamp_api.update_automation(self.target_auto, 'user_options', b_updated_exe_list)


'''Customized Tk/TcL Classes used through Basecamp Frames'''
class CustomTk_ButtonHover(tk.Button):
    def __init__(self, master, **kw):
        tk.Button.__init__(self, master=master, **kw)
        self.defaultBackground = self["background"]
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        self['background'] = self['activebackground']

    def on_leave(self, e):
        self['background'] = self.defaultBackground


class CustomTk_ToolTip(object):
        '''
        create a tooltip for a given widget, originally from Stack.

        https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tk
        '''
        def __init__(self, widget,
                    *,
                    bg='#FFFFEA',
                    pad=(5, 3, 5, 3),
                    text='widget info',
                    waittime=400,
                    wraplength=250):

            self.waittime = waittime  # in miliseconds, originally 500
            self.wraplength = wraplength  # in pixels, originally 180
            self.widget = widget
            self.text = text
            self.widget.bind("<Enter>", self.onEnter)
            self.widget.bind("<Leave>", self.onLeave)
            self.widget.bind("<ButtonPress>", self.onLeave)
            self.bg = bg
            self.pad = pad
            self.id = None
            self.tw = None

        def onEnter(self, event=None):
            self.schedule()

        def onLeave(self, event=None):
            self.unschedule()
            self.hide()

        def schedule(self):
            self.unschedule()
            self.id = self.widget.after(self.waittime, self.show)

        def unschedule(self):
            id_ = self.id
            self.id = None
            if id_:
                self.widget.after_cancel(id_)

        def show(self):
            def tip_pos_calculator(widget, label,
                                *,
                                tip_delta=(10, 5), pad=(5, 3, 5, 3)):

                w = widget

                s_width, s_height = w.winfo_screenwidth(), w.winfo_screenheight()

                width, height = (pad[0] + label.winfo_reqwidth() + pad[2],
                                pad[1] + label.winfo_reqheight() + pad[3])

                mouse_x, mouse_y = w.winfo_pointerxy()

                x1, y1 = mouse_x + tip_delta[0], mouse_y + tip_delta[1]
                x2, y2 = x1 + width, y1 + height

                x_delta = x2 - s_width
                if x_delta < 0:
                    x_delta = 0
                y_delta = y2 - s_height
                if y_delta < 0:
                    y_delta = 0

                offscreen = (x_delta, y_delta) != (0, 0)

                if offscreen:

                    if x_delta:
                        x1 = mouse_x - tip_delta[0] - width

                    if y_delta:
                        y1 = mouse_y - tip_delta[1] - height

                offscreen_again = y1 < 0  # out on the top

                if offscreen_again:
                    # No further checks will be done.

                    # TIP:
                    # A further mod might automagically augment the
                    # wraplength when the tooltip is too high to be
                    # kept inside the screen.
                    y1 = 0

                return x1, y1

            bg = self.bg
            pad = self.pad
            widget = self.widget

            # creates a toplevel window
            self.tw = tk.Toplevel(widget)

            # Leaves only the label and removes the app window
            self.tw.wm_overrideredirect(True)

            win = tk.Frame(self.tw,
                        background=bg,
                        borderwidth=0)
            label = ttk.Label(win,
                            text=self.text,
                            justify=tk.LEFT,
                            background=bg,
                            relief=tk.SOLID,
                            borderwidth=0,
                            wraplength=self.wraplength)

            label.grid(padx=(pad[0], pad[2]),
                    pady=(pad[1], pad[3]),
                    sticky=tk.NSEW)
            win.grid()

            x, y = tip_pos_calculator(widget, label)

            self.tw.wm_geometry("+%d+%d" % (x, y))

        def hide(self):
            tw = self.tw
            if tw:
                tw.destroy()
            self.tw = None


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
    def __init__(self, parent, vertical=True, horizontal=False, **kwargs):
        super().__init__(parent, **kwargs)

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
            # Hiding bar by default.
            self._vertical_bar.grid_forget()
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
        self._vertical_bar.grid(row=0, column=1, sticky='ns')

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
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))

    def inner_resize(self, event):
        # resize inner frame to canvas size
        if self.resize_width:
            self._canvas.itemconfig("inner", width=event.width)
            # Removing LEGACY scrollbar toggle for now.
            #self.check_scrollbar_render()
        if self.resize_height:
            self._canvas.itemconfig("inner", height=event.height)

    def check_scrollbar_render(self, event=None):
        if (self._canvas.yview())[1] == 1:
            self._vertical_bar.grid_forget()
        else:
            self._vertical_bar.grid(row=0, column=1, sticky='ns')

    def hide_scrollbar(self, event=None):
        self._vertical_bar.grid_forget()


class CustomTk_BaseTextEditor(tk.Frame):
    '''
    This class defines the foundation for the Text Entry widget, with extra 
    features implemented such as Search, Multiline Tab, and Shortcuts.

    This is used as the base for "LogViewer", "CaseNotes", and "FileNotes"
    widgets used by bCamp
    '''

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
        self.title.set("*TESTING BASETEXT*")
        self.case_frame = case_frame
        # Removing auto-render when selecting file.
        #self.case_frame.fb_cur_sel.register_callback(self.open_selected_file)
        self.RPATH = root_path

        # Setting Fonts for text_box.
        self.def_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.text_font = tk_font.Font(
            family="Segoe UI", size=12, weight="normal", slant="roman")
        
        #TK Methods
        self.config_widgets()
        self.config_binds()
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
        # Intialize Tk_LogSearchBar
        self.search_bar = self.Tk_SearchBar(self.notepad_top_frame, self.key_value, self.text_box)

    def config_grid(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='ew')

        # Notepad_top_frame_grid
        self.notepad_top_frame.rowconfigure(1, weight=1)
        self.notepad_top_frame.columnconfigure(0, weight=1)
        self.notepad_top_frame.columnconfigure(1, weight=1)
        self.title_label.grid(row=0, column=0, columnspan=2, padx=5, pady=3, sticky='ew')
        self.search_button.grid(row=0, column=2, padx=3, sticky='e')
        self.options_button.grid(row=0, column=3, padx=3, sticky='e')
        self.search_bar.grid(row=1, column=0, columnspan=4, sticky='ew')
        # Hiding SearchBar
        self.search_bar.grid_remove()

        # Text_box Frame
        self.text_box_frame.rowconfigure(0, weight=1)
        self.text_box_frame.columnconfigure(0, weight=1)
        self.text_box.grid(row=1, column=0, sticky='nsew')
        self.text_box_xsb.grid(row=2, column=0, sticky='ew')
        self.text_box_ysb.grid(row=1, column=1, rowspan=2, sticky='ns')
        # Hiding Scrollbars
        self.text_box_xsb.grid_remove()
        self.text_box_ysb.grid_remove()

        # Options Menu
        self.options_menu = tk.Menu(
            tearoff="false",
            background='#404b4d',
            foreground="#CCCCCC",
        )
        self.options_menu.add_command(
            label="Toggle Scrollbar",
            command=self.toggle_ysb
        )
        self.options_menu.add_command(
            label="Toggle Word-Wrap",
            command=self.toggle_wordwrap
        )

    def config_binds(self):
        self.text_box.bind("<Tab>", self.tabtext)
        #self.text_box.bind("<FocusIn>", self.set_focusIn_colors)
        #self.text_box.bind("<FocusOut>", self.set_focusOut_colors)
        #self.text_box.bind("<<TextModified>>", self.save_notify)
        #self.text_box.bind("<Key>", lambda e: "break") # Readonly textbox

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
        search_bar = self.Tk_SearchBar(self, self.key_value, self.text_box)
        search_bar.update_idletasks()
        w = search_bar.winfo_width()
        h = search_bar.winfo_height()

        search_bar.place(width=w, height=h)

        #search_bar.place(("%dx%d+%d+%d" % (w, h, x + frame_w - 383, y + 32)))

    def tabtext(self, e):
        '''
        When multiple lines are selected, this allows them to be tabbed 
        together.
        '''
        last = self.text_box.index("sel.last linestart")
        index = self.text_box.index("sel.first linestart")
        try:
            while self.text_box.compare(index,"<=", last):
                self.text_box.insert(index, "        ")
                index = self.text_box.index("%s + 1 line" % index)
            return "break"
        except:
            pass


    class Tk_SearchBar(tk.Frame):
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
            self.basebg = "#1E1F21" ##
            self.blk600 = "#15171C"
            self.blk700 = "#0F1117"
            self.blk900 = "#05070F"
            self.act300 = "#D5A336"

            self.sr_font = tk_font.Font(
                family="Segoe UI", size=14, weight="bold", slant="roman")
            self.mini_font = tk_font.Font(
                family="Segoe UI", size=8, weight="bold", slant="italic")
            self.sub_font = tk_font.Font(
                family="Segoe UI", size=10, weight="normal", slant="roman")

            # ONLY for frames. 
            #self.wm_overrideredirect(True) # Hide windows title_bar
            ##self.attributes('-topmost', 'true')
            #self.resizable = False
            self.config_widgets()
            self.config_binds()
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
                background=self.basebg,
                foreground="#eeeeee",
                insertbackground="#eeeeee",
                insertwidth=1,
                relief='flat'
            )
            self.match_count = tk.Label(
                self,
                background=self.blk400,
                foreground=self.basebg,
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

        def config_binds(self):
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


'''Basecamp Root Tk/TcL Frames '''
class Tk_RootPane(tk.Frame):
    '''
    This is the "Master Pane" that contains all main Widget frames such as
    "Tk_WorkbenchTabs" or "Tk_CaseViewer" - Allowing them to be resized
    via Sash grips.
    '''
    def __init__(self, master):
        super().__init__(master=master)
        self.Gui = master

        self.config_theme()
        self.config_widgets()
        self.config_grid()

    def config_theme(self):
        self.rootbg = "#0C0D0B"

    def config_widgets(self):
        self.config(bg=self.rootbg)
        self.horizontal_pane = tk.PanedWindow(
            self,
            handlesize=16,
            #handlepad=100,
            sashwidth=2,
            background=self.rootbg,
            orient='vertical',
            borderwidth=0
        )
        self.vertical_pane = tk.PanedWindow(
            self.horizontal_pane,
            handlesize=16,
            #handlepad=100,
            sashwidth=3,
            background=self.rootbg,
            #background='red',
            orient='horizontal',
            borderwidth=0
        )
        #self.sidebar_pane = tk.PanedWindow(
        #    self.vertical_pane,
        #    handlesize=16,
        #    #handlepad=100,
        #    sashwidth=2,
        #    background=self.rootbg,
        #    orient='vertical',
        #    borderwidth=0
        #)
        self.sidebar_pane = Tk_SideBar(
            self.vertical_pane,
            self.Gui
        )

    def config_grid(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.vertical_pane.add(self.sidebar_pane, sticky='nsew', stretch='never')
        self.horizontal_pane.add(self.vertical_pane, sticky='nsew', stretch='always')
        self.horizontal_pane.grid(row=0, column=0, sticky='nsew')
        

class Tk_SideBar(tk.PanedWindow):
    '''
    Root SideBar Class initalized under the 'Tk_RootPane' as 'sidebar_pane'
    '''
    def __init__(self, master, Gui):
        super().__init__(master=master)
        self.Gui = Gui
        self.init_apps = bcamp_api.callbackVar()
        self.init_apps.value = []
        self.init_apps.register_callback(self.on_init_apps_update)

        # Checkbutton Vars for Sidebar Apps
        self.caseviewer_chkval = tk.IntVar()
        self.todo_chkval = tk.IntVar()


        self.config_theme()
        self.config_widgets()
        self.config_binds()
        self.config_grid()

    # Tk Methods
    def config_theme(self):
        # Font Config
        self.def_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.bold_font = tk_font.Font(
            family="Segoe UI", size=10, weight="bold", slant="roman")
        self.sym_font = tk_font.Font(
            family="consolas", size=13, weight="normal", slant="roman")

        self.basebg = "#10100B"
        self.basefg = '#919288'
        self.topbarfg = '#454533'

        # Notification Presets. 
        self.notify_nocol = self.basebg
        self.notify_grncol = "#A6E22E"
        self.notify_redcol = "#F92672"
        self.notify_yellcol = "#E6CD4A"
    
    def config_widgets(self):
        self.configure(
            background=self.basebg,
        )
        # Topbar
        self.topbar = tk.Frame(
            self,
            background=self.basebg
        )
        self.topbar_label = tk.Label(
            self.topbar,
            text='SIDEBAR',
            background=self.basebg,
            foreground=self.topbarfg,
            relief='flat',
            font=self.def_font,
            anchor='w'
        )
        self.topbar_opts = tk.Button(
            self.topbar,
            text='⋯',
            background=self.basebg,
            foreground=self.basefg,
            relief='flat',
            font=self.sym_font,
            command=self.show_optionsmenu,
            cursor='hand2'
        )
        # Container PanedWindow
        self.content_pane = tk.PanedWindow(
            self,
            background=self.basebg,
            orient='vertical',
            border=0
        )
        # Collapsed Frame
        self.collapsed_frame = tk.Frame(
            self,
            background=self.basebg
        )

        # Options Menu
        self.options_menu = tk.Menu(
            tearoff="false",
            background=self.basebg,
            foreground=self.basefg,
            font=self.def_font
        )
        self.options_menu.add_checkbutton(
            label="Caseviewer",
            selectcolor=self.basefg,
            variable=self.caseviewer_chkval,
            command=(
                lambda widget_name='Tk_CaseViewer':
                    self.toggle_init_apps(widget_name)
                )
        )
        self.options_menu.add_checkbutton(
            label="TODO",
            selectcolor=self.basefg,
            variable=self.todo_chkval,
            command=(
                lambda widget_name='Tk_TodoList':
                    self.toggle_init_apps(widget_name)
                )
        )

        # Right-Click Options Menu
        self.rc_options_menu = tk.Menu(
            tearoff="false",
            background=self.basebg,
            foreground=self.basefg,
            font=self.def_font
        )
        self.rc_options_menu.add_checkbutton(
            label="Caseviewer",
            selectcolor=self.basefg,
            variable=self.caseviewer_chkval,
            command=(
                lambda widget_name='Tk_CaseViewer':
                    self.toggle_init_apps(widget_name)
                )
        )
        self.rc_options_menu.add_checkbutton(
            label="TODO",
            selectcolor=self.basefg,
            variable=self.todo_chkval,
            command=(
                lambda widget_name='Tk_TodoList':
                    self.toggle_init_apps(widget_name)
                )
        )
        self.rc_options_menu.add_separator()
        # ---
        self.rc_options_menu.add_command(
            label="Hide Side Bar             Ctrl+B",
            command=self.Gui.toggle_sidebar
        )
        self.rc_options_menu.add_command(
            label="Move Side Bar Right",
            command=lambda pos='right': self.Gui.update_sidebar_pos(pos)
        )
        self.rc_options_menu.add_command(
            label="Move Side Bar Left",
            command=lambda pos='left': self.Gui.update_sidebar_pos(pos)
        )        

    def config_binds(self):
        self.topbar.bind('<Button-3>', self.right_click_optionsmenu)
        self.topbar_label.bind('<Button-3>', self.right_click_optionsmenu)

    def config_grid(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        # Top Frame
        self.topbar.columnconfigure(0, weight=1)
        self.topbar.grid(
            row=0, column=0, sticky='nsew'
        )
        self.topbar_label.grid(
            row=0, column=0, sticky='new', padx=5, pady=(4,0)
        )
        self.topbar_opts.grid(
            row=0, column=1, sticky='ne'
        )
        # 
        self.content_pane.grid(
            row=1, column=0, sticky='nsew'
        )
        # Collapsed Frame
        self.collapsed_frame.grid(
            row=2, column=0, sticky='nsew'
        )
        self.collapsed_frame.columnconfigure(0, weight=1)
        
    # UI Methods
    def show_optionsmenu(self, event=None):
        # Get current edge of Tile...
        self.topbar.update_idletasks()
        x = self.topbar.winfo_rootx()
        y = self.topbar.winfo_rooty()
        frame_w = self.topbar.winfo_width()
        # Render Menu at edge
        self.options_menu.post((x + frame_w) - 30, y + 30)

    def right_click_optionsmenu(self, event):
        self.rc_options_menu.post(event.x_root + 10, event.y_root + 10)

    # Sidebar App Methos
    def toggle_init_apps(self, widget_name):
        print('!widget_name', widget_name)
        cur_init_apps = self.init_apps.value
        index_count = 0
        for item in cur_init_apps:
            py_name = item[0]
            active = item[1]['active']
            # Check if 'widget' 'active' bool, and flip - triggering callback
            if py_name == widget_name:
                if active != True:
                    print('NEW ACTIVE ->', py_name)
                    cur_init_apps[index_count][1]['active'] = True
                else:
                    print('!ACTIVE ->', py_name)
                    cur_init_apps[index_count][1]['active'] = False
                # update self.init_apps
                self.init_apps.value = cur_init_apps
                break
            # increment index
            index_count += 1

    def add_sidebar_app(self, widget, expand, title, active, **kwargs):
        '''
        Replicates the Tk.Panedwindow add() but with the parent frames
        wrapping the frame added here. 
        '''
        # Intialize TargetWidget in 'content_pane'
        new_pane = self.Tk_SidebarPane(self.content_pane, widget, self.Gui, self, expand, title, **kwargs)
        new_collapsedFrame = self.Tk_SideBarCollapsed(self.collapsed_frame, widget, self.Gui, self, title)
        cur_init_apps = self.init_apps.value
        if active: # Either Expanded or Collapsed
            if expand:
                cur_init_apps.append([widget.__name__, {'pane':new_pane, 'collapsedframe':new_collapsedFrame, 'active':True, 'expand':True}])
                self.init_apps.value = cur_init_apps
            elif not expand:
                cur_init_apps.append([widget.__name__, {'pane':new_pane, 'collapsedframe':new_collapsedFrame, 'active':True, 'expand':False}])
                self.init_apps.value = cur_init_apps
        elif not active:
                cur_init_apps.append([widget.__name__, {'pane':new_pane, 'collapsedframe':new_collapsedFrame, 'active':False, 'expand':False}])
                self.init_apps.value = cur_init_apps
    
    def on_init_apps_update(self, new_init_apps): # **CALLBACK
        '''
        Callback Method called whenever the Classes 'init_apps.value' is changed.
        '''
        #print('$init_apps >> ', new_init_apps)
        pane_height = 120 # default, unless only.

        # Enumerate through whole list and update Pane and CollapsedFrame.
        index_count = 0
        hide_collapsedframe = True
        for item in new_init_apps:
            py_name = item[0]
            pane = item[1]['pane']
            collapsedframe = item[1]['collapsedframe']
            expand = item[1]['expand']
            active = item[1]['active']
            index = index_count #Used for CollapseFrame placement.
            if active:
                if expand:
                    self.content_pane.paneconfig(pane, sticky='nsew', width=300, minsize=80, height=pane_height, hide=False, stretch='first')
                    collapsedframe.grid_remove()
                if not expand:
                    hide_collapsedframe = False
                    self.content_pane.paneconfig(pane, sticky='nsew', width=300, minsize=30, height=pane_height, hide=True)
                    collapsedframe.grid(
                        row=index, column=0, sticky='nsew', pady=(1,0)
                    )
                # Update chkvals for sidebar apps
                if py_name == 'Tk_CaseViewer':
                    self.caseviewer_chkval.set(1)
                if py_name == 'Tk_TodoList':
                    self.todo_chkval.set(1)
                #
            elif not active:
                self.content_pane.paneconfig(pane, sticky='nsew', width=300, minsize=30, height=pane_height, hide=True)
                collapsedframe.grid_remove()
                # Update chkvals for sidebar apps
                if py_name == 'Tk_CaseViewer':
                    self.caseviewer_chkval.set(0)
                if py_name == 'Tk_TodoList':
                    self.todo_chkval.set(0)
                #
            # increment index
            index_count += 1
        
        # Update self.collapsed_frame .grid based on hide_collapsedframe flag.
        if hide_collapsedframe:
            self.collapsed_frame.grid_remove()
        else:
            self.collapsed_frame.grid()


    class Tk_SideBarCollapsed(tk.Frame):
        def __init__(self, master, TargetWidget, Gui, SideBar, Title):
            super().__init__(master=master)
            self.title = Title
            self.Gui = Gui
            self.SideBar = SideBar
            self.TargetWidget = TargetWidget
            self._widgetname = tk.StringVar()
            self._widgetname.set(Title.upper())
            self.config_theme()
            self.config_widgets()
            self.config_binds()
            self.config_grid()
        
        def config_theme(self):
            # Font Config
            self._def_font = tk_font.Font(
                family="Segoe UI", size=10, weight="normal", slant="roman")
            self._bold_font = tk_font.Font(
                family="Segoe UI", size=10, weight="bold", slant="roman")
            self._sym_font = tk_font.Font(
                family="Consolas", size=12, weight="bold", slant="roman")

            self._basebg = "#1D1E19"
            self._basefg = '#919288'
            self._labelfg = '#919288'
            self._topbarbg = "#1D1E19"
            self._topbarfg = '#C0C1BA'

            # Notification Presets. 
            self._notify_nocol = self._basebg
            self._notify_grncol = "#A6E22E"
            self._notify_redcol = "#F92672"
            self._notify_yellcol = "#E6CD4A"

        def config_widgets(self):
            # Topbar Frame.
            self._topbar_frame = tk.Frame(
                self,
                background=self._topbarbg
            )
            self._expand_btn = tk.Button(
                self._topbar_frame,
                text='ᐳ ', # ᐳ ᐯ
                background=self._topbarbg,
                foreground=self._topbarfg,
                relief='flat',
                font=self._bold_font,
                command=self.open_targetpane,
                cursor='hand2'
            )
            self._topbar_label = tk.Label(
                self._topbar_frame,
                textvariable=self._widgetname,
                background=self._topbarbg,
                foreground=self._labelfg,
                relief='flat',
                font=self._bold_font
            )
            self._topbar_subframe = tk.Frame(
                self._topbar_frame,
                background=self._topbarbg
            )
        
        def config_grid(self):
            self.columnconfigure(0, weight=1)
            # Topbar Frame.
            self._topbar_frame.grid(
                row=0, column=0, padx=0, pady=0, sticky='nsew'
            )
            self._topbar_frame.columnconfigure(2, weight=1)
            self._expand_btn.grid(
                row=0, column=0, padx=0, pady=0, sticky='nsew'
            ) 
            self._topbar_label.grid(
                row=0, column=1, padx=0, pady=0, sticky='nsew'
            ) 
            self._topbar_subframe.grid(
                row=0, column=2, padx=0, pady=0, sticky='nsew'
            )
        
        def config_binds(self):
            pass

        def open_targetpane(self, event=None):
            _init_apps = self.SideBar.init_apps.value
            # Find 'self' in SideBar init_apps and flip 'expand' bool
            indx = 0
            for item in _init_apps:
                if item[1]['collapsedframe'] == self:
                    _init_apps[indx][1]['expand'] = True
                indx += 1
            # Update the callback var to make UI changes.
            self.SideBar.init_apps.value = _init_apps


    class Tk_SidebarPane(tk.Frame):
        '''
        Base Sidebar Frame that contains a simple header with expansion capability
        and an empty container frame that will be popoulated with any Tk widget.
        
        **kwargs options
        - 'name' - String: Title for the Wrapping frame.

        Subpane Widget Class Options
        - 'refresh_callback' - method(): Enables the refresh icon in the 
            topbar. 'TargetWidget' needs a '_sb_refresh' method within its
            definitions for this to be present.
        '''
        def __init__(self, master, TargetWidget, Gui, SideBar, expand, title, **kwargs):
            super().__init__(master=master)
            self.Gui = Gui # For pulling data from other widgets if needed.
            self.SideBar = SideBar
            self.master = master
            self.TargetWidget = TargetWidget
            self.init_targetwidget = None # for now.
            self._widgetname = tk.StringVar()
            self._refresh_callback = None
            self._expand = expand
            self._widgetname.set(title.upper())
 
            # TK Methods
            self._config_theme()
            self._config_widgets()
            self._config_binds()
            # Add TargetWidget to container frame.
            self.add_widget()
            # Then Draw...
            self._config_grid()

        def _config_theme(self):
            # Font Config
            self._def_font = tk_font.Font(
                family="Segoe UI", size=10, weight="normal", slant="roman")
            self._bold_font = tk_font.Font(
                family="Segoe UI", size=10, weight="bold", slant="roman")
            self._sym_font = tk_font.Font(
                family="Consolas", size=12, weight="bold", slant="roman")

            self._basebg = "#1D1E19"
            self._basefg = '#919288'
            self._labelfg = '#919288'
            self._topbarbg = "#1D1E19"
            self._topbarfg = '#C0C1BA'

            # Notification Presets. 
            self._notify_nocol = self._basebg
            self._notify_grncol = "#A6E22E"
            self._notify_redcol = "#F92672"
            self._notify_yellcol = "#E6CD4A"

        def _config_widgets(self):
            # Topbar Frame.
            self._topbar_frame = tk.Frame(
                self,
                background=self._topbarbg
            )
            self._collapse_btn = tk.Button(
                self._topbar_frame,
                text='ᐯ', # ᐳ ᐯ
                background=self._topbarbg,
                foreground=self._topbarfg,
                relief='flat',
                font=self._bold_font,
                command=self._collapse_frame,
                cursor='hand2'
            )
            self._topbar_label = tk.Label(
                self._topbar_frame,
                textvariable=self._widgetname,
                background=self._topbarbg,
                foreground=self._labelfg,
                relief='flat',
                font=self._bold_font
            )
            self._topbar_subframe = tk.Frame(
                self._topbar_frame,
                background=self._topbarbg
            )
            self._topbar_buttonframe = tk.Frame(
                self._topbar_frame,
                background=self._topbarbg
            )
            # TB ButtonFrame Contents
            self._close_btn = tk.Button(
                self._topbar_buttonframe,
                text='X',
                background=self._topbarbg,
                foreground=self._topbarbg, # Start hidden. 
                relief='flat',
                font=self._bold_font,
                command=self._destroy_frame,
                cursor='hand2'
            )
            self._refresh_btn = tk.Button(
                self._topbar_buttonframe,
                text='⟳',
                background=self._topbarbg,
                foreground=self._topbarbg, # Start hidden. 
                relief='flat',
                font=self._bold_font,
                cursor='hand2'
            )
            # Container ScrolledFrame
            self._container_frame = tk.Frame(
                self,
                background=self._basebg
                #background='red'
            )
        
        def _config_grid(self):
            # Root
            self.columnconfigure(0, weight=1)
            self.rowconfigure(1, weight=1)
            # Topbar Frame.
            self._topbar_frame.grid(
                row=0, column=0, padx=0, pady=0, sticky='nsew'
            )
            self._topbar_frame.columnconfigure(2, weight=1)
            self._collapse_btn.grid(
                row=0, column=0, padx=0, pady=0, sticky='nsew'
            ) 
            self._topbar_label.grid(
                row=0, column=1, padx=0, pady=0, sticky='nsew'
            ) 
            self._topbar_subframe.grid(
                row=0, column=2, padx=0, pady=0, sticky='nsew'
            ) 
            self._topbar_buttonframe.grid(
                row=0, column=3, padx=0, pady=0, sticky='nsew'
            ) 
            # TB ButtonFrame Contents
            if self._refresh_callback != None:
                self._refresh_btn.grid(
                    row=0, column=0, padx=0, pady=0, sticky='nsew'
                )
            self._close_btn.grid(
                row=0, column=1, padx=0, pady=0, sticky='nsew'
            )
            # Container ScrolledFrame
            self._container_frame.grid(
                row=1, column=0, padx=0, pady=0, sticky='nsew'
            )
        
        def _config_binds(self):
            self.bind('<Enter>', self.set_topbar_colors)
            self.bind('<Leave>', self.reset_topbar_colors)
        
        def _destroy_frame(self):
            _init_apps = self.SideBar.init_apps.value
            # Find 'self' in SideBar init_apps and flip 'expand' bool
            indx = 0
            for item in _init_apps:
                if item[1]['pane'] == self:
                    _init_apps[indx][1]['active'] = False
                    break
                indx += 1
            
            # Update the callback var to make UI changes.
            self.SideBar.init_apps.value = _init_apps

        def _collapse_frame(self):
            _init_apps = self.SideBar.init_apps.value
            # Find 'self' in SideBar init_apps and flip 'expand' bool
            indx = 0
            for item in _init_apps:
                if item[1]['pane'] == self:
                    _init_apps[indx][1]['expand'] = False
                indx += 1
            # Update the callback var to make UI changes.
            self.SideBar.init_apps.value = _init_apps

        # Theme Methods
        def set_topbar_colors(self, event=None):
            '''
            Sets the Colors of the TK widgets so that can be visible when a user
            mouses over the toolbar as they are "hidden" by default.
            '''
            # Default Colors on enter - will override if enabled shortly.
            self._close_btn['fg'] = self._topbarfg
            self._refresh_btn['fg'] = self._topbarfg

        def reset_topbar_colors(self, event):
            '''
            Sets the Colors of the TK widgets so that they are HIDDEN.
            '''
            self._close_btn['fg'] = self._topbarbg
            self._refresh_btn['fg'] = self._topbarbg
        
        # Population methods
        def add_widget(self):
            self._container_frame.rowconfigure(0, weight=1)
            self._container_frame.columnconfigure(0, weight=1)
            container_w = self.TargetWidget(
                self._container_frame,
                self.Gui
            )
            # Save initalized TargetWidget to 'self.init_targetwidget'
            self.init_targetwidget = container_w
            # Check if refresh_method present.
            if hasattr(container_w, '_sb_refresh'):
                self._refresh_callback = container_w._sb_refresh
                self._refresh_btn.configure(
                    command=self._refresh_callback
                )
            #
            # Check if topbar_subframe method is present.
            #if hasattr(container_w, '_sb_topbar'):
            #    self._refresh_callback = container_w._sb_refresh
            #    self._refresh_btn.configure(
            #        command=self._refresh_callback
            #    )
            #
            container_w.grid(
                row=0, column=0, sticky='nsew'
            )


class Tk_BottomBar(tk.Frame):
    '''
    A dynamic Frame at the bottom of the UI to store Connection status, and
    Progressbar details.
    '''
    def __init__(self, Gui):
        super().__init__()
        self.Gui = Gui
        # ProgressBar Vars
        self.progress_strVar = tk.StringVar()
        self.progress_perc_strVar = tk.StringVar()
        self.queue_strVar = tk.StringVar()
        self.poll_strVar = tk.StringVar()
        self.poll_cnt_strVar = tk.StringVar()
        self.jira_sec_var = tk.StringVar()
        self.Gui.FileOpsQ.progress_obj.register_callback(self.update_progressbar)
        self.Gui.FileOpsQ.queue_callback.register_callback(self.update_queue)
        self.Gui.CasePoll.thread_running.register_callback(self.update_poll_status)
        self.Gui.CasePoll.prog_val.register_callback(self.update_poll_cnt)

        self.config_widgets()
        self.config_grid()
        self.after(200, self.check_remotedir_access)

        # Starting Periodic PollThread after 3 seconds.
            #self.after(3000, self.Gui.CasePoll.start_poll)
        # DEBUG Option is to comment the line above to prevent AutoCase Poll.

    def config_widgets(self):
        # Font
        self.def_font = tk_font.Font(
            family="Segoe UI", size=8, weight="normal", slant="roman")

        # Colors
        self.basebg = "#10100B"
        self.basefg = "#7E7E71"
        self.prog_fg = "#A6E22E"
        self.entry_bg = "#272822"
        self.entry_fg = "#BBC0A4"
        self.act_red = "#F92672"
        self.act_yellow = "#E6CD4A"
        self.act_grn = "#A6E22E"
        self.act_blu = "#22A6B3"

        # Root Background color
        self.configure(
            background=self.basebg
        )
        # Spacer frame, black-line at top of BB.
        self.spacer_frame = tk.Frame(
            self,
            bg="#000000",
            height=1
        )

        # FileOps Frame
        self.queue_strVar.set('QUEUE : 0') # Default Queue String
        self.fileops_frame = tk.Frame(
            self,
            background=self.basebg
        )
        self.queue_label = tk.Label(
            self.fileops_frame,
            textvariable=self.queue_strVar,
            background=self.basebg,
            foreground=self.basefg,
            relief="flat"
        )        
        self.progress_percent = tk.Label(
            self.fileops_frame,
            textvariable=self.progress_perc_strVar,
            background=self.basebg,
            foreground=self.prog_fg           
        )
        self.progress_label = tk.Label(
            self.fileops_frame,
            textvariable=self.progress_strVar,
            background=self.basebg,
            foreground=self.basefg,
        )
        self.poll_status = tk.Label(
            self.fileops_frame,
            textvariable=self.poll_strVar,
            background=self.basebg,
            foreground=self.basefg,
        )
        self.poll_cnt = tk.Label(
            self.fileops_frame,
            textvariable=self.poll_cnt_strVar,
            background=self.basebg,
            foreground=self.basefg,
        )

        # Connectivity/Ver Frame
        self.conn_frame = tk.Frame(
            self,
            background=self.basebg
        )
        self.bb_ver = tk.Label(
            self.conn_frame,
            text=bcamp_api.BCAMP_VERSION,
            background=self.basebg,
            foreground=self.basefg,
            font=self.def_font
        )
        self.bb_remote_canvas = tk.Canvas(
            self.conn_frame,
            width=12,
            height=12,
            background=self.basebg,
            highlightthickness=0,
        )
        self.remote_oval = self.bb_remote_canvas.create_oval(
            0, 0, 10, 10, fill='#000000', outline='#333333')
        self.bb_remote_on = self.bb_remote_canvas.create_oval(
            0, 0, 10, 10, fill=self.act_blu, outline='#333333')
        self.bb_remote_off = self.bb_remote_canvas.create_oval(
            0, 0, 10, 10, fill=self.act_red, outline='#333333')

        self.bb_telemen_canvas = tk.Canvas(
            self.conn_frame,
            width=12,
            height=12,
            background=self.basebg,
            highlightthickness=0
        )
        self.bb_telemen_on = self.bb_telemen_canvas.create_oval(
            0, 0, 10, 10, fill=self.act_grn, outline='#333333')
        self.bb_telemen_off = self.bb_telemen_canvas.create_oval(
            0, 0, 10, 10, fill=self.act_red, outline='#333333')

        # JIRA Frame
        self.jira_frame = tk.Frame(
            self,
            #text="JIRA Integration",
            background=self.basebg,
            #foreground=self.basefg,                
        )
        self.jira_sec_label = tk.Label(
            self.jira_frame,
            text="JIRA Password",
            background=self.basebg,
            foreground=self.basefg,
            relief='flat'
        )             
        self.jira_sec_entry = tk.Entry(
            self.jira_frame,
            show="*",
            textvariable=self.jira_sec_var,
            background=self.entry_bg,
            foreground=self.entry_fg,
            relief='flat',
        )
        self.jira_sec_entry.bind('<Return>', self.check_jira_access)

        # Tooltip Group
        self.tt_telemen_tip = CustomTk_ToolTip(
            self.bb_telemen_canvas, text="JIRA Server Connectivity")
        self.tt_remote_tip = CustomTk_ToolTip(
            self.bb_remote_canvas, text="Remote Folder Connectivity")
        self.tt_jira_sec_entry = CustomTk_ToolTip(
            self.jira_sec_entry, text="Press <ENTER> to attempt login!")
        self.tt_queue_label = CustomTk_ToolTip(
            self.queue_label, text="FileOperations Queue Size - Shared by each Workbench.")                        

    def config_grid(self):
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        # Root Frames 
        self.spacer_frame.grid(
            row=0, column=0, columnspan=3, sticky="nsew"
        )
        self.fileops_frame.grid(
            row=1, column=0, sticky="nsw", pady=5
        )
        self.jira_frame.grid(
            row=1, column=1, sticky='nse', pady=5
        )
        self.conn_frame.grid(
            row=1, column=2, sticky='nse', pady=5
        )

        # Filesops Frame Grid
        self.queue_label.grid(
            row=0, column=0, sticky='nsw', padx=1
        )
        self.progress_percent.grid(
            row=0, column=1, sticky='nsw', padx=1
        )
        self.progress_label.grid(
            row=0, column=2, sticky='nsw', padx=1
        )
        self.poll_status.grid(
            row=0, column=3, sticky='nsw', padx=1
        )
        self.poll_cnt.grid(
            row=0, column=4, sticky='nse', padx=1
        )
        # JIRA Integ Frame
        self.jira_sec_label.grid(
            row=0, column=0
        )
        self.jira_sec_entry.grid(
            row=0, column=1, padx=2
        )
        # Conn Frame Grid
        self.bb_remote_canvas.grid(row=0, column=0, padx=2)
        self.bb_telemen_canvas.grid(row=0, column=1, padx=2)
        self.bb_ver.grid(row=0, column=2, sticky='se', padx=3)

    # ProgressBar Methods
    def update_progressbar(self, new_progress_obj):
        '''
        Callback method whenever *FilesOpsQ.progress_obj* var is modified from
        the FileOpsQueue daemon initialized on start.

        Parses the 'new_progress_obj' dictionary which contains a default
        'mode' value, and any other info provided from the API scripts
        for progress string formatting, which is done here!
        '''
        def calc_percentage(cursize, totalsize):
            # Converts Totalsize/cursize to a rounded percentage.
            raw_percent = cursize / totalsize
            formated_percent = "{:.0%}".format(raw_percent)
            return formated_percent
        
        if new_progress_obj['mode'] == None:
            # Set when reset by FileOps Worker Thread
            self.progress_strVar.set("")
            self.progress_perc_strVar.set("")

        if new_progress_obj['mode'] == 'download':
            # convert bytes to kB
            cur_kb = new_progress_obj['curbytes'] / 100
            total_kb = new_progress_obj['totalbytes'] / 100
            # Get percentage
            prog_percentage = calc_percentage(cur_kb, total_kb)
            # Get name and sr
            fname = os.path.basename(new_progress_obj['srcpath'])
            sr = new_progress_obj['sr']
            formatted_string = (
                "DOWNLOAD - " + sr + "/" + fname
            )
            self.progress_perc_strVar.set("[" + prog_percentage + "]")
            self.progress_strVar.set(formatted_string)

        if new_progress_obj['mode'] == 'upload':
            # convert bytes to kB
            cur_kb = new_progress_obj['curbytes'] / 100
            total_kb = new_progress_obj['totalbytes'] / 100
            # Get percentage
            prog_percentage = calc_percentage(cur_kb, total_kb)
            # Get name and sr
            fname = os.path.basename(new_progress_obj['srcpath'])
            sr = new_progress_obj['sr']
            formatted_string = (
                "UPLOAD - " + sr + "/" + fname
            )
            self.progress_perc_strVar.set("[" + prog_percentage + "]")
            self.progress_strVar.set(formatted_string)

        if new_progress_obj['mode'] == 'automation':

            # Base Message wth vars from *new_progress_obj* dictionary.
            automation_path = new_progress_obj['srcpath']
            sr = new_progress_obj['sr']
            fname = os.path.basename(new_progress_obj['srcpath'])
            base_msg = (
                "AUTOMATION - "
                + sr
                + "/" + fname
            )
            self.progress_strVar.set(base_msg)

            def set_perc_val(input_val):
                self.progress_perc_strVar.set(input_val)

            # Checking if 'automation' already complete since recursive call.
            if self.Gui.FileOpsQ.progress_obj.value['mode'] == 'automation':
                # Modify progress string with *self.after* - measured in ms
                self.after(1000, set_perc_val, "[.  ]")
                self.after(2000, set_perc_val, "[.. ]")
                self.after(3000, set_perc_val, "[...]")

            # Recursive Call back to *self* with og new_progress_obj to loop
            # the progress dots.
            if self.Gui.FileOpsQ.progress_obj.value['mode'] == 'automation' and self.Gui.FileOpsQ.progress_obj.value['srcpath'] == automation_path:
                self.after(4000, self.update_progressbar, new_progress_obj)
            else:
                # Jobs Done! - *self.FileOpsQ.progress_obj* cleared by FileopsQueue.
                # Manually clearing string here so we dont have to wait for the 
                # threads to sync.
                self.progress_strVar.set("")

    def update_queue(self, new_queue_size):
        self.queue_strVar.set('QUEUE : ' + str(new_queue_size))

    def update_poll_status(self, show_status):
        '''
        Callback when Poll Thread is running.
        '''
        #print("$.update_poll", show_status)
        if show_status:
            self.poll_strVar.set('Scanning SR changes')
        else:
            self.poll_strVar.set('')
            # Manually update 'update_poll_cnt'
            self.update_poll_cnt('')
    
    def update_poll_cnt(self, new_count):
        self.poll_cnt_strVar.set(new_count)
    
    # Connectivity Methods
    def check_remotedir_access(self):
        def update_remotecanvas(connected):
            if connected:
                self.bb_remote_canvas.itemconfigure(self.bb_remote_off, state='hidden')
                self.bb_remote_canvas.itemconfigure(self.bb_remote_on, state='normal')
                # Changing color for Dev Mode when enabled.
                if devmode == "True":
                    self.bb_remote_canvas.itemconfigure(self.bb_remote_on, fill='#FD7C29')
                elif devmode == "False":
                    self.bb_remote_canvas.itemconfigure(self.bb_remote_on, fill='#6ab04c')
            else:
                # Make the DOT red if DEAD.
                self.bb_remote_canvas.itemconfigure(self.bb_remote_on, state='hidden')
                self.bb_remote_canvas.itemconfigure(self.bb_remote_off, state='normal')
        
        def thread_obj():
            if os.access(nas, os.R_OK):
                remoteupdate_callback.value = True
        
        #print("$.chk_remote_canvas")
        nas = bcamp_api.get_config("remote_root")
        devmode = bcamp_api.get_config("dev_mode")
        remoteupdate_callback = bcamp_api.callbackVar()
        remoteupdate_callback.register_callback(update_remotecanvas)
        # Start seperate thread to check Remote Access, and use callback to 
        # update the UI in 'MainThread'
        threading.Thread(target=thread_obj).start()
        self.after(60000 * 15, self.check_remotedir_access)

    def check_jira_access(self, event=None):
        def test_creds(user, jira_sec):
            testurl = 'https://jira-lvs.prod.mcafee.com/rest/api/2/mypermissions'
            connection_result.value = bcamp_api.jira_response(testurl, user, jira_sec)

        def set_ui(new_response):
            red = "#F92672"
            grn = "#A6E22E"
            if new_response == '<Response [200]>':
                print("*CONNECTED*")
                bcamp_api.jira_db_sec(jira_sec)
                self.jira_frame.grid_remove()
                update_jiracanvas(True)
                Gui.JIRA_ENABLED.value = True
            else:
                self.jira_sec_entry['fg'] = red
                update_jiracanvas(False)
        
        def update_jiracanvas(connected):
            # BottomBar Telemetry connectivity Poll
            if connected:
                self.bb_telemen_canvas.itemconfigure(self.bb_telemen_off, state='hidden')
                self.bb_telemen_canvas.itemconfigure(self.bb_telemen_on, state='normal')
                # Changing color for Dev Mode when enabled.
                if devmode == "True":
                    self.bb_telemen_canvas.itemconfigure(self.bb_telemen_on, fill='#FD7C29')
                elif devmode == "False":
                    self.bb_telemen_canvas.itemconfigure(self.bb_telemen_on, fill='#22a6b3')
            else:
                # Make the DOT red if DEAD.
                self.bb_telemen_canvas.itemconfigure(self.bb_telemen_on, state='hidden')
                self.bb_telemen_canvas.itemconfigure(self.bb_telemen_off, state='normal')

        devmode = bcamp_api.get_config("dev_mode")
        jira_sec = self.jira_sec_var.get()  
        user = os.getlogin()
        connection_result = bcamp_api.callbackVar()
        connection_result.register_callback(set_ui)
        # Start seperate thread to check Remote Access, and use callback to 
        # update the UI in 'MainThread'
        threading.Thread(target=test_creds, args=(user, jira_sec)).start()


'''Basecamp Sidebar Tk/TcL Frames'''       
class Tk_CaseViewer(tk.Frame):
    '''
    The CaseViewer is the Sidebar that contains the Case "Tiles". This class
    sources data from the local SQLite basecamp.db file and renders the Tiles
    using the "CaseTile_Template" Subclass for reference.
    '''
    def __init__(self, master, Gui):
        super().__init__(master=master)
        # For starting new tabs in Workspace
        #self.workspace_man = workspace_manager
        self.master = master
        self.Gui = Gui
        self._def_width = 300
        self.frame_state = "on"
        self.RPATH = str(pathlib.Path(
            __file__).parent.absolute()).rpartition('\\')[0]
        self.sel_case_tab = None
        self.isFiltered = False # Flag if we render all or cur tiles.
        self.f_notification_tiles = []
        self.j_notification_tiles = []
        
        # NEW TILEORDER METHODS
        self.master_casetiles = bcamp_api.callbackVar()
        self.master_casetiles.register_callback(self.NEW_on_master_casetiles_update)
        self.search_results = None
        self.casetiles_order_rule = 'default'
        #self.casetiles_order_rule = 'hasbug'
        # NEW TILEORDER

        # CasePollDaemon for File Cnt & JIRA changes
        self.Gui.CasePoll.results.register_callback(self.update_casetiles)

        # Search/Filter Vars
        self.default_search_str = "(Search/Filter Cases)"
        self.search_strVar = tk.StringVar()
        self.search_strVar.set(self.default_search_str)
        self.filtertiles_obj = []
        self.filterset_callback = bcamp_api.callbackVar()
        self.filterset_callback.value = {
                    'account': [],
                    'product': [],
                    'tag': [],
                    'custom': [],
                    'o_rule': 'default'
            }
        self.filterset_callback.register_callback(self.on_filterset_callback)

        self.config_widgets()
        self.config_grid()
        self.config_binds()
        
        # Draw ALL CaseTiles on init...
        #self.get_all_casetiles()
        self.NEW_gen_all_casetiles()

    def config_widgets(self):
        # Font Config
        self.def_font = tk_font.Font(
            family="Segoe UI", size=11, weight="normal", slant="roman")
        self.bold_font = tk_font.Font(
            family="Segoe UI", size=11, weight="bold", slant="roman")
        self.sym_font = tk_font.Font(
            family="Consolas", size=12, weight="bold", slant="roman")
        
        # Colors
        self.basebg = "#10100B"
        self.basefg = "#f5f5f5"

        self.configure(
            bg=self.basebg
        )
        # Creating Canvas widget to contain the Case Tiles, enabling a
        # scrollbar if the user has a lot of cases imported.
        self.master_frame = CustomTk_ScrolledFrame(
            self,
            background=self.basebg
        )
        self.master_frame.resize_width = True # Enable resize of inner canvas
        self.master_frame.resize_height = False
        self.master_frame._canvas.configure(
            background=self.basebg
        )
        self.master_frame.inner.configure(
            background=self.basebg
        )

        # Defining search frame at the bottom of the CaseViewer Window to
        # filter shown CaseTiles.
        self.search_frame = tk.Frame(
            self,
            bg='#3B3C35'
        )
        self.search_entry = tk.Entry(
            self.search_frame,
            textvariable=self.search_strVar,
            bg="#101010",
            fg="#8B9798",
            insertbackground="#8B9798",
            justify='center',
            relief='flat',
            font=self.def_font
        )
        self.search_run_btn = tk.Button(
            self.search_frame,
            text=">",
            bg="#3B3C35",
            fg="#FFFFFF",
            relief='flat',
            font=self.bold_font,
            command=self.run_search            
        )
        self.filter_subframe = tk.Frame(
            self.search_frame,
            bg='#3B3C35',
            #bg='#404247'
        )

        # Search right-click menu.
        self.searchmenu = tk.Menu(
            relief='flat',
            tearoff=False,
            background=self.basebg,
            foreground=self.basefg,
            borderwidth=0,            
        )
        self.searchmenu.add_command(
            label='Filter: Has Bug',
            command=lambda r='hasbug': self.update_o_rule(r)
        )
        self.searchmenu.add_command(
            label='Filter: No Bug',
            command=lambda r='nobug': self.update_o_rule(r)
        )
        self.searchmenu.add_command(
            label='Filter: JIRA-needinfo',
            command=lambda r='jiraneedinfo': self.update_o_rule(r)
        )
        self.searchmenu.add_command(
            label='Filter: JIRA-notifications',
            command=lambda r='jiranotify': self.update_o_rule(r)
        )
        self.searchmenu.add_command(
            label='Filter: New Customer Uploads',
            command=lambda r='filenotify': self.update_o_rule(r)
        )

        # Tooltips
        self.tt_search_run_btn = CustomTk_ToolTip(self.search_run_btn, text='Filter cases by entry value.')

    def config_grid(self):
        self.columnconfigure(0, weight=1)
        
        # Check DB for Search Location to render Master frame and Search Frame
        if bcamp_api.get_config('ui_render_caseviewer_search') == 'True':
            if bcamp_api.get_config('ui_caseviewer_search_location') == 'top':
                # Allow Row 1 to stretch for Master Frame.
                self.rowconfigure(0, weight=0)
                self.rowconfigure(1, weight=1)
                self.search_frame.grid(row=0, column=0, pady=(0,3), padx=(0,1), sticky="nsew")
                self.master_frame.grid(row=1, column=0, sticky="nsew")
            elif bcamp_api.get_config('ui_caseviewer_search_location') == 'bottom':
                # Allow Row 0 to stetch for Master Frame.
                self.rowconfigure(0, weight=1)
                self.rowconfigure(1, weight=0)
                self.master_frame.grid(row=0, column=0, sticky="nsew")
                self.search_frame.grid(row=1, column=0, pady=(3,0), padx=(0,1), sticky="nsew") 
        elif bcamp_api.get_config('ui_render_caseviewer_search') == 'False':      
            # Allow Row 0 to stetch for Master Frame.
            self.rowconfigure(0, weight=1)
            self.rowconfigure(1, weight=0)
            self.master_frame.grid(row=0, column=0, sticky="nsew") 
            self.search_frame.grid_remove()
        
        # Search Frame widgets
        self.search_frame.rowconfigure(0, weight=1)
        self.search_frame.rowconfigure(2, weight=1)
        self.search_frame.columnconfigure(0, weight=1)
        #self.search_label.grid(row=0, column=0, sticky="nsw")
        self.search_entry.grid(row=1, column=0, pady=2, padx=2, sticky="nsew")
        self.search_run_btn.grid(row=1, column=1, pady=2, padx=2, sticky="nse")
        self.filter_subframe.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.filter_subframe.rowconfigure(0, weight=1)

    def config_binds(self):
        self.search_entry.bind("<FocusIn>", self.clear_search_entry)
        self.search_entry.bind("<FocusOut>", self.reset_search_entry)
        self.filter_subframe.bind("<Configure>", self.update_filtertiles_grid)
        self.search_entry.bind("<Return>", self.run_search)
        self.search_entry.bind("<Button-3>", self.draw_searchmenu)

    # Casetiles Methods
    def NEW_gen_all_casetiles(self):
        '''
        Query DB and get sets for each SR containing various properties used
        to order/filter the casetiles shown on the left.

        1. Get 'tileprops' of current imported cases from DB

        2. For each SR in 'tileprops', create 'CaseTile Template' Widget. 
            This should be stored with the 'tileprops' lst.
            NOTE: These templates SHOULD NOT be destroyed, just hidden.

        3. Get default 'tiles_order' type from ?DB?
            *pinned SRs will always be at the TOP, in order based on 'tiles_order'
            - Age
            - Account Grouping
            - Product Grouping
            - Has-Bug
            - Jira Status (Need Info -> Ready)
            - Jira Notification
            - File Notification

        4. Compute 'casetiles_index' based on filter.

        5. Render the tiles that are present in the 'casetiles_index'.

        6. If a value for a var in the tile_template is updated, either from CasePoll
            or manually by a user, CallbackVar() to the CaseTile Template Obj to update
            the value in the UI.
        '''
        raw_tileprops = bcamp_api.dbget_case_casetiles()
        tileprops_dict = {}
        for item in raw_tileprops:
            # Create Widget for imported items.
            tk_widget = self.CaseTile_template(
                self.master_frame.inner,
                item[0],
                self)
            # flatten Dicts together and append data to new 'tileprops_dict'
            tileprops_dict[item[0]] = {
                'widget': tk_widget,
                'pinned': item[1],
                'account': item[2],
                'product': item[3],
                'bug_id': item[4],
                'jira_status': item[5],  
                'jira_notify_flag': item[6],
                'file_notify_flag': item[7] 
            }

        self.master_casetiles.value = tileprops_dict

    def NEW_on_master_casetiles_update(self, new_master_casetiles):
        '''
        registered as the callback for 'self.master_casetiles' when the .value
        is changed. If a user has search-filters applied, they will be checked
        here and items that do not exist in 'self.search_results' will be 
        excluded from being rendered. The resulting 'tilesindex' list will be
        provided to the 'render_casetiles()' method to handle UI grid.
        '''
        # Get current 'order_rule' and 'search_results'
        o_rule = self.casetiles_order_rule
        search_res = self.search_results

        # Check active search filters and generate 'match_tiles' dict.
        # NOTE: 'match_tiles' and 'new_master_casetiles' have the same schema
        if search_res == None:
            print("CaseViewer: Search is NONE, not limiting results.")
            match_tiles = new_master_casetiles
        else:
            '''SEARCH FILTERS APPLIED - NEED TO REMOVE MISSING SR's'''
            match_tiles = {}
            for item in new_master_casetiles:
                #print('->', item)
                for sr in search_res:
                    if sr == item:
                        match_tiles[sr] = new_master_casetiles[item]

        # Pass 'match_tiles' to the correct 'o_rule' method to get the 
        # resulting 'tileindex' which will be used as the key to render the 
        # CaseTile widgets in order. 
        if o_rule == 'default':
            # Pass to 'age' method.
            tilesindex = self.NEW_build_tileindex_age(match_tiles)
        if o_rule == 'hasbug':
            # Pass to 'has-bug' method
            tilesindex = self.NEW_build_tileindex_hasbug(match_tiles)
        if o_rule == 'nobug':
            # Pass to 'has-bug' method
            tilesindex = self.NEW_build_tileindex_nobug(match_tiles)
        if o_rule == 'jiraneedinfo':
            # Pass to 'has-bug' method
            tilesindex = self.NEW_build_tileindex_jiraneedinfo(match_tiles)
        if o_rule == 'jiranotify':
            # Pass to 'has-bug' method
            tilesindex = self.NEW_build_tileindex_jiranotify(match_tiles)
        if o_rule == 'filenotify':
            # Pass to 'has-bug' method
            tilesindex = self.NEW_build_tileindex_filenotify(match_tiles)

        #DEBUG
        #print("*******")
        #print('\to_rule>', o_rule)
        #print('\tresult_inx', tilesindex)
        #print("*******")

        # Pass the 'tilesindex' index to 'render_casetiles()' to be drawn.
        self.NEW_render_casetiles(tilesindex)

    def NEW_create_new_casetile(self, key_value):
        '''
        Creates the new CaseTile Object using 'key_value' and appends the
        new values to 'master_casetiles' - triggering the callback.
        '''
        print('@NEW_create_new_casetile.key_value:', key_value)

    def NEW_render_casetiles(self, tilesindex):
        '''
        Actually draws the Casetiles within the 'master_frame.inner' 
        scrollable frame based on the order defined in the 'tilesindex'
        '''
        #print("*******")
        #print('\tresult_inx', tilesindex)
        #print("*******")

        # Remove GRID for each Tile.
        for wchild in self.master_frame.inner.winfo_children():
            wchild.grid_forget()

        for item in tilesindex:
            grid_index = item[0]
            sr = item[1]
            tk_widget = self.master_casetiles.value[sr]['widget']
            #print('\n**')
            #print('grid_index', grid_index)
            #print('sr', sr)
            #print('tk_widget', tk_widget)
            #print('**')
            ##### RENDER TO GRID #####
            tk_widget.grid(row=grid_index, column=0, padx=2,
                pady=1, sticky='nsew')

        self.master_frame._canvas.yview_moveto(0.0)
        self.master_frame._canvas.update_idletasks()

    # CasePoll Notifications
    def update_casetiles(self, CasePoll_results):
        '''
        Registered as a callback method whenever the 'CasePoll.results.value'
        changes.
        '''
        print(">>> CaseViewer >>>>")
        # Iterate through CasePoll Results and save the SR number (Key) from 
        # the dict where 'new_files' value is not None. The value is the num
        # of new files in the remote share since the 'last_ran_time' was 
        # updated

        ## DEBUG
        print('...\n')
        #print(self.master_casetiles.value)
        print('...\n')

        #{'4-21778380721': {'new_files': None, 'jira_id': None, 'jira_status': None}
        newfiles_lst = []
        for sr in CasePoll_results:
            if CasePoll_results[sr]['new_files'] != None:
                newfiles_lst.append(sr)
        #print("$.nflst", newfiles_lst)

        jirasts_lst = []
        for sr in CasePoll_results:
            if CasePoll_results[sr]['jira_status'] == 'Need Info':
                jirasts_lst.append(sr)

        # Update SR file notification for items newfiles_lst
        for sr in newfiles_lst:
            # Get index of Casetile Object if it matches the SR.
            print("$.newfiles_lst", sr)
            casetileobj = self.master_casetiles.value[sr]['widget']
            # enable CaseTile Notification icon
            casetileobj.enable_fnotification()

            # And caching to self.f_notification_tiles lst for future renders.
            if sr not in self.f_notification_tiles:
                self.f_notification_tiles.append(sr)

        # Update JIRA notification for sr in jirasts_lst
        for sr in jirasts_lst:
            # Get index of Casetile Object if it matches the SR.
            print("$.jirasts_lst", sr)

            casetileobj = self.master_casetiles.value[sr]['widget']
            # enable CaseTile Notification icon
            casetileobj.enable_jnotification()

            # And caching to self.f_notification_tiles lst for future renders.
            if sr not in self.j_notification_tiles:
                self.j_notification_tiles.append(sr)

    # ORDER METHODS
    def NEW_build_tileindex_age(self, new_master_casetiles):
        '''
        Orders tiles based on...
        - Pinned/Age
        - !Pinned/Age

        'widget': tk_widget,
        'pinned': item[1],
        'account': item[2],
        'product': item[3],
        'bug_id': item[4],
        'jira_status': item[5],  
        'jira_notify_flag': item[6],
        'file_notify_flag': item[7]         
        '''
        # Iterate checking if pinned and compiling two lists that will be 
        # used to build the final result.
        pinned_cases = []
        reg_cases = []        

        for sr in new_master_casetiles:
            if new_master_casetiles[sr]['pinned'] == 1:
                pinned_cases.append(sr)
            else:
                reg_cases.append(sr)
        
        # 'Age' is calculated based on the value of the SR number.
        # if the SR number is lower... this is an 'older' SR.
        final_index_lst = []
        index_cnt = 1
        for item in pinned_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1

        for item in reg_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1

        return final_index_lst

    def NEW_build_tileindex_hasbug(self, new_master_casetiles):
        '''
        Orders tiles based on...

        If there is a 'big_id' assigned.     
        '''
        # Iterate checking if pinned and compiling two lists that will be 
        # used to build the final result.
        pinned_cases = []
        reg_cases = []        
        for sr in new_master_casetiles:
            if new_master_casetiles[sr]['pinned'] == 1 and new_master_casetiles[sr]['bug_id'] != None:
                pinned_cases.append(sr)
            elif new_master_casetiles[sr]['bug_id'] != None:
                reg_cases.append(sr)

        final_index_lst = []
        index_cnt = 1
        for item in pinned_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1
        for item in reg_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1

        return final_index_lst

    def NEW_build_tileindex_nobug(self, new_master_casetiles):
        '''
        Orders tiles based on...

        If there is a 'bug_id' assigned.     
        '''
        # Iterate checking if pinned and compiling two lists that will be 
        # used to build the final result.
        pinned_cases = []
        reg_cases = []        
        for sr in new_master_casetiles:
            if new_master_casetiles[sr]['pinned'] == 1 and new_master_casetiles[sr]['bug_id'] == None:
                pinned_cases.append(sr)
            elif new_master_casetiles[sr]['bug_id'] == None:
                reg_cases.append(sr)

        final_index_lst = []
        index_cnt = 1
        for item in pinned_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1
        for item in reg_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1

        return final_index_lst

    def NEW_build_tileindex_jiraneedinfo(self, new_master_casetiles):
        '''
        Orders tiles based on...

        If 'jira_status' is 'Need Info'   
        '''
        # Iterate checking if pinned and compiling two lists that will be 
        # used to build the final result.
        pinned_cases = []
        reg_cases = []        
        for sr in new_master_casetiles:
            if (new_master_casetiles[sr]['pinned'] == 1 
                and new_master_casetiles[sr]['jira_status'] == 'Need Info'
                ):
                pinned_cases.append(sr)
            elif new_master_casetiles[sr]['jira_status'] == 'Need Info':
                reg_cases.append(sr)

        final_index_lst = []
        index_cnt = 1
        for item in pinned_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1
        for item in reg_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1

        return final_index_lst

    def NEW_build_tileindex_jiranotify(self, new_master_casetiles):
        '''
        Orders tiles based on...

        If 'jira_notify_flag' is 1  
        '''
        # Iterate checking if pinned and compiling two lists that will be 
        # used to build the final result.
        pinned_cases = []
        reg_cases = []        
        for sr in new_master_casetiles:
            if (new_master_casetiles[sr]['pinned'] == 1 
                and new_master_casetiles[sr]['jira_notify_flag'] == 1
                ):
                pinned_cases.append(sr)
            elif new_master_casetiles[sr]['jira_notify_flag'] == 1:
                reg_cases.append(sr)

        final_index_lst = []
        index_cnt = 1
        for item in pinned_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1
        for item in reg_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1

        return final_index_lst

    def NEW_build_tileindex_filenotify(self, new_master_casetiles):
        '''
        Orders tiles based on...

        If 'jira_notify_flag' is 1  
        '''
        # Iterate checking if pinned and compiling two lists that will be 
        # used to build the final result.
        pinned_cases = []
        reg_cases = []        
        for sr in new_master_casetiles:
            if (new_master_casetiles[sr]['pinned'] == 1 
                and new_master_casetiles[sr]['file_notify_flag'] == 1
                ):
                pinned_cases.append(sr)
            elif new_master_casetiles[sr]['file_notify_flag'] == 1:
                reg_cases.append(sr)

        final_index_lst = []
        index_cnt = 1
        for item in pinned_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1
        for item in reg_cases:
            index_set = (index_cnt, item)
            final_index_lst.append(index_set)
            index_cnt += 1

        return final_index_lst
    
    # Search Frame Methods.
    def clear_search_entry(self, event=None):
        # Clear Text if default and change entry color.
        if self.search_strVar.get() == self.default_search_str:
            self.search_strVar.set("")
        self.search_entry['justify'] = 'left'
        self.search_entry['fg'] = "#D0E2E4"

    def reset_search_entry(self, event=None):
        # Add Text only if empty and change entry Color
        if self.search_strVar.get() == "":
            self.search_strVar.set(self.default_search_str)
            self.search_entry['justify'] = 'center'
        self.search_entry['fg'] = "#8B9798"

    def update_search_pos(self, event=None):
        '''
        Method called from the main Gui class to update the Search frame view
        within the CaseViewer. The should be DB is updated BEFORE this method
        is called.
        '''
        if bcamp_api.get_config('ui_render_caseviewer_search') == "True":
            if bcamp_api.get_config('ui_caseviewer_search_location') == 'top':
                # Allow Row 1 to stretch for Master Frame.
                self.rowconfigure(0, weight=0)
                self.rowconfigure(1, weight=1)
                self.search_frame.grid(row=0, column=0, pady=(0,3), padx=(0,1), sticky="sew")
                self.master_frame.grid(row=1, column=0, sticky="nsew")
            elif bcamp_api.get_config('ui_caseviewer_search_location') == 'bottom':
                # Allow Row 0 to stetch for Master Frame.
                self.rowconfigure(0, weight=1)
                self.rowconfigure(1, weight=0)
                self.master_frame.grid(row=0, column=0, sticky="nsew")
                self.search_frame.grid(row=1, column=0, pady=(3,0), padx=(0,1), sticky="sew")       

        elif bcamp_api.get_config('ui_render_caseviewer_search') == "False":
            # Last Setting was "shown" - Remove Caseviewer Search...
            self.search_frame.grid_remove()
            # And render master_frame
            self.rowconfigure(0, weight=1)
            self.rowconfigure(1, weight=0)
            self.master_frame.grid(row=0, column=0, sticky="nsew")

    def run_search(self, event=None):
        '''
        Intialization method to read the user-defined query and return a new
        Caseviewer tileset based on the parameters. This method calls the API 
        to search through the DB to compile the returned list and then updates
        the Class' self.casetiles_callback - triggering the actual render of
        casetiles in the UI
        '''
        # First, get raw string from Entry...
        ui_query = self.search_strVar.get()
        # And Clear text from entry widget.
        self.search_strVar.set("")

        # Second, parse the raw string from the UI using the API. The returned
        # value already contains exisiting rules.
        if self.filterset_callback.value == "":
            filterset = {
                'account': [],
                'product': [],
                'tag': [],
                'custom': [],
                'o_rule': 'default'
            }
        elif self.filterset_callback.value != "":
            filterset = self.filterset_callback.value

        new_filterset = bcamp_api.parse_filter_search(ui_query, filterset)

        # Third, Update the 'filterset_callback.value' to trigger the callback
        # sent to the 'on_filterset_callback' method.
        self.filterset_callback.value = new_filterset

    ## Search/Filter Tiles Methods
    def on_filterset_callback(self, new_filterset):
        '''
        A callback method ran everytime the self.filterset_callback.value is 
        updated. This method is responsible for...

        1 - Creating the new filtertile widgets based on the 'new_filterset'
        2 - Resetting the CaseViewer when all filters are removed.
        3 - Querying the DB to get the returned list of CaseTiles based on filters.
        4 - Updating the CaseViewer tiles based on returned list from DB.

        The expected format for the filterset is...

            {
               'account':['str',],
               'product':['str',],
               'tag':['str',],
               'custom':['str',] 
            }
        '''
        # First - Create the filtertiles based on the self.cur_fileset
        self.create_filtertiles(new_filterset)

        # Second, actually search the DB using the API method, and return a
        # list of cases that match the defined filters.
        search_litmus = (
            new_filterset['account'] 
            + new_filterset['product'] 
            + new_filterset['tag'] 
            + new_filterset['custom']
        )
        if search_litmus != []: #empty list, bypass search.
            search_results = bcamp_api.search_cases(new_filterset)
            self.search_results = search_results
        else:
            self.search_results = None 

        # Finally, "update" 'master_casetiles' with the same OG value.
        # Search results will be parsed in 'on_master_casetiles_update()'
        self.master_casetiles.value = self.master_casetiles.value

    def create_filtertiles(self, new_filterset):
        '''
        Destroys all previous filter-tile widgets for the search function and
        redraws based on the query_set var.
        '''
        # Destory ALL THE THINGS (widgets)
        for widget in self.filter_subframe.winfo_children():
            widget.destroy()
            self.filter_subframe.update_idletasks()
        
        # Widget List for smart_grid later.
        widget_list = []
        # Create the FilterTiles based on 'new_filterset'
        account_lst = new_filterset['account']
        product_lst = new_filterset['product']
        tag_lst = new_filterset['tag']
        custom_lst = new_filterset['custom']
        o_rule = new_filterset['o_rule']

        ## Building 'casetiles_order_rule' filter for non-defaults
        if o_rule != 'default':
            print("RENDER O-RULE -->", o_rule)
            filter_tkObj = self.FilterTile_template(
                self.filter_subframe,
                'o_rule', 
                o_rule,
                self
                )
            widget_list.append(filter_tkObj)
        else:
            print("DEFAULT O-RULE, DO NOTHING?")


        ## Building account filter widgets...
        for item in account_lst:
            filter_tkObj = self.FilterTile_template(
                self.filter_subframe,
                'account', 
                item,
                self
                )
            widget_list.append(filter_tkObj)

        ## Building product filter widgets...
        for item in product_lst:
            filter_tkObj = self.FilterTile_template(
                self.filter_subframe,
                'product', 
                item,
                self
                )
            widget_list.append(filter_tkObj)    

        ## Building tag filter widgets...
        for item in tag_lst:
            filter_tkObj = self.FilterTile_template(
                self.filter_subframe,
                'tag', 
                item,
                self
                )
            widget_list.append(filter_tkObj)    

        ## Building custom filter widgets...
        for item in custom_lst:
            filter_tkObj = self.FilterTile_template(
                self.filter_subframe,
                'custom', 
                item,
                self
                )
            widget_list.append(filter_tkObj)    
        
        # Update filterfiles_obj list
        self.filtertiles_obj = widget_list
        # And render sub_frame.
        self.filter_subframe.grid()
        self.update_filtertiles_grid()
        
    def update_filtertiles_grid(self, event=None):
        '''
        Method responsible for controlling FilterTile Geometry.
        '''
        bcamp_api.smart_grid(self.filter_subframe, *self.filtertiles_obj, pady=3, padx=3)
    
    def remove_filtertile(self, target_widget, f_type, f_string):
        '''
        Called when a user hits the remove button on a filtertile widget. 
        Updates the 'filtertiles_obj' list and calls the 
        '''
        self.isFiltered = True
        # Removing widget from TK list.
        if target_widget in self.filtertiles_obj:
            temp_lst = self.filtertiles_obj
            temp_lst.remove(target_widget)
            self.filtertiles_obj = temp_lst
        
        # And removing filter from self.filterset_callback.
        if f_type != 'o_rule':
            new_f_set = self.filterset_callback.value
            removal_index = new_f_set[f_type].index(f_string)
            del new_f_set[f_type][removal_index]
            self.filterset_callback.value = new_f_set
        else:
            self.casetiles_order_rule = 'default'
            cur_filterset = self.filterset_callback.value
            cur_filterset['o_rule'] = 'default'
            self.filterset_callback.value = cur_filterset

        # Check if last widget was removed (i.e empty list.)
        if self.filtertiles_obj == []:
            self.reset_filtertiles()

    def reset_filtertiles(self):
        '''
        Called when there are no more filtertiles, this method hides the 
        'filtertile sub-frame' in the UI, and resets the filter allowing all
        cases to be shown again!
        '''
        self.isFiltered = False
        print("$reset_filtetiles called!")
        # First, hide the sub_frame.
        self.filter_subframe.grid_remove()
        # And redraw ALL imported cases as no more filters are present.
        # reset to init vals.
        self.search_results = None
        self.casetiles_order_rule = 'default'
        self.master_casetiles.value = self.master_casetiles.value

    def update_o_rule(self, o_rule):
        # get current filtertiles and modify 'o_rule' str.
        cur_filtertiles = self.filterset_callback.value 
        cur_filtertiles['o_rule'] = o_rule
        # Update class value 
        self.casetiles_order_rule = o_rule
        # Update filterset_callback with new o_rule value and trigger callback.
        self.filterset_callback.value = cur_filtertiles

    def update_search_pos(self, pos):
        # First, check if Caseviewer is rendered.
        if bcamp_api.get_config('ui_render_caseviewer_search') == "True":
            # If so, remove it, and move it!
            self.search_frame.grid_remove()
        if pos == 'top':
            bcamp_api.update_config('ui_caseviewer_search_location', 'top')
            self.update_search_pos()
        if pos == 'bottom':
            bcamp_api.update_config('ui_caseviewer_search_location', 'bottom')
            self.update_search_pos()

    def draw_searchmenu(self, event):
        self.searchmenu.post(
                event.x_root + 10, event.y_root + 10)

    # Refresh_callback method
    def _sb_refresh(self, event=None):
        self.Gui.CasePoll.start_manual_poll()


    #TK Definitions for CaseTile and Filter Tile Widgets
    class CaseTile_template(tk.Frame):
        '''
        Template for each "Case Tab" in CaseViewer

        index_num determines the tk.Grid placement for this template. This
        is the value determines what is shown (>0) and in what order (0-X)
        '''
        def __init__(self, master, key_value, CaseViewer):
            super().__init__(master=master)
            self.key_value = key_value
            self.master = master
            #self.workspace_man = workspace_man
            self.CaseViewer = CaseViewer
            self.RPATH = str(pathlib.Path(
                __file__).parent.absolute()).rpartition('\\')[0]
            
            # Tk Vars
            self.sub_frame_state = tk.BooleanVar()
            self.sub_frame_state.set(False)
            self.tag_obj_list = []
            self.sr_var = tk.StringVar()
            self.sr_var.set(self.key_value)
            self.notify_var = tk.StringVar()
            self.account_var = tk.StringVar()
            self.product_var = tk.StringVar()
            self.last_ran_var = tk.StringVar()
            self.imported_var = tk.StringVar()
            self.bug_var = tk.StringVar()
            self.sr_local_path = tk.StringVar()
            self.sr_remote_path = tk.StringVar()
            self.pin_unpin_var = tk.StringVar()
            self.open_create_local_var = tk.StringVar()
            ## Jira spec StringVars
            self.jira_status_var = tk.StringVar()
            self.jira_updated_var = tk.StringVar()
            self.jira_title_var = tk.StringVar()
            self.jira_last_comment_var = tk.StringVar()
            self.jira_last_comment_time_var = tk.StringVar()

            # Notification flags
            if self.key_value in self.CaseViewer.f_notification_tiles:
                self.fnotify_enable = True
            else:
                self.fnotify_enable = False

            if self.key_value in self.CaseViewer.j_notification_tiles:
                self.jnotify_enable = True
            else:
                self.jnotify_enable = False

            # Getting vals for SR. 
            self.sr_vals = bcamp_api.query_all_sr(self.key_value)
            self.remote_path = self.sr_vals[1]
            self.local_path = self.sr_vals[2]
            self.pinned = self.sr_vals[3]
            self.product = self.sr_vals[4]
            self.account = self.sr_vals[5]
            self.bug_id = self.sr_vals[7]

            # Determine if local path exist... for right click menu.
            if os.access(self.local_path, os.R_OK):
                self.open_create_local_var.set("Open Local Folder")
            else:
                self.open_create_local_var.set("Create Local Folder")
            self.sr_remote_path.set(self.remote_path)

            self.config_theme()
            self.config_widgets()
            self.config_grid()
            self.config_binds()
            self.refresh_tkVars() # update Record
            # Get tags, and pass to "render_tags" method.
            raw_tags = bcamp_api.query_tags(self.key_value)
            self.tag_tk_objs = self.render_tags(raw_tags)

        def config_theme(self):
            # Fonts
            self.sr_font = tk_font.Font(
                family="Segoe UI", size=15, weight="bold", slant="roman")
            self.mini_font = tk_font.Font(
                family="Segoe UI", size=9, weight="bold", slant="italic")
            self.sub_font = tk_font.Font(
                family="Segoe UI", size=11, weight="normal", slant="roman")
            self.bold_sub_font = tk_font.Font(
                family="Segoe UI", size=11, weight="bold", slant="roman")

            # Colors...
            self.act2 = "#E6BB43"
            self.basebg = "#1C1C16" #"#1D1E19"
            self.act300 = "#66D9EF"
            self.blk300 = "#B2B6BC"
            self.blk400 = "#717479"
            self.blk600 = "#141414"
            self.blk700 = "#0F1117"
            self.account_col = '#919288'

            # Notification Presets. 
            self.notify_nocol = self.basebg
            self.notify_grncol = "#A6E22E"
            self.notify_redcol = "#F92672"
            self.notify_yellcol = "#E6CD4A"

            ### "IMPORTANT/PINNED" SR Changes
            if self.pinned == 1: # True/False NA in SQLite3
                self.pin_unpin_var.set("Un-Pin SR")
                self.sr_text_color = "#E6CD4A"
            else:
                self.pin_unpin_var.set("Pin SR")
                self.sr_text_color = "#919288"

        def config_widgets(self):
            # Colors
            self.configure(background=self.basebg)
            self.master_frame = tk.Frame(
                self,
                background=self.basebg,
            )
            self.sr_frame = tk.Frame(
                self.master_frame,
                background=self.basebg,         
            )
            self.notify_icon = tk.Label(
                self.sr_frame,
                text="⬤",
                anchor="e",
                font=self.sr_font,
                background=self.basebg,
                foreground=self.notify_nocol, # hidden at first.
            )                
            self.sr_label = tk.Label(
                self.sr_frame,
                textvariable=self.sr_var,
                anchor="center",
                font=self.sr_font,
                background=self.basebg,
                foreground=self.sr_text_color,
            )
            self.options_button = tk.Button(
                self.sr_frame,
                text="☰",
                anchor="e",
                command=self.render_right_click_menu,
                relief='flat',
                #font=self.sub_font,
                background=self.basebg,
                foreground=self.basebg, # Start hidden.
                cursor="hand2"      
            )
            self.detail_frame = tk.Frame(
                self.master_frame,
                background=self.basebg,
            )
            self.account_label = tk.Label(
                self.detail_frame,
                textvariable=self.account_var,
                anchor="w",
                font=self.mini_font,
                background=self.basebg,
                foreground=self.account_col,
                cursor="hand2"    
            )
            self.product_label = tk.Label(
                self.detail_frame,
                textvariable=self.product_var,
                anchor="w",
                font=self.mini_font,
                background=self.basebg,
                foreground=self.act300,
                cursor="hand2"    
            )
            self.dropdown_button = tk.Button(
                self.master_frame,
                text="˅",
                command=self.render_sub_frame,
                relief='flat',
                font=self.sub_font,
                background=self.basebg,
                foreground=self.basebg, # Start hidden.
                cursor="hand2"                
            )
            # Frame "drop_down" when expanded.
            self.sub_frame = tk.Frame(
                self.master_frame,
                background=self.blk600,
            )
            self.tag_label = tk.Label(
                self.sub_frame,
                text="Tags :",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400
            )
            self.tags_frame = tk.Frame(
                self.sub_frame,
                background=self.blk600,
            )
            self.bug_label = tk.Label(
                self.sub_frame,
                text='JIRA :',
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.bug_button= tk.Button(
                self.sub_frame,
                textvariable=self.bug_var,
                background=self.blk600,
                foreground=self.act2,
                relief='flat',
                font=self.sub_font,
                command=self.launch_jira_browser,
                anchor='center'
            )
            self.last_ran_label = tk.Label(
                self.sub_frame,
                text="Last Ran :",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.last_ran_time_label = tk.Label(
                self.sub_frame,
                textvariable=self.last_ran_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.imported_label = tk.Label(
                self.sub_frame,
                text="Imported :",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.imported_time_label = tk.Label(
                self.sub_frame,
                textvariable=self.imported_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )

            # Tooltips Group
            self.tt_dropdown_button = CustomTk_ToolTip(self.dropdown_button, text='Show Details.')
            self.tt_account_label = CustomTk_ToolTip(self.account_label, text='Filter by Account.')
            self.tt_product_label = CustomTk_ToolTip(self.product_label, text='Filter by Product.')
            self.tt_bug_button = CustomTk_ToolTip(self.bug_button, text='Open JIRA in Browser.')
            self.tt_options_button = CustomTk_ToolTip(self.options_button, text='Options')
            self.tt_sr_label = CustomTk_ToolTip(self.sr_label, text='Open Workbench.')
            #self.tt_self = CustomTk_ToolTip(self, text='Open Workbench.')

            # Jira Frame - Hidden unless bug is added.
            '''
            self.jira_status_var = tk.StringVar()
            self.jira_updated_var = tk.StringVar()
            self.jira_title_var = tk.StringVar()
            self.jira_last_comment = tk.StringVar()
            self.jira_last_comment_time = tk.StringVar()
            '''

            self.jira_status_lbl = tk.Label(
                self.sub_frame,
                text="Status : ",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_status_data = tk.Label(
                self.sub_frame,
                textvariable=self.jira_status_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_updated_lbl = tk.Label(
                self.sub_frame,
                text="Updated :",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_updated_data = tk.Label(
                self.sub_frame,
                textvariable=self.jira_updated_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_title_lbl = tk.Label(
                self.sub_frame,
                text="Title :",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_title_data = tk.Label(
                self.sub_frame,
                textvariable=self.jira_title_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_cmmttime_lbl = tk.Label(
                self.sub_frame,
                text="Last Comment Time>",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_cmmttime_data = tk.Label(
                self.sub_frame,
                textvariable=self.jira_last_comment_time_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_cmmt_lbl = tk.Label(
                self.sub_frame,
                text="Comment>",
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
            )
            self.jira_cmmttime_data = tk.Label(
                self.sub_frame,
                textvariable=self.jira_last_comment_var,
                font=self.sub_font,
                background=self.blk600,
                foreground=self.blk400,
                anchor='center'
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
            self.master.columnconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.master_frame.grid(row=0, column=0, padx=2,
                pady=1, sticky='nsew')
            self.master_frame.columnconfigure(0, weight=1)
            
            # Master_Frame Content.
            self.sr_frame.grid(row=0, column=0, columnspan=2, padx=3, pady=3, sticky="nsew")
            self.sr_frame.columnconfigure(0, weight=1)
            self.sr_frame.columnconfigure(2, weight=1)
            self.notify_icon.grid(row=0, column=0, padx=(4,2), sticky="nse")
            self.sr_label.grid(row=0, column=1, sticky="nsew")
            self.options_button.grid(row=0, column=2, sticky="e")
            self.dropdown_button.grid(row=2, column=1, padx=5, pady=3,
                sticky="e")
            
            # Detail Frame Content.
            self.detail_frame.grid(row=2, column=0, columnspan=2,
                padx=5, pady=3, sticky="w")
            self.product_label.grid(row=0, column=0, sticky="w")
            self.account_label.grid(row=0, column=1, sticky="w")

            # Sub_frame Content.
            self.sub_frame.columnconfigure(0, weight=3)
            self.sub_frame.columnconfigure(1, weight=1)
            self.sub_frame.columnconfigure(2, weight=1)
            self.sub_frame.columnconfigure(3, weight=3)
            self.sub_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
            self.sub_frame.grid_remove()

            # Import Frame
            self.last_ran_label.grid(
                row=0, column=1, sticky='nsew'
                )
            self.last_ran_time_label.grid(
                row=0, column=2, sticky='nsew'
                )
            self.imported_label.grid(
                row=1, column=1, sticky='nsew'
                )
            self.imported_time_label.grid(
                row=1, column=2, sticky='nsew'
                )
            self.bug_label.grid(
                row=2, column=1, sticky='nsew'
                )
            self.bug_button.grid(
                row=2, column=2, sticky='nsew'
                )

            # JIRA Frame
            self.jira_status_lbl.grid(
                row=3, column=1, padx=0, pady=0, sticky='nsew'
                )
            self.jira_status_data.grid(
                row=3, column=2, padx=0, pady=0, sticky='nsew'
                )
            self.jira_updated_lbl.grid(
                row=4, column=1, padx=0, pady=0, sticky='nsew'
                )
            self.jira_updated_data.grid(
                row=4, column=2, padx=0, pady=0, sticky='nsew'
                )
            # Hiding by def.
            self.jira_status_lbl.grid_remove()
            self.jira_status_data.grid_remove()
            self.jira_updated_lbl.grid_remove()
            self.jira_updated_data.grid_remove()
            # TAGS FRAME
            self.tag_label.grid(
                row=5, column=1, sticky='nsew', pady=5
                )
            self.tags_frame.grid(
                row=5, column=2, sticky='nsew',  pady=5, padx=1
                )
            # Tag frame grid for resize.
            self.tags_frame.rowconfigure(0, weight=1)

        def config_binds(self):
            # Bindings to show dropdown...
            self.master_frame.bind('<Shift-Button-1>', self.render_sub_frame)
            self.sr_label.bind('<Shift-Button-1>', self.render_sub_frame)
            self.product_label.bind('<Shift-Button-1>', self.render_sub_frame)
            self.account_label.bind('<Shift-Button-1>', self.render_sub_frame)

            # Right Click_menu
            self.master_frame.bind('<Button-3>', self.draw_menu)
            self.sr_label.bind('<Button-3>', self.draw_menu)
            self.product_label.bind('<Button-3>', self.draw_menu)
            self.account_label.bind('<Button-3>', self.draw_menu)

            # Open Workspace
            self.master_frame.bind('<Double-1>', self.right_click_open)
            self.sr_label.bind('<Double-1>', self.right_click_open)

            # Filter By...
            self.product_label.bind('<Button-1>', self.product_clicked)
            self.account_label.bind('<Button-1>', self.account_clicked)

            # Show Options, Buttons
            self.master_frame.bind("<Enter>", self.show_tile_buttons)
            self.master_frame.bind("<Leave>", self.hide_tile_buttons)

            # Reside Tag_frame on configure (Resize)
            self.tags_frame.bind('<Configure>', self.update_tag_grid)




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
            # GET VALS FROM DB.
            new_sr_vals = bcamp_api.query_all_sr(self.key_value)
            new_remote_path = new_sr_vals[1]
            new_local_path = new_sr_vals[2]
            self.pinned_state = new_sr_vals[3]
            new_product = new_sr_vals[4]
            new_account = new_sr_vals[5]
            new_bug = new_sr_vals[7]
            new_import_time = new_sr_vals[10]
            new_last_ran_time = new_sr_vals[11]
            # JIRA starts at 13.
            jira_title = new_sr_vals[13]
            jira_status = new_sr_vals[14]
            jira_updated = new_sr_vals[15]
            jira_description = new_sr_vals[16]
            jira_sr_owner = new_sr_vals[17]
            jira_last_comment = new_sr_vals[18]
            jira_last_comment_time = new_sr_vals[19]
            # Notification Vals
            jira_notify_flag = new_sr_vals[27]
            file_notify_flag = new_sr_vals[28]
            #print('notifys(jira/file)', jira_notify_flag, file_notify_flag)

            # SETTING TK VARS WITH VALUES FROM DB.
            self.account_var.set(new_account)
            self.product_var.set(new_product)
            self.sr_local_path.set(new_local_path)
            self.sr_remote_path.set(new_remote_path)
            self.bug_var.set(new_bug)
            if self.bug_var.get() != "None":
                self.bug_button.configure(
                    cursor='hand2',
                    font=self.bold_sub_font
                )
                # Show JIRA widgets
                self.jira_status_lbl.grid()
                self.jira_status_data.grid()
                #self.jira_updated_lbl.grid()
                #self.jira_updated_data.grid()
            else:
                self.bug_button.configure(
                    state=tk.DISABLED,
                    font=self.sub_font
                )
            ## JIRA Subframe Vars
            self.jira_title_var.set(jira_title)
            self.jira_status_var.set(jira_status)             
            self.jira_updated_var.set(jira_updated)
            #self.jira_last_comment_var.set(jira_last_comment)
            self.jira_last_comment_time_var.set(jira_last_comment_time)

            ## Formatting Time Vals from DB.
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
            
            # Update Notification color if self.
            if file_notify_flag == 1:
                print('file_note_flag', self.key_value)
                self.notify_icon.configure(
                    foreground = self.notify_redcol
                )
                self.fnotify_enable = True
            
            if jira_notify_flag == 1:
                print('jira_notify_flag', self.key_value)
                self.dropdown_button.configure(
                    foreground = self.notify_redcol
                )
                self.jnotify_enable = True

            # FORMATTING COLORS BASED ON RESULTS.
            if jira_status == 'Need Info':
                self.jira_status_data.configure(
                    foreground = self.notify_redcol,
                    font = self.bold_sub_font
                )
                self.bug_button.configure(
                    foreground = self.notify_redcol,
                    font = self.bold_sub_font
                )
            elif jira_status == 'Ready For Engineering':
                self.jira_status_data.configure(
                    foreground = self.notify_grncol,
                    font = self.bold_sub_font
                )
                self.bug_button.configure(
                    foreground = self.notify_grncol,
                    font = self.bold_sub_font
                )                       
            elif jira_status == 'Ready For Work':
                self.jira_status_data.configure(
                    foreground = self.notify_yellcol,
                    font = self.bold_sub_font
                )
                self.bug_button.configure(
                    foreground = self.notify_yellcol,
                    font = self.bold_sub_font
                )
            else:
                self.jira_status_data.configure(
                    font=self.sub_font,
                    foreground=self.blk400,
                )
                self.bug_button.configure(
                    font=self.sub_font,
                    foreground=self.blk400,
                )            
            #UPDATE IDLETASKS INCASE CHANGES ARE MISSED
            #self.update_idletasks()
        
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
                            cursor='hand2'
                        )
                        tag_label.bind("<Button-1>", self.tag_clicked)
                        tag_labels.append(tag_label)
                        # Update
                        tag_label.update_idletasks()
            return tag_labels

        def update_tag_grid(self, event=None):
            '''
            Renders the tags based on the current tag_frame dimensions.
            '''
            self.tags_frame.update_idletasks()
            self.smart_grid(self.tags_frame, *self.tag_tk_objs, pady=3, padx=3)

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

        def show_tile_buttons(self, event=None):
            '''
            Changes the color of the Option/dropdown widgets so they can be 
            seen ONLY when moused over.
            '''
            self.options_button['fg'] = self.blk400
            if not self.jnotify_enable:
                self.dropdown_button['fg'] = self.blk400
            else:
                self.dropdown_button['fg'] = self.notify_redcol

        def hide_tile_buttons(self, event=None):
            '''
            Changes the color of the option/dropdown widgets to the bg color.
            '''
            self.options_button['fg'] = self.basebg
            if not self.jnotify_enable:
                self.dropdown_button['fg'] = self.basebg
            else:
                self.dropdown_button['fg'] = self.notify_redcol

        def tag_clicked(self, event):
            # Get Widget text
            selected_tag = (event.widget).cget('text')
            # Add to temp 'new_set' val.
            new_set = self.CaseViewer.filterset_callback.value
            new_set['tag'].append(selected_tag)
            # Update CaseViewer FilterSet.
            self.CaseViewer.filterset_callback.value = new_set

        def product_clicked(self, event):
            # Get Widget text
            selected_tag = (event.widget).cget('text')
            # Add to temp 'new_set' val.
            new_set = self.CaseViewer.filterset_callback.value
            new_set['product'].append(selected_tag)
            # Update CaseViewer FilterSet.
            self.CaseViewer.filterset_callback.value = new_set
            
        def account_clicked(self, event):
            # Get Widget text
            selected_tag = (event.widget).cget('text')
            # Add to temp 'new_set' val.
            new_set = self.CaseViewer.filterset_callback.value
            new_set['account'].append(selected_tag)
            # Update CaseViewer FilterSet.
            self.CaseViewer.filterset_callback.value = new_set

        def enable_fnotification(self):
            # Update value in DB.
            bcamp_api.update_case(self.key_value, 'file_notify_flag', 1)
            # Update UI
            self.notify_icon['foreground'] = self.notify_redcol
            self.fnotify_enable = True

        def disable_fnotification(self):
            # Update value in DB.
            bcamp_api.update_case(self.key_value, 'file_notify_flag', 0)
            # Update UI
            self.notify_icon['foreground'] = self.notify_nocol
            self.fnotify_enable = False
            # Remove from CaseViewer notify list
            try:
                self.CaseViewer.f_notification_tiles.remove(self.key_value)
            except ValueError: # When SR not in list.
                return

        def enable_jnotification(self):
            # Update value in DB.
            bcamp_api.update_case(self.key_value, 'jira_notify_flag', 1)
            # Update UI
            self.dropdown_button['foreground'] = self.notify_redcol
            self.jnotify_enable = True

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
                self.master.update_idletasks()
                self.master.event_generate("<Configure>")
            elif self.sub_frame_state.get() == True:
                self.sub_frame.grid_remove()
                self.sub_frame_state.set(False)
                self.master.update_idletasks()
                self.master.event_generate("<Configure>")

        def render_right_click_menu(self):
            # Get current edge of Tile...
            self.master_frame.update_idletasks()
            x = self.master_frame.winfo_rootx()
            y = self.master_frame.winfo_rooty()
            frame_w = self.master_frame.winfo_width()
            # Render Menu at edge
            self.right_click_menu.post(x + frame_w, y + 0)

        def draw_menu(self, event):
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
            self.CaseViewer.Gui.Workbench.render_workspace(self.key_value)
            #self.workspace_man.render_workspace(self.key_value)
            # Update Last ran time in DB.
            new_ran_time = datetime.datetime.now()
            new_ran_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            bcamp_api.update_case(self.key_value, "last_ran_time", new_ran_time)
            # Update the CaseTile Notification for new files.
            self.disable_fnotification()
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
                bcamp_api.update_case(self.key_value, 'pinned', 0)
            else: # Unpinned
                self.pinned_state = 1
                self.pin_unpin_var.set("Un-Pin SR")
                bcamp_api.update_case(self.key_value, 'pinned', 1)
            self.right_click_menu.update_idletasks()
            # Callback to Caseveiwer to redraw tiles.
            self.CaseViewer.NEW_gen_all_casetiles()

        def right_click_copy_sr(self, event=None):
            threading.Thread(target=bcamp_api.to_win_clipboard,
                args=[self.key_value]).start()

        def right_click_copy_remote(self, event=None):
            path = self.remote_path
            threading.Thread(target=bcamp_api.to_win_clipboard,
                args=[path]).start()

        def right_click_copy_local(self, event=None):
            # Get path of remote content from DB
            path = self.local_path
            threading.Thread(target=bcamp_api.to_win_clipboard,
                args=[path]).start()

        def right_click_reveal_remote(self, event=None):
            # Get path of remote content from DB
            os.startfile(self.sr_remote_path.get())

        def right_click_reveal_local(self, event=None):
            '''
            Opens the local folder. If it does not exist, creates it! 
            '''
            # Get path of remote content from DB
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
            edit_menu = self.CaseViewer.Tk_EditCaseMenu(self.key_value, self.CaseViewer)
            edit_menu.update_idletasks()
            w = edit_menu.winfo_width()
            h = edit_menu.winfo_height()
            edit_menu.geometry("%dx%d+%d+%d" % (w, h, x + frame_w + 2, y + 0))

            # Close SubFrame to prevent Geometry glitches.
            if self.sub_frame_state.get() == True:
                self.sub_frame.grid_remove()
                self.sub_frame_state.set(False)

        def right_click_delete(self, event=None):
            # Remove Frames
            self.master_frame.destroy()
            self.sub_frame.destroy()
            self.destroy()
            # Destorying SR contents.
            bcamp_api.destroy_sr(self.key_value)

        def right_click_save_all_notes(self, event=None):
            # Utilizing API to generate notes
            bcamp_api.create_allnotes_file(self.key_value)

        def right_click_save_case_notes(self, event=None):
            # Utilizing API to generate notes
            bcamp_api.create_casenotes_file(self.key_value)

        def right_click_clipboard_case_notes(self, event=None):
            casenotes_val = bcamp_api.query_case(self.key_value, 'notes')
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

                self.def_font = tk_font.Font(
                    family="Segoe UI", size=10, weight="normal", slant="roman")

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


    class Tk_EditCaseMenu(tk.Toplevel):
        '''
        Similar to the "ImportMenu" - but to edit exisiting Case records.
        '''
        def __init__(self, key_value, CaseViewer):
            super().__init__()
            self.key_value = key_value
            self.CaseViewer = CaseViewer

            #%%hex
            self.blk100 = "#EFF1F3"
            self.blk300 = "#B2B6BC"
            self.blk400 = "#717479"
            self.basebg = "#1E1F21" ##
            self.blk600 = "#15171C"
            self.blk700 = "#0F1117"
            self.blk900 = "#05070F"
            self.act300 = "#D5A336"

            #%%f
            self.sr_font = tk_font.Font(
                family="Segoe UI", size=14, weight="bold", slant="roman")
            self.mini_font = tk_font.Font(
                family="Segoe UI", size=8, weight="bold", slant="italic")
            self.sub_font = tk_font.Font(
                family="Segoe UI", size=10, weight="normal", slant="roman")


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
                background=self.basebg,
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
                background=self.basebg,
                foreground="#ffffff",
                width=12,
                relief='flat'
            )
            self.btn_cancel = tk.Button(
                self.buttons_frame,
                text="Cancel",
                command=self.destroy,
                background=self.basebg,
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

            bcamp_api.update_case_record(self.key_value, new_sr_dict)
            # Refresh Caseview Tiles.
            self.CaseViewer.NEW_gen_all_casetiles()

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
                return_val = account_val.strip()

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
                return_val = product_val.strip()

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
            bug_val = self.entry_bug.get()
            return_val = None
            if bug_val != "":
                return_val = bug_val.strip()

            return return_val


    class FilterTile_template(tk.Frame):
        '''
        Template for the filter widgets that appear after a query is ran in 
        search
        '''
        def __init__(self, parent_frame, f_type, f_string, CaseViewer):
            super().__init__(master=parent_frame)
            self.master = parent_frame
            self.f_type = f_type
            self.f_string = f_string
            self.CaseViewer = CaseViewer
            self.config_theme()
            self.config_widgets()
            self.config_grid()
        
        def config_widgets(self):
            self.config(
                bg=self.bg_col
            )
            self.f_string_label = tk.Label(
                self,
                text=self.f_string,
                bg=self.bg_col,
                fg=self.fg_col,
                font=self.def_font_bld
            )
            self.del_button = CustomTk_ButtonHover(
                self,
                text="X",
                bg=self.bg_col,
                fg=self.fg_col,
                relief='flat',
                command=self.remove_item,
                font=self.def_font,
                activebackground="#F92672"
            )
        
        def config_grid(self):
            self.f_string_label.grid(row=0, column=0)
            self.del_button.grid(row=0, column=1)

        def config_theme(self):
            '''
            Should be called BEFORE config_widgets. Defines theme details
            based on 'f_type'.
            '''
            ## DEFINE FONTS
            self.def_font = tk_font.Font(
                family="Segoe UI", size=10, weight="normal", slant="roman")
            self.def_font_bld = tk_font.Font(
                family="Segoe UI", size=10, weight="bold", slant="roman")

            ## DEFINE COLORS 
            if self.f_type == "product":
                self.fg_col = "#66D9E2"
                self.bg_col = "#1D1E19"
                self.tt_product = CustomTk_ToolTip(self, text='Product Filter')
            if self.f_type == "account":
                self.fg_col = "#F92672"  
                self.bg_col = "#1D1E19"
                self.tt_product = CustomTk_ToolTip(self, text='Account Filter')
            if self.f_type == "tag":
                self.fg_col = "#FD7C29"
                self.bg_col = "#1D1E19"
                self.tt_product = CustomTk_ToolTip(self, text='Tag Filter')
            if self.f_type == "custom":
                self.fg_col = "#E6CD4A"
                self.bg_col = "#1D1E19"       
                self.tt_product = CustomTk_ToolTip(self, text='Custom Filter')
            if self.f_type == "o_rule":
                self.bg_col = "#1D1E19"
                self.fg_col = "#A6E22E"
                self.tt_product = CustomTk_ToolTip(self, text='Order Rule')
        
        def remove_item(self):
            '''
            Deletes the filter from the UI, and updates the filter parameters
            '''
            # Remove widget
            self.destroy()
            # Then call the CaseViewer 'remove_filtertile' method.
            self.CaseViewer.remove_filtertile(self, self.f_type, self.f_string)


class Tk_TodoList(tk.Frame):
    '''
    This class defines the TK Frame for the TodoList. This class is init. in
    Gui, and is "add"ed as a child frame of the "Tk_RootPane" - Allowing
    users to resize this Frame, and other contents added to "Tk_RootPane".

    This initial implementation is simplified but will be added to later.
    '''
    def __init__(self, master, Gui):
        super().__init__(master=master)
        self.Gui = Gui
        # Class Vars
        self.todo_list = []
        # Tk def Methods.
        self.config_theme()
        self.config_widgets()
        self.config_grid()

    def config_theme(self):
        # Define Colors
        self.insertbg = "#E6CD4A"
        self.basebg = "#1D1E19"
        self.basefg = "#EDF2E0"
        self.topbg = "#3B3C35"
        self.topfg = "#EDF2E0"
        self.notify_grncol = "#A6E22E"
        self.notify_redcol = "#F92672"
        self.notify_yellcol = "#E6CD4A"

        # Setting Fonts
        self.def_font = tk_font.Font(
            family="Segoe UI", size=11, weight="normal", slant="roman")
        self.def_font_bld = tk_font.Font(
            family="Segoe UI", size=11, weight="bold", slant="roman")

    def config_widgets(self):
        self.configure(
            background=self.basebg
        )
        self.list_frame = tk.Frame(
            self,
            background=self.basebg
        )
        self.add_button = tk.Button(
            self,
            text="+",
            command=self.create_todo_object,
            background=self.basebg,
            foreground=self.basefg,
            font=self.def_font,
            relief='flat'
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
            super().__init__(master=master)
            # Tk Vars
            self.created_time_stringVar = tk.StringVar()
            # Set time for "created_time" Var
            datetimeObj = datetime.datetime.now()
            f_timestamp = datetimeObj.strftime("%d-%b-%Y (%H:%M:%S)")
            self.created_time_stringVar.set(f_timestamp)
            # Tk Methods
            self.config_theme()
            self.config_widgets()
            self.config_grid()

        def config_theme(self):
            # Define Colors
            self.insertbg = "#E6CD4A"
            self.basebg = "#1D1E19"
            self.basefg = "#EDF2E0"
            self.editbg = "#33352D"
            self.textfg = "#70ADB3"
            self.textbg = "#0F0F0C"
            self.topbg = "#272822"
            self.topfg = "#EDF2E0"
            self.notify_grncol = "#A6E22E"
            self.notify_redcol = "#F92672"
            self.notify_yellcol = "#E6CD4A"

            # Setting Fonts
            self.def_font = tk_font.Font(
                family="Segoe UI", size=11, weight="normal", slant="roman")
            self.def_font_bld = tk_font.Font(
                family="Segoe UI", size=11, weight="bold", slant="roman")
            self.text_font = tk_font.Font(
                family="Segoe UI", size=9, weight="normal", slant="roman")

        def config_widgets(self):
            self.configure(
                background=self.basebg
            )
            self.topbar_frame = tk.Frame(
                self,
                background=self.basebg
            )
            self.todo_text = tk.Text(
                self,
                height=5,
                insertbackground=self.insertbg,
                background=self.textbg,
                foreground=self.textfg,
                font=self.text_font,
                relief='flat',
                wrap='word'
            )
            self.created_time_label = tk.Label(
                self.topbar_frame,
                textvariable=self.created_time_stringVar,
                background=self.basebg,
                foreground=self.basefg,
                font=self.def_font,
                relief='flat'
            )
            self.edit_button = tk.Button(
                self.topbar_frame,
                text="Edit",
                command=self.enable_edit,
                background=self.editbg,
                foreground=self.basefg,
                #font=self.def_font,
                relief='flat'
            )
            self.remove_button = tk.Button(
                self.topbar_frame,
                text="✓",
                command=self.remove_todo,
                background=self.basebg,
                foreground=self.basefg,
                #font=self.def_font,
                relief='flat'
            )
        
        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.rowconfigure(1, weight=1)
            self.columnconfigure(0, weight=1)
            #self.grid(columnspan=3)
            self.topbar_frame.grid(row=0, column=0, sticky='new')
            self.topbar_frame.columnconfigure(0, weight=1)
            #
            #self.created_time_label.grid(
            #    row=0, column=0, sticky='nw'
            #)
            self.edit_button.grid(
                row=0, column=1, sticky="ne"
            )
            self.remove_button.grid(
                row=0, column=2, sticky="ne"
            )
            #
            self.todo_text.grid(
                row=1, column=0, sticky='nsew'
            )

        def enable_edit(self):
            print("$would enable_edit")

        def remove_todo(self):
            print("$would remove Item.")
  

'''Basecamp Workbench Tk/Tcl Frames'''
class Tk_WorkbenchTabs(tk.Frame):
    '''
    This renders the default, and new workspace tabs when a user imports new
    data, or recalls a previously worked item (Sr Number, Path, etc.) through
    the "Case Data" pane.

    Example.) Getting file_paths from <SR> for Treeview Rendering.
    '''
    # Tk_WorkbenchTabs Methods...
    def __init__(self, master, FileOpsQ, Gui):
        super().__init__(master=master)
        self.FileOpsQ = FileOpsQ
        self.Gui = Gui
        self.RPATH = str(pathlib.Path(
            __file__).parent.absolute()).rpartition('\\')[0]
        self.tab_id = tk.StringVar()
        self.open_tabs = ['+']
        # Rendering Tk Elements
        self.config_widgets()
        self.config_grid()
        self.focus_set()
        self.render_default_tab()

    # Ttk Config Methods
    def config_widgets(self):
        # Building "Notebook" for multiple SR's to tab through...
        self.blk100 = "#EFF1F3"
        self.blk300 = "#B2B6BC"
        self.blk400 = "#717479"
        self.basebg = "#1E1F21" ##
        self.blk600 = "#15171C"
        self.blk700 = "#0F1117"
        self.blk900 = "#05070F"
        self.act300 = "#D5A336"

        self.tab_notebook = ttk.Notebook(
            self,
            width=400,
            height=320,
        )
        self.tab_notebook.bind('<Button-3>', self.popup_menu)
        self.tab_notebook.bind('<Control-1>', self.ctrl_click_close)

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
            label="Close Tab",
            command=self.right_click_close
        )
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(
            label="Open Remote Folder",
            command=self.right_click_reveal_remote
        )
        self.right_click_menu.add_command(
            label="Open Local Folder",
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

    def ctrl_click_close(self, event):
        clicked_tab = self.tab_notebook.tk.call(
            self.tab_notebook._w, "identify", "tab", event.x, event.y)
        #print("$.tab", clicked_tab)
        self.tab_notebook.forget(clicked_tab)
        #print("$.o_tabs", self.open_tabs[1])
        self.open_tabs.pop(clicked_tab)

    def _LEGACY_update_case_template(self, widget):
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
                    # Flip the bool for target_pane[1] to Toggle 
                    print(target_pane[1])
                    if target_pane[1]: # True
                        new_pane_set = (target_pane[0], False)
                    else: # False
                        new_pane_set = (target_pane[0], True)
                    # Update self.template.value with changes...
                    temp_template = target_case.template.value
                    temp_template[col_index]['workpanes'][pane_index] = new_pane_set
                    # Update template.value...
                    # which calls targets init Tk_CaseWorkbench.render_panes"
                    target_case.template.value = temp_template

    # Called by Import_handler or opening a CaseView Tab
    def render_workspace(self, key_value):
        '''
        On new imports, or recalling previous SR's via the search pane, 
        the render_workspace method is called, intializing the Tk_CaseWorkbench
        class, and adding the frame to the "tab_notebook" widget.

        The open_tabs objects have the following format...

        ['+', ,('4-11111111111', <__main__.Tk_CaseWorkbench object 
            .!Tk_CaseWorkbench>, False)]
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
            # Key-Value passed to Tk_CaseWorkbench instance to render "
            # Workspace" template.
            new_tab_frame = Tk_CaseWorkbench(self.tab_notebook, key_value, 
                self, self.FileOpsQ, open_index, self.Gui)
            # Add Tab with new Workpane
            self.tab_notebook.add(
                new_tab_frame,
                text=key_value, # Tab Header
                padding=2,
                sticky='nsew'
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

    def render_default_tab(self):
        '''
        Creates a the default import tab when a new session is rendered.
        '''
        #self.default_tab(Tk_DefaultTab, self, "＋")
        #f_newtab = ttk.Frame(self.tab_notebook)
        ## Intialzing Default Tab Class with Args
        #target_frame(f_newtab, Tk_WorkbenchTabs)
        #self.tab_notebook.add(
        #    f_newtab,
        #    text=header
        #)

        new_tab_frame = Tk_DefaultTab(self.tab_notebook, self)
        # Add Tab with new Workpane
        self.tab_notebook.add(
            new_tab_frame,
            text=' + ', # Tab Header
            padding=2,
            sticky='nsew',
            #underline=1
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

    # Right-click Methods for selected tabs.
    def right_click_close(self):
        self.tab_notebook.forget(self.tab_id.get())
        self.open_tabs.pop(int(self.tab_id.get()))

    def right_click_copy_sr(self, event=None):
        sel_tabindx = int(self.tab_id.get())
        tab_keyval = self.open_tabs[sel_tabindx][0]
        tab_obj = self.open_tabs[sel_tabindx][1]
        threading.Thread(target=bcamp_api.to_win_clipboard,
            args=[tab_keyval,]).start()

    def right_click_copy_remote(self, event=None):
        sel_tabindx = int(self.tab_id.get())
        tab_keyval = self.open_tabs[sel_tabindx][0]
        tab_obj = self.open_tabs[sel_tabindx][1]
        path = bcamp_api.query_case(tab_keyval, 'remote_path')
        threading.Thread(target=bcamp_api.to_win_clipboard,
            args=[path]).start()

    def right_click_copy_local(self, event=None):
        sel_tabindx = int(self.tab_id.get())
        tab_keyval = self.open_tabs[sel_tabindx][0]
        tab_obj = self.open_tabs[sel_tabindx][1]
        # Get path of remote content from DB
        path = bcamp_api.query_case(tab_keyval, 'local_path')
        threading.Thread(target=bcamp_api.to_win_clipboard,
            args=[path]).start()

    def right_click_reveal_remote(self, event=None):
        sel_tabindx = int(self.tab_id.get())
        tab_keyval = self.open_tabs[sel_tabindx][0]
        tab_obj = self.open_tabs[sel_tabindx][1]
        # Get path of remote content from DB
        os.startfile(bcamp_api.query_case(tab_keyval, 'remote_path'))

    def right_click_reveal_local(self, event=None):
        sel_tabindx = int(self.tab_id.get())
        tab_keyval = self.open_tabs[sel_tabindx][0]
        tab_obj = self.open_tabs[sel_tabindx][1]
        '''
        Opens the local folder. If it does not exist, creates it! 
        '''
        # Get path of remote content from DB
        local_path = bcamp_api.query_case(tab_keyval, 'local_path')
        if os.access(local_path, os.R_OK):
            os.startfile(local_path)
        else:
            print("Local File Missing, creating it...")
            os.mkdir(local_path)
            os.startfile(local_path)


class Tk_DefaultTab(tk.Frame):
    '''
    The Default "import" tab. If no other workspaces are rendered,
    users will be presented with this Widget first.
    '''

    def __init__(self, master, Tk_WorkbenchTabs):
        super().__init__(master=master)
        self.Tk_WorkbenchTabs = Tk_WorkbenchTabs
        self.master = master

        self.config_theme()
        self.config_widgets()
        self.config_binds()
        self.config_grid()

    def config_theme(self):
        self.basefg = "#8B9798"
        self.basebg = "#24251F"
        self.def_font = tk_font.Font(
            family="Segoe UI", size=12, weight="normal", slant="roman")

    def config_widgets(self):
        self.configure(
            background=self.basebg,
            cursor="plus",            
        )
        self.label_one = tk.Label(
            self,
            text='Click anywhere here to import a new Case.',
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            cursor="plus",
            relief='flat',
            anchor='center'
        )
        self.label_two = tk.Label(
            self,
            text='Or use Ctrl+N.',
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            cursor="plus",
            relief='flat',
            anchor='center'
        )
        self.label_three = tk.Label(
            self,
            text="You may also import a 'list_of_cases.txt' using Ctrl+Click.",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            cursor="plus",
            relief='flat',
            anchor='center'
        )

    def config_binds(self):
        self.bind('<Button-1>', self.render_import_menu)
        self.bind('<Control-1>', self.direct_import_broswer)
        self.bind('<Control-Motion>', self.bulk_cursor)
        self.bind('<Motion>', self.default_cursor)

        self.label_one.bind('<Button-1>', self.render_import_menu)
        self.label_one.bind('<Control-1>', self.direct_import_broswer)
        self.label_one.bind('<Control-Motion>', self.bulk_cursor)
        self.label_one.bind('<Motion>', self.default_cursor)

        self.label_two.bind('<Button-1>', self.render_import_menu)
        self.label_two.bind('<Control-1>', self.direct_import_broswer)
        self.label_two.bind('<Control-Motion>', self.bulk_cursor)
        self.label_two.bind('<Motion>', self.default_cursor)

        self.label_three.bind('<Button-1>', self.render_import_menu)
        self.label_three.bind('<Control-1>', self.direct_import_broswer)
        self.label_three.bind('<Control-Motion>', self.bulk_cursor)
        self.label_three.bind('<Motion>', self.default_cursor)

    def config_grid(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        self.label_one.grid(row=1, column=0, sticky="nsew")
        self.label_two.grid(row=2, column=0, sticky="nsew", pady=2)
        self.label_three.grid(row=3, column=0, sticky="nsew")

    def render_import_menu(self, event=None):
        '''
        Renders the Import Menu within a new WorkspaceTabs Tab.
        '''
        self.Tk_WorkbenchTabs.import_tab()

    def direct_import_broswer(self, event=None):
        # Passing Args to API to do the actually work.
        bcamp_api.bulk_importer(Gui.import_item)

    def bulk_cursor(self, event=None):
        self['cursor'] = 'top_side'
        self.label_one['cursor'] = 'top_side'
        self.label_two['cursor'] = 'top_side'
        self.label_three['cursor'] = 'top_side'

    def default_cursor(self, event=None):
        self['cursor'] = 'plus'
        self.label_one['cursor'] = 'plus'
        self.label_two['cursor'] = 'plus'
        self.label_three['cursor'] = 'plus'


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

    def __init__(self, master, Tk_WorkbenchTabs, import_string, event=None):
        super().__init__(master=master)
        self.Tk_WorkbenchTabs = Tk_WorkbenchTabs
        self.import_string = import_string # Used to define what tab to remove
        self.advanced_opts_state = "off"
        self.notes_frame_state = "off"
        self.chkbtn_download_var = tk.IntVar()
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
                self.copy_alert.grid()
        except:
            print("Tk_ImportMenu failed to import Clipboard contents.")

    def config_widgets(self):
        bg_2 = "#111111"
        bg_1 = "#333333"
        bg_0 = "#272822"
        fg_0 = "#FFFFFF"
        self.grn_0 = "#badc58"
        def_font = tk_font.Font(
            family="Segoe UI", size=11, weight="normal", slant="roman")
        bb_font = tk_font.Font(
            family="Segoe UI", size=12, weight="normal", slant="roman")
        bold_font = tk_font.Font(
            family="Segoe UI", size=12, weight="bold", slant="roman")

        # Input Validation registration
        vcmd = (self.register(self.onValidate),
        '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

        # Main Widgets
        self.config(
            background=bg_0
        )
        self.sr_entry_frame = tk.Frame(
            self,
            background=bg_0
        )
        self.label_sr = tk.Label(
            self.sr_entry_frame,
            text="SR NUMBER ⮞",
            relief='flat',
            background=bg_0,
            foreground=fg_0,
            font=bold_font
        )
        self.entry_sr = tk.Entry(
            self.sr_entry_frame,
            width=24,
            relief='flat',
            font=bold_font,
            validate="key",
            validatecommand=vcmd,
            justify='center'
        )
        self.copy_alert = tk.Label(
            self.sr_entry_frame,
            text="Pasted from Clipboard",
            font=def_font,
            background=bg_0,
            foreground="#CBFF44",
        )
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
            foreground="#555555",
            font=def_font
        )

        # Bottom Bar Buttons
        self.bottom_bar_frame = tk.Frame(
            self,
            background="#3B3C35",
            relief='flat'
        )
        self.btn_browse = tk.Button(
            self.bottom_bar_frame,
            text="Bulk Import",
            command=self.open_bulk_importer,
            relief='flat',
            font=bb_font
        )
        self.btn_start = tk.Button(
            self.bottom_bar_frame,
            text="Import",
            command=self.start_import,
            relief='flat',
            font=bb_font,
            state="disabled"
        )

        # CaseNotes Block
        self.show_notes_btn = tk.Button(
            self,
            text="Case Notes",
            command=self.show_notes,
            relief='flat',
            background=bg_0,
            foreground=fg_0
        )
        self.notes_frame = tk.Frame(
            self,
            background=bg_0,
            relief='flat'
        )
        self.text_notes = tk.Text(
            self.notes_frame,
            relief='flat',
            height=20,
            background=bg_0,
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
            background=bg_0,
            foreground=fg_0
        )
        self.ext_opts_frame = tk.Frame(
            self,
            background=bg_0,
            relief='flat'
        )
        self.download_label = tk.Label(
            self.ext_opts_frame,
            text="Download Files : ",
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.download_chkbtn = tk.Checkbutton(
            self.ext_opts_frame,
            background=bg_0,
            font=def_font,
            variable=self.chkbtn_download_var,
            onvalue=1,
            offvalue=0
        )
        self.label_account = tk.Label(
            self.ext_opts_frame,
            text="Account :",
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.combox_account = CustomTk_autoEntry(
            self.ext_opts_frame,
            width=29,
            background=bg_0,
            font=def_font
        )
        self.label_product = tk.Label(
            self.ext_opts_frame,
            text="Product :",
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.combox_product = CustomTk_autoEntry(
            self.ext_opts_frame,
            width=29,
            background=bg_0,
            font=def_font
        )
        self.label_bug = tk.Label(
            self.ext_opts_frame,
            text="JIRA/Bug ID :",
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.entry_bug = ttk.Entry(
            self.ext_opts_frame,
            width=29,
            font=def_font
        )
        self.label_tags = tk.Label(
            self.ext_opts_frame,
            text="Tag(s) :",
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.entry_tags = ttk.Entry(
            self.ext_opts_frame,
            width=29,
            font=def_font
        )
        self.label_workspace = tk.Label(
            self.ext_opts_frame,
            text="Default Workspace :",
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.combox_workspace = ttk.Combobox(
            self.ext_opts_frame,
            width=26,
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.label_customs = tk.Label(
            self.ext_opts_frame,
            text="Custom Path(s):",
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.label_hint1 = tk.Label(
            self.ext_opts_frame,
            text="Use ',' to seperate Tags",
            anchor=tk.CENTER,
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )
        self.entry_customs = ttk.Entry(
            self,
            width=29,
            background=bg_0,
            foreground=fg_0,
            font=def_font
        )

        # Populating Autofill record
        # Setting auto-complete list
        account_autofill = bcamp_api.query_cases_distinct('account')
        product_autofill = bcamp_api.query_cases_distinct('product')
        self.combox_account.set_completion_list(tuple(account_autofill))
        self.combox_product.set_completion_list(tuple(product_autofill))

    def config_grid(self):
        '''
        Defines Grid layout for Tk.Widgets defined in init.
        '''
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Main Widgets
        self.sr_entry_frame.grid(
            row=1, column=0, sticky="nsew"
        )
        self.ext_opts_frame.grid(
            row=2, column=0, columnspan=2, padx=4, pady=(20,0), sticky="nsew")
        self.bulk_hint.grid(
            row=3, column=0, columnspan=2, padx=4, pady=(20,0), sticky="ew")
        self.bottom_bar_frame.grid(
            row=4, column=0, columnspan=2, padx=4, pady=4, sticky="sew")

        # Sr Entry Frame contents
        self.sr_entry_frame.columnconfigure(0, weight=1)
        self.label_sr.grid(
            row=0, column=0, padx=5, pady=4, sticky="e", ipady=10)
        self.entry_sr.grid(
            row=0, column=1, padx=5, pady=2, sticky="w")
        #self.entry_sr_clear.grid(
        #    row=0, column=2, padx=8, pady=2, sticky="w")    
        self.copy_alert.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.copy_alert.grid_remove()

        # ext_opts_frame contents
        self.ext_opts_frame.columnconfigure(0, weight=1)
        self.ext_opts_frame.columnconfigure(1, weight=1)

        self.label_account.grid(
            row=4, column=0, padx=4, pady=2, sticky="e")
        self.combox_account.grid(
            row=4, column=1, padx=4, pady=2, sticky="w")

        self.label_product.grid(
            row=5, column=0, padx=4, pady=2, sticky="e")
        self.combox_product.grid(
            row=5, column=1, padx=4, pady=2, sticky="w")

        self.label_bug.grid(
            row=6, column=0, padx=4, pady=2, sticky="e")
        self.entry_bug.grid(
            row=6, column=1, padx=4, pady=2, sticky="w")

        self.label_tags.grid(
            row=7, column=0, padx=4, pady=2, sticky="e")
        self.entry_tags.grid(
            row=7, column=1, padx=4, pady=2, sticky="w")
        self.download_label.grid(
            row=8, column=0, padx=4, pady=2, sticky="e")
        self.download_chkbtn.grid(
            row=8, column=1, padx=4, pady=2, sticky="w")
        self.label_hint1.grid(
            row=12, column=0, columnspan=2, padx=4, pady=2, sticky="nsew")


        # Browse/Start Buttons
        self.bottom_bar_frame.columnconfigure(0, weight=1)
        self.btn_browse.grid(
            row=0, column=0, padx=4, pady=4, sticky="e")
        self.btn_start.grid(
            row=0, column=1, padx=4, pady=4, sticky="w")

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

    def open_bulk_importer(self):
        bcamp_api.bulk_importer(Gui.import_item)
        # Removing "import" from Tk_WorkbenchTabs.open_tabs
        pop_index = next((i for i, item in enumerate(self.Tk_WorkbenchTabs.open_tabs) if item[0] == self.import_string), None)
        del self.Tk_WorkbenchTabs.open_tabs[pop_index]
        # Closing window...
        self.destroy()

    def start_import(self, event=None):
        # Creating "import_item" Dictionary
        new_import_dict = {
            'type':'single', 
            'case_data': [{
                'sr_number': self.entry_sr.get(),
                'pinned': self.chkbtn_fav_var.get(),
                'product': self.get_product(),
                'account': self.get_account(),
                'bug_id': self.get_bug(),
                'workspace': self.get_workspace(),
                'tags_list': self.get_tags(),
                'customs_list': self.get_customs(),
                'notes': self.get_notes(),
                'download_flag': self.chkbtn_download_var.get()
            }]
        }

        # Updating "import_item" -> Gui.import_handler(new_import_dict)
        Gui.import_item.value = new_import_dict
        # Removing "import" from Tk_WorkbenchTabs.open_tabs
        pop_index = next((i for i, item in enumerate(self.Tk_WorkbenchTabs.open_tabs) if item[0] == self.import_string), None)
        del self.Tk_WorkbenchTabs.open_tabs[pop_index]
        # Closing window...
        self.destroy()

    def clear_sr_entry(self):
        '''
        Removes the value stored in the SR entry field.
        '''
        print("!")
        self.entry_sr.delete(0, 'end')

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

    #Input Validation
    def onValidate(self, d, i, P, s, S, v, V, W):
        '''
        valid percent substitutions (from the Tk entry man page)
        note: you only have to register the ones you need; this
        example registers them all for illustrative purposes

        %d = Type of action (1=insert, 0=delete, -1 for others)
        %i = index of char string to be inserted/deleted, or -1
        %P = value of the entry if the edit is allowed
        %s = value of entry prior to editing
        %S = the text string being inserted or deleted, if any
        %v = the type of validation that is currently set
        %V = the type of validation that triggered the callback
            (key, focusin, focusout, forced)
        %W = the tk name of the widget   
        '''
        #Sub-method to enable or disable the import button
        def enable_importBtn():
            self.btn_start["state"] = "normal"
            self.btn_start["background"] = self.grn_0

        def disable_importBtn():
            self.btn_start["state"] = "disabled"
            self.btn_start["background"] = "#F0F0F0"

        # Input Val Filters         
        if int(i) > 12: 
            # Limit input to 13 chars.
            disable_importBtn()
            return False
        elif S.isnumeric() or S == "-" and i == "1": 
            # Allows input of numbers or '-'
            self.copy_alert.grid_remove()
            # Check len to determine if import should be enabled.
            if int(i) == 12 and int(d) == 1:
                enable_importBtn()
            else:
                disable_importBtn()
            return True
        elif len(P) == 13 and "4-" in P:
            # Allows for user to copy SR into field.
            self.copy_alert.grid()
            enable_importBtn()
            return True
        else:
            return False # General False for outliers


class Tk_CaseWorkbench(tk.Frame):
    '''
    The Main Frame that contains all Workpanes, for a target SR.

    This class also contains the default Workpane template for new imports, 
    and the methods to Hide/Show Workpanes when a user interacts with the UI.
    '''
    # Tk_CaseWorkbench Methods...

    def __init__(self, master, key_value, WorkspaceTabs, FileOpsQ, tab_index, Gui):
        super().__init__(master=master)
        # Vars
        self.master = master
        self.Gui = Gui
        self.key_value = key_value
        self.WorkspaceTabs = WorkspaceTabs
        self.FileOpsQ = FileOpsQ
        self.tab_index = tab_index
        self.RPATH = str(pathlib.Path(
            __file__).parent.absolute()).rpartition('\\')[0]
        self.frame_list = []
        self.open_panes = []
        self.fb_cur_sel = bcamp_api.callbackVar()

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
                {
                    'index': 3,
                    'workpanes': [('default_jira', False), ]
                },
            ]

        # Check if item has a bug to hide JIRA button.
        self.bugid = bcamp_api.query_case(self.key_value, 'bug_id')

        # Methods
        self.config_widgets()
        self.config_grid()
        self.config_binds()
        self.template = bcamp_api.callbackVar()
        self.template.register_callback(self.render_panes)
        self.template.value = self.get_template()

    # Tk Methods
    def config_widgets(self):
        # Fonts
        self.def_font = tk_font.Font(
            family="Segoe UI", size=8, weight="bold", slant="roman")
        
        # Colors
        self.main_bg = "#414438"
        #self.active_bg = "#10100D"
        self.enabled_bg = "#1D1E19"
        self.enabled_txt = "#A6E22E"
        self.active_bg = "#1D1E19"   #"#52564A"
        self.active_txt = "#FDFFD0" #"#141414"
        self.spacer_col = "#000000"

        # Panedwindow
        self.main_pane = tk.PanedWindow(
            self,
            background="#10100B",
            bd=0,
            sashwidth=2,
            #showhandle=True
        )

        # NOTE - When attempting to render the template within a loop,
        # performance was impacted after 15 cycles, likely due to a memory
        # leak or some other error in the [Python -> Tk/Tcl -> C] transfer
        # Programmer included :). As a result, I am "hardcoding" the
        # Workbench to 4 columns.

        self.main_col0 = tk.PanedWindow(
            self.main_pane,
            background=self.spacer_col,
            bd=0,
            orient='vertical',
            sashwidth=2,
            #showhandle=True
        )
        self.main_col1 = tk.PanedWindow(
            self.main_pane,
            background=self.spacer_col,
            bd=0,
            orient='vertical',
            sashwidth=2,
            #showhandle=True
        )            
        self.main_col2 = tk.PanedWindow(
            self.main_pane,
            background=self.spacer_col,
            bd=0,
            orient='vertical',
            sashwidth=2,
            #showhandle=True
        )
        self.main_col3 = tk.PanedWindow(
            self.main_pane,
            background=self.spacer_col,
            bd=0,
            orient='vertical',
            sashwidth=2,
            #showhandle=True
        )
        # Intializing Frames
        self.tk_file_browser = Tk_FileBrowser(self.main_col0, self.key_value, self.FileOpsQ, self)
        self.tk_log_viewer = Tk_LogViewer(self.main_col1, self.key_value, self.FileOpsQ, self, self.Gui)
        self.tk_case_notes = Tk_CaseNotes(self.main_col2, self.key_value)                    
        self.tk_file_notes = Tk_FileNotes(self.main_col2, self.key_value, self.FileOpsQ, self, None)
        self.tk_jira = Tk_JiraSummary(self.main_col3, self.key_value)
        # "Adding" to Panedwindow - Similar to Grid or Pack in TcL/Tk
        self.main_col0.add(self.tk_file_browser, stretch="always")
        self.main_col1.add(self.tk_log_viewer, stretch="always")
        self.main_col2.add(self.tk_case_notes, stretch="always")
        self.main_col2.add(self.tk_file_notes, stretch="always")
        self.main_col3.add(self.tk_jira, stretch="always")


        # Top Bar to render different columns
        self.toolbar_frame = tk.Frame(
            self,
            bg=self.main_bg
        )

        # PANES SUBFRAME
        self.toolbar_panes_frame = tk.Frame(
            self.toolbar_frame,
            bg=self.main_bg
        )
        self.tb_spacer = tk.Frame(
            self.toolbar_frame,
            bg=self.spacer_col,
            height=1
        )
        self.fb_btn = tk.Button(
            self.toolbar_panes_frame,
            text="FILEBROWSER",
            bg=self.main_bg,
            fg=self.main_bg,
            relief='flat',
            width=20,
            font=self.def_font,
            cursor='hand2',
            command=lambda widget='default_filebrowser': self.update_pane_template(widget)
        )
        self.lv_btn = tk.Button(
            self.toolbar_panes_frame,
            text="LOGVIEWER",
            bg=self.main_bg,
            fg=self.main_bg,
            relief='flat',
            width=20,
            font=self.def_font,
            cursor='hand2',
            command=lambda widget='default_logview': self.update_pane_template(widget)
        )
        self.cn_btn = tk.Button(
            self.toolbar_panes_frame,
            text="CASENOTES",
            bg=self.main_bg,
            fg=self.main_bg,
            relief='flat',
            width=20,
            font=self.def_font,
            cursor='hand2',
            command=lambda widget='default_casenotes': self.update_pane_template(widget)
        )
        self.fn_btn = tk.Button(
            self.toolbar_panes_frame,
            text="FILENOTES",
            bg=self.main_bg,
            fg=self.main_bg,
            relief='flat',
            width=20,
            font=self.def_font,
            cursor='hand2',
            command=lambda widget='default_filenotes': self.update_pane_template(widget)
        )
        self.ji_btn = tk.Button(
            self.toolbar_panes_frame,
            text="JIRA",
            bg=self.main_bg,
            fg=self.main_bg,
            relief='flat',
            width=20,
            font=self.def_font,
            cursor='hand2',
            command=lambda widget='default_jira': self.update_pane_template(widget)
        )
        # OPTIONS SUBFRAME
        self.toolbar_opts_frame = tk.Frame(
            self.toolbar_frame,
            bg=self.main_bg
        )
        self.options_btn = tk.Button(
            self.toolbar_opts_frame,
            text="☰",
            bg=self.main_bg,
            fg=self.active_txt,
            relief='flat',
            #font=self.def_font
        )
        self.close_btn = tk.Button(
            self.toolbar_opts_frame,
            text="X",
            bg=self.main_bg,
            fg=self.active_txt,
            relief='flat',
            font=self.def_font,
            command=self.close_workspace,
            cursor='hand2',
        )

        # Tooltip Group
        self.tt_close_btn = CustomTk_ToolTip(self.close_btn, text='Close Workbench')

    def config_grid(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        # Default order of toolbar is on TOP
        self.toolbar_frame.grid(
            row=0, column=0, sticky="new"
        )
        self.main_pane.grid(
            row=1, column=0, sticky='nsew'
        )

        self.toolbar_frame.columnconfigure(0, weight=1)
        self.tb_spacer.grid(row=1, column=0, columnspan=2, sticky="nsew")
        # Toolbar Panes Grid
        self.toolbar_panes_frame.grid(
            row=0, column=0, sticky="nsw"
        )
        self.fb_btn.grid(
            row=0, column=0, padx=3, pady=3, sticky="nsw"
        )
        self.lv_btn.grid(
            row=0, column=1, padx=3, pady=3, sticky="nsw"
        )
        self.cn_btn.grid(
            row=0, column=2, padx=3, pady=3, sticky="nsw"
        )
        self.fn_btn.grid(
            row=0, column=3, padx=3, pady=3, sticky="nsw"
        )
        if self.bugid != None:
            self.ji_btn.grid(
                row=0, column=4, padx=3, pady=3, sticky="nsw"
            )
        # Toolbar Options Frame
        self.toolbar_opts_frame.grid(
            row=0, column=1, sticky="nse"
        )
        #self.options_btn.grid(
        #    row=0, column=0, padx=3, pady=3, sticky="nsw"
        #)
        self.close_btn.grid(
            row=0, column=1, padx=3, pady=3, sticky="nse"
        )

    def config_binds(self):
        self.main_pane.bind("<Double-1>", self.auto_resize_pane)
        self.toolbar_frame.bind("<Enter>", self.set_toolbar_colors)
        self.toolbar_frame.bind("<Leave>", self.reset_toolbar_colors)

    def get_template(self):
        db_template = bcamp_api.query_case(self.key_value, 'workspace')
        if db_template == None:  # Not specified on import.
            return self.default_template
        else:
            #Deserialize 'pickle' Binary Object back to python Dict.
            return pickle.loads(db_template)

    def render_panes(self, template):
        '''
        This method translates the datastore "workspace" template
        and renders the actual horizontal panes, vertical panes.

        Also updates the toolbar pane color sets based on what is enabled
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
            elif index == 1:
                columnpane = self.main_col1
            elif index == 2:
                columnpane = self.main_col2
            elif index == 3:
                columnpane = self.main_col3

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
                    if pane_class[0] == 'default_jira':
                        rendered_pane = self.tk_jira

                    if pane_class[1] == True:
                        columnpane.paneconfigure(rendered_pane, hide=False, stretch="always")
                        # Append pane name to 'open_panes' for UI colors
                        # if not already in list to prevent dupes
                        if pane_class[0] not in self.open_panes:
                            self.open_panes.append(pane_class[0])
                    else:
                        columnpane.paneconfigure(rendered_pane, hide=True)
                        ### # Remove from 'open_panes'
                        ### try:
                        ###     self.open_panes.remove(pane_class[0])
                        ### except:
                        ###     # Errors thrown if item does not exist in list,
                        ###     # which is expected on intial render.
                        ###     pass 
                        hidden_pane_count += 1
                    
                # "Place" columnpane now with rendered frame, into
                # the *main_pane* Panedwindow. Note indent.
                #print("Hidden Cnt >", hidden_pane_count)
                if hidden_pane_count == len(columnpane.winfo_children()): # All panes are hidden
                    self.main_pane.paneconfigure(columnpane, hide=True)
                else:
                    main_pane_width = self.master.winfo_width()
                    self.main_pane.paneconfigure(columnpane, hide=False)
                    self.main_pane.add(columnpane, stretch='always', minsize=10, width=main_pane_width/4)


        # Save new template into Sqlite3 DB
        print("SQLite3: Saving template changes to DB for", self.key_value)
        binary_template = pickle.dumps(template)
        bcamp_api.update_case(self.key_value, 'workspace', binary_template)

    def auto_resize_pane(self, event):
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

    def set_toolbar_colors(self, event=None):
        '''
        Sets the Colors of the TK widgets so that can be visible when a user
        mouses over the toolbar as they are "hidden" by default.
        '''
        # Default Colors on enter - will override if enabled shortly.
        self.fb_btn['bg'] = self.active_bg
        self.fb_btn['fg'] = self.active_txt
        self.lv_btn['bg'] = self.active_bg
        self.lv_btn['fg'] = self.active_txt
        self.cn_btn['bg'] = self.active_bg
        self.cn_btn['fg'] = self.active_txt
        self.fn_btn['bg'] = self.active_bg
        self.fn_btn['fg'] = self.active_txt
        self.ji_btn['bg'] = self.active_bg
        self.ji_btn['fg'] = self.active_txt

        # Get items in 'self.open_panes' as these will have a different
        # color set than the hidden panes.
        if "default_filebrowser" in self.open_panes:
            self.fb_btn['bg'] = self.enabled_bg
            self.fb_btn['fg'] = self.enabled_txt

        if "default_logview" in self.open_panes:
            self.lv_btn['bg'] = self.enabled_bg
            self.lv_btn['fg'] = self.enabled_txt

        if "default_casenotes" in self.open_panes:
            self.cn_btn['bg'] = self.enabled_bg
            self.cn_btn['fg'] = self.enabled_txt

        if "default_filenotes" in self.open_panes:
            self.fn_btn['bg'] = self.enabled_bg
            self.fn_btn['fg'] = self.enabled_txt

        if "default_jira" in self.open_panes:
            self.ji_btn['bg'] = self.enabled_bg
            self.ji_btn['fg'] = self.enabled_txt

    def reset_toolbar_colors(self, event):
        '''
        Sets the Colors of the TK widgets so that they are HIDDEN.
        '''
        self.fb_btn['bg'] = self.main_bg
        self.fb_btn['fg'] = self.main_bg
        self.lv_btn['bg'] = self.main_bg
        self.lv_btn['fg'] = self.main_bg
        self.cn_btn['bg'] = self.main_bg
        self.cn_btn['fg'] = self.main_bg
        self.fn_btn['bg'] = self.main_bg
        self.fn_btn['fg'] = self.main_bg
        self.ji_btn['fg'] = self.main_bg
        self.ji_btn['bg'] = self.main_bg        

    def update_pane_template(self, widget):
        '''
        Bind method when user selects one of the Workpane tiles in the 
        toolbar. This will update the 'self.template' with an updated dictObj,
        either showing or hiding the selected widget, and call the 
        'set_toolbar_colors' method for UI updates. 
        '''
        # Get dictionary object of target Case & Widget.
        for col_dict in self.template.value:
            pane_index = -1 # Offset from 0
            for workpane in col_dict["workpanes"]:
                pane_index += 1
                if workpane[0] == widget:
                    col_index = col_dict["index"]
                    # Create a copy of self.template
                    target_pane = self.template.value[col_index]['workpanes'][pane_index]
                    # Flip the bool for target_pane[1] to Toggle 
                    if target_pane[1]: # Shown = True
                        new_pane_set = (target_pane[0], False)
                        # We can remove item safely here as rendered frames
                        # are added to self.open_panes during init.
                        #
                        # target_pane[0] = 'default_x' pane name.
                        self.open_panes.remove(target_pane[0])

                    else: # Hidden = False
                        new_pane_set = (target_pane[0], True)
                    # Update self.template.value with changes...
                    temp_template = self.template.value
                    temp_template[col_index]['workpanes'][pane_index] = new_pane_set
                    # Update template.value...
                    # which calls targets init Tk_CaseWorkbench.render_panes"
                    self.template.value = temp_template

        # And call set_toolbar_colors to render the new UI colors.
        self.set_toolbar_colors()

    def close_workspace(self, event=None):
        # First, define index of tab.
        pop_index = next(
            (i for i, item in enumerate(self.WorkspaceTabs.open_tabs) if item[0] == self.key_value), None)
        # Remove Tab from UI
        self.WorkspaceTabs.tab_notebook.forget(pop_index)
        # And update the 'open_tabs' so the indexes are accurate later.
        del self.WorkspaceTabs.open_tabs[pop_index]


'''Basecamp Workpanes Tk/Tcl Frames'''
class Tk_FileBrowser(tk.Frame):
    '''
    A Default Workpane that displays files found in the remote and
    local folders. This also contains the "Favorites" tree, and 
    the "QueueManager" for unpack and download operations against
    files in the trees.

    TODO - *RANGE* scanning for .log or .dbg* files needs to be complete. - On hold for beta.
    '''

    def __init__(self, master, key_value, FileOpsQ, Tk_CaseWorkbench):
        super().__init__(master=master)
        self.master = master
        self.key_value = key_value
        self.FileOpsQ = FileOpsQ
        self.case_frame = Tk_CaseWorkbench

        # Getting install dir path...
        self.RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]

        # Get time_format from config
        self.time_zone = bcamp_api.get_config('time_zone')
        self.time_format = bcamp_api.get_config('time_format')
        self.show_favTree = bcamp_api.get_config('ui_render_favtree')
        # Get Remote root path for 'key_value'
        self.sr_remote_path = bcamp_api.query_case(self.key_value, "remote_path")
        self.sr_local_path = bcamp_api.query_case(self.key_value, "local_path")

        # Toggle FavTree Var
        self.show_favTree = bcamp_api.callbackVar()
        self.show_favTree.value = bcamp_api.get_config("ui_render_favtree")
        self.show_favTree.register_callback(self.render_favTree)

        # Show Scrollbar for File/Fav Tree
        self.show_ysb_intvar = tk.IntVar()
        self.show_ysb_intvar.set(0)

        # Building Tk Elements
        self.config_widgets()
        self.config_treecols()
        self.config_binds()
        self.config_grid()

        # Rendering File's via refresh threads
        #self.render_snapshot(self.key_value)
        threading.Thread(
            target=self.refresh_file_record,
            args=['remote', True]).start()
        threading.Thread(
            target=self.refresh_file_record,
            args=['local', True]).start()

    def config_widgets(self):
        # Colors...
        self.blk100 = "#EFF1F3"
        self.blk300 = "#B2B6BC"
        self.blk400 = "#717479"
        self.basebg = "#1E1F21" ##
        self.blk600 = "#15171C"
        self.blk700 = "#0F1117"
        self.blk900 = "#05070F"
        self.act300 = "#D5A336"

        self.topbar_bg = "#272822"
        self.topbar_fg = "#919288"

        # Fonts
        self.top_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.def_font = tk_font.Font(
            family="Segoe UI", size=11, weight="normal", slant="roman")
        self.dir_font = tk_font.Font(
            family="Segoe UI", size=11, weight="bold", slant="roman")


        self.configure(
            background="#111111",
            relief='flat'
        )
        # TopBar widgets
        self.topbar_frame = tk.Frame(
            self,
            bg=self.topbar_bg,
        )
        self.run_simpleparser = tk.Button(
            self.topbar_frame,
            text='>',
            bg=self.topbar_bg,
            fg=self.topbar_fg,
            relief='flat',
            font=self.top_font,
            command=self.launch_SimpleParser,
            cursor='hand2'
        )
        self.refresh_trees = tk.Button(
            self.topbar_frame,
            text='⟳',
            bg=self.topbar_bg,
            fg=self.topbar_fg,
            relief='flat',
            font=self.top_font,
            command=self.start_tree_refresh,
            cursor='hand2'
        )
        self.download_all = tk.Button(
            self.topbar_frame,
            text='↧',
            bg=self.topbar_bg,
            fg=self.topbar_fg,
            relief='flat',
            font=self.top_font,
            command=self.download_all_files,
            cursor='hand2'
        )
        self.upload_all = tk.Button(
            self.topbar_frame,
            text='↥',
            bg=self.topbar_bg,
            fg=self.topbar_fg,
            relief='flat',
            font=self.top_font,
            command=self.upload_all_files,
            cursor='hand2'
        )
        self.options_btn = tk.Button(
            self.topbar_frame,
            text='☰',
            bg=self.topbar_bg,
            fg=self.topbar_fg,
            relief='flat',
            command=self.render_options_menu,
            cursor='hand2'
        )

        #Tooltip Group
        self.tt_run_simpleparser = CustomTk_ToolTip(self.run_simpleparser, text='Run Parser')
        self.tt_refresh_trees = CustomTk_ToolTip(self.refresh_trees, text='Refresh file(s)')
        self.tt_download_all = CustomTk_ToolTip(self.download_all, text='Download ALL file(s)')
        self.tt_upload_all = CustomTk_ToolTip(self.upload_all, text='Upload ALL file(s)')
        self.tt_options_btn = CustomTk_ToolTip(self.options_btn, text='Options')

        ## Options Menu
        self.options_menu = tk.Menu(
            tearoff="false",
            background='#404b4d',
            foreground="#CCCCCC",
        )
        self.options_menu.add_command(
            label="Toggle Scrollbar",
            command=self.toggle_ysb
        )
        self.options_menu.add_command(
            label="Toggle Favorites",
            command=self.toggle_favTree
        )

        # FileTrees Pane - Main Container for Tree Widgets to allow resize.
        self.trees_pane = tk.PanedWindow(
            self,
            orient='vertical',
            background="#101010",
            sashwidth=12,
            bd=0,
            borderwidth=0
        )
        # Main Tree Config
        self.main_tree_frame = tk.Frame(
            self.trees_pane,
            bg="black"
        )
        self.file_tree = ttk.Treeview(self.main_tree_frame, columns=(
            "date", "size"), style="Custom.Treeview")
        ## File Treeview Scrollbars
        self.file_ysb = ttk.Scrollbar(
            self.main_tree_frame, orient='vertical', command=self.file_tree.yview)
        self.file_tree.configure(
            yscroll=self.file_ysb.set,
            show="tree headings")

        #Favorites Tree Config
        self.fav_tree_frame = tk.Frame(
            self.trees_pane,
            bg="black"
        )
        self.fav_tree = ttk.Treeview(self.fav_tree_frame, columns=("date", "size"), style="Custom.Treeview")
        ## Fav Treeview Scrollbars
        self.fav_ysb = ttk.Scrollbar(
            self.fav_tree_frame, orient='vertical', command=self.fav_tree.yview)
        self.fav_tree.configure(
            yscroll=self.fav_ysb.set,
        )

        self.remote_menu = self.CustomTk_Filebrowser_Menu(
            self.file_tree, 
            "remote", 
            self,
            self.case_frame,
            self.key_value
            )
        self.local_menu = self.CustomTk_Filebrowser_Menu(
            self.file_tree, 
            "local", 
            self,
            self.case_frame,
            self.key_value
            )
        self.fav_menu = self.CustomTk_Filebrowser_Menu(
            self.fav_tree, 
            "fav", 
            self,
            self.case_frame,
            self.key_value
            )

        # Inserting local tree if local_path exist and contains files.
        self.local_tree = self.sr_local_path
        if os.access(self.sr_local_path, os.R_OK):
            # Now check for contents, insert if !0
            if len(os.listdir(self.sr_local_path)) != 0:
                self.file_tree.insert('', '0', iid='local_filler_space', tags=('default'))
                self.file_tree.insert('', '0', iid=self.local_tree, text="Local Files (Downloads)", tags=('dir_color'))

    def config_grid(self):
        # GRID
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        #self.columnconfigure(1, weight=1)
        #self.columnconfigure(2, weight=1)

        # Root Panes
        self.topbar_frame.grid(
            row=0, column=0, sticky="nsew"
        )
        self.trees_pane.grid(row=1, column=0, padx=0, pady=(10,0), sticky='nsew')

        # Topbar Grid
        self.topbar_frame.columnconfigure(0, weight=1)
        self.run_simpleparser.grid(
            row=0, column=0, sticky="nse", padx=0, pady=0            
        )
        self.download_all.grid(
            row=0, column=1, sticky="nse", padx=0, pady=0
        )
        self.upload_all.grid(
            row=0, column=2, sticky="nse", padx=0, pady=0
        )
        self.refresh_trees.grid(
            row=0, column=3, sticky="nse", padx=0, pady=0
        )
        self.options_btn.grid(
            row=0, column=4, sticky="nse", padx=0, pady=0
        )
        # Main Tree Grid
        self.main_tree_frame.rowconfigure(0, weight=1)
        self.main_tree_frame.columnconfigure(0, weight=1)
        self.file_tree.grid(
            row=0, column=0, sticky='nsew'
        )
        self.file_ysb.grid(
            row=0, column=1, sticky='ns'
        )
        self.file_ysb.grid_remove() # Hide YSB

        # Fav Tree Grid
        self.fav_tree_frame.rowconfigure(0, weight=1)
        self.fav_tree_frame.columnconfigure(0, weight=1)
        self.fav_tree.grid(
            row=0, column=0, sticky='nsew'
        )
        self.fav_ysb.grid(
            row=0, column=1, sticky='ns'
        )
        self.fav_ysb.grid_remove() # Hide YSB

        # Treespane Grid
        self.trees_pane.add(self.main_tree_frame, sticky='nsew')
        self.trees_pane.add(self.fav_tree_frame, sticky='nsew', hide=True)

        # Checks DB to determine if fav_tree pane should be hidden.
        if bcamp_api.get_config('ui_render_favtree') == 'True':
            self.trees_pane.paneconfigure(self.fav_tree_frame, hide=False)

    def config_binds(self):
        # File Treeview Command Bindings
        self.file_tree.bind("<ButtonRelease-3>", self.popup)
        self.file_tree.bind("<Double-Button-1>", self.on_double_click)
        self.file_tree.bind("<Return>", self.right_click_open_win)
        self.file_tree.bind("<<TreeviewSelect>>", self.toggle_trees_focus)
        
        # Favorite Treeview Command Bindings
        self.fav_tree.bind("<ButtonRelease-3>", self.fav_popup)
        self.fav_tree.bind("<Double-Button-1>", self.on_double_click)
        self.fav_tree.bind("<Return>", self.fav_right_click_open)
        self.fav_tree.bind("<<TreeviewSelect>>", self.toggle_trees_focus)

    def config_treecols(self):
        # Treeview Tags
        self.file_tree.tag_configure('debug',  background="#0a0a0a", foreground="#ff7979", font=self.def_font)
        self.file_tree.tag_configure('default',  background="#0a0a0a", foreground="#fdfdfd", font=self.def_font)
        self.file_tree.tag_configure('log_color', background="#0a0a0a", foreground="#a9e34b", font=self.def_font)
        self.file_tree.tag_configure('zip_color', background="#0a0a0a", foreground="#ffd43b", font=self.def_font)
        self.file_tree.tag_configure('dir_color', background="#0F0F0F", foreground="#fdfdfd", font=self.dir_font)
        self.file_tree.tag_configure('enc_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)
        self.file_tree.tag_configure('bin_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)
        self.file_tree.tag_configure('img_color', background="#0a0a0a", foreground="#FF5E96", font=self.def_font)
        # Treeview Column Config
        self.file_tree.heading('#0', text="Name",)
        self.file_tree.heading('date', text="Creation Time", anchor='center')
        self.file_tree.heading('size', text="Size", anchor='center')
        #self.file_tree.heading('range', text="Range", anchor='center')
        self.file_tree.column('#0', minwidth=100, width=260, anchor='e')
        self.file_tree.column("date", anchor="center", minwidth=10, width=40)
        self.file_tree.column("size", anchor="e", minwidth=9, width=10)
        #self.file_tree.column("range", anchor="center", minwidth=10, width=40)

        # fav_tree Tags
        self.fav_tree.tag_configure('default',  background="#0a0a0a", foreground="#fdfdfd", font=self.def_font)
        self.fav_tree.tag_configure('log_color', background="#0a0a0a", foreground="#a9e34b", font=self.def_font)
        self.fav_tree.tag_configure('zip_color', background="#0a0a0a", foreground="#ffd43b", font=self.def_font)
        self.fav_tree.tag_configure('dir_color', background="#0F0F0F", foreground="#fdfdfd", font=self.dir_font)
        self.fav_tree.tag_configure('enc_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)
        self.fav_tree.tag_configure('bin_color', background="#0a0a0a", foreground="#66d9e8", font=self.def_font)
        self.fav_tree.tag_configure('img_color', background="#0a0a0a", foreground="#FF5E96", font=self.def_font)
        self.fav_tree.heading('#0', text="Favorites",)
        self.fav_tree.heading('date', text="", anchor='center')
        self.fav_tree.heading('size', text="", anchor='center')
        #self.fav_tree.heading('range', text="Range", anchor='center')
        self.fav_tree.column('#0', minwidth=100, width=260, anchor='e')
        self.fav_tree.column("date", anchor="center", minwidth=10, width=40)
        self.fav_tree.column("size", anchor="e", minwidth=9, width=10)
        #self.fav_tree.column("range", anchor="center", minwidth=10, width=40)

    def render_options_menu(self):
        # Get current edge of Tile...
        self.topbar_frame.update_idletasks()
        x = self.topbar_frame.winfo_rootx()
        y = self.topbar_frame.winfo_rooty()
        frame_w = self.topbar_frame.winfo_width()
        # Render Menu at edge
        self.options_menu.post((x + frame_w) - (self.options_menu.winfo_reqwidth() + 20), y + 30)

    def toggle_favTree(self, event=None):
        # Updates the DB value for "ui_render_favtree"
        if bcamp_api.get_config("ui_render_favtree") == "False":
            bcamp_api.update_config('ui_render_favtree', "True")
            self.show_favTree.value = "True"
        else:
            bcamp_api.update_config('ui_render_favtree', "False")
            self.show_favTree.value = "False"
    
    def render_favTree(self, new_string):
        '''
        Callback function : Checks the DB to render or hide the 
        'Favorites Tree' in the classes root pane.
        '''
        print("render_favTree -> called w/", new_string)
        # GET DB
        config_val = bcamp_api.get_config('ui_render_favtree')
        # LOGIC
        if config_val == 'True': #SQLite3 stores strings, not bool.
            self.trees_pane.paneconfigure(self.fav_tree_frame, hide=False)          
        elif config_val == 'False':
            self.trees_pane.paneconfigure(self.fav_tree_frame, hide=True)  

    def toggle_ysb(self):
        if self.show_ysb_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_ysb_intvar.set(1)
            self.file_ysb.grid()
            self.fav_ysb.grid()
        elif self.show_ysb_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_ysb_intvar.set(0)
            self.file_ysb.grid_remove()
            self.fav_ysb.grid_remove()

    # Content Methods
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

        for file_tup in cur_filestable:
            #print("***", file_tup[2], file_tup[10])
            # Saving raw vars from SQLite3 DB 
            file_path = file_tup[2]
            file_type = file_tup[3]
            file_raw_size = int(file_tup[4])    # Stored as str in SQLite3
            file_raw_ctime = float(file_tup[5]) # Stored as str in SQLite3
            file_date_range = file_tup[7]

            # Converting Time to readable format from config DB
            tree_ctime = (datetime.datetime.fromtimestamp(
                file_raw_ctime)).strftime(self.time_format)

            # Converting File Size - Omiting Dirs for now...
            format_size = "{size:.3f} MB"
            if file_type != 'dir':
                tree_size = format_size.format(size=file_raw_size / (1024*1024))
            else:
                tree_size = "..."

            # Setting Range

            # Defining Color Tags based on User config
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
                    
    def refresh_file_record(self, mode, enableParser):
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
            if favfiles_list != None:
                if os.path.basename(_path) in favfiles_list:
                    # Pass to 'insert_to_favtree' with vars
                    insert_to_favtree(_path, file_stats, _type)

            new_record = {
                'name': os.path.basename(_path),
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

            # 'updated_file_record' appeneded to here ONLY
            updated_file_record[_path] = new_record
        
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
            tree_range = "" # Default 
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
            if _type == ".bin" or _type == ".html" or _type == ".conf" or _type == '.cnf' or _type == ".xml":
                tree_tag = 'bin_color'
            if _type == ".zip" or _type == '.gz' or _type == '.tar':
                tree_tag = 'zip_color'
            if _type == ".log" or _type == ".dbg":
                tree_tag = 'log_color'
            if _type == ".jpeg" or _type == '.png':
                tree_tag = 'img_color'

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
                    self.file_tree.insert('', '0', iid=self.local_tree, text="Local Files (Downloads)", tags=('dir_color'))
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
            if _type == ".bin" or _type == ".html":
                tree_tag = 'bin_color'
            if _type == ".zip" or _type == '.gz' or _type == '.tar':
                tree_tag = 'zip_color'
            if _type == ".log" or _type == ".dbg":
                tree_tag = 'log_color'
            if _type == ".jpeg" or _type == '.png':
                tree_tag = 'img_color'

            for item in self.fav_tree.get_children():
                lst = self.fav_tree.get_children(item)
                for item in lst:
                    loc_litmus = self.sr_local_path + "\\" + parent[0] + "\\" + os.path.basename(_path)
                    rem_litmus = self.sr_remote_path + "\\" + parent[0] + "\\" + os.path.basename(_path)
                    if loc_litmus == item:
                        print("loc")
                        # DO NOT INSERT TO TREE, LOCAL VAL ALREADY PRES.
                        return
                    if rem_litmus == item:
                        print("rem")
                        # REMOVE FROM TREE AND INSERT LOCAL INSTEAD
                        try:
                            self.fav_tree.delete(rem_litmus)
                        except:
                            pass
            
            if len(parent) == 2:
                #print("**result**", "\n", "parent_tree:", parent[0], "\n", "fav_tree_text:", parent[1], "\n", "fav_tree_iid:", _path, "\n")
                # Inserting Files into *self.fav_tree*
                try:
                    self.fav_tree.insert(
                        os.path.dirname(_path), 
                        'end', 
                        iid=_path, 
                        text=parent[1],
                        values=(tree_ctime, tree_size),
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
                            values=(tree_ctime, tree_size),
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
                        values=(tree_ctime, tree_size), 
                        tags=(tree_tag))
                except tk.TclError:
                    #print(mode, "Passing " + os.path.basename(_path) + " : Already in Tree")
                    pass

        # Determine root path pased on *mode*
        if mode == 'remote':
            if os.access(self.sr_remote_path, os.R_OK):
                dir_depth_list = [[self.sr_remote_path]]
            # Update SR DB last_file_count here...
            try:
                fresh_count = len(os.listdir(self.sr_remote_path))
            except FileNotFoundError:
                fresh_count = 0
            bcamp_api.update_case(self.key_value, 'last_file_count', fresh_count)
            #print("$last_file_cnt>", fresh_count)

        if mode == 'local':
            if os.access(self.sr_local_path, os.R_OK):
                dir_depth_list = [[self.sr_local_path]]
            else:
                return

        updated_file_record = {}
        depth_index = -1
        time_format = self.time_format

        if mode == 'remote' and not os.access(self.sr_remote_path, os.R_OK):
            print("Filebrowser: FATAL - UNABLE TO LOCATE REMOTE FOLDER. CHECK VPN AND TRY AGAIN?")
            return #exit method
        
        # Get list of favorite files from DB.
        favfiles_record = bcamp_api.get_fav_files()
        favfiles_list = [] #contains ONLY filenames, not BCAMP_ROOTPATH.
        for item in favfiles_record:
            favfiles_list.append(item[0])

        # Generator Loop to iterate through files in order of Depth.
        while True:
            data = tree_gen(depth_index)
            depth_index += 1
            # Recursive call here, if EOF, stopIter thrown.
            try:
                next(tree_gen(depth_index))
            except StopIteration:
                #print(mode, "Jobs Done!")
                self.post_task(updated_file_record)
                return

    def post_task(self, updated_file_record):
        '''
        This method calls various post file render parsers using the 
        'updated_file_record' dictionary to ensure the latest file structure
        is scanned, and no longer existing files are attempted to be scanned.

        The actual parsers called here are written within the 'bcamp_api' file
        for better organization.
        '''
        # Launching seperate thread to update DB.
        threading.Thread(target=bcamp_api.update_files, 
                args=(self.key_value, updated_file_record)).start()
            
    # General Treeview Methods
    def start_tree_refresh(self):
        '''
        bcamp-api: Refreshes the File-Trees with an independent thread not in
        the FileOpsQ.
        '''
        bcamp_api.refresh_filetrees(self.key_value, self)

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
            
            # Item/File Clicked in browser.
            # Passing values to open_default, dynamic for each treeview
            target_tree = event.widget
            iid = target_tree.selection()[0]
            self.open_default(iid, event.widget)

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

    def open_default(self, fpath, src_tree):
        '''
        Depending on user config in settings, this method will launch either
        Notepad++, or the internal LogViewer text editor for txt files.
        '''
        # First, get user preference from DB.
        userPref = bcamp_api.get_config('user_texteditor')

        #       userPref stores one of the following
        #
        #       'logviewer' - The Default built-in editor
        #       'notepad++' - Third-party, and well loved editor.
        #       'windows' - Will use the windows default application
        #       'custom' - Will reference to the "custom" python fild found in
        #            /extensions/bcamp_customTextEditor.py

        # Second, call nessicary code to render file.
        if userPref == "Logviewer":
            # Open in logviewer
            # Check if LogViewer is "open" - Open if closed
            curTemplate = self.case_frame.template.value 
            # TEMPORARY - Updates LogViewer val manually, will need to be adjusted
            # when Workpanes can be dynamically placed.
            logViewer_shown = (curTemplate[1])['workpanes'][0][1]
            if not logViewer_shown:
                self.case_frame.update_pane_template('default_logview')
            # Update self.case_frame.main_col1 Width for Logviewer.
            self.case_frame.main_col1.paneconfig(
                self.case_frame.tk_log_viewer, stretch="always")
            
            # Starting thread to render content from target_file,
            # Defined within the Logviewer method.
            self.case_frame.tk_log_viewer.open_selected_file(fpath)

        elif userPref == "Notepad++":
            #Open in Notepad
            bcamp_api.open_notepad(fpath)

        elif userPref == "Windows Default":
            # Open with default windows app
            bcamp_api.open_in_windows(fpath)

        elif userPref == "custom":
            #FUTURE
            bcamp_api.open_customTextEditor(fpath)

    def right_click_open_win(self, event=None):
        iid = self.file_tree.selection()[0]
        try:
            os.startfile(iid)
        except OSError:
            print("ERROR - NO APPLICATION ASSOCIATED.")
        # FUTURE - Multiple Selection -> [0] removed and should handle tuple
        self.file_tree.selection_remove(self.file_tree.selection()[0])

    def fav_right_click_open(self, event=None):
        iid = self.fav_tree.selection()[0]
        try:
            os.startfile(iid)
        except OSError:
            print("ERROR - NO APPLICATION ASSOCIATED.")
        # FUTURE - Multiple Selection -> [0] removed and should handle tuple
        self.fav_tree.selection_remove(self.fav_tree.selection()[0])

    def popup(self, event):
        """action in event of button 3 on tree view"""
        # select row under mouse
        iid = self.file_tree.identify_row(event.y)
        if iid:
            # mouse pointer over item
            self.file_tree.selection_set(iid)
            # Configuring menu based on IID...
            if self.sr_local_path in iid:
                self.local_menu.post(
                    event.x_root + 10, event.y_root + 10)
            else:
                self.remote_menu.post(
                    event.x_root + 10, event.y_root + 10)
        else:
            # mouse pointer not over item
            # occurs when items do not fill frame
            # no action required
            pass

    def fav_popup(self, event):
        """action in event of button 3 on tree view"""
        # select row under mouse
        iid = self.fav_tree.identify_row(event.y)
        if iid:
            # mouse pointer over item
            self.fav_tree.selection_set(iid)
            self.fav_menu.post(
                event.x_root + 10, event.y_root + 10)
        else:
            # mouse pointer not over item
            # occurs when items do not fill frame
            # no action required
            pass

    def launch_SimpleParser(self):
        '''
        Called when user selects "Run SimpleParser" in the menu.
        '''
        bcamp_api.SimpleParser(self.key_value, self)

    # FileOps Queue Methods
    def download_all_files(self, event=None):
        '''
        bcamp_api call:
        Querys the DB for all files in the remote location, and puts a 
        'download' thread into the FileOpsQ for each one that is not present
        in the local folder.
        '''
        bcamp_api.download_all_files(self.key_value, self.FileOpsQ, self)

    def upload_all_files(self, event=None):
        '''
        bcamp_api call:
        Querys the DB for all files in the local location, and puts a 
        'upload' thread into the FileOpsQ for each one that is not present
        in the remote folder.
        '''
        bcamp_api.upload_all_files(self.key_value, self.FileOpsQ, self)


    # Filebrowser Menu Class 
    class CustomTk_Filebrowser_Menu(tk.Menu):
        '''
        Predefined Filebrowser Menu, containing menu commands for the different
        file trees within the Tk_Filebrowser class.
        '''
        def __init__(self, file_tree, ftype, parent_browser, case_masterFrame, key_val):
            super().__init__()
            # Defining target file_tree
            self.tree = file_tree
            self.type = ftype
            self.parent_browser = parent_browser
            self.case_frame = case_masterFrame
            self.key_val = key_val
            
            # Defining colors.
            self.blk100 = "#EFF1F3"
            self.blk300 = "#B2B6BC"
            self.blk400 = "#717479"
            self.basebg = "#1E1F21"
            self.blk600 = "#15171C"
            self.blk700 = "#0F1117"
            self.blk900 = "#05070F"
            self.act300 = "#D5A336"

            # Generating Menu based on 'ftype'
            if ftype == "remote":
                self.base_commands()
                self.remote_commands()
            elif ftype == "local":
                self.base_commands()
                self.local_commands()
            elif ftype == "fav":
                self.base_commands()
                self.favorite_commands()

        def base_commands(self):
            '''
            Method contains definitions for the Menu to contain shared commands
            used by the Local, Remote, and Favorite filetrees.
            '''
            # Gen/Populate Automation menu
            self.automations_menu = tk.Menu(self)
            self.automations_menu.configure(
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

            # Main Menu Commands
            self.configure(
                relief='flat',
                tearoff=False,
                background=self.blk700,
                foreground=self.blk300,
                borderwidth=0,
            )
            self.add_command(
                label="Open w/ LogViewer",
                command=self.right_click_open_logview
            )
            self.add_command(
                label="Open w/ Notepad++",
                command=self.right_click_open_notepad
            )
            self.add_command(
                label="Open w/ Default App",
                command=self.right_click_open_win
            )
            self.add_command(
                label="Reveal in Explorer",
                command=self.right_click_reveal_in_explorer
            )
            self.add_separator()

            self.add_command(
                label="Copy Name",
                command=self.right_click_copy_name
            )
            self.add_command(
                label="Copy Path",
                command=self.right_click_coexe_path
            )
            self.add_separator()
            self.add_cascade(
                label="Automations",
                menu=self.automations_menu
            )
            self.add_separator()

        def local_commands(self):
            '''
            Contains commands and changes specific to the local file tree.
            '''
            self.add_command(
                label="Add to 'Favorites'",
                command=self.right_click_favorite
            )
            self.add_command(
                label="Upload Content",
                command=self.right_click_upload
            )
            self.add_separator()
            self.add_command(
                label="Delete from Local Disk",
                command=self.right_click_delete_local
            )

        def remote_commands(self):
            '''
            Contains commands and changes specific to the remote file tree.
            '''
            self.add_command(
                label="Add to 'Favorites'",
                command=self.right_click_favorite
            )
            self.add_command(
                label="Download Content",
                command=self.right_click_download
            )

        def favorite_commands(self):
            '''
            Contains commands and changes specific to the favorite file tree.
            '''
            self.add_command(
                label="Remove from 'Favorites'",
                command=self.fav_right_click_unfavorite
            )
            self.add_command(
                label="Download",
                command=self.right_click_download
            )

        # Logic for Commands in Menu
        def right_click_open_logview(self, event=None):
            iid = self.tree.selection()[0]

            # Check if LogViewer is "open" - Open if closed
            curTemplate = self.parent_browser.case_frame.template.value 
            # TEMPORARY - Updates LogViewer val manually, will need to be adjusted
            # when Workpanes can be dynamically placed.
            logViewer_shown = (curTemplate[1])['workpanes'][0][1]
            if not logViewer_shown:
                self.parent_browser.case_frame.show_workpane('default_logview')
            # Update self.case_frame.main_col1 Width for Logviewer.
            self.parent_browser.case_frame.main_col1.paneconfig(
                self.parent_browser.case_frame.tk_log_viewer, stretch="always")
            
            # Starting thread to render content from target_file,
            # Defined within the Logviewer method.
            self.case_frame.tk_log_viewer.open_selected_file(iid)

        def right_click_open_win(self, event=None):
            iid = self.tree.selection()[0]
            try:
                os.startfile(iid)
            except OSError:
                print("ERROR - NO APPLICATION ASSOCIATED.")
            # FUTURE - Multiple Selection -> [0] removed and should handle tuple
            self.tree.selection_remove(self.tree.selection()[0])

        def right_click_open_notepad(self, event=None):
            iid = self.tree.selection()[0]
            # Get path to configured text editor.
            notepad_path = bcamp_api.get_config('notepad_path')
            # Launch file with assigned path.
            try:
                subprocess.Popen([notepad_path, iid])
            except:
                print("FileBrowser: Unable to launch Notepadd++, Check PATH! ")
            # FUTURE - Multiple Selection -> [0] removed and should handle tuple
            self.tree.selection_remove(self.tree.selection()[0])

        def right_click_copy_name(self, event=None):
            iid = self.tree.selection()[0]
            bcamp_api.to_win_clipboard(os.path.basename(iid))

        def right_click_coexe_path(self, event=None):
            iid = self.tree.selection()[0]
            bcamp_api.to_win_clipboard(iid)

        def right_click_download(self):
            iid = self.tree.selection()[0]
            print("DOWNLOAD> ", iid)
            # Add download to threaded Queue.
            self.parent_browser.FileOpsQ.add_download(self.parent_browser.key_value, iid)
            remote_refresh = threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['remote', True],
                name=(self.parent_browser.key_value + "::remote_refresh")
                )
            local_refresh = threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['local', True],
                name=(self.parent_browser.key_value + "::local_refresh")
                )
            # Local refresh first because you download to local :)
            self.parent_browser.FileOpsQ.put(local_refresh)
            # REMOVED for Optimization -> self.FileOpsQ.put(remote_refresh)
            # FUTURE - Multiple Selection -> [0] removed and should handle tuple
            self.tree.selection_remove(self.tree.selection()[0])

        def right_click_upload(self):
            iid = self.tree.selection()[0]
            print("UPLOAD> ", iid)
            # Add download to threaded Queue.
            self.parent_browser.FileOpsQ.add_upload(self.parent_browser.key_value, iid)
            remote_refresh = threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['remote', True],
                name=(self.parent_browser.key_value + "::remote_refresh")
                )
            local_refresh = threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['local', True],
                name=(self.parent_browser.key_value + "::local_refresh")
                )
            # Remote refresh first because you upload to remote :)
            self.parent_browser.FileOpsQ.put(remote_refresh)
            # REMOVED for Optimization -> self.FileOpsQ.put(local_refresh)
            # FUTURE - Multiple Selection -> [0] removed and should handle tuple
            self.tree.selection_remove(self.tree.selection()[0])
            
        def right_click_reveal_in_explorer(self):
            iid = self.tree.selection()[0]
            print("would reveal... " + iid)
            subprocess.Popen((r'explorer /select,' + iid))
            self.tree.selection_remove(self.tree.selection()[0])

        def right_click_favorite(self):
            '''
            Using the 'file name' as a key, this file is added to the
            users favorites table in the DB. When this file name
            is seen during 'post_task', it will be 
            automatically appended to the 'self.tree' during
            future scans for ANY product.
            '''
            # iid is full path of 'x' in tree
            iid = self.tree.selection()[0]
            cur_favorites = bcamp_api.get_fav_files()
            bcamp_api.add_fav_file(self.parent_browser.key_value, iid)

            # Finally, insert results into treeview
            threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['remote', False]).start()
            threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['local', False]).start()

        def right_click_delete_local(self):
            # iid is full path of 'x' in tree
            iid = self.tree.selection()[0]
            print("Deleting", iid)
            try:
                shutil.rmtree(iid)
            except:
                os.remove(iid)
            print(iid, "deleted!")
            # Check if count of local files, may need to remove root path
            if len(os.listdir(self.parent_browser.sr_local_path)) > 1:
                # Drop IID from tree only
                self.tree.delete(iid)
                self.tree.item(self.parent_browser.sr_local_path, open=True)
            else:
                # Drop IID and ROOT local Tree items
                self.tree.delete('local_filler_space')
                self.tree.delete(self.parent_browser.sr_local_path)

            # Local refresh only, only change.
            local_refresh = threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['local', False],
                name=(self.parent_browser.key_value + "::local_refresh")
                )
            #local_refresh.start()
            self.parent_browser.FileOpsQ.put(local_refresh)
        
        def fav_right_click_unfavorite(self):
            iid = self.tree.selection()[0]
            print("unfavorite... " + iid)
            # Remove from tree
            self.tree.detach(iid)
            # Remove from "favorite_files" table
            bcamp_api.remove_fav_file(iid)

        def get_automations_list(self):
            '''
            Returns a list of "enabled" Automations stored in the DB.
            '''
            automations = bcamp_api.get_automations()
            return automations[0]

        def launch_automation(self, targetAuto):
            iid = self.tree.selection()[0]

            # Starting thread to prevent UI from hanging...
            self.parent_browser.FileOpsQ.add_automation(self.parent_browser.key_value, iid, targetAuto)
            # Put refresh threads into queue after - will run once unpacked.
            remote_refresh = threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['remote', True],
                name=(self.parent_browser.key_value + "::remote_refresh")
                )
            local_refresh = threading.Thread(
                target=self.parent_browser.refresh_file_record,
                args=['local', True],
                name=(self.parent_browser.key_value + "::local_refresh")
                )
            # Local refresh first because you unpack to local :)
            self.parent_browser.FileOpsQ.put(local_refresh)
            self.parent_browser.FileOpsQ.put(remote_refresh)
            self.tree.selection_remove(self.tree.selection()[0])

        # LEGACY
        def launch_SimpleParser(self):
            '''
            Called when user selects "Run SimpleParser" in the menu.
            '''
            bcamp_api.SimpleParser(self.key_val, self.parent_browser)


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
        global BCAMP_ROOTPATH
        self.RPATH = BCAMP_ROOTPATH
        #self.master = master
        self.key_value = key_value
        self.title = tk.StringVar()
        self.title.set("CaseNotes")
        # Var to show or hide JIRA summary.
        self.show_jira_intvar = tk.IntVar()
        self.show_ysb_intvar = tk.IntVar()
        self.wordwrap_intvar = tk.IntVar() 
        self.wordwrap_intvar.set(1)
        self.show_ysb_intvar.set(0)
        # Saving SQLite Notes Val for Case.
        self.notes_val = bcamp_api.query_case(self.key_value, 'notes')
        if self.notes_val == None:
            self.notes_val = ""

        # Setting Fonts for text_box
        self.def_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.text_font = tk_font.Font(
            family="Consolas", size=12, weight="normal", slant="roman")

        #TK Methods
        self.config_widgets()
        self.config_binds()
        self.config_grid()

        #Binding Keyboard shortcuts
        self.bind('<Control-s>', self.save_button)

    def config_widgets(self):
        # Define Colors
        self.spacer_col = "#000000"
        self.search_accnt = "#A6E22E"
        self.basebg = "#404b4d"
        self.basefg = "#EDF2E0"
        self.textbox_bg = "#161C1F"
        self.textbox_fg = "#DCDEB6"
        self.textbox_cursor = "#E0E5D3"

        # Setting Fonts
        self.def_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.def_font_bld = tk_font.Font(
            family="Segoe UI", size=10, weight="bold", slant="roman")
        self.text_font = tk_font.Font(
            family="Consolas", size=13, weight="normal", slant="roman")
        self.text_font_bold = tk_font.Font(
            family="Consolas", size=13, weight="bold", slant="roman")

        # Self config to prevent White flicker on resize.
        self.config(
            bg="#1e2629"
        )
        self.notepad_top_frame = tk.Frame(
            self,
            background='#404b4d',
        )
        self.root_pane = tk.PanedWindow(
            self,
            orient='vertical',
            bd=0,
            sashwidth=2,
            bg=self.spacer_col
        )
        self.save_button = tk.Button(
            self.notepad_top_frame,
            background='#404b4d',
            foreground='#5b6366',
            text="🖿",
            font=self.def_font,
            relief="flat",
            command=self.save_notes,
            cursor='hand2',
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
            font=self.def_font
        )
        self.options_button = tk.Button(
            self.notepad_top_frame,
            background=self.basebg,
            foreground=self.basefg,
            relief="flat",
            text='☰',
            command=self.render_options_menu,
            cursor='hand2',
        )
        self.text_box = CustomTk_Textbox(
            self.root_pane,
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
        self.text_box_xsb = ttk.Scrollbar(
            self.root_pane,
            orient='horizontal',
            command=self.text_box.xview
        )
        self.text_box_ysb = ttk.Scrollbar(
            self.root_pane,
            orient='vertical',
            command=self.text_box.yview
        )
        self.text_box.configure(
            xscrollcommand = self.text_box_xsb.set,
            yscrollcommand = self.text_box_ysb.set
        )

        #Tooltip Group
        self.tt_save_button = CustomTk_ToolTip(self.save_button, text='Save Changes')
        self.tt_options_button = CustomTk_ToolTip(self.options_button, text='Options')

        #Getting notes from datastore
        self.text_box.insert('1.0', self.notes_val)

        # JIRA Summary Pane
        self.jira_frame = Tk_JiraSummary(
            self.root_pane,
            self.key_value
        )

        # Options Menu
        self.options_menu = tk.Menu(
            tearoff="false",
            background='#404b4d',
            foreground="#CCCCCC",
        )
        self.options_menu.add_command(
            label="Toggle Word-Wrap",
            command=self.toggle_wordwrap
        )
        self.options_menu.add_command(
            label="Toggle Scrollbar",
            command=self.toggle_ysb
        )
        self.options_menu.add_command(
            label="Save Casenotes to File",
            command=self.api_save_case_notes
        ) 
        self.options_menu.add_command(
            label="Save ALL notes to File",
            command=self.api_save_all_notes
        )
        self.options_menu.add_command(
            label="Show JIRA Summary",
            command=self.toggle_jira_summary
        )

        # Creating "Shortcuts Menu"
        self.sc_menu = tk.Menu(
            self,
            tearoff=False
        )
        self.sc_menu.add_command(
            label="Copy",
            command=self.copy_sel
        )
        self.sc_menu.add_command(
            label="Paste",
            command=self.paste_from_clipboard
        )
        self.sc_menu.add_separator()
        self.sc_menu.add_command(
            label="Search Selection in JIRA",
            command=self.search_sel_jira
        )
        self.sc_menu.add_command(
            label="Search Selection w/ Google",
            command=self.search_sel_google
        )

    def config_grid(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='ew')
        #top_frame_grid
        self.notepad_top_frame.columnconfigure(0, weight=1)
        self.title_label.grid(row=0, column=0, padx=5, sticky='ew')
        self.save_button.grid(row=0, column=1, padx=3, sticky='e')
        self.options_button.grid(row=0, column=2, padx=3, sticky='e')
        #/top_frame_grid
        self.root_pane.grid(row=1, column=0, sticky='nsew')
        self.root_pane.columnconfigure(0, weight=1)
        self.root_pane.rowconfigure(0, weight=1)
        self.text_box_ysb.grid(row=0, column=2, sticky='ns')
        self.text_box_xsb.grid(row=2, column=0, sticky='ew')
        self.text_box_ysb.grid_remove()
        self.text_box_xsb.grid_remove()
        # Adding Text_box as def shown.
        self.root_pane.add(self.text_box, sticky='nsew')
        self.root_pane.add(self.jira_frame, sticky='nsew', hide=True)
        #self.text_box.grid(row=1, column=0, sticky='nsew')

    def config_binds(self):
        self.text_box.bind("<Button-3>", self.popup_menu)
        self.text_box.bind("<FocusIn>", self.set_focusIn_colors)
        self.text_box.bind("<FocusOut>", self.set_focusOut_colors)
        self.text_box.bind("<<TextModified>>", self.save_notify)
        self.text_box.bind("<Tab>", self.tabtext)
        self.text_box.bind("<Control-s>", self.save_notes)
        self.text_box.bind("<Configure>", self.check_scrollbar_render)
        #self.text_box.bind("<Control-c>", self.copy_sel)
        #self.text_box.bind("<Control-v>", self.paste_from_clipboard)

    def render_options_menu(self):
        # Get current edge of Tile...
        self.notepad_top_frame.update_idletasks()
        x = self.notepad_top_frame.winfo_rootx()
        y = self.notepad_top_frame.winfo_rooty()
        frame_w = self.notepad_top_frame.winfo_width()
        # Render Menu at edge
        self.options_menu.post((x + frame_w) - (self.options_menu.winfo_reqwidth() + 20), y + 30)

    def toggle_jira_summary(self, event=None):
        if self.show_jira_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_jira_intvar.set(1)
            self.root_pane.paneconfigure(self.jira_frame, hide=False)

        elif self.show_jira_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_jira_intvar.set(0)
            self.root_pane.paneconfigure(self.jira_frame, hide=True)

    def toggle_wordwrap(self, event=None):
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
            self.check_scrollbar_render()

    def toggle_ysb(self):
        if self.show_ysb_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_ysb_intvar.set(1)
            self.text_box_ysb.grid()
        elif self.show_ysb_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_ysb_intvar.set(0)
            self.text_box_ysb.grid_remove()

    def check_scrollbar_render(self, event=None):
        if self.wordwrap_intvar.get() == 0:
            # 
            if (self.text_box.xview())[1] == 1:
                self.text_box_xsb.grid_remove()
            else:
                self.text_box_xsb.grid()

    def api_save_all_notes(self, event=None):
        # Utilizing API to generate notes
        bcamp_api.create_allnotes_file(self.key_value)

    def api_save_case_notes(self, event=None):
        # Utilizing API to generate notes
        bcamp_api.create_casenotes_file(self.key_value)

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

    def popup_menu(self, event):
        self.sc_menu.post(event.x_root + 10, event.y_root + 10)

    def paste_from_clipboard(self, event=None):
        # Get clipboard
        content = bcamp_api.from_win_clipboard_str()
        # Insert to textbox.
        self.text_box.insert(tk.INSERT, content)
        
    def copy_sel(self, event=None):
        content = self.text_box.selection_get()
        print("content>", content)
        bcamp_api.to_win_clipboard(content)     

    def search_sel_jira(self):
        content = self.text_box.selection_get()
        print("content>", content)
        bcamp_api.search_w_jira(content)
    
    def search_sel_google(self):
        content = self.text_box.selection_get()
        print("content>", content)
        bcamp_api.search_w_google(content)

    def save_notify(self, event):
        self.title.set("⬤ CaseNotes")
        self.save_button.config(
            background='#404b4d',
            foreground='#badc58',
        )

    def save_notes(self, event=None):
        new_notes = self.text_box.get('1.0', tk.END)
        bcamp_api.update_case(self.key_value, 'notes', new_notes)
        self.title.set("CaseNotes")
        self.save_button.config(
            background='#404b4d',
            foreground='#ffffff',
        )

    def tabtext(self, e):
        '''
        When multiple lines are selected, this allows them to be tabbed 
        together.
        '''
        last = self.text_box.index("sel.last linestart")
        index = self.text_box.index("sel.first linestart")
        try:
            while self.text_box.compare(index,"<=", last):
                self.text_box.insert(index, "        ")
                index = self.text_box.index("%s + 1 line" % index)
            return "break"
        except:
            pass


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

        # Getting values from config DB
        self.RPATH = root_path

        # Setting Fonts for text_box
        self.def_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.text_font = tk_font.Font(
            family="Segoe UI", size=12, weight="normal", slant="roman")
        
        #TK Methods
        self.config_widgets()
        self.config_binds()
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

        self.tt_save_button = CustomTk_ToolTip(self.save_button, text='Save Changes')
        #self.tt_options_btn = CustomTk_ToolTip(self.options_btn, 'Options')

    def config_grid(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='ew')
        #top_frame_grid
        self.notepad_top_frame.columnconfigure(1, weight=1)
        self.title_label.grid(row=0, column=1, padx=5, sticky='ew')
        self.save_button.grid(row=0, column=2, padx=3, sticky='e')
        #self.search_text_btn.grid(row=0, column=2, sticky='e')
        #/top_frame_grid
        self.text_box.grid(row=1, column=0, sticky='nsew')

    def config_binds(self):
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
        ".14", ".15", ".16", ".properties", ".xml", ".results", ".conf", 
        ".out", " ", "", ".html", ".console"]

    IMG_FILE_EXT = [".jpeg", ".png", ".gif", ".JPEG", ".PNG", ".GIF"]
    
    def __init__(self, master, key_value, root_path, case_frame, Gui):
        super().__init__(master=master)
        #self.master = master
        self.key_value = key_value
        self.Gui = Gui
        self.show_notes_intvar = tk.IntVar()
        self.wordwrap_intvar = tk.IntVar() 
        self.show_search_intvar = tk.IntVar() 
        self.show_ysb_intvar = tk.IntVar()
        self.show_notes_intvar.set(0) # Default: start notes pane.
        self.wordwrap_intvar.set(0) # Default: Enable Wrap
        self.show_search_intvar.set(0) # Default: Hidden
        self.selected_file = ""
        self.title = tk.StringVar()
        self.title.set("*Select a file first* - LogViewer")
        self.subsearch_title = tk.StringVar()
        self.subsearch_title.set("")
        self.case_frame = case_frame

        # List Obj to store contents of 'selected_file' in order of line.
        #   example> self.cur_filelines[32] = 'ln 32: Hello World'
        self.cur_filelines = ['null-offset']

        # Removing auto-render when selecting file.
        #self.case_frame.fb_cur_sel.register_callback(self.open_selected_file)

        self.RPATH = root_path

        #TK Methods
        self.config_widgets()
        self.config_binds()
        self.config_grid()

    def config_widgets(self):
        # Define Colors
        self.spacer_col = "#000000"
        self.search_accnt = "#A6E22E"
        self.basebg = "#404b4d"
        self.basefg = "#EDF2E0"
        self.textbox_bg = "#161C1F"
        self.textbox_fg = "#DCDEB6"
        self.textbox_cursor = "#E0E5D3"

        # Setting Fonts
        self.def_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.def_font_bld = tk_font.Font(
            family="Segoe UI", size=10, weight="bold", slant="roman")
        self.text_font = tk_font.Font(
            family="Consolas", size=13, weight="normal", slant="roman")
        self.text_font_bold = tk_font.Font(
            family="Consolas", size=13, weight="bold", slant="roman")

        # Self config to prevent White flicker on resize.
        self.config(
            bg=self.textbox_bg
        )
        self.notepad_top_frame = tk.Frame(
            self,
            background=self.basebg,
        )
        self.search_button = tk.Button(
            self.notepad_top_frame,
            background=self.basebg,
            foreground=self.basefg,
            relief="flat",
            text='⌕',
            command=self.toggle_search_bar,
            font=self.def_font
        )
        self.title_label = tk.Label(
            self.notepad_top_frame,
            textvariable=self.title,
            background=self.basebg,
            foreground=self.basefg,
            relief="flat",
            anchor="center",
            font=self.def_font
        )
        self.options_button = tk.Button(
            self.notepad_top_frame,
            background=self.basebg,
            foreground=self.basefg,
            relief="flat",
            text='☰',
            command=self.render_options_menu
        )

        ## <NEW FILETABS WIDGETS>
        self.roottabs_pane = tk.PanedWindow(
            self,
            orient='horizontal',
            bd=0,
            sashwidth=2,
            bg=self.spacer_col
        )

        ## <<TEXTBOX WIDGETS>>
        self.text_pane = tk.PanedWindow(
            self,
            orient='vertical',
            bd=0,
            sashwidth=2,
            bg=self.spacer_col
        )
        self.text_box_frame = tk.Frame(
            self.text_pane,
            bg="#1e2629"
        )
        self.text_box = CustomTk_Textbox(
            self.text_box_frame,
            background=self.textbox_bg,
            foreground=self.textbox_fg,
            insertbackground=self.textbox_cursor, #Cursor, ugh TK Naming conventions...
            padx=20,
            pady=10,
            wrap='none',
            undo=True,
            font=self.text_font,
            relief='flat',
            spacing2=3,
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
        ## <</TEXTBOX WIDGETS>>


        self.file_notes_frame = tk.Frame(
            self.text_pane,
            background=self.basebg
        )
        #Defining SearchFrame
        self.subsearch_pane = tk.Frame(
            self.text_pane,
            bg=self.textbox_bg,
        )
        self.subsearch_topbar = tk.Frame(
            self.subsearch_pane,
            background=self.basebg,
        )
        self.subsearch_title_label = tk.Label(
            self.subsearch_topbar,
            textvariable=self.subsearch_title,
            background=self.basebg,
            foreground=self.search_accnt,
            relief="flat",
            anchor="center",
            font=self.def_font_bld
        )
        self.subsearch_baselabel = tk.Label(
            self.subsearch_topbar,
            text="SEARCH (ALL LINES) : ",
            background=self.basebg,
            foreground=self.basefg,
            relief="flat",
            anchor="center",
            font=self.def_font
        )
        self.subseach_close = tk.Button(
            self.subsearch_topbar,
            background=self.basebg,
            foreground=self.basefg,
            relief="flat",
            text='X',
            command=self.close_subsearch_pane 
        )
        self.subsearch_textbox = CustomTk_Textbox(
            self.subsearch_pane,
            background=self.textbox_bg,
            foreground=self.textbox_fg,
            insertbackground=self.textbox_cursor, #Cursor, ugh TK Naming conventions...
            padx=20,
            pady=10,
            wrap='word',
            undo=True,
            font=self.text_font,
            relief='flat',
            spacing2=3,
        )
        self.sub_textbox_xsb = ttk.Scrollbar(
            self.subsearch_pane,
            orient='horizontal',
            command=self.subsearch_textbox.xview
        )
        self.sub_textbox_ysb = ttk.Scrollbar(
            self.subsearch_pane,
            orient='vertical',
            command=self.subsearch_textbox.yview
        )
        self.subsearch_textbox.configure(
            xscrollcommand = self.sub_textbox_xsb.set,
            yscrollcommand = self.sub_textbox_ysb.set
        )
        # Intialize Tk_CaseNotes
        self.file_notes = Tk_FileNotes(self.file_notes_frame, self.key_value, self.RPATH, self.case_frame, self)
        # Intialize Tk_LogSearchBar
        self.search_bar = self.Tk_LogSearchBar(self.notepad_top_frame, self.key_value, self)

        # Options Menu
        self.options_menu = tk.Menu(
            tearoff="false",
            background='#404b4d',
            foreground="#CCCCCC",
        )
        self.options_menu.add_command(
            label="Toggle Scrollbar",
            command=self.toggle_ysb
        )
        self.options_menu.add_command(
            label="Toggle File Notes",
            command=self.show_file_notes
        ) 
        self.options_menu.add_command(
            label="Toggle Word-Wrap",
            command=self.toggle_wordwrap
        )

        # Tooltip Group
        self.tt_options_button = CustomTk_ToolTip(self.options_button, text='Options')
        self.tt_search_button = CustomTk_ToolTip(self.search_button, text='Search')
        self.tt_subseach_close = CustomTk_ToolTip(self.subseach_close, text='Close Subpane')

        # Creating "Shortcuts Menu"
        self.sc_menu = tk.Menu(
            self,
            tearoff=False
        )
        self.sc_menu.add_command(
            label="Search Selection in JIRA",
            command=self.search_sel_jira
        )
        self.sc_menu.add_command(
            label="Search Selection w/ Google",
            command=self.search_sel_google
        )

    def config_grid(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='ew')
        self.text_pane.grid(row=1, column=0, sticky='nsew')

        # Notepad_top_frame_grid
        self.notepad_top_frame.rowconfigure(1, weight=1)
        self.notepad_top_frame.columnconfigure(0, weight=1)
        self.notepad_top_frame.columnconfigure(1, weight=1)
        self.title_label.grid(row=0, column=0, columnspan=2, padx=5, pady=2, sticky='ew')
        self.search_button.grid(row=0, column=2, padx=3, sticky='e')
        self.options_button.grid(row=0, column=3, padx=3, sticky='e')
        self.search_bar.grid(row=1, column=0, columnspan=4, sticky='ew')

        # Text_box Frame
        self.text_box_frame.rowconfigure(0, weight=1)
        self.text_box_frame.columnconfigure(0, weight=1)
        self.text_box.grid(row=0, column=0, sticky='nsew')
        self.text_box_xsb.grid(row=1, column=0, sticky='ew')
        self.text_box_ysb.grid(row=0, column=1, sticky='ns')

        # Search SubFrame
        self.subsearch_pane.rowconfigure(1, weight=1)
        self.subsearch_pane.columnconfigure(0, weight=1)
        self.subsearch_pane.columnconfigure(1, weight=1)
        ## SubFrame TopBar
        self.subsearch_topbar.grid(row=0, column=0, sticky='nsew', columnspan=3)
        self.subsearch_topbar.columnconfigure(2, weight=1)
        self.subsearch_baselabel.grid(row=0, column=0, sticky='nsew')
        self.subsearch_title_label.grid(row=0, column=1, sticky='nsew')
        self.subseach_close.grid(row=0, column=2, sticky='nse')
        ## SubFrame Text Widget
        self.subsearch_textbox.grid(row=1, column=0, sticky="nsew", columnspan=2)
        self.sub_textbox_xsb.grid(row=2, column=0, columnspan=2, sticky='ew')
        self.sub_textbox_ysb.grid(row=1, column=2, sticky='ns')

        # File Notes grid.
        self.file_notes_frame.rowconfigure(0, weight=1)
        self.file_notes_frame.columnconfigure(0, weight=1)
        self.file_notes.grid(row=0, column=0, sticky='nsew')

        # Hiding Scrollbars
        #self.text_box_xsb.grid_remove()
        self.text_box_ysb.grid_remove()
        #self.sub_textbox_xsb.grid_remove()
        self.sub_textbox_ysb.grid_remove()
        # Hiding SearchBar
        self.search_bar.grid_remove()

        # Paned Window Config.
        self.text_pane.add(self.text_box_frame, sticky="nsew", stretch="always")
        self.text_pane.add(self.subsearch_pane, sticky="nsew", stretch="always")
        self.text_pane.paneconfigure(self.subsearch_pane, hide=True)

    def config_binds(self):
        self.text_box.bind("<Tab>", self.tabtext)
        self.text_box.bind("<Button-3>", self.popup_menu)
        self.text_box.bind("<Control-f>", self.toggle_search_bar)
        self.search_bar.search_entry.bind("<Control-f>", self.toggle_search_bar)
        self.text_box.bind("<Control-w>", self.toggle_wordwrap)

        self.text_box.bind("<Configure>", self.check_scrollbar_render)
        self.subsearch_textbox.bind("<Configure>", self.check_scrollbar_render)
        #self.text_box.bind("<FocusIn>", self.set_focusIn_colors)
        #self.text_box.bind("<FocusOut>", self.set_focusOut_colors)
        #self.text_box.bind("<<TextModified>>", self.save_notify)

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
            self.title.set(trimmed_fname + " - LogViewer")
            # Clear TextBox Widget
            self.text_box.delete('1.0', tk.END)
            # Flush cur_filelines
            self.cur_filelines = ['null-offset']
            # Open File
            # Get file size, if less than *SIZE*, load at one,
            # otherwise, render line by line! For BIG log files...
            fsize = os.path.getsize(fb_cur_sel)
            print("File_Size >", fsize)
            with open(fb_cur_sel, 'rb') as f:
                for line in f:
                    self.text_box.insert(tk.END, line)
                    # Append to cur_filelines
                    self.cur_filelines.append(line)
            
            # onrender search sets.
            #self.onrender_search('show', bg="red", fg="white", font=self.text_font)
            #self.onrender_search_re(r'(?:^|\b(?<!\.))(?:1?\d\d?|2[0-4]\d|25[0-5])(?:\.(?:1?\d\d?|2[0-4]\d|25[0-5])){3}(?=$|[^\w.])',
            #    bg="red",
            #    fg="white",
            #    font=self.text_font_bold,
            #    )

            print("Finishing 'open' thread - SUCCESS!")
        
        # Defining thread Var to check
        # Check if *fb_cur_sel* is a supported file type.
        if os.path.splitext(fb_cur_sel)[1] in Tk_LogViewer.SUPPORTED_FILE_EXT:
            threading.Thread(target=open_file_threadobj, name=("fopen_" + os.path.basename(fb_cur_sel))).start()
            # Refresh UI after changes
            #self.onrender_search('show', bg="red", fg="white", font=self.text_font)
            self.text_box.event_generate("<Configure>")
            self.text_box.update_idletasks()
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
            self.text_box.insert(tk.END, "Un-Supported File Type!\n\nHint: Hitting <Enter> will launch the default Windows Application for this file.")           

    def onrender_search(self, target_str, bg, fg, font):
        '''
        Method to define keyword format searches.

        IP: \b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b
        '''
        self.text_box.tag_configure(target_str, background=bg, foregound=fg)
        start="1.0"
        if len(target_str) > 0:
            while True:
                pos = self.text_box.search(
                    pattern=target_str,
                    index=start, 
                    stopindex=tk.END,
                    nocase=1,
                    ) 
                if pos == "": 
                    break       
                start = pos + "+%dc" % len(target_str) 
                self.text_box.tag_add(target_str, pos, "%s + %dc" % (pos,len(target_str)))

    def onrender_search_re(self, target_str, bg, fg, font):
        '''
        Method to define keyword format searches.

        IP: \b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b
        '''
        self.text_box.tag_configure('ipaddr', background=bg, foregound=fg)
        start="1.0"
        if len(target_str) > 0:
            while True:
                pos = self.text_box.search(
                    pattern=target_str,
                    index=start, 
                    stopindex=tk.END,
                    nocase=1,
                    regexp=True
                    ) 
                if pos == "": 
                    break       
                start = pos + "+%dc" % 12
                self.text_box.tag_add('ipaddr', pos, + "+%dc" % 12)

    def show_file_notes(self):
        if self.show_notes_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_notes_intvar.set(1)
            self.text_pane.add(self.file_notes_frame, sticky="nsew", stretch="always")
            # Resizing pane of new notepad
            self.text_pane.paneconfig(self.file_notes_frame, height=(self.winfo_height()/2))
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
        self.options_menu.post((x + frame_w) - (self.options_menu.winfo_reqwidth() + 20), y + 30)

    def toggle_ysb(self):
        if self.show_ysb_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_ysb_intvar.set(1)
            self.text_box_ysb.grid()
            self.sub_textbox_ysb.grid()
        elif self.show_ysb_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_ysb_intvar.set(0)
            self.text_box_ysb.grid_remove()
            self.sub_textbox_ysb.grid_remove()

    def toggle_search_bar(self, event=None):
        if self.show_search_intvar.get() == 0: # Hidden *Default Value
            # Display the FileNotes Pane by "add"ing it.
            self.show_search_intvar.set(1)
            self.search_bar.grid()

        elif self.show_search_intvar.get() == 1: # Shown
            # Hidding the FileNotes Pane by "remove"ing it.
            self.show_search_intvar.set(0)
            self.search_bar.grid_remove()

    def toggle_wordwrap(self, event=None):
        if self.wordwrap_intvar.get() == 0: # Disabled
            # Update IntVar, and ENABLE wordwrap
            self.wordwrap_intvar.set(1)
            self.text_box.configure(wrap=tk.WORD)
            # Remove Scrollbar
            self.text_box_xsb.grid_remove()
            self.sub_textbox_xsb.grid_remove()

        elif self.wordwrap_intvar.get() == 1: # Enabled *Default Value
            # Update IntVar, and DISABLE wordwrap
            self.wordwrap_intvar.set(0)
            self.text_box.configure(wrap=tk.NONE)
            self.subsearch_textbox.configure(wrap=tk.NONE)
            self.check_scrollbar_render()

    def check_scrollbar_render(self, event=None):
        if self.wordwrap_intvar.get() == 0:
            # 
            if (self.text_box.xview())[1] == 1:
                self.text_box_xsb.grid_remove()
            else:
                self.text_box_xsb.grid()
            #
            if (self.subsearch_textbox.xview())[1] == 1:
                self.sub_textbox_xsb.grid_remove()
            else:
                self.sub_textbox_xsb.grid()

    def legacy_render_search_frame(self):
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty()
        frame_w = self.winfo_width()
        search_bar = self.Tk_LogSearchBar(self, self.key_value, self.text_box)
        search_bar.update_idletasks()
        w = search_bar.winfo_width()
        h = search_bar.winfo_height()

        search_bar.place(width=w, height=h)

        #search_bar.place(("%dx%d+%d+%d" % (w, h, x + frame_w - 383, y + 32)))

    def tabtext(self, e):
        '''
        When multiple lines are selected, this allows them to be tabbed 
        together.
        '''
        last = self.text_box.index("sel.last linestart")
        index = self.text_box.index("sel.first linestart")
        try:
            while self.text_box.compare(index,"<=", last):
                self.text_box.insert(index, "        ")
                index = self.text_box.index("%s + 1 line" % index)
            return "break"
        except:
            pass

    def popup_menu(self, event):
        self.sc_menu.post(event.x_root - 10, event.y_root + 10)

    def search_sel_jira(self):
        content = self.text_box.selection_get()
        print("content>", content)
        bcamp_api.search_w_jira(content)
    
    def search_sel_google(self):
        content = self.text_box.selection_get()
        print("content>", content)
        bcamp_api.search_w_google(content)

    # Subsearch Pane Methods
    def render_subsearch_pane(self):
        self.text_pane.paneconfigure(self.subsearch_pane, hide=False)

    def close_subsearch_pane(self):
        '''
        Called when user hits the 'close' button on the Subseach Topbar.
        '''
        self.text_pane.paneconfigure(self.subsearch_pane, hide=True)


    class Tk_LogSearchBar(tk.Frame):
        '''
        Default search bar shared by various "Log" focused panes such as 
        "LogViewer" or "CaseNotes"
        '''
        def __init__(self, master, key_value, LogViewer):
            super().__init__(master=master)
            self.key_value = key_value
            self.LogViewer = LogViewer
            self.target_textbox = LogViewer.text_box
            self.subpane_textbox = LogViewer.subsearch_textbox
            self.shown_match = 0
            self.total_match = 0
            self.match_count_stringvar = tk.StringVar()
            self.match_count_stringvar.set("No results") #Default/empty Val

            # Directs if lines w/ matches will be sent to the search pane.
            self.getall_enabled = False 

            # ONLY for frames. 
            #self.wm_overrideredirect(True) # Hide windows title_bar
            ##self.attributes('-topmost', 'true')
            #self.resizable = False
            self.config_widgets()
            self.config_binds()
            self.config_grid()
            # Taking Focus**
            self.focus_set()
            self.search_entry.focus_set()
            # TODO "destroy" TopLevel when focus lost.
            #self.bind("<FocusOut>", self.on_focus_out)
            
        def config_widgets(self):
            self.entrybg = "#1E1F21"
            self.entryfg = "#EEEEEE"
            self.basebg = "#404B4D"
            self.basefg = "#EEEEEE"
            self.enablebg = "#5F7073"
            self.enablefg = "#EEEEEE"

            self.def_font = tk_font.Font(
                family="Segoe UI", size=10, weight="normal", slant="roman")
            self.bold_font = tk_font.Font(
                family="Segoe UI", size=10, weight="bold", slant="roman")
            self.sym_font = tk_font.Font(
                family="Segoe UI", size=10, weight="bold", slant="roman")

            self.configure(
                background=self.basebg,
            )
            self.search_entry = tk.Entry(
                self,
                background=self.entrybg,
                foreground=self.entryfg,
                insertbackground=self.entryfg,
                insertwidth=1,
                relief='flat',
                font=self.def_font
            )
            self.match_count = tk.Label(
                self,
                background=self.basebg,
                foreground=self.basefg,
                textvariable=self.match_count_stringvar,
                relief='flat',
                font=self.def_font
            )
            self.prev_match_button = tk.Button(
                self,
                background=self.basebg,
                foreground=self.basefg,
                text="ᐱ",
                relief='flat',
                command=self.prev_match,
                font=self.sym_font
            )
            self.next_match_button = tk.Button(
                self,
                background=self.basebg,
                foreground=self.basefg,
                text="ᐯ",
                relief='flat',
                command=self.next_match,
                font=self.sym_font  
            )
            self.get_all_btn = tk.Button(
                self,
                background=self.basebg,
                foreground=self.basefg,
                text="ALL",
                relief='flat',
                command=self.toggle_getall_matches 
            )
            self.exit_button = tk.Button(
                self,
                background=self.basebg,
                foreground=self.basefg,
                text="X",
                relief='flat',
                command=self.exit,
                font=self.sym_font
            )

            # Tooltip Group
            self.tt_prev_match_button = CustomTk_ToolTip(self.prev_match_button, text='Previous Match')
            self.tt_next_match_button = CustomTk_ToolTip(self.next_match_button, text='Next Match')
            self.tt_get_all_btn = CustomTk_ToolTip(self.get_all_btn, text='Show LINES that match in Subpane')
            self.tt_exit_button = CustomTk_ToolTip(self.exit_button, text='Close Search window')

        def config_binds(self):
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
            self.get_all_btn.grid(row=0, column=1, sticky='w')
            self.match_count.grid(row=0, column=2, padx=2, sticky='ew')
            self.prev_match_button.grid(row=0, column=3, padx=2, sticky='ew')
            self.next_match_button.grid(row=0, column=4, padx=2, sticky='ew')
            self.exit_button.grid(row=0, column=5, padx=2, sticky='ew')

        def exit(self):
            '''
            Remove search bar TopLevel when focus is not a child widget of toplevel.
            '''
            self.grid_remove()

        def search_target_textbox(self, event=None):
            # Reset UI counters from previous search
            self.match_count_stringvar.set("...")
            self.shown_match = 0
            self.match_lines = []
            # Begin Search Algo.
            searchEntry = self.search_entry
            self.target_textbox.tag_delete("search")
            self.target_textbox.tag_configure("search", background="#39494F", foregound="#1E1F21")
            start="1.0"
            if len(searchEntry.get()) > 0:
                self.target_textbox.mark_set(
                    "insert",
                    self.target_textbox.search(
                        pattern=searchEntry.get(),  # Pattern to search
                        index=start,              # Starting Index of search
                        nocase=1            # Makes Search Case-Insensitive
                        )
                    )
                
                self.target_textbox.see("insert")
                self.shown_match += 1

                while True:
                    pos = self.target_textbox.search(
                        pattern=searchEntry.get(),
                        index=start, 
                        stopindex=tk.END,
                        nocase=1,
                        ) 
                    if pos == "": 
                        break       
                    start = pos + "+%dc" % len(searchEntry.get()) 
                    self.target_textbox.tag_add("search", pos, "%s + %dc" % (pos,len(searchEntry.get())))
                    # Add resulting start/end position of matches to self.match_lines lst.
                    self.match_lines.append((pos, len(searchEntry.get())))
                    self.update_idletasks()
                    self.event_generate('<Configure>')
            
            # Count results and update Counter
            match_string_count = len(self.target_textbox.tag_ranges('search'))/2
            self.total_match = "{:n}".format(match_string_count)
            self.match_count_stringvar.set(str(self.shown_match) + " of " + str(self.total_match))

            # Get lines with matches if getall enabled to send to subframe if enabled.
            if self.getall_enabled:
                self.gen_allmatches()
                self.subpane_textbox.focus_set()
            else:
                self.target_textbox.focus_set()

        def next_match(self, event=None):
            if self.match_count_stringvar.get() == "No results": # Default/Empty
                return

            # Take focus back.
            self.target_textbox.focus_set()
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

            # Take focus back.
            self.target_textbox.focus_set()
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

        def toggle_getall_matches(self, event=None):
            '''
            Updates the Widget UI, and the 'getall_enabled' var.
            '''
            if self.getall_enabled:
                # Reset var
                self.getall_enabled = False
                # Update UI.
                self.get_all_btn['bg'] = self.basebg
                self.get_all_btn['fg'] = self.basefg
                self.get_all_btn['font'] = self.def_font
            elif self.getall_enabled == False:
                # Reset var
                self.getall_enabled = True
                # Update UI.
                self.get_all_btn['bg'] = self.enablebg
                self.get_all_btn['fg'] = self.enablefg
                self.get_all_btn['font'] = self.bold_font

        def gen_allmatches(self):
            '''
            Gets the line of each matched tag from the search, and passes the
            lines to the 'LogViewer' subsearch pane text widget to be rendered.
            '''
            # Update Parent LogViewer UI
            self.LogViewer.subsearch_title.set(self.search_entry.get())
            self.LogViewer.render_subsearch_pane()
            #print("$.gen_allmatches")
            # Get matchlines from recent_search.
            #print("$.pos_i", self.match_lines)
            # Get lines from 'LogViewer.cur_filelines'
            #print("$.cur_lines", self.LogViewer.cur_filelines[2])

            # Clear the textbox first before inserting new vals.
            self.subpane_textbox.delete('1.0', tk.END)
            self.subpane_textbox.tag_delete("search")
            self.subpane_textbox.tag_configure("search", background="#39494F", foregound="#1E1F21")

            line_index = 1
            for match_set in self.match_lines: # [('10.2', 7), etc.]
                raw_pos = match_set[0]  # '10.2' >> line=10, firstChar=2
                search_len = match_set[1]   # 7 >> length of match.
                # Get line from start_i val
                src_linenum = int(raw_pos.split('.')[0])
                # And get start/end char index for matches for later.
                start_i = str(line_index) + '.' + str(int(raw_pos.split('.')[1]))
                end_i = str(line_index) + '.' + str(int(raw_pos.split('.')[1]) + search_len)
                # Now, Render lines into textbox based on new vars.
                self.subpane_textbox.insert(tk.END, self.LogViewer.cur_filelines[src_linenum])
                # And add tags using start and end vals for the current line.
                self.subpane_textbox.tag_add("search", start_i, end_i)
                line_index += 1
            self.LogViewer.update_idletasks()


    class Tk_TabsPane(tk.Frame):
        '''
        A Dynamic PanedWindow Container that can be added to the 
        'LogViewer.roottabs'. This class defines a Horizontal PanedWindow that
        contains a ttk.Notebook Widget for each initalized pane. Each Notebook
        holds the open file contents when the Tab is selected, with the Tab 
        header being the name of the file itself.

        Remember that the opened files are all stored into "master" 

        '''
        def __init__(self, master, key_value, LogViewer):
            super().__init__(master=master)
            self.key_value = key_value
            self.LogViewer = LogViewer

            self.config_theme()
            self.config_widgets()
            self.config_binds()
            self.config_grid()
        
        def config_theme(self):
            '''
            '''
            pass
        def config_widgets(self):
            '''
            '''
            pass
        def config_binds(self):
            '''
            '''
            pass
        def config_grid(self):
            '''
            '''
            pass


class Tk_JiraSummary(tk.Frame):
    def __init__(self, master, key_val):
        super().__init__(master=master),
        self.configure(bg='red', height=10)
        self.key_value = key_val


        ## Jira spec StringVars
        # TITLE BLOCK
        self.jira_title_var = tk.StringVar()
        self.jira_key = tk.StringVar()
        self.jira_project_var = tk.StringVar()
        # /TITLE BLOCK

        # SUM BLOCK
        self.jira_status_var = tk.StringVar()
        self.jira_resolution_var = tk.StringVar()
        self.jira_affectedver_var = tk.StringVar()
        self.jira_fixedver_var = tk.StringVar()
        self.jira_component_var = tk.StringVar()
        self.jira_priority_var = tk.StringVar()
        # /SUM BLOCK

        # DESC BLOCK
        self.jira_desc_auth_var = tk.StringVar()
        self.jira_desc_time_var = tk.StringVar()
        # /DESC BLOCK

        # COMMENT BLOCK
        self.jira_updated_var = tk.StringVar()
        self.jira_last_comment_var = tk.StringVar()
        self.jira_last_comment_time_var = tk.StringVar()
        self.jira_last_comment_author = tk.StringVar()
        # /COMMENT BLOCK

        # Tk Methods
        self.config_theme()
        self.config_widgets()
        self.config_grid()
        if bcamp_api.query_case(self.key_value, 'bug_id') != None:
            self.get_JiraData()
            self.gen_linked_issues()
            self.gen_comments()

    def config_theme(self):
        # Define Colors
        self.spacer_col = "#000000"
        self.jira_spacer_col = "cyan"
        self.search_accnt = "#A6E22E"
        self.basebg = "#1D1E19"
        self.basefg = "#EDF2E0"
        self.topbg = "#272822"
        self.topfg = "#EDF2E0"
        self.textbox_bg = "#10100B"
        self.textbox_fg = "#DCDEB6"
        self.textbox_cursor = "#E0E5D3"
        self.statusbg = 'yellow'
        self.statusfg = 'black'

        self.notify_grncol = "#A6E22E"
        self.notify_redcol = "#F92672"
        self.notify_yellcol = "#E6CD4A"

        # Setting Fonts
        self.top_font = tk_font.Font(
            family="Segoe UI", size=10, weight="normal", slant="roman")
        self.def_font = tk_font.Font(
            family="Segoe UI", size=11, weight="normal", slant="roman")
        self.def_font_bld = tk_font.Font(
            family="Segoe UI", size=14, weight="bold", slant="roman")
        self.text_font = tk_font.Font(
            family="Consolas", size=11, weight="normal", slant="roman")
        self.text_font_bold = tk_font.Font(
            family="Consolas", size=13, weight="bold", slant="roman")
        self.status_font = tk_font.Font(
            family="Segoe UI", size=11, weight="bold", slant="roman")

    def config_widgets(self):
        self.configure(bg=self.basebg)
        # TOP FRAME
        self.notepad_top_frame = tk.Frame(
            self,
            background=self.topbg,
        )
        self.title_label = tk.Label(
            self.notepad_top_frame,
            text='JIRA Viewer',
            #textvariable=self.jira_key,
            background=self.topbg,
            foreground=self.topfg,
            relief="flat",
            anchor="center",
            font=self.top_font
        )
        self.options_button = tk.Button(
            self.notepad_top_frame,
            background=self.topbg,
            foreground=self.topfg,
            relief="flat",
            text='☰',
            #command=self.render_options_menu
        )
        self.spacer_frame = tk.Frame(
            self.notepad_top_frame,
            background='#101010',
            height=1
        )
        # JIRA PAGE
        self.master_frame = CustomTk_ScrolledFrame(
            self,
        )
        self.master_frame.resize_width = True # Enable resize of inner canvas
        self.master_frame.resize_height = False
        self.master_frame._canvas.configure(
            background=self.basebg
        )
        self.master_frame.inner.configure(
            background=self.basebg
            #background='red'
        )
        # TITLE BLOCK
        self.jira_projectbloc_frame = tk.Frame(
            self.master_frame.inner,
            background=self.basebg
        )
        self.jira_project_label = tk.Label(
            self.jira_projectbloc_frame,
            textvariable=self.jira_project_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            relief='flat',
            justify='left'
        )
        self.jira_key_labelspacer = tk.Label(
            self.jira_projectbloc_frame,
            text="/",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            relief='flat',
            justify='left'
        )
        self.jira_key_label = tk.Label(
            self.jira_projectbloc_frame,
            textvariable=self.jira_key,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            relief='flat',
            justify='left'
        )

        self.jira_title_data = tk.Entry(
            self.master_frame.inner,
            textvariable=self.jira_title_var,
            font=self.def_font_bld,
            background=self.basebg,
            foreground=self.basefg,
            readonlybackground=self.basebg,
            state='readonly',
            relief='flat',
            justify='left'
        )
        # /TITLE BLOCK

        # SUMMARY BLOCK
        self.jira_sumbloc_frame = tk.Frame(
            self.master_frame.inner,
            background=self.basebg,
        )
        self.jira_status_lbl = tk.Label(
            self.jira_sumbloc_frame,
            text="Status: ",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_status_data = tk.Entry(
            self.jira_sumbloc_frame,
            textvariable=self.jira_status_var,
            font=self.status_font,
            background=self.statusbg,
            foreground=self.statusfg,
            readonlybackground=self.statusbg,
            state='readonly',
            relief='flat',
            justify='center'
        )
        self.jira_resolution_lbl = tk.Label(
            self.jira_sumbloc_frame,
            text="Resolution: ",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_resolution_data = tk.Entry(
            self.jira_sumbloc_frame,
            textvariable=self.jira_resolution_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            readonlybackground=self.basebg,
            state='readonly',
            relief='flat',
            justify='left'
        )
        self.jira_component_lbl = tk.Label(
            self.jira_sumbloc_frame,
            text="Component(s): ",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_component_data = tk.Entry(
            self.jira_sumbloc_frame,
            textvariable=self.jira_component_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            readonlybackground=self.basebg,
            state='readonly',
            relief='flat',
            justify='left'
        )
        self.jira_affectedver_lbl = tk.Label(
            self.jira_sumbloc_frame,
            text="Affects Version(s): ",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_affectedver_data = tk.Entry(
            self.jira_sumbloc_frame,
            textvariable=self.jira_affectedver_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            readonlybackground=self.basebg,
            state='readonly',
            relief='flat',
            justify='left'
        )
        self.jira_fixedver_lbl = tk.Label(
            self.jira_sumbloc_frame,
            text="Fix Version(s): ",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_fixedver_data = tk.Entry(
            self.jira_sumbloc_frame,
            textvariable=self.jira_fixedver_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            readonlybackground=self.basebg,
            state='readonly',
            relief='flat',
            justify='left'
        )
        self.jira_priority_lbl = tk.Label(
            self.jira_sumbloc_frame,
            text="Priority: ",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_priority_data = tk.Entry(
            self.jira_sumbloc_frame,
            textvariable=self.jira_priority_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            readonlybackground=self.basebg,
            state='readonly',
            relief='flat',
            justify='left'
        )
        self.jira_sumbloc_spacer = tk.Frame(
            self.jira_sumbloc_frame,
            background=self.jira_spacer_col
        )   
        # /SUMMARY BLOCK

        # LINKED ISSUES BLOCK
        self.jira_linkedbloc_frame = tk.Frame(
            self.master_frame.inner,
            background=self.basebg,
        )
        self.jira_linkedissue_lbl = tk.Label(
            self.jira_linkedbloc_frame,
            text="Related Issues :",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_linkedissue_root = tk.Frame(
            self.jira_linkedbloc_frame,
            background=self.basebg,
        )

        # DESC BLOCK
        self.jira_descbloc_frame = tk.Frame(
            self.master_frame.inner,
            #background=self.basebg
            background='red'
        )
        self.jira_desc_auth_lbl = tk.Label(
            self.jira_descbloc_frame,
            textvariable=self.jira_desc_auth_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_desc_spacer = tk.Frame(
            self.jira_descbloc_frame,
            background=self.jira_spacer_col
        )   
        self.jira_desc_lbl = tk.Label(
            self.jira_descbloc_frame,
            text="Description :",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_desc_txt = tk.Text(
            self.jira_descbloc_frame,
            font=self.text_font,
            background=self.textbox_bg ,
            foreground=self.basefg,
            #state='disabled',
            height=30,
            width=25,
            padx=12,
            wrap='word',
            relief='flat'
        )
        # /DESC BLOCK

        # COMMENT BLOCK
        self.jira_commentbloc_spacer = tk.Frame(
            self.master_frame.inner,
            background=self.jira_spacer_col
        )   
        self.comment_root_frame = tk.Frame(
            self.master_frame.inner,
            background=self.basebg,
        )
        # /COMMENT BLOCK


        # < LEFTOVERs ? >
        self.jira_updated_lbl = tk.Label(
            self.master_frame.inner,
            text="Updated :",
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            anchor='nw'
        )
        self.jira_updated_data = tk.Entry(
            self.master_frame.inner,
            textvariable=self.jira_updated_var,
            font=self.def_font,
            background=self.basebg,
            foreground=self.basefg,
            readonlybackground=self.basebg,
            state='readonly',
            relief='flat',
            justify='center'
        )

    def config_binds(self):
        #self.master_frame.bind("<Configure>", self.master_frame.check_scrollbar_render())
        pass

    def config_grid(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.notepad_top_frame.grid(row=0, column=0, sticky='nsew')
        self.notepad_top_frame.columnconfigure(0, weight=1)
        self.title_label.grid(row=0, column=0, sticky='nsew', pady=4)
        #self.options_button.grid(row=0, column=1, sticky='nsew')
        self.spacer_frame.grid(row=1, column=0, columnspan=2, sticky='nsew')
        self.master_frame.grid(row=1, column=0, columnspan=3, sticky='nsew')
        self.master_frame.inner.columnconfigure(0, weight=1)
        self.master_frame.inner.columnconfigure(1, weight=4)
        self.master_frame.inner.columnconfigure(2, weight=4)
        self.master_frame.inner.columnconfigure(10, weight=1)
        self.master_frame.inner.rowconfigure(5, weight=1)

        ### TITLE BLOCK
        self.jira_projectbloc_frame.grid(
            row=1, column=1, columnspan=3, sticky='nsew', padx=5, pady=(15,0)
        )
        self.jira_project_label.grid(
            row=0, column=0, sticky='nw'
        )
        self.jira_key_labelspacer.grid(
            row=0, column=1, sticky='nw'
        ) 
        self.jira_key_label.grid(
            row=0, column=2, sticky='nw'
        ) 
                # Part of master frame.
        self.jira_title_data.grid(
            row=2, column=1, columnspan=3, sticky='nsew', padx=5, pady=(3,15)
        ) 
        ### /TITLE BLOCK

        ## SUMM BLOC
        self.jira_sumbloc_frame.grid(
            row=3, column=1, columnspan=4, sticky='nsew', padx=20, pady=5
        )
        self.jira_sumbloc_frame.columnconfigure(1, weight=1)
        self.jira_sumbloc_frame.columnconfigure(3, weight=1)
        self.jira_priority_lbl.grid(
            row=0, column=0,  sticky='nsew', padx=2, pady=1
            )
        self.jira_priority_data.grid(
            row=0, column=1,  sticky='nsw', padx=2, pady=1
        )
        self.jira_component_lbl.grid(
            row=1, column=0,  sticky='nsew', padx=2, pady=1
        )
        self.jira_component_data.grid(
            row=1, column=1,  sticky='nsw', padx=2, pady=1
        )
        self.jira_affectedver_lbl.grid(
            row=2, column=0,  sticky='nsew', padx=2, pady=1
        )
        self.jira_affectedver_data.grid(
            row=2, column=1,  sticky='nsw', padx=2, pady=1
        )
                ## <>
        self.jira_status_lbl.grid(
            row=0, column=2,  sticky='nsew', padx=2, pady=1
        )
        self.jira_status_data.grid(
            row=0, column=3,  sticky='nsw', padx=2, pady=1
        )
        self.jira_resolution_lbl.grid(
            row=1, column=2,  sticky='nsew', padx=2, pady=1
        )
        self.jira_resolution_data.grid(
            row=1, column=3,  sticky='nsw', padx=2, pady=1
        )
        self.jira_fixedver_lbl.grid(
            row=2, column=2,  sticky='nsew', padx=2, pady=1
        )
        self.jira_fixedver_data.grid(
            row=2, column=3,  sticky='nsw', padx=2, pady=1
        )
        self.jira_sumbloc_spacer.grid(
            row=3, column=0, columnspan=4, sticky='sew', pady=(10,0)
        )
        ## /SUM BLOC
        self.jira_linkedbloc_frame.grid(
            row=4, column=1, columnspan=2, sticky='nsew', padx=10, pady=5
        )
        self.jira_linkedissue_lbl.grid(
            row=0, column=0, sticky='nsw', padx=1, pady=2
        )
        self.jira_linkedissue_root.grid(
           row=1, column=0, columnspan=2, sticky='nsw', padx=1, pady=2 
        )

        ### DESC BLOCK
        self.jira_descbloc_frame.grid(
            row=5, column=1, columnspan=2, sticky='nsew', padx=10, pady=5
        )
        self.jira_descbloc_frame.columnconfigure(0, weight=1)
        self.jira_desc_auth_lbl.grid(
            row=0, column=0, columnspan=2, sticky='nsew'
        )
        self.jira_desc_spacer.grid(
            row=1, column=0, columnspan=2, sticky='nsew'
        )
        self.jira_desc_lbl.grid(
            row=2, column=0, columnspan=1, sticky='nsew'
        )
        self.jira_desc_txt.grid(
            row=3, column=0, columnspan=2, sticky='nsew'
        )
        ## /DESC BLOCK

        ### COMMENT BLOCK - NOTE: Rendered under 'self.master.inner'
        self.jira_commentbloc_spacer.grid(
            row=6, column=1, columnspan=2, sticky='nsew', pady=2
        )
        self.comment_root_frame.grid(
            row=7, column=1, columnspan=2, sticky='nsew', padx=10, pady=5
        )
        self.comment_root_frame.columnconfigure(0, weight=1)
        # Comments grid defined further in 'gen_comments()'
        ## / COMMENT BLOCK
    
    def get_JiraData(self):
        db_srvals = bcamp_api.query_all_sr(self.key_value)
        if db_srvals[7] != None:
            self.jira_key.set(db_srvals[7])
            # JIRA starts at 13.
            jira_title = db_srvals[13]
            jira_status = db_srvals[14]
            jira_updated = db_srvals[15]
            jira_description = db_srvals[16]
            jira_sr_owner = db_srvals[17]
            jira_last_comment_time = db_srvals[19]
            jira_project = db_srvals[21]
            jira_priority = db_srvals[22]
            jira_resolution = db_srvals[25]
            # Get Comment Object
            jira_last_comment = bcamp_api.jira_get_comment_db(self.key_value)
            # Get IssueLinks
            jira_issuelinks = bcamp_api.jira_get_issuelinks(self.key_value)
            try:
                jira_components = pickle.loads(db_srvals[23])[0]
                print("compo>", jira_components)
            except:
                jira_components = None     #LST
            try:
                jira_affected_ver = pickle.loads(db_srvals[24])[0]
                print('jira_affected_ver', jira_affected_ver)
            except:
                jira_affected_ver = None
            try:
                jira_fix_ver = pickle.loads(db_srvals[26])[0]
                print('jira_fix_ver', jira_fix_ver)
            except:
                jira_fix_ver = None
            
            # SET TK VALS
            self.jira_title_var.set(jira_title)
            self.jira_status_var.set(jira_status)
            self.jira_updated_var.set(jira_updated)
            if jira_description != None:
                self.jira_desc_txt.insert('1.0', jira_description)
            self.jira_project_var.set(jira_project)
            self.jira_status_var.set(jira_status)
            self.jira_resolution_var.set(jira_resolution)
            self.jira_priority_var.set(jira_priority)
            #self.jira_affectedver_var.set(jira_)
            #self.jira_fixedver_var.set(jira_)
            if jira_components != None:
                self.jira_component_var.set(jira_components['name'])

            # FORMATTING COLORS BASED ON RESULTS.
            if jira_status == 'Need Info':
                self.jira_status_data.configure(
                    background=self.notify_redcol
                )
            elif jira_status == 'Ready for Engineering':
                self.jira_status_data.configure(
                    background=self.notify_grncol
                )                
            elif jira_status == 'Ready for Work':
                self.jira_status_data.configure(
                    background=self.notify_yellcol
                )

    def gen_comments(self):
        commentdb_obj = bcamp_api.jira_get_comment_db(self.key_value)
        #print("COMMENT DICT>>", commentdb_obj)
        if commentdb_obj == None:
            return None
        else:
            comment_indx = 0
            #comments_lst = []
            for item in commentdb_obj:
                item_dict = {
                    'auth_displayname': item['updateAuthor']['displayName'],
                    'auth_email': item['updateAuthor']['emailAddress'],
                    'time': item['updated'],
                    'body': item['body'],
                }
                #comments_lst.append(item_dict)
                comment_widget = self.Tk_CommentTemplate(
                    self.comment_root_frame, comment_indx, item_dict)
                comment_widget.grid(row=comment_indx, column=0, columnspan=2, sticky='nsew')
                comment_indx += 1
            print("Comment FINAL >", comment_indx)

    def gen_linked_issues(self):
        linkedissues_lst = bcamp_api.jira_get_issuelinks(self.key_value)
        print("linkedissues_lst>>", linkedissues_lst)
        if linkedissues_lst == None:
            return None
        else:
            issue_indx = 0
            linked_lst = []
            for item in linkedissues_lst:
                print("\n\n***** LINKED ISSUES ******")
                print(item)
                print("\n\n**/LINKED")
                result = {
                    'linked_key': item['key'],
                    'linked_status': item['status'],
                    'linked_title': item['title']
                }
                linked_lst.append(result)
                linked_widget = self.Tk_LinkedIssue_Template(
                    self.jira_linkedissue_root, issue_indx, result)
                linked_widget.grid(row=issue_indx, column=0, columnspan=2, sticky='nsew')
                issue_indx += 1
            print("issue_indx FINAL >", issue_indx)


    class Tk_CommentTemplate(tk.Frame):
        def __init__(self, master, comment_index, content_dict):
            super().__init__(master=master)
            self.master = master
            self.comment_index = comment_index
            self.content_dict = content_dict

            self._author = self.content_dict['auth_displayname']
            self._author_email = self.content_dict['auth_email']
            self._time = self.content_dict['time']
            self._body = self.content_dict['body']

            # TK STRING VARS
            self.jira_desc_auth_var = tk.StringVar()

            # TK METHODS
            self.config_widgets()
            self.config_grid()
            self.set_comment_content()

        def config_widgets(self):
            # Define Colors
            self.spacer_col = "#000000"
            self.jira_spacer_col = "cyan"
            self.search_accnt = "#A6E22E"
            self.basebg = "#1D1E19"
            self.basefg = "#EDF2E0"
            self.topbg = "#272822"
            self.topfg = "#EDF2E0"
            self.textbox_bg = "#10100B"
            self.textbox_fg = "#DCDEB6"
            self.textbox_cursor = "#E0E5D3"
            self.statusbg = 'yellow'
            self.statusfg = 'black'

            # Setting Fonts
            self.top_font = tk_font.Font(
                family="Segoe UI", size=10, weight="normal", slant="roman")
            self.def_font = tk_font.Font(
                family="Segoe UI", size=11, weight="normal", slant="roman")
            self.def_font_bld = tk_font.Font(
                family="Segoe UI", size=14, weight="bold", slant="roman")
            self.text_font = tk_font.Font(
                family="Consolas", size=11, weight="normal", slant="roman")
            self.text_font_bold = tk_font.Font(
                family="Consolas", size=13, weight="bold", slant="roman")

            self.configure(
                background=self.basebg
            )
            self.jira_comment_frame = tk.Frame(
                self,
                background=self.basebg
                #background='red'
            )
            self.author_frame = tk.Frame(
                self.jira_comment_frame,
                background=self.basebg
                #background='red'
            )
            self.jira_cmmt_auth_lbl = tk.Label(
                self.author_frame,
                textvariable=self.jira_desc_auth_var,
                font=self.def_font,
                background=self.basebg,
                foreground=self.basefg,
                anchor='nw'
            )
            #self.jira_desc_spacer = tk.Frame(
            #    self.jira_comment_frame,
            #    background=self.jira_spacer_col
            #)   
            self.jira_cmmt_lbl = tk.Label(
                self.author_frame,
                text="Comment:",
                font=self.def_font,
                background=self.basebg,
                foreground=self.basefg,
                anchor='nw'
            )
            self.jira_cmmt_txt = tk.Text(
                self.jira_comment_frame,
                font=self.text_font,
                background=self.textbox_bg ,
                foreground=self.basefg,
                #state='disabled',
                height=10,
                width=25,
                padx=12,
                wrap='word',
                relief='flat'
            )
        
        def config_grid(self):
            self.columnconfigure(0, weight=1)
            self.jira_comment_frame.grid(
                row=0, column=0, columnspan=2, sticky='nsew', pady=10
            )
            self.jira_comment_frame.columnconfigure(0, weight=1)
            self.jira_comment_frame.rowconfigure(1, weight=1)
            # FRAME SUB CONTENT
            self.author_frame.grid(
                row=0, column=0, columnspan=1, sticky='nw', padx=3, pady=1
            )
            self.jira_cmmt_lbl.grid(
                row=0, column=0, columnspan=1, sticky='nw'
            )
            self.jira_cmmt_auth_lbl.grid(
                row=0, column=1, columnspan=1, sticky='ne'
            )
                #<>
            self.jira_cmmt_txt.grid(
                row=1, column=0, columnspan=2, sticky='nsew'
            )

        def set_comment_content(self):
            #Format Author
            author_string = self._author + " - " + self._time
            self.jira_desc_auth_var.set(author_string)
            # Get Comment based on index.
            self.jira_cmmt_txt.insert('1.0', self._body)


    class Tk_LinkedIssue_Template(tk.Frame):
        def __init__(self, master, comment_index, content_dict):
            super().__init__(master=master)
            self.master = master
            self.comment_index = comment_index
            self.content_dict = content_dict

            self._linked_key = self.content_dict['linked_key']
            self._linked_status = self.content_dict['linked_status']
            self._linked_title = self.content_dict['linked_title']

            # TK STRING VARS
            self.linkedissue_key_var = tk.StringVar()
            self.linkedissue_status_var = tk.StringVar()

            # TK METHODS
            self.config_widgets()
            self.config_grid()
            self.config_binds()
            self.set_comment_content()

        def config_widgets(self):
            # Define Colors
            self.basebg = "#656A57"
            self.basefg = "#000000"
  
            # Setting Fonts
            self.def_font = tk_font.Font(
                family="Segoe UI", size=11, weight="normal", slant="roman")
            self.def_font_bld = tk_font.Font(
                family="Segoe UI", size=11, weight="bold", slant="roman")


            self.configure(
                background=self.basebg
            )
            self.linkedissue_key = tk.Label(
                self,
                textvariable=self.linkedissue_key_var,
                font=self.def_font,
                background=self.basebg,
                foreground=self.basefg,
                anchor='nw',
                cursor='hand2'
            )
            self.linkedissue_status = tk.Label(
                self,
                textvariable=self.linkedissue_status_var,
                font=self.def_font_bld,
                background=self.basebg,
                foreground=self.basefg,
                anchor='nw',
                cursor='hand2'
            )

            # Tooltop Group
            self.tt_linkedissue_title = CustomTk_ToolTip(self.linkedissue_key, text=self._linked_title)
            self.tt_linkedissue_title = CustomTk_ToolTip(self.linkedissue_status, text='Linked Status')
        
        def config_grid(self):
            self.columnconfigure(0, weight=1)
            # FRAME SUB CONTENT
            self.linkedissue_key.grid(
                row=0, column=0, columnspan=1, sticky='nw', padx=3, pady=1
            )
            self.linkedissue_status.grid(
                row=0, column=1, columnspan=1, sticky='nw', padx=3, pady=1
            )

        def config_binds(self):
            self.linkedissue_key.bind('<Button-1>', self.launch_issue)
            self.linkedissue_status.bind('<Button-1>', self.launch_issue)

        def set_comment_content(self):
            #Format Author
            self.linkedissue_key_var.set(self._linked_key)
            # Get Comment based on index.
            self.linkedissue_status_var.set(self._linked_status)

        def launch_issue(self, event=None):
            print("!?")
            base_url = "https://jira-lvs.prod.mcafee.com/browse/"
            search_query = base_url + self._linked_key
            webbrowser.open(search_query)


'''
MAIN INIT
    See you Space Cowboy!
'''
if __name__ == "__main__":
    bcamp_setup.CheckReqs()
    # Create Folder Structure
    bcamp_setup.CreateDirs()
    # Configuring main log...
    bcamp_api.create_mainlog()
    # Creating "basecamp.db" if not available.
    bcamp_setup.CreateDB()
    # Starting UI
    Gui()