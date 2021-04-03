'''
Actively changing file to test the first builds of LogFlow.

ALPHA LYFE.
'''

# Private Import
from tkinter.constants import OFF
import CaseDatastore

# Public Imports
import os
import stat
import json
import time
import datetime
import threading
import subprocess
import tkinter as tk
import tkinter.font as tk_font
from tkinter import TclError, ttk, colorchooser, filedialog


'''
Values from Config Simulated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''
config_netShare = "\\\\dnvcorpvf2.corp.nai.org\\nfs_dnvspr"
config_localFolder = "C:\\Users\\cspears1\\Desktop\\CaseContent"
LQ_NET_SHARE = config_netShare
LQ_LOCAL_DIR = config_localFolder

'''
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''
class Task():
    '''   
    A Methods that are ran during a Workflow are defined here. Often I/O
    operations for Case Data such as "ParsingEngine" 
    '''
    def __init__(self, sub_dir, sr_num):
        # Constants from "config.py"
        '''
        self.LQ_NET_SHARE = config_test.config_netShare
        self.LQ_LOCAL_DIR = config_test.config_localFolder
        self.LQ_DEV_ENABLED = config_test.config_enableDevTools
        self.LQ_AUTO_UPLOAD_ENABLED = config_test.config_autoUpload
        self.LQ_DELETE_ONCE_UNPACKED = config_test.config_delete_encrypted_leftovers
        self.LQ_CREATE_MISSING_DIRS = config_test.config_create_missing_dirs
        '''

        # Selfs - Variables used by "Task" classes'
        self.sub_dir = sub_dir
        self.sr_num = sr_num
        self.remote_dir_path = LQ_NET_SHARE + "\\" + sr_num
        self.local_dir_path = LQ_LOCAL_DIR + "\\" + sub_dir + "\\" + sr_num
        

    def download(file_path):
        print("Download Task started for -> "
            + file_path
        )
'''
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''


class Utilities:
    '''
    General methods to help build data structures found within CaseData such
    as 'files' nested dictionary records that contain the lightweight metadata
    from the 'remote', 'local' or 'custom paths.
    '''

    def get_dir_entries(path):
        '''
        Returns list of os.DirEntry's from *path*
        '''
        if os.path.isdir(path):
            dir_entry_list = []
            with os.scandir(path) as scanner:
                for entry in scanner:
                    dir_entry_list.append(entry)
            return dir_entry_list             

    def get_snapshot(path, debug_val):
        '''
        Returns a single nested {<file_name>: {'path', 'type', etc.},} for all files
        in a directory, by utilizing os.scandir and iterating through the resulting
        dir_entries.
        '''
        print("Working ", path)
        #Determine 'origin'
        if LQ_NET_SHARE in path:
            origin = "remote"
        elif LQ_LOCAL_DIR in path:
            origin = "local"
        else:
            origin = "custom" 
        # Start iterating through dirs...
        dir_entries = Utilities.get_dir_entries(path)
        final_file_table = {}
        file_dict = {}
        file_location = ""
        if dir_entries != None:
            for file_obj in dir_entries:
                # Getting stats for each file...
                file_stats = file_obj.stat()
                if origin == "custom":
                    # Custom paths/files only local.
                    file_location = 'local'                        

                # Building dict table...
                if file_obj.is_file():
                    single_file_table = {
                        file_obj.name: {
                            '_stats_': {
                                'path': file_obj.path,
                                'type': "file",
                                'size': file_stats.st_size, # Bytes -> kB
                                'creation_time': file_stats.st_ctime,
                                'modified_time': file_stats.st_mtime,
                                'location': file_location,
                                'favorite': False #Set later
                            }
                        }
                    }
                    file_dict.update(single_file_table)

                if file_obj.is_dir():
                    single_file_table = {
                        file_obj.name: {
                            '_stats_': {
                                'path': file_obj.path,
                                'type': "dir",
                                'size': (file_stats.st_size / 1024), # Bytes -> kB
                                'creation_time': file_stats.st_ctime,
                                'modified_time': file_stats.st_mtime,
                                'location': file_location,
                                'favorite': False #Set later
                            }
                        }
                    }
                    file_dict.update(single_file_table)
            final_file_table = file_dict
            return final_file_table

    def get_file_stats_in(self, path, debug_val):
        '''
        Returns a single nested {<file_name>: {'path', 'type', etc.},} for all files
        in a directory, by utilizing os.scandir and iterating through the resulting
        dir_entries.
        '''
        print("Working ", path)
        #Determine 'origin'
        if LQ_NET_SHARE in path:
            origin = "remote"
        elif LQ_LOCAL_DIR in path:
            origin = "local"
        else:
            origin = "custom" 
        # Start iterating through dirs...
        dir_entries = Utilities.get_dir_entries(path)
        final_file_table = {}
        file_dict = {}
        file_location = ""
        if dir_entries != None:
            for file_obj in dir_entries:
                # Getting stats for each file...
                file_stats = file_obj.stat()
                # Determining file location...
                if origin == "remote":
                    root_path = str(file_obj.path).replace(LQ_NET_SHARE,'')
                    mirror_path = LQ_LOCAL_DIR + root_path
                    if os.access(mirror_path, os.R_OK):
                        mirror_stats = os.stat(mirror_path)
                        if mirror_stats.st_size == file_stats.st_size:
                            file_location = "synced"
                        else:
                            file_location = "remote"
                    else:
                        file_location = "remote"

                if origin == "local":
                    root_path = str(file_obj.path).replace(LQ_LOCAL_DIR,'')
                    mirror_path = LQ_NET_SHARE + root_path
                    if os.access(mirror_path, os.R_OK):
                        #mirror_stats = os.stat(mirror_path)
                        #if mirror_stats.st_size == file_stats.st_size:
                        file_location = "synced"
                    else:
                        file_location = "local"
                    #else:
                    #    file_location = "local"

                if origin == "custom":
                    # Custom paths/files only local.
                    file_location = 'local'                       

                # Building dict table...
                if file_obj.is_file():
                    single_file_table = {
                        file_obj.name: {
                            '_stats_': {
                                'path': file_obj.path,
                                'type': "file",
                                'size': file_stats.st_size,
                                'creation_time': file_stats.st_ctime,
                                'modified_time': file_stats.st_mtime,
                                'location': file_location,
                                'favorite': False #Set later
                            }
                        }
                    }
                    #File stream 
                    # END OF TEST
                    file_dict.update(single_file_table)

                if file_obj.is_dir():
                    single_file_table = {
                        file_obj.name: {
                            '_stats_': {
                                'path': file_obj.path,
                                'type': "dir",
                                'size': file_stats.st_size,
                                'creation_time': file_stats.st_ctime,
                                'modified_time': file_stats.st_mtime,
                                'location': file_location,
                                'favorite': False #Set later
                            }
                        }
                    }
                    # Recursive Call to self for sub-dir scanning...
                    nested_result = self.get_file_stats_in(file_obj.path, (debug_val + "/" + file_obj.name))
                    file_dict.update(single_file_table | nested_result)
            final_file_table = file_dict
            return final_file_table

    def findkeys(self, node, key_val):
        if isinstance(node, list):
            for i in node:
                for x in self.findkeys(i, key_val):
                    yield x
        elif isinstance(node, dict):
            if key_val in node:
                yield node[key_val]
            for j in node.values():
                for x in self.findkeys(j, key_val):
                    yield x

    def case_file_updater(paths_dict):
        '''
        Returns a tuple ('remote_dict', and 'local_dict'), with each
        dictionary containing files stats for ALL files, as subdirs are 
        crawled via a recursive call to 'self'. The word "file" can be
        replaced with "directory" for the description below as both types
        are handled via this method.

        To optimize perfomance as we may need to scan thousands of files
        depending on the SR, Below is the current algoritm. Note, we use
        file name, file type, and file size to determine a match. If a 
        LOCAL file is renamed, this file will no longer be 'synced' with
        the origin file in the "Remote Share". 
        
        1 - 'REMOTE' dir is scanned via 'os.scandir'

        2 - For each resulting 'file_obj'(os.dirEntry), a "possible path"
            for the 'local' file is tested for existence. If this returns
            'False' - 'file_location' is set to 'remote'.

        3 - If the "possible path" is readable (os.R_OK), 'os.stat' is
            ran against this path, storing type (st_mode) & size (st_size)
            for the exisiting 'LOCAL' file.

        4 - If the "possible path" file name, size, and type match the
            original remote 'file_obj', the "possible_path" file stats
            dictionary is created and appended to 'local_files_dict' with
            a 'location' value of 'synced'. The original 'file_obj'
            'location' value is also set to 'synced'

        5 - The original REMOTE 'file_obj' file stats dictionary is
            appended to 'remote_files_dict' with the applicable 'location'
            value based on previous steps.
        
        6 - The 'LOCAL' directory is scanned via 'os.scandir'

        7 - The resulting 'file_obj's' names are tested against the
            exisiting 'local_files_dict' - If we find a match, we move on
            to the next file. If the file is not in 'local_files_dict', 
            the local 'file_obj' stats are appended to 'local_files_dict'
            with a 'location' calue of 'local'
        
        Further Reading:
        https://docs.python.org/3/library/os.html
        https://docs.python.org/3/library/stat.html

        '''
        # Storing paths from 'paths_dict' 
        r_path = paths_dict['remote']
        l_path = paths_dict['local']
        c_path_list = paths_dict['customs']

        def remote_crawler(path, debug_val):
            print("rCrawl> ", path)
            # Start iterating through Remote Dir
            dir_entries = Utilities.get_dir_entries(path)
            remote_file_dict = {} #placeholder
            local_file_dict = {} #placeholder
            file_location = "remote" #placeholder
            if dir_entries != None:
                for file_obj in dir_entries:
                    # Getting stats for each file...
                    file_stats = file_obj.stat()
                    # Determining file location...
                    root_path = str(file_obj.path).replace(LQ_NET_SHARE,'')
                    mirror_path = LQ_LOCAL_DIR + root_path
                    # Comparing "mirror" file if it exist.
                    if os.access(mirror_path, os.R_OK):
                        mirror_stats = os.stat(mirror_path)
                        if mirror_stats.st_size == file_stats.st_size:
                            if mirror_stats.st_mode == file_stats.st_mode:
                                #Setting 'file_location' var
                                file_location = "synced"
                                # converting st_mode to expected format
                                is_dir = stat.S_ISDIR(mirror_stats.st_mode)
                                if is_dir != 0:
                                    mirror_type = "dir"
                                else:
                                    mirror_type = "file"
                                # Creating local dict...
                                local_file_record = {
                                    file_obj.name: {
                                        '_stats_': {
                                            'path': mirror_path,
                                            'type': mirror_type,
                                            'size': file_stats.st_size,
                                            'creation_time': file_stats.st_ctime,
                                            'modified_time': file_stats.st_mtime,
                                            'location': file_location,
                                            'favorite': False #Set later
                                        }
                                    }
                                }
                                #... and appending to 'local_file_dict'
                                local_file_dict.update(local_file_record)

                    # Building dict table...
                    if file_obj.is_file():
                        remote_file_record = {
                            file_obj.name: {
                                '_stats_': {
                                    'path': file_obj.path,
                                    'type': "file",
                                    'size': file_stats.st_size,
                                    'creation_time': file_stats.st_ctime,
                                    'modified_time': file_stats.st_mtime,
                                    'location': file_location,
                                    'favorite': False #Set later
                                }
                            }
                        }
                        remote_file_dict.update(remote_file_record)

                    if file_obj.is_dir():
                        # Recursive Call to self for sub-dir scanning...
                        nested_result = remote_crawler(file_obj.path, (debug_val + "/" + file_obj.name))
                        remote_file_record = {
                            file_obj.name: {
                                '_stats_': {
                                    'path': file_obj.path,
                                    'type': "dir",
                                    'size': file_stats.st_size,
                                    'creation_time': file_stats.st_ctime,
                                    'modified_time': file_stats.st_mtime,
                                    'location': file_location,
                                    'favorite': False #Set later
                                },
                                '_files_': nested_result[0]
                            }
                        }
                        # Saving results from nested files to OG dicts.
                        remote_file_dict.update(remote_file_record)
                        local_file_dict.update(nested_result[1])

            # Now to scan the local directory, creating the "file record" for
            # the local files. Omitting any files that already exist in the 
            # 'local_file_dict' from the "possible path" test.
            return remote_file_dict, local_file_dict


        def local_crawler(path, imported_dict, debug_val):
            local_file_dict = {}
            # Start iterating through local Dir
            dir_entries = Utilities.get_dir_entries(path)
            if dir_entries != None:
                for file_obj in dir_entries:
                    if file_obj.name in imported_dict:
                        print("lCrawl> Found " + file_obj.name)
                        # DO NOTHING ELSE  - Already have a record :)
                    else:
                        print("lCrawl> " + file_obj.path)
                        file_stats = file_obj.stat()
                        # Building dict table...
                        if file_obj.is_file():
                            local_file_record = {
                                file_obj.name: {
                                    '_stats_': {
                                        'path': file_obj.path,
                                        'type': 'file',
                                        'size': file_stats.st_size,
                                        'creation_time': file_stats.st_ctime,
                                        'modified_time': file_stats.st_mtime,
                                        'location': 'local',
                                        'favorite': False #Set later
                                    }
                                }
                            }
                            local_file_dict.update(local_file_record)

                        if file_obj.is_dir():
                            nested_result = local_crawler(file_obj.path, imported_dict, file_obj.name)
                            local_file_record = {
                                file_obj.name: {
                                    '_stats_': {
                                        'path': file_obj.path,
                                        'type': "dir",
                                        'size': file_stats.st_size,
                                        'creation_time': file_stats.st_ctime,
                                        'modified_time': file_stats.st_mtime,
                                        'location': 'local',
                                        'favorite': False #Set later
                                    },
                                    '_files_': nested_result
                                }
                            }
                            # Saving results from nested files to OG dict.
                            local_file_record.update(nested_result)
                            local_file_dict.update(local_file_record)

            return local_file_dict


        def custom_crawler(c_path_list):
            '''
            To be completed...
            '''
            customs_list = ()
            all_paths_dict = {}
            if customs_list != None:
                for path in customs_list:
                    try:
                        customs_dict = Utilities.get_file_stats_in(path, "customs")
                        all_paths_dict.update(customs_dict)
                    except TypeError:
                        customs_dict = None
                return all_paths_dict


        # RUNNING METHOD
        remote_file_final, local_file_dict = remote_crawler(r_path, "[ :) ]")
        local_file_small = local_crawler(l_path, local_file_dict, "[ :) ]")

        # Merging local dicts...
        local_file_final = (local_file_small)

        #custom_file_final = custom_crawler(c_path_list)
        final_file_record = {
            'remote': remote_file_final,
            'local': local_file_final,
            'customs': None #for now. 
        }
        return final_file_record

    #def get_datastore_dump():
    #    json.load("")

class VarCallback:
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

class Gui(tk.Tk):
    '''
    Where the UI/UX is built. This class is only responsible for drawing the UI
    and nessicary logic to do so. When a user interacts with "Case Data", this class
    passes keyword-values (sr_number, target path, etc.) to the backend Automation 
    Engine for further processing. See "Datastore and Automation Engine Integration 
    Methods" within Gui.__init__ for specifics.

    This class contains Ttk.Frame, and Ttk.Toplevel sub-classes. This helps organize the 
    Tk.Widgets drawn in each "Frame". Keeping the GUI modular, and easily configurable.

    Further Reading...
    - https://docs.python.org/3/library/tkinter.html
    - https://docs.python.org/3/library/tkinter.ttk.html#module-tkinter.ttk
    '''

    # Defined outside of __init__ with intent
    # These are Import vars used to create CaseData objects when '_item' is 
    # modified. Other 'import_X' values passed to CaseData "set_X" methods.
    import_item = VarCallback()
    refresh_dict = VarCallback() 

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
                self.menu_options.add_command(label="Export Theme", command=self.export_theme)
                self.menu.add_cascade(label="File", menu=self.menu_options)
                #self.config(menu=self.menu)
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
                print("debug")
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

    class Tk_WorkspaceManager(ttk.Frame):
        '''
        The workhorse of the UI frames. This renders the default, and new
        workspace tabs when a user imports new data, or recalls a previously
        worked item (Sr Number, Path, etc.) through the "Case Data" pane.

        This is the only Tk.Frame classes that is passed the "case_datastore"
        from Gui.__init__ due to workspaces needing the ability to query the
        Datastore directly.

        Example.) Getting file_paths from <SR> for Treeview Rendering.
        '''
        
        class Tk_DefaultTab(ttk.Frame):
            '''
            The Default "import" tab. If no other workspaces are rendered,
            users will be presented with this Widget first.
            '''
            def __init__(self, master):
                super().__init__()
                self.master = master
                self.btn_big = ttk.Button(
                    self.master,
                    text="Click anywhere here, the '+' tab, or '<CTRL> + <'n'>' to query a new Case",
                    command=Gui.Tk_ImportMenu
                    )
                self.master.rowconfigure(0, weight=1)
                self.master.columnconfigure(0, weight=1)
                self.btn_big.grid(row=0, column=0, sticky="nsew")

        class Tk_TabPane(tk.PanedWindow):
            '''
            This should be the root window whenever a workspace contains
            multiple Frames. This allows these Frames to be
            resized, or moved in the Workspace Window, expanding user
            configurability.

            new_tab_frame = self.Tk_TabPane(self, self.case_datastore, key_value)
            '''
            class Tk_FileBrowser(ttk.Frame):

                class Tk_QueueManager(ttk.Frame):
                    def __init__(self):
                        super().__init__()
                        self.text = "Queue Manager"
                        self.frame_label_queue_state = "off"
                        self.listbox_dnd = tk.Listbox(self)
                        self.listbox_dnd.bind('<Button-1>', self.dnd_set_current)
                        self.listbox_dnd.bind('<B1-Motion>', self.dnd_shift_selection)
                        self.dnd_cur_index = None

                        # GRID
                        self.columnconfigure(0, weight=1)
                        self.listbox_dnd.grid(row=0, column=0, sticky='nsew')
            
                    def dnd_set_current(self, event):
                        self.listbox_dnd.dnd_cur_index = self.listbox_dnd.nearest(self.event.y)

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

                def __init__(self, master, case_datastore, key_value):
                    super().__init__()
                    self.master = master
                    self.case_datastore = case_datastore
                    self.key_value = key_value
                    #Register callback when refresh_flag is updated.
                    Gui.refresh_dict.register_callback(self.refresh_tree)

                    # Building Tk Elements
                    self.create_widgets()
                    self.config_grid()

                    # Rendering Workspace Elements (Treeview, Notepad, etc.)
                    self.populate_file_tree()

                def create_widgets(self):               
                    # Context Menu when "Right-Click"ing.
                    self.right_click_menu = tk.Menu(self)
                    # Building Treeview for SR Content
                    self.tree_browser = ttk.Treeview(self, columns=("date", "size"))
                    self.tree_browser.bind("<ButtonRelease-3>", self.popup)
                    self.tree_browser.bind("<Double-Button-1>", self.right_click_open)
                    self.tree_browser.bind("<Return>", self.right_click_open)
                    self.tree_browser.column("date", anchor="center", minwidth=100)
                    self.tree_browser.column("size", anchor="center", minwidth=100)
                    self.tree_ysb = ttk.Scrollbar(self, orient='vertical', command=self.tree_browser.yview)
                    self.tree_xsb = ttk.Scrollbar(self, orient='horizontal', command=self.tree_browser.xview)
                    self.tree_browser.configure(yscroll=self.tree_ysb.set, xscroll=self.tree_xsb.set)
                    self.right_click_menu.configure(
                        relief='flat',
                        tearoff= False
                        )
                    self.right_click_menu.add_command(
                        label = "Open",
                        command=self.right_click_open
                        )
                    self.right_click_menu.add_command(
                        label = "Unpack",
                        )
                    self.right_click_menu.add_command(
                        label = "Download"
                        )
                    self.right_click_menu.add_command(
                        label = "Add to 'Favorites'",
                        command= self.right_click_favorite
                        )           
                    self.right_click_menu.add_command(
                        label = "Reveal in Explorer",
                        command= self.right_click_reveal_in_explorer
                        )
            
                    # Progressbar Content
                    self.thread = tk.StringVar()
                    #self.thread.trace_add('write', self.updateProgressBarLabel) #Write to "self.thread" to call updateProBar -> Changes label text.
                    self.progbar_intvar = tk.IntVar()
                    self.label_progbar = tk.Label(
                        self, 
                        textvariable=self.thread
                        )
                    self.progbar = ttk.Progressbar(
                        self, 
                        variable=self.progbar_intvar, 
                        orient="horizontal", 
                        mode="indeterminate", #For now...
                        )
                    self.thread.set("[4-21781634495] unpacking >") #FOR NOW

                    #Queue Manager 
                    self.btn_show_queue = ttk.Button(
                        self,
                        text="^",
                        command=self.show_QueueManager
                        )
                    self.queue_frame = self.Tk_QueueManager()

                
                def config_grid(self):
                    # GRID
                    self.rowconfigure(0, weight=1)
                    self.columnconfigure(0, weight=1)
                    self.tree_browser.grid(row=0, column=0, columnspan=2, sticky='nsew')
                    self.tree_ysb.grid(row=0, column=2, sticky='ns')
                    self.tree_xsb.grid(row=1, column=0, columnspan=2, sticky='ew')
                    self.label_progbar.grid(row=2, column=0, sticky="nsw")
                    self.progbar.grid(row=2, column=1, sticky="nsew")
                    self.btn_show_queue.grid(row=3, column=0, sticky='sew')
                    self.queue_frame.grid(
                        row=4, 
                        column=0, 
                        columnspan=3, 
                        sticky="sew"
                        )
                    self.queue_frame.grid_remove()

                def show_QueueManager(self, event=None):
                    if self.queue_frame.frame_label_queue_state == "on":
                        self.queue_frame.grid_remove()
                        self.queue_frame.frame_label_queue_state = "off"
                        self.btn_show_queue['text'] = "^"
                    else:
                        self.queue_frame.grid()
                        self.queue_frame.frame_label_queue_state = "on"
                        self.btn_show_queue['text'] = "˅"


                def populate_file_tree(self):
                    '''
                    Called when Filebrowser is first rendered. 
                    '''
                    #Getting files in Datastore orig. from "get_snapshot"
                    datastore_files_dict = self.case_datastore.query_files(self.key_value)
                    #print("REMOTE FILES")
                    #print(datastore_files_dict['remote'])
                    for key in datastore_files_dict['remote']:
                        file_raw_ctime = datastore_files_dict['remote'][key]['_stats_']['creation_time']
                        file_raw_size = datastore_files_dict['remote'][key]['_stats_']['size']
                        file_path = str(datastore_files_dict['remote'][key]['_stats_']['path'])
                        #Converting Raw values to readable values...
                        #ctime = datetime.datetime.fromtimestamp(file_raw_ctime.strftime('%Y-%m-%d-%H:%M'))
                        ctime = datetime.datetime.fromtimestamp(file_raw_ctime)
                        size = file_raw_size / 1024
                        self.tree_browser.insert('', 'end', iid=file_path, text=key, values=(ctime, (str(size) + " KB" )))
                    print("LOCAL FILES")
                    for key in datastore_files_dict['local']:
                        print(key)

                def refresh_tree(self, refresh_dict):
                    print("REFRESHING TREE...")
                    #Getting files in Datastore. Updated w/ nested files at this point.
                    for result in self.dict_generator(refresh_dict):
                        current_file = result[1]
                        print("BIGBOY :) ", result)
                        if 'path' in result:
                            split_path = str(result[len(result)-1]).rsplit('\\', 1)
                            root_path = split_path[0]
                            file_name = split_path[1]
                            print("path part :) ", file_name, root_path)
                        





                        
                            

                                



                def dict_generator(self, indict, pre=None):
                    pre = pre[:] if pre else []
                    if isinstance(indict, dict):
                        for key, value in indict.items():
                            if isinstance(value, dict):
                                for d in self.dict_generator(value, pre + [key]):
                                    yield d
                            elif isinstance(value, list) or isinstance(value, tuple):
                                for v in value:
                                    for d in self.dict_generator(v, pre + [key]):
                                        yield d
                            else:
                                yield pre + [key, value]
                    else:
                        yield pre + [indict]

                    


                #def refresh_tree(self, new_value):
                def refresh(self, new_value):
                    print("REFRESHING TREE...")
                    #Getting files in Datastore orig. from "get_snapshot"
                    datastore_files_dict = self.case_datastore.query_files(self.key_value)
                    for key in datastore_files_dict['remote']:
                        if '_files_' in datastore_files_dict['remote'][key]:
                            oid = datastore_files_dict['remote'][key]['_stats_']['path']
                            for file_key in datastore_files_dict['remote'][key]['_files_']:
                                print("DEBUGBOIS>" + file_key)
                                for nested_dict in self.findkeys(datastore_files_dict, file_key):
                                    file_path = nested_dict['_stats_']['path']
                                    if LQ_NET_SHARE in file_path:
                                        file_path = nested_dict['_stats_']['path']
                                        file_raw_ctime = nested_dict['_stats_']['creation_time']
                                        file_raw_size = nested_dict['_stats_']['size']
                                        ctime = str(datetime.datetime.fromtimestamp(file_raw_ctime))
                                        size = str(file_raw_size / 1024)
                                        results = [ctime, size, file_key]
                                        print(results)
                                        try:
                                            self.tree_browser.insert(oid, 'end', iid=file_path, text=file_key, values=(ctime, (str(size) + " KB" )))
                                        except TclError:
                                            print("DUPLICATE ERROR")   


                def findkeys(self, node, key_val):
                    if isinstance(node, list):
                        for i in node:
                            for x in self.findkeys(i, key_val):
                                yield x
                    elif isinstance(node, dict):
                        if key_val in node:
                            yield node[key_val]
                        for j in node.values():
                            for x in self.findkeys(j, key_val):
                                yield x


                ##"Right-Click" Menu Methods
                def popup(self, event):
                    """action in event of button 3 on tree view"""
                    # select row under mouse
                    iid = self.tree_browser.identify_row(event.y)
                    if iid:
                        # mouse pointer over item
                        self.tree_browser.selection_set(iid)
                        print(iid)
                        self.right_click_menu.post(event.x_root, event.y_root)            
                    else:
                        # mouse pointer not over item
                        # occurs when items do not fill frame
                        # no action required
                        pass

                def right_click_open(self, event):
                    iid = self.tree_browser.selection()[0]
                    os.startfile(iid)

                def right_click_download(self):
                    iid = self.tree_browser.selection()[0]
                    Task.download(iid)

                def right_click_unpack(self):
                    iid = self.tree_browser.selection()[0]
                    print("unpack -> " + str(iid))

                def right_click_reveal_in_explorer(self):
                    iid = self.tree_browser.selection()[0]
                    print("would reveal... " + iid)
                    subprocess.Popen((r'explorer /select,' + iid))

                def right_click_favorite(self):
                    iid = self.tree_browser.selection()[0]
                    print("would favorite... " + iid)

            class Tk_Notepad(tk.Frame):
                def __init__(self, parent, case_datastore, key_value):
                    super().__init__()
                    self.parent = parent
                    self.text_box = tk.Text(
                        self,
                        background="#333333",
                        foreground="#ffffff",
                        height=30,
                        width=80,
                        
                    )
                    self.rowconfigure(0, weight=1)
                    self.columnconfigure(0, weight=1)
                    self.text_box.grid(row=0, column=0, sticky="nsew")
                    with open("datastore.json", "r") as read_file:
                        self.master_dict = json.load(read_file)
                        json_notes = self.master_dict[key_value]['notes']
                        self.text_box.insert(tk.END, json_notes)

            # Tk_TabPane Methods...
            def __init__(self, master, case_datastore, key_value):
                super().__init__()
                self.master = master
                self.case_datastore = case_datastore
                self.key_value = key_value
                self.frame_list = []
                self.config_grid()
                self.template = self.get_template(self.key_value)
                self.set_template_frames()
                self.render_frames()
                self.configure(
                    background="black",
                    sashwidth=5,
                    )
                
            def get_template(self, key_value):
                template = self.case_datastore.query_for(key_value, 'workspace')
                if template == None:
                    template = "basic"
                elif isinstance(template, dict):
                    print("Workspace> Reading custom template file...")
                    template = "basic" # for now...
                print("Workspace> rendering <" + template + ">")
                return template
            
            def set_template_frames(self):
                if self.template == "basic":
                    # DEFAULT WORKSPACE WIDGETS DECLARED HERE.
                    filetree = self.Tk_FileBrowser
                    notepad = self.Tk_Notepad
                    self.frame_list.append(filetree)
                    self.frame_list.append(notepad)
                else:
                    print("wPane> PARSE JSON FILE HERE...")
            
            def render_frames(self):
                for frame_class in self.frame_list:
                    run = frame_class(self, self.case_datastore, self.key_value)
                    self.add(run)

            def config_grid(self):
                self.columnconfigure(0, weight=1)
                self.rowconfigure(0, weight=1)                           
        
        # Tk_WorkspaceManager Methods...
        def __init__(self, case_datastore):
            super().__init__()
            self.case_datastore = case_datastore

            #Registering refresh_flag for updating treeview
            

            # Rendering Tk Elements
            self.create_widgets()
            self.config_grid()
            self.focus_set()
            #self.bind('<Control-n>', Gui.Tk_ImportMenu)

        # Ttk Config Methods
        def create_widgets(self):
            # Building "Notebook" for multiple SR's to tab through...
            self.tab_notebook = ttk.Notebook(
                self,
                width=200,
                height=160,
                )
            self.default_tab(self.Tk_DefaultTab, "+")
 
        def config_grid(self):
            # Grid Layout
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.tab_notebook.grid(row=0, column=0, sticky='nsew')

        # Import_Handler w/ File Scanning Methods
        def tab_import_handler(self, key_value):
            '''
            On new imports, or recalling previous SR's via the search pane, 
            the tab_import_handler is called, querying the Datastore for the
            workspace to render for <key_value>.

            This also spawns a 'refresh_files_thread', a background process
            that updates the 'files' record for <key_value>, safely running
            long and "expensive" processes that scan the ENTIRE scope of the
            defined directories under 'paths'.

            '''
            def refresh_files_thread(key_value):
                '''
                'key_values' 'dirs' dictionary is queried. The resulting
                paths are handed to CaseData methods, which recursivlely
                scan the directories, updating the Datastore.json for a specific
                <key_value> aka SR Number. 

                This should be called as a seperate thread.
                '''
                # Querying 'paths' from <key_value> in Datastore.JSON
                paths_dict = self.case_datastore.query_for(key_value, 'paths')    

                # Updating records for 'remote', 'local' and 'customs'
                final_file = Utilities.case_file_updater(paths_dict)

                # Appending to Datastore.
                self.case_datastore.append_to_files_for(key_value, final_file)                 

                # Pushing updated table to Tk_Filebrowser...
                Gui.refresh_dict.value = final_file
            
            # Passed to Tk_TabPane to render "Workspace" template.
            new_tab_frame = self.Tk_TabPane(self.tab_notebook, self.case_datastore, key_value)

            # Add Tab with new Workpane
            self.tab_notebook.add(
                new_tab_frame,
                text = key_value
            )
            #Spawning Update thread...
            threading.Thread(target=refresh_files_thread, args=[key_value]).start()

        # Workspace Building Methods
        def default_tab(self, target_frame, header):
            '''
            Creates a the default import tab when a new session is rendered.
            '''
            f_newtab = ttk.Frame(self.tab_notebook)
            target_frame(f_newtab)
            self.tab_notebook.add(
                f_newtab,
                text = header
            )

        # LEGACY File Browser Methods
        def create_file_browser(self, key_value):
            '''
            Using 'key_value', the Case Datastore is queried to obtain
            file stats such as paths. Then a new thread is generated to 
            render this content - preventing a hung UI or loading screen,
            and storing the new file stats to update the Datastore later.

            If this is a new import, the inital drawing of the available 
            sub-dirs will not contain any "child" files and will be
            updated in a "stream" as the files are crawled through by later
            methods.
            '''
            def query_files_for(self, key_value):
                '''
                Returns the entire {<key_value>: 'files':{}} Dict if the
                <key_value> exist in the Datastore.
                '''
                file_dict = self.case_datastore.query_files(key_value)
                return file_dict

            def insert_file_stats(self, node, path_list):
                '''
                - node -> Used for scanning directories found in root node
                - path_list -> list of paths to insert. 
                '''
                pass
                #if dir_entry_list is not None:
                #    for entry in dir_entry_list:
                #        if entry.is_file:
                #            # Saving Various File Stats
                #            file_name = entry.name
                #            os_stats = entry.stat()
                #            raw_birthtime = os_stats.st_ctime
                #            file_birthday = datetime.datetime.fromtimestamp(raw_birthtime).strftime('%Y/%m/%d %H:%M')
                #            file_size = "{size:.3f} MB".format(size = ((os_stats.st_size)/(1024*1024)))
                #            # Adding File + Stats under "parent" node
                #            oid = self.tree_browser.insert(node, 'end', iid=entry.path, text=file_name, values=(file_birthday, file_size), open=False, tags=('default', 'on_click'))
                #        if entry.is_dir:
                #            self.fill_treeview(oid, entry.path)
            
            def update_files_for(self, key_value, updated_file_table):
                '''
                Replaces the previous {<key_value>: 'files':{here}} with
                'updated_file_table'
                '''
                pass

            # Query the Datastore
            file_dict = query_files_for(key_value)

            # Render available content in the Datastore

            # Scanning Remote/Local files and sub-dirs

            # Update Datastore <key_value> with results from Scan


            # LEGACY
            #threading.Thread(target=self.fill_treeview, args=('', path_list)).start()

    class Tk_ImportMenu(tk.Toplevel):
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
        def __init__(self, event=None):
            super().__init__()
            self.advanced_opts_state = "off"
            self.chkbtn_fav_var = tk.IntVar()
            self.direct_import = False

            # Main Widgets
            self.label_sr = ttk.Label(
                self,
                text="SR Number",
                )
            self.entry_sr = ttk.Entry(
                self,
                width=29
                )
            self.label_adv_opts = ttk.Label(
                self,
                text="Show Advanced Options",
                anchor='e',
                )
            self.chkbtn_show_adv_opts = ttk.Checkbutton(
                self,
                command=self.show_advanced_opts,
                onvalue=(self.advanced_opts_state == "on"),
                offvalue=(self.advanced_opts_state == "off"),
                state='!selected'
                )
            self.label_favorite = ttk.Label(
                self,
                text="Mark as Important",
                )
            self.chkbtn_favorite = ttk.Checkbutton(
                self,
                variable=self.chkbtn_fav_var,
                state='!selected'
                )
            
            # Advanced Options Tk Widgets
            self.label_tags = ttk.Label(
                self,
                text="Tags :",
                )
            self.entry_tags =  ttk.Entry(
                self,
                width=29
                )
            self.label_product = ttk.Label(
                self,
                text="Product :",
                )
            self.combox_product = ttk.Combobox(
                self,
                width=26
                )                                
            self.label_account = ttk.Label(
                self,
                text="Account :",
                )
            self.combox_account = ttk.Combobox(
                self,
                width=26
                )    
            self.label_bug = ttk.Label(
                self,
                text="JIRA/Bug ID :"
            )
            self.entry_bug =  ttk.Entry(
                self,
                width=29
                )
            self.label_workspace = ttk.Label(
                self,
                text="Default Workspace :",
                )
            self.combox_workspace = ttk.Combobox(
                self,
                width=26
                )
            self.label_customs = ttk.Label(
                self,
                text="Custom folders or file Paths :"
                )    
            self.entry_customs = ttk.Entry(
                self,
                width=29
                )

            # Bottom Buttons
            self.btn_browse = ttk.Button(
                self,
                text="Browse",
                command=self.direct_import_broswer
                )
            self.btn_start = ttk.Button(
                self,
                text="Import",
                command=self.start
                )
            
            self.config_grid()
            # Taking Focus of window...
            self.focus_force()
            self.entry_sr.focus_force()

            #Binding <enter> to SR entry for keyboard traversal.
            self.entry_sr.bind('<Return>', self.start)

            # DEBUG - Pre-Filling with test SR. My poor fingers
            self.entry_sr.insert(tk.END, "4-11111111111")

        def config_grid(self):
            '''
            Defines Grid layout for Tk.Widgets defined in init.
            '''
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=1)
            #self.master.grid_rowconfigure(0, weight=1)
            #self.master.grid_rowconfigure(1, weight=1)
            #self.master.grid_rowconfigure(2, weight=1)
            #self.master.grid_rowconfigure(3, weight=1)
            #self.master.grid_rowconfigure(4, weight=1)
            #self.master.grid_rowconfigure(5, weight=1)
            #self.master.grid_rowconfigure(6, weight=1)
            #self.master.grid_rowconfigure(7, weight=1)
            #self.master.grid_rowconfigure(8, weight=1)


            # Main Widgets
            self.label_sr.grid(row=0, column=0, padx=4, pady=4, sticky="ne")
            self.entry_sr.grid(row=0, column=1, padx=4, pady=2, sticky="nw")
            self.label_favorite.grid(row=1, column=0, padx=4, pady=2, sticky="e")
            self.chkbtn_favorite.grid(row=1, column=1, padx=4, pady=2, sticky="w")
            self.label_adv_opts.grid(row=2, column=0, padx=4, pady=2, sticky="e")
            self.chkbtn_show_adv_opts.grid(row=2, column=1, padx=4, pady=2, sticky="w")

            # Advanced options Frame
            self.label_tags.grid(row=3, column=0, padx=4, pady=2, sticky="e")
            self.label_tags.grid_remove()
            self.entry_tags.grid(row=3, column=1, padx=4, pady=2, sticky="w")
            self.entry_tags.grid_remove()
            self.label_product.grid(row=4, column=0, padx=4, pady=2, sticky="e")
            self.label_product.grid_remove()
            self.combox_product.grid(row=4, column=1, padx=4, pady=2, sticky="w")
            self.combox_product.grid_remove()
            self.label_account.grid(row=5, column=0, padx=4, pady=2, sticky="e")
            self.label_account.grid_remove()
            self.combox_account.grid(row=5, column=1, padx=4, pady=2, sticky="w")
            self.combox_account.grid_remove()
            self.label_bug.grid(row=6, column=0, padx=4, pady=2, sticky="e")
            self.label_bug.grid_remove()
            self.entry_bug.grid(row=6, column=1, padx=4, pady=2, sticky="w")
            self.entry_bug.grid_remove()
            self.label_workspace.grid(row=7, column=0, padx=4, pady=2, sticky="e")
            self.label_workspace.grid_remove()
            self.combox_workspace.grid(row=7, column=1, padx=4, pady=2, sticky="w")
            self.combox_workspace.grid_remove()
            self.label_customs.grid(row=8, column=0, padx=4, pady=2, sticky="e")
            self.label_customs.grid_remove()
            self.entry_customs.grid(row=8, column=1, padx=4, pady=2, sticky="w")
            self.entry_customs.grid_remove()
    
            # Browse/Start Buttons
            self.btn_browse.grid(row=9, column=0, padx=4, pady=4, sticky="e")
            self.btn_start.grid(row=9, column=1, padx=4, pady=4, sticky="w")

        # Tk.Widgets "commands"
        def show_advanced_opts(self):
            if self.advanced_opts_state == "on":
                self.entry_tags.grid_remove()
                self.label_tags.grid_remove()
                self.entry_tags.grid_remove()
                self.label_product.grid_remove()
                self.combox_product.grid_remove()
                self.label_account.grid_remove()
                self.combox_account.grid_remove()
                self.label_bug.grid_remove()
                self.entry_bug.grid_remove()
                self.label_workspace.grid_remove()
                self.combox_workspace.grid_remove()
                self.label_customs.grid_remove()
                self.entry_customs.grid_remove()
                self.advanced_opts_state = "off"
            else:
                self.entry_tags.grid()
                self.label_tags.grid()
                self.entry_tags.grid()
                self.label_product.grid()
                self.combox_product.grid()
                self.label_account.grid()
                self.combox_account.grid()
                self.label_bug.grid()
                self.entry_bug.grid()
                self.label_workspace.grid()
                self.combox_workspace.grid()
                self.label_customs.grid()
                self.entry_customs.grid()
                self.advanced_opts_state = "on"

        def direct_import_broswer(self):
            filename = filedialog.askopenfilename(
                initialdir = "/",
                title = "Select a File",
                filetypes = (("Text files",
                                "*.txt*"),
                            ("all files",
                                "*.*")))
    
            # Change label contents
            self.label_sr.configure(text="Importing >")
            self.entry_sr.insert(0, filename)
            self.direct_import = True

        def start(self, event=None):
            # Getting Values from GUI
            sr_string = self.entry_sr.get()
            tags_list = self.get_tags()
            account_string = self.get_account()
            customs_list = self.get_customs()
            product_string = self.get_product()
            bug_string = self.get_bug()
            workspace_string = self.get_workspace()
            important_bool = self.get_important()

            # Creating "import_item" Dictionary 
            new_item_dict = {
                'sr_string': sr_string,
                'tags_list': tags_list,
                'account_string': account_string,
                'customs_list': customs_list,
                'product_string': product_string,
                'bug_string': bug_string,
                'workspace_string': workspace_string,
                'important_bool': important_bool
            }

            # Updating "import_item" -> Gui.import_handler(new_item_dict)   
            Gui.import_item.value = new_item_dict
            # Closing window...
            self.destroy()
        
        # Advanced Options "Get" methods 
        def get_tags(self):
            '''
            Returns list of [Tags] from the UI, seperated by ','

            If the ImportMenu entry is not populated, this will return None
            '''
            raw_tags = str(self.entry_tags.get())
            tags_list = raw_tags.split(",")
            return_val = None
            if raw_tags != "":
                return_val = tags_list
            print("IMPORT: Tags set to <" + str(return_val) + ">")
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
            product_val = self.combox_account.get()
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
            default_workspace = ""
            if workspace_val == "":
                default_workspace = 'basic'
            else:
                default_workspace = workspace_val
            print("IMPORT: Setting workspace to <" + str(default_workspace) + ">")
            return default_workspace

        def get_important(self):
            '''
            Returns bool if the favorite checkbox is checked or not.
            '''
            chkbtn_val = self.chkbtn_fav_var.get()
            return_val = False
            if chkbtn_val == 1:
                return_val = True
            print("IMPORT: Setting Favorite to <" + str(return_val) + ">")
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
                
    class Tk_SearchPane(ttk.LabelFrame):
        def __init__(self):
            super().__init__()
            #self.case_datastore = case_datastore
            self.text = "Recent Cases"
            self.frame_lable_datastore_state = "off"
            self.search_entry = ttk.Entry(
                self,
                width=40
            )
            self.search_btn = ttk.Button(
                self,
                text="Search"
            )
            self.case_listbox = tk.Listbox(
                self,
                selectmode="single",
                )
            self.case_listbox_ysb = ttk.Scrollbar(
                self, 
                orient='vertical', 
                command=self.case_listbox.yview,
                )
            self.case_listbox_xsb = ttk.Scrollbar(
                self, 
                orient='horizontal', 
                command=self.case_listbox.xview,
                )
            #self.case_listbox.bind(
            #    "<ButtonRelease-1>", 
            #    print("You pressed something :)")
            #    )
            self.case_listbox.configure(
                width=50,
                yscrollcommand=self.case_listbox_ysb.set, 
                xscrollcommand=self.case_listbox_xsb.set
            )

            self.config_grid()

        def config_grid(self):
            #self.rowconfigure(0, weight=1)
            self.rowconfigure(1, weight=1)
            self.search_entry.grid(row=0, column=0, sticky='ew')
            self.search_btn.grid(row=0, column=1, sticky='ew')
            self.case_listbox.grid(row=1, column=0, columnspan=2, sticky='nsew')
            self.case_listbox_ysb.grid(row=1, column=1, rowspan=3, sticky='nse')
            self.case_listbox_xsb.grid(row=3, column=0, sticky='ew')

        def create_entry(self, key_value):
            '''
            Appends "key_value" to the Tk.Listbox Widget.
            '''
            self.case_listbox.insert(0, key_value)
                   
    class Tk_ButtonHover(ttk.Button):
        def __init__(self, master, **kw):
            tk.Button.__init__(self,master=master,**kw)
            self.defaultBackground = self["background"]
            self.bind("<Enter>", self.on_enter)
            self.bind("<Leave>", self.on_leave)

        def on_enter(self, e):
            self['background'] = self['activebackground']

        def on_leave(self, e):
            self['background'] = self.defaultBackground

    class Tk_BottomBar(ttk.Frame):
        def __init__(self):
            super().__init__()
            self.config_widgets()
            self.config_grid()
        
        def config_widgets(self):
            self.bb_ver = ttk.Label(
                self,
                text="Version 0.1 Alpha"
            )
            self.bb_remote_canvas = tk.Canvas(
                self,
                width=10,
                height=10,
                background="yellow"
            )
            self.bb_remote_canvas.create_oval(10, 10, 200, 150, fill='green', outline='grey')
        
        def config_grid(self):
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.bb_ver.grid(row=0, column=0, sticky='se')
            self.bb_remote_canvas.grid(row=0, column=1)


        
    def __init__(self, case_datastore):
        super().__init__()
        # Attaching UI to Case Datastore
        self.case_datastore = case_datastore

        # Register Callback method for "Gui.import_item" changes to "import_handler()"
        Gui.import_item.register_callback(self.import_handler)

        # Intializing Ttk.Frames 
        self.SearchPane = self.Tk_SearchPane()
        self.WorkspaceManager = self.Tk_WorkspaceManager(self.case_datastore)
        self.BottomBar = self.Tk_BottomBar()

        # Configuring UI Window
        self.expansion_buttons()
        #self.config_widgets()
        self.config_grid()
        self.config_window()
        self.bind('<Control-n>', Gui.Tk_ImportMenu)
        self.bind('<Control-b>', self.show_SearchCaseData)
        # STARTING TK/TTK UI
        self.configure(background="black")
        self.start_ui()

    def expansion_buttons(self):
        # Show/Collapse Buttons
        self.btn_show_datastore = ttk.Button(
            self,
            text=">",
            width=2, 
            command=self.show_SearchCaseData
            )

    def show_SearchCaseData(self, event=None):
        if self.SearchPane.frame_lable_datastore_state == "on":
            self.SearchPane.grid_remove()
            self.SearchPane.frame_lable_datastore_state = "off"
            self.btn_show_datastore['text'] = ">"
        else:
            self.SearchPane.grid()
            self.SearchPane.frame_lable_datastore_state = "on"
            self.btn_show_datastore['text'] = "<"

    def config_grid(self):
        self.rowconfigure(2, weight=1) 
        self.columnconfigure(2, weight=1)
        self.btn_show_datastore.grid(
            row=0, 
            column=0, 
            rowspan=4, 
            sticky="nsw"
            )
       

        self.SearchPane.grid(
            row=0, 
            column=1, 
            rowspan=4, 
            padx=2, 
            pady=2, 
            sticky="nsew")
        self.SearchPane.grid_remove() # Start hidden

        self.WorkspaceManager.grid(
            row=0, 
            column=2,
            rowspan=3,
            padx=3,
            pady=3,
            sticky='nsew'
            )

        self.BottomBar.grid(row=5, column=0, columnspan=5, sticky="sew")

    def config_window(self):
        # Intial Window Size
        self.geometry("800x600")
        # Options Menu
        self.menu = tk.Menu(self)
        self.menu_options = tk.Menu(self.menu, tearoff=0)
        self.menu_options.add_command(label="Launch Theme Wizard", command=self.Tk_ThemeWizard)
        self.menu.add_cascade(label="Options", menu=self.menu_options)
        self.config(menu=self.menu)
        # Misc
        self.title("LogFlow 0.1")
        
    def refresh(self):
        '''
        If any Widget config needs to be updated after other UI events,
            it should be ".set" here.
        '''
        self.update()
        # DO NOT WRITE ABOVE THIS COMMENT

        # DO NOT WRITE BELOW THIS COMMENT
        self.after(1000, self.refresh)

    def start_ui(self):
        self.refresh()
        self.mainloop()

    # Datastore and Automation Engine Integration Methods
    def import_handler(self, new_import_dict):
        '''
        This method is called whenever "Gui.import_item" is modified. The
        expected input is a dictionary with the following syntax...

            new_import_dict = {
                'sr_string': sr_string,
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
        #Unpacking SR key_value from import Dict.
        import_key_value = new_import_dict['sr_string']
        print("IMPORT: Caught new_value <" + import_key_value + ">")

        #SR Numbers are 13 characters long.
        if len(import_key_value) == 13:
            print("IMPORT: Type <SR Number>")
            if self.unique_in_datastore(import_key_value):
                self.create_CaseData_for(new_import_dict)
                self.WorkspaceManager.tab_import_handler(import_key_value)
            else:
                self.WorkspaceManager.tab_import_handler(import_key_value)

    def unique_in_datastore(self, key_value):
        '''
        Returns True if key-value is not already in the Case Datastore
        '''
        if not self.case_datastore.check_key(key_value):
            print("IMPORT: <" + key_value + "> not in Datastore")
            return True
        else:
            print("IMPORT: <" + key_value + "> already exist in Datastore.")
            return False

    def create_CaseData_for(self, new_import_dict):
        '''
        Initalizes a new CaseData object which is automatically appended to
        the Case Datastore. This passes 'new_import_dict' as a reference for
        intial entries to CaseData.

        See "CaseData" class for more details.
        '''
        import_key_value = new_import_dict['sr_string']
        print("IMPORT: <" + import_key_value + "> creating CaseData...")
        CaseDatastore.Data(self.case_datastore, new_import_dict)
        self.update_SearchFrame()
        return True
        
    def update_SearchFrame(self):
        '''
        This method appends new "key_values" to the UI's SearchFrame found
        in the collapsable left window. 
        '''
        _datastore_copy = self.case_datastore.get_master_dict()
        for key in _datastore_copy.keys():
            self.SearchPane.create_entry(key)

#RUN
case_datastore = CaseDatastore.Datastore()
#Other Engine Code Here...
Gui(case_datastore)