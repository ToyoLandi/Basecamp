#This is a test
'''
    Notepad and workspace for testing Python commands for logGuru
'''

import os
import filecmp
import threading
from tkinter.constants import S
import tkinter.font as tk_font
import tkinter as tk
from tkinter import Event, Tk, ttk, font


config_netShare = "\\\\dnvcorpvf2.corp.nai.org\\nfs_dnvspr"
config_localFolder = "C:\\Users\\cspears1\\Desktop\\CaseContent"
LQ_NET_SHARE = config_netShare
LQ_LOCAL_DIR = config_localFolder


'''
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import os
import datetime
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import colorchooser, filedialog

class Utilities():
    '''
    Non-class specfific shared methods. 
    '''

    def compare_content(local_dir_path, remote_dir_path, mode):
        '''
        Utilizing the "filecmp" native library, this method compares the local
        and remote directories. The "mode" argument determines the returned
        result, but these are always raw file paths. ex.) "c:/../4-21/file.txt"

        Mode can be defined as...
        - "0" = Return paths of items missing in REMOTE directory.
        - "1" = Return paths of items missing in LOCAL directory.
        - "2" = Return paths of items missing in LOCAL directory, but omit
                items that have a directory in LOCAL directory.
        - "3" = Return file names and sub dir names in BOTH local and remote dirs
        '''
        dircmp_results = filecmp.dircmp(remote_dir_path, local_dir_path)
        result_list = [] # 

        #Returning files and sub dirs ONLY in LOCAL dir.
        if mode == 0:
            for file in dircmp_results.right_only:
                local_path = local_dir_path + "\\" + file
                print("Appending : " + local_path)
                result_list.append(local_path)
                
        #Returning files and sub dirs ONLY in REMOTE dir.
        if mode == 1:
            for file in dircmp_results.left_only:
                remote_path = remote_dir_path + "\\" + file
                print("Appending : " + remote_path)
                result_list.append(remote_path)

        # Returning files and subdirs ONLY in REMOTE dir, but skip "file.ext"
        #  that has a been unpacked by checking for "file" dir in local_dir.  
        if mode == 2:
            for file in dircmp_results.left_only: # Files only in remote_dir
                remote_path = remote_dir_path + "\\" + file
                test_path = local_dir_path + "\\" + str(file).rpartition(".")[0]
                if not os.access(test_path, os.R_OK):
                    result_list.append(remote_path)
        
        # Return files and sub dirs in LOCAL and REMOTES dirs
        if mode == 3:
            for file in dircmp_results.common:
                # Returning REMOTE path for use in UI treeview
                remote_path = remote_dir_path + "\\" + file
                print("Appending : " + remote_path)
                result_list.append(remote_path)


        return result_list

    def get_dir_entries(path):
        '''
        Returns list of os.DirEntry's from *path*
        '''
        print("get_dir - Start")
        if os.path.isdir(path):
            dir_entry_list = []
            with os.scandir(path) as scanner:
                for entry in scanner:
                    dir_entry_list.append(entry)
            print("get_dir - Fin")
            return dir_entry_list             

    def get_file_stats_in(path):
        '''
        Returns a single nested {<file_name>: {'path', 'type', etc.},} for all files
        in a directory, by utilizing os.scandir and iterating through the resulting
        dir_entries.
        '''
        dir_entries = Utilities.get_dir_entries(path)
        final_file_table = {'key': 'value'}
        for file_obj in dir_entries:
            # Getting stats for each file...
            file_name = file_obj.name
            file_path = file_obj.path
            file_stats = file_obj.stat()
            file_size = file_stats.st_size
            file_creation_time = file_stats.st_ctime
            file_modified_time = file_stats.st_mtime
            if file_obj.is_file():
                file_type = "file"
            if file_obj.is_dir():
                file_type = "dir"
            if file_obj.is_symlink():
                file_type = "symlink"
            # Saving captured stats to 'partial_file_table'
            partial_file_table = {
                    'path': file_path,
                    'type': file_type,
                    'size': file_size,
                    'creation_time': file_creation_time,
                    'modified_time': file_modified_time,
                    'location': None, #Set during Workspace Init
                    'favorite': False #Set during Workspace Init
                }
            #Appending partial to full file table...
            final_file_table[file_name] = partial_file_table
            # Looping For loop until no more files to scan...
        return final_file_table

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

class VarCallback:
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

class CaseData(object):
    '''
    A Nested Dictionary Object that is created for each unique SR import.
    The SR Number is the root primary key, defined as 'key_value' in 
    applicable methods throughout the Application.

    [Dictionary Structure]
    
        <MASTER_DICT> {
            <SR_number 0> {
                'tags': [] or None
                'account': 'string' or None
                'last_ran_time': 'string'
                'paths': {
                    'remote': <os.path.abspath Object>
                    'local': <os.path.abspath Object>
                    'custom': [<os.path.abspath Object 0>, <os.path.abspath Object 1>,] or None
                }
                'files': None or {
                    <FILE 0>: {
                        'path': file path - <os.abspath Object>
                        'type': "file" or "dir" or "symlink" - string
                        'size': file size - int in Bytes
                        'creation_time': Time of original creation - int in secs.
                        'modified_time': Time of last modified event - int in secs
                        'location': None or "remote" or "local" or "remote_local" or "custom" - string
                        'favorite': False - bool
                        }
                    <FILE 1>: {
                        ...
                    }
                }
                'product': 'string' or None
                'workspace': 'string' or None
                'bug': None or {
                    'support_id': 'string'
                    'issue_uuid': 'string'
                    'dev_id': 'string'
                }
                'favorite': bool
                'cached': bool
                'active': bool
            }
            <SR_number 1> {
                ...
            }
        }

    [What is Defined on Import?]

        CaseData has the following. These methods parse 'import_dict' passed
        from 'Gui.import_handler' and complete the defined task below.

            [item_dict] = {
                'sr_string': sr_string,
                'tags_list': tags_list,
                'account_string': account_string,
                'customs_list': customs_list,
                'product_string': product_string,
                'workspace_string': workspace_string,
                'important_bool': important_bool
            }

            - set_tags() : Returns list of [Tags] from the UI, seperated by ','
            - set_account() : Returns provided account name as a "string".
            - set_customs() : Returns list of <os.abspath Objects>, seperated by ','
            - set_product() : Returns provided Product as a "string".
            - set_workspace() : Returns provided Workspace as a "string".
            - set_favorite() : Returns provided bool
            - set_time() : Captures local time, and converts to readable "string".
                
        Files:
        The remote, local, and any custom root paths are scanned during during init.
        Using "os.scandir(path)". Because the resulting os.dirEntry objects are not 
        meant to be long-lived data types, Important file statistics such as its
        path, are stored to a nested Dictionary with the file_name as the root key. 
        
        The resulting file_table is then saved under the <SR Number>:{'Files':Entry} 
        At init, the file_table is incomplete, and will be appended to when a 
        "Workspace" for a target SR Number is rendered and any sub-directories can 
        be parsed through.

        This design is to reduce the time it takes to generate a new Casedata Entry, by
        only storing the files found in the root of 'x_path'. This allows the "Workspace"
        to render immediately and allow the user to work without having to wait for all
        files to be scanned. 
    '''
    def __init__(self, datastore, import_dict):
        self.case_datastore = datastore
        self.import_dict = import_dict
        self.sr_number = self.import_dict['sr_string']
        self.remote_path = os.path.abspath((LQ_NET_SHARE + "\\" + self.sr_number))
        self.local_path = os.path.abspath((LQ_LOCAL_DIR + "\\" + self.sr_number))

        #Adding content to Datastore
        self.build_intial_entries()
    
    # Initial Value Methods
    def build_intial_entries(self):
        '''
        Returns a Dictionary table that is stored into the "CaseDatastore"
        "key'ed" by the SR number as this is a unique value.
        '''
        self.case_data = {
            "tags":self.set_tags(),
            "account": self.set_account(),
            "last_ran_time":self.set_time(),
            "paths": self.set_dirs(),
            "files": self.set_files_snapshot(),
            "product":self.set_product(),
            "workspace": self.set_workspace(),
            "bug": self.set_bug(),
            "favorite": self.set_favorite(),
            "cached": False, #Set during workspace init
            "active": False, #Set during workspace init
            }
        
        #Adding to Datastore with sr_number as primary key
        self.case_datastore.add_casedata(self.sr_number, self.case_data)


    def set_tags(self):
        '''
        Using the tags defined in the "import" window, these strings are
        seperated by ',' and then stored as a list under...
        
        {<'SR_Number'>: {'tags': [<'here'>, <'and_here'>],}}
        '''
        tag_rstring = self.import_dict['tags_list']
        if tag_rstring == None:
            print("CaseData: No 'tags' Defined on import...")
        else:
            tags_list = tag_rstring.split(",")
            return tags_list

    def set_account(self):
        '''
        Using the 'account' defined in the "import" window, this string
        is stored under...
        
        {<'SR_Number'>: {'account': <'here'>,}}
        '''
        return self.import_dict['account_string']

    def set_time(self):
        '''
        Utilizing the 'datetime' library, the machine local time is captured, 
        converted to a readable format (Day, Month, 2-digit Year - TI:ME) and
        stored under...

        {<'SR_Number'>: {'last_ran_time': <'here'>,}}
        '''
        pass

    def set_dirs(self):
        '''
        Returns Dict for {<key_value>: 'dirs':{<here>}}

        These directory paths are calculated using the local and remote
        CONTANT paths plus the newly provided SR Number. 
        
        If a user imports a directory or file not found in one of these paths,--
        they can map the "orphaned" import to an SR Number, which will store
        that file or directory path under "custom_paths". Allowing this
        content to be rendered when calling the "parent" SR number to a 
        workspace. 
        '''
        # Formating and storing Custom_paths from Import.
        customs_rstring = self.import_dict['customs_list']
        custom_paths = [] #Stored as a list in Datastore**

        #Building Dict for {<key_value>: 'dirs':{<here>}}
        dirs_dict = {
            'remote': self.remote_path,
            'local': self.local_path,
            'customs': custom_paths
        }

        # Returning dirs_dict
        return dirs_dict

    # {<SR Number>: 'file':{'name':{}}} Methods
    def set_files_snapshot(self):
        '''
        Returns a dictionary that contains local, and remote file stat entries
        such as 'path' or 'creation_time'

        Entries for each <file_name>
            'path': file path - <os.abspath Object>
            'type': "file" or "dir" or "symlink" - string
            'size': file size - int in Bytes
            'creation_time': Time of original creation - int in secs.
            'modified_time': Time of last modified event - int in secs
            'location': None or "remote" or "local" or "remote_local" or "custom" - string
            'favorite': False - bool
        '''
        # Getting Remote Data
        remote_file_table = Utilities.get_file_stats_in(self.remote_path)

        # Getting Local Data
        if os.access(self.local_path, os.R_OK): #If file is read-able
            local_file_table = Utilities.get_file_stats_in(self.local_path)

        # Combining remote and local file tables, return result.
        combined_file_table = remote_file_table.update(local_file_table)
        return combined_file_table

    def set_workspace(self):
        '''
        Returns the default workspace, if not set
        manually during import.
        '''

    def set_product(self):
        '''
        Returns the abbreviated product name (MWG, ePO, etc.) which is
        determined by the contents of the root Remote path, if not set
        manually during import.
        '''
        pass


    def set_bug_info(self):
        '''
        Unless specified, new imports have a default value of 'None'.

        A "TSNS" value can be set manually during import. If defined, we can 
        query JIRA later (when we update the 'files' dict for example) to 
        populate the remaining missing bug details
        '''
        pass

class CaseDatastore:
    '''
    The Datastore for "CaseData" Objects. This is a nested Dictionary data 
    structure with the following syntax. 

    MASTER DICTIONARY { 
        <sr_number1>: { 
            <CaseData Object>
        }
        <sr_number2>: {
            <CaseData Object>
        }
    }

    Methods defined here are used by UI elements AND the Automation Engine to 
    easily interact with the data within the Datastore. 
    '''

    def __init__(self):
        print("Intializing Case Datastore")
        self.master_dict = {}

    def check_key(self, key_value):
        '''
        Checks the "CaseDatastore" if the defined key_value" is present.
        If key is present, return "True", otherwise return "None".
        '''
        if key_value in self.master_dict.keys():
            return True
        else:
            return None

    def add_casedata(self, key_value, case_dict):
        try:
            self.master_dict[key_value] = case_dict
            print("Successfully appended Case to Datastore.")
        except:
            print("Unable to add Case to Datastore.")

    # Query/Get methods
    def get_master_dict(self):
        return self.master_dict

    def query_files(self, key_value):
        '''
        Returns a Dict of {<key_value>: 'files': <File Stats>}

        First, check if 'key_value' exist in the Datastore. If present,
        fetch the entire sub-Dict of <key_value> files. If <key_value>
        is not present, returns None
        '''
        if self.check_key(key_value):
            file_dict = self.master_dict[key_value] ['files']
            return file_dict
        else:
            print("DS: <" + key_value + "> does not exist in Datastore.")
            return None
        
    def query_tags(self, key_value):
        '''
        Returns <key_value> : "tags" from Datastore.
        '''
        return self.master_dict[key_value]['tags']

    def query_workspace(self, key_value):
        '''
        Returns <key_value> : "workspace" from Datastore.
        '''
        return self.master_dict[key_value]['workspace']

    # Modifying Existing Data methods
    def update_for(self, key_value, sub_key, arg):
        '''
        Used to update root key values for under a target SR Number defined by
        'key_value'. Overwriting the original.

        - 'key_value' : Target SR Number - a string
        - 'sub_key' : The key to update like 'last_ran_time' - a string
        - 'arg' : Overwrites the previous value with this argument. - any
        '''
        self.master_dict[key_value][sub_key] = arg

    def update_files_for(self, key_value, file_name, file_key, arg):
        '''
        Used to update the nested 'files' key values for a specific file, 
        under a target SR Number defined by 'key_value'. Overwriting the 
        original.

        - 'key_value' : Target SR Number - a string
        - 'file_name' : The target file to be updated.
        - 'file_key' : The key in nested 'file' dict to update, like 'path'
        - 'arg' : Overwrites the previous value with this argument. - any
        '''
        self.master_dict[key_value]['files'][file_name][file_key] = arg

    def update_custom_paths_for(self, key_value, arg):
        '''
        Used to update the nested 'paths' key value for 'custom' paths, 
        under a target SR Number defined by 'key_value'. Overwriting the 
        original.

        Note, 'arg' will be converted to a os.abspath object in a list before 
        being stored in the Datastore.

        - 'key_value' : Target SR Number - a string
        - 'file_name' : The target file to be updated.
        - 'file_key' : The key in nested 'file' dict to update
        - 'arg' : Overwrites the previous value with this argument. - any
        '''
        converted_arg = os.path.abspath(arg)
        self.master_dict[key_value]['paths']['custom'] = converted_arg
    
    def update_bug_for(self, key_value, arg):
        '''
        Used to update the nested 'bug' key value for 'support_id' under a 
        target SR Number defined by 'key_value'. Overwriting the original.

        - 'key_value' : Target SR Number - a string
        - 'arg' : Overwrites the previous value with this argument. - a string
        '''
        self.master_dict[key_value]['bug']['support_id'] = arg

    # Appending Data methods
    def append_to_files_for(self, key_value, file_stats_dict):
        '''
        Creates a new <File Name> record under a target SR's 'files' 
        Dictionary, defined by 'key_value'.

        Note, 'file_stats_dict' should be a dictionary object with the necessary
        items. See below structure as reference...

            <file_stats_dict>
                'file_name': {
                    'path': file path - <os.abspath Object>
                    'type': "file" or "dir" or "symlink" - string
                    'size': file size - int in Bytes
                    'creation_time': Time of original creation - int in secs.
                    'modified_time': Time of last modified event - int in secs
                    'location': None or "remote" or "local" or "remote_local" or "custom" - string
                    'favorite': False - bool
                }
        '''
        self.master_dict[key_value]['files'] = file_stats_dict
        
class WorkspacePorter:
    '''
    Converts Tk Workspace layouts into an JSON files.
    '''

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


    def __init__(self, case_datastore):
        super().__init__()
        # Attaching UI to Case Datastore
        self.case_datastore = case_datastore

        # Register Callback method for "Gui.import_item" changes to "import_handler()"
        Gui.import_item.register_callback(self.import_handler)

        # Intializing Ttk.Frames 
        self.SearchPane = self.Tk_SearchPane()
        self.WorkspaceManager = self.Tk_WorkspaceManager(self.case_datastore)
        self.QueueManager = self.Tk_QueueManager()
        # Configuring UI Window
        self.expansion_buttons()
        self.config_grid()
        self.config_window()
        # STARTING TK/TTK UI
        self.start_ui()

    def expansion_buttons(self):
        # Show/Collapse Buttons
        self.btn_show_datastore = ttk.Button(
            self,
            text=">",
            width=2, 
            command=self.show_SearchCaseData
            )
        self.btn_show_queue = ttk.Button(
            self,
            text="^",
            command=self.show_QueueManager
            )

    def show_SearchCaseData(self):
        if self.SearchPane.frame_lable_datastore_state == "on":
            self.SearchPane.grid_remove()
            self.SearchPane.frame_lable_datastore_state = "off"
            self.btn_show_datastore['text'] = ">"
        else:
            self.SearchPane.grid()
            self.SearchPane.frame_lable_datastore_state = "on"
            self.btn_show_datastore['text'] = "<"

    def show_QueueManager(self):
        if self.QueueManager.frame_label_queue_state == "on":
            self.QueueManager.grid_remove()
            self.QueueManager.frame_label_queue_state = "off"
            self.btn_show_queue['text'] = "^"
        else:
            self.QueueManager.grid()
            self.QueueManager.frame_label_queue_state = "on"
            self.btn_show_queue['text'] = "˅"

    def config_grid(self):
        self.btn_show_datastore.grid(
            row=0, 
            column=0, 
            rowspan=6, 
            sticky="nsw"
            )
       
        self.btn_show_queue.grid(
            row=5, 
            column=2, 
            columnspan=3, 
            sticky="sew"
            )

        self.SearchPane.grid(
            row=0, 
            column=1, 
            rowspan=6, 
            padx=2, 
            pady=2, 
            sticky="nsew")
        self.SearchPane.grid_remove() # Start hidden

        self.WorkspaceManager.grid(
            row=0, 
            column=2,
            rowspan=3,
            padx=2,
            pady=2,
            sticky='nsew'
            )

        self.QueueManager.grid(
            row=4, 
            column=2, 
            columnspan=3, 
            sticky='nsew'
            )
        self.QueueManager.grid_remove() # Start Hidden
        self.rowconfigure(2, weight=1) 
        self.columnconfigure(2, weight=1)

    def config_window(self):
        # Intial Window Size
        self.geometry("800x600")
        # Options Menu
        self.menu = tk.Menu(self)
        self.menu_options = tk.Menu(self.menu, tearoff=0)
        self.menu_options.add_command(label="Launch Theme Wizard", command=self.Tk_ThemeWizard)
        self.menu.add_cascade(label="Options", menu=self.menu_options)
        self.config(menu=self.menu)
        
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
        spawn a seperate thread from the UI "mainThread", creating only the 
        inital CaseData Object for 'new_value'. 

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
                # Creating NEW CaseData Object Thread
                new_import = threading.Thread(
                    target=self.create_CaseData_for,
                    args=[new_import_dict]
                )
                #Starting Thread...
                new_import.start()
                # Wait for Import thread to complete
                new_import.join()
                # Finally, 
                self.WorkspaceManager.new_tab(import_key_value)
            else:
                self.WorkspaceManager.new_tab(import_key_value)

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
        CaseData(self.case_datastore, new_import_dict)
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
        class FrameThemeWizard():
            def __init__(self, master):
                self.master = master
                self.f_config = self.FrameThemeConfig(self.master)
                self.f_viewer = self.FrameJsonEditor(self.master)

            class FrameJsonEditor():
                def __init__(self, master):
                    pass

            class FrameThemeConfig():
                def __init__(self, master):
                    self.style = ttk.Style()
                    self.master = master

                    # Labels
                    self.label_theme = ttk.Label(
                        self.master,
                        text="Theme"
                    )
                    self.label_widget = ttk.Label(
                        self.master,
                        text="Widget Selector"
                    )
                    # Comboboxes
                    self.combox_theme = ttk.Combobox(
                        self.master,
                        postcommand=self.get_themes_list
                        )
                    self.combox_widget = ttk.Combobox(
                        self.master,
                        postcommand=self.get_widgets_list
                        )
                    # Colorpickers
                    self.btn_background = ttk.Button(
                        self.master,
                        text="Choose",
                        command=self.choose_color
                        )

                    self.btn_apply = ttk.Button(
                        self.master,
                        text="Apply",
                        command=self.apply_theme
                        )

                    # Grid
                    self.master.columnconfigure(0, weight=0)
                    self.label_theme.grid(row=0, column=0)
                    self.label_widget.grid(row=1, column=0)
                    self.combox_theme.grid(row=0, column=1)
                    self.combox_widget.grid(row=1, column=1)
                    self.btn_background.grid(row=14, column=1)
                    self.btn_apply.grid(row=15, column=0, columnspan=2)

                def get_themes_list(self):
                    self.combox_theme['values'] = self.style.theme_names()
                        
                def get_widgets_list(self):
                    self.widgets = [
                        "Label",
                        "Button",
                        "Combobox",
                        "Frame",
                        "LabelFrame",
                        "Progressbar",
                        "Scrollbar",
                        "Notebook"
                        ]
                    self.combox_widget['values'] = self.widgets        
                    ## REF -> ttk.Style().lookup("TButton", "font")

                def get_theme(self):
                    theme = {
                        "name": self.combox_theme.get(),
                    }
                    return theme

                def apply_theme(self):
                    theme = self.get_theme()
                    self.style.theme_use(theme["name"])

                def choose_color(self):
                    # variable to store hexadecimal code of color
                    color_code = tk.colorchooser.askcolor(title="Be Happy :)") 
                    print(color_code)

        def __init__(self):
            super().__init__()
            print("Starting Theme Wizard TopLevel")
            self.f_wizard = ttk.Frame(self)
            self.FrameThemeWizard(self.f_wizard)
            self.f_wizard.grid(row=0, column=0)

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

    class Tk_WorkspaceManager(ttk.Frame):
        '''
        The workhorse of the UI frames. This renders the default, and new
        workspace tabs when a user imports new data, or recalls a previously
        worked item (Sr Number, Path, etc.) through the "Case Data" pane.

        This is the 1/2 Tk.Frame classes that is passed the "case_datastore"
        from Gui.__init__ due to workspaces needing the ability to query the
        Datastore directly.

        Example.) Getting file_paths from <SR> for Treeview Rendering.
        '''
        def __init__(self, case_datastore):
            super().__init__()
            self.case_datastore = case_datastore

            # Rendering Tk Elements
            self.create_widgets()
            self.config_grid()

        # Ttk Config Methods
        def create_widgets(self):
            # Building "Notebook" for multiple SR's to tab through...
            self.notebook_browser = ttk.Notebook(
                self,
                width=200,
                height=160
                )
            self.default_tab(self.Tk_DefaultTab, "+")
 
        def config_grid(self):
            # Grid Layout
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.notebook_browser.grid(row=0, column=0, sticky='nsew')

        # Workspace Building Methods
        def default_tab(self, target_frame, header):
            '''
            Creates a the default import tab when a new session is rendered.
            '''
            f_newtab = ttk.Frame(self.notebook_browser)
            target_frame(f_newtab)
            self.notebook_browser.add(
                f_newtab,
                text = header
            )

        def new_tab(self, key_value):
            '''
            Creates a new workspace tab defined under the <key_value>'s
            'workspace' value in the Case Datastore.
            '''
            tab_header = key_value # Will need to be "cleaned" when not an SR Num.
            f_newtab = ttk.Frame(self.notebook_browser)
            workspace_to_render = self.case_datastore.query_workspace(key_value)






            target_frame(f_newtab, self.case_datastore, key_value)
            self.notebook_browser.add(
                f_newtab,
                text = tab_header
            )

        # File Browser Methods
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
            # Query the Datastore
            file_dict = self.query_files_for(key_value)

            # Render available content in the Datastore

            # Scanning Remote/Local files and sub-dirs

            # Update Datastore <key_value> with results from Scan


            # LEGACY
            #threading.Thread(target=self.fill_treeview, args=('', path_list)).start()

        def query_files_for(self, key_value):
            '''
            Returns the entire {<key_value>: 'files':{}} Dict if the
            <key_value> exist in the Datastore.
            '''
            file_dict = self.case_datastore.query_files(key_value)
            return file_dict

        def render_datastore_files(self, key_value):
            '''
            Inserts 'files' from <key_value> into the File Browser UI
            '''
            pass

        def scan_render_all_files(self, key_value):
            '''
            Using os.scandir, '
            '''
            pass

        def update_datastore_for(self, key_value):
            pass

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
                    command=self.draw_import_menu
                    )
                self.master.rowconfigure(0, weight=1)
                self.master.columnconfigure(0, weight=1)
                self.btn_big.grid(row=0, column=0, sticky="nsew")

            def draw_import_menu(self):
                '''
                Replaces the "Import" Button with a new Tk_ImportMenu(frame) instance.
                '''
                self.btn_big.grid_remove()
                import_menu_frame = Gui.Tk_ImportMenu(self.master)

        class Tk_WorkspacePane(ttk.PanedWindow):
            '''
            This should be the root window whenever a workspace contains
            multiple Frames aka "Widgets". This allows these Frames to be
            resized, or moved in the Workspace Window, expanding user
            configurability.

            Datastore variables are not accessed here, so they are not
            part of __init__ like other Workspace Frames
            '''
            def __init__(self, master, orient):
                super().__init__()
                self.parent = master
                self.orient = orient

        class Tk_FileBrowser(ttk.Frame):
            def __init__(self, master, case_datastore, key_value):
                super().__init__()
                self.master = master
                self.case_datastore = case_datastore
                self.key_value = key_value

                # Building Tk Elements
                self.create_widgets()
                self.config_grid()

                # Rendering Workspace Elements (Treeview, Notepad, etc.)
                self.start_file_tree(self.key_value)

            def create_widgets(self):               
                # Context Menu when "Right-Click"ing.
                self.right_click_menu = tk.Menu(self.master)
                # Building Treeview for SR Content
                self.tree_browser = ttk.Treeview(self.master, columns=("date", "size"))
                self.tree_browser.bind("<ButtonRelease-3>", self.popup)
                self.tree_browser.column("date", anchor="center", minwidth=100)
                self.tree_browser.column("size", anchor="center", minwidth=100)
                self.tree_ysb = ttk.Scrollbar(self.master, orient='vertical', command=self.tree_browser.yview)
                self.tree_xsb = ttk.Scrollbar(self.master, orient='horizontal', command=self.tree_browser.xview)
                self.tree_browser.configure(yscroll=self.tree_ysb.set, xscroll=self.tree_xsb.set)

                self.right_click_menu.configure(
                    relief='flat'
                    )
                self.right_click_menu.add_command(
                    label = "Unpack",
                    )
                self.right_click_menu.add_command(
                    label = "Download Selected"
                    )

            def config_grid(self):
                # GRID
                self.master.rowconfigure(0, weight=1)
                self.master.columnconfigure(0, weight=1)
                self.tree_browser.grid(row=0, column=0, sticky='nsew')
                self.tree_ysb.grid(row=0, column=1, sticky='ns')
                self.tree_xsb.grid(row=1, column=0, sticky='ew')

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

            def right_click_download(self):
                iid = self.tree_browser.selection()[0]
                Task.download(iid)

            def right_click_unpack(self):
                iid = self.tree_browser.selection()[0]
                print("unpack -> " + str(iid))

    class Tk_ImportMenu(ttk.Frame):
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
        def __init__(self, master):
            super().__init__()
            self.master = master
            self.advanced_opts_state = "off"
            self.direct_import = False

            self.label_sr = ttk.Label(
                self.master,
                text="SR Number",
                )
            self.entry_sr = ttk.Entry(
                self.master,
                width=30
                )
            self.label_adv_opts = ttk.Label(
                self.master,
                text="Show Advanced Options",
                anchor='e',
                )
            self.chkbtn_show_adv_opts = ttk.Checkbutton(
                self.master,
                command=self.show_advanced_opts,
                onvalue=(self.advanced_opts_state == "on"),
                offvalue=(self.advanced_opts_state == "off")
                )
            self.entry_tags = ttk.Entry(
                self.master,
                width=30
            )
            self.btn_browse = ttk.Button(
                self.master,
                text="Browse",
                command=self.direct_import_broswer
            )
            self.btn_start = ttk.Button(
                self.master,
                text="Import",
                command=self.start
            )
            self.config_grid()

        def config_grid(self):
            '''
            Defines Grid layout for Tk.Widgets defined in init.
            '''
            # Main Widgets
            self.label_sr.grid(row=0, column=0, padx=4, pady=4)
            self.entry_sr.grid(row=0, column=1, padx=4, pady=2)
            self.label_adv_opts.grid(row=1, column=0, padx=4, pady=4)
            self.chkbtn_show_adv_opts.grid(row=1, column=1, padx=4, pady=4)

            # Advanced options Frame
            self.entry_tags.grid(row=2, column=2, padx=4, pady=2)
            self.entry_tags.grid_remove()

            # Browse/Start Buttons
            self.btn_browse.grid(row=8, column=0, padx=4, pady=4)
            self.btn_start.grid(row=8, column=1, padx=4, pady=4)

        # Tk.Widgets "commands"
        def show_advanced_opts(self):
            if self.advanced_opts_state == "on":
                self.entry_tags.grid_remove()
                self.advanced_opts_state = "off"
            else:
                self.entry_tags.grid()
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

        def start(self):
            # Getting Values from GUI
            sr_string = self.entry_sr.get()
            tags_list = self.get_tags()
            account_string = self.get_account()
            customs_list = self.get_customs()
            product_string = self.get_product()
            workspace_string = self.get_workspace()
            important_bool = self.get_important()

            # Creating "import_item" Dictionary 
            new_item_dict = {
                'sr_string': sr_string,
                'tags_list': tags_list,
                'account_string': account_string,
                'customs_list': customs_list,
                'product_string': product_string,
                'workspace_string': workspace_string,
                'important_bool': important_bool
            }

            # Updating "import_item" -> Gui.import_handler(new_item_dict)   
            Gui.import_item.value = new_item_dict

            #Deleting Frame
            self.master.destroy()
        
        # Advanced Options "Get" methods 
        def get_tags(self):
            '''
            Returns list of [Tags] from the UI, seperated by ','

            If the ImportMenu entry is not populated, this will return None
            '''
            entry = self.entry_tags.get()

        def get_account(self):
            '''
            Returns provided account name as a "string".

            If the ImportMenu entry is not populated, this will return None
             '''
        
        def get_customs(self):
            '''
            Returns list of <os.abspath Objects>, seperated by ','

            If the ImportMenu entry is not populated, this will return None
             '''
        
        def get_product(self):
            '''
            Returns provided Product as a "string".

            If the ImportMenu entry is not populated, this will return None
            '''
        
        def get_workspace(self):
            '''
            Returns provided Workspace as a "string". 

            If the ImportMenu entry is not populated, this will return None
            '''

        def get_important(self):
            '''
            Returns bool if the favorite checkbox is checked or not.
            '''

    class Tk_SearchPane(ttk.LabelFrame):
        def __init__(self):
            super().__init__()
            self.text = "Recent Cases"
            self.frame_lable_datastore_state = "off"
            self.case_listbox = tk.Listbox(
                self,
                selectmode="single",
                )
            case_listbox_ysb = ttk.Scrollbar(
                self, 
                orient='vertical', 
                command=self.case_listbox.yview,
                )
            case_listbox_xsb = ttk.Scrollbar(
                self, 
                orient='horizontal', 
                command=self.case_listbox.xview,
                )
            self.case_listbox.bind(
                "<ButtonRelease-1>", 
                print("You pressed something :)")
                )
            self.case_listbox.configure(
                width=20,
                yscrollcommand=case_listbox_ysb.set, 
                xscrollcommand=case_listbox_xsb.set
            )

        # Grid Layout
            self.rowconfigure(0, weight=1)
            self.case_listbox.grid(row=0, column=0, sticky='nsew')
            case_listbox_ysb.grid(row=0, column=1, rowspan=3, sticky='ns')
            case_listbox_xsb.grid(row=2, column=0, sticky='ew')

        def create_entry(self, key_value):
            '''
            Appends "key_value" to the Tk.Listbox Widget.
            '''
            self.case_listbox.insert(0, key_value)

    class Tk_ProgBar(ttk.Frame):
        def __init__(self):
            super().__init__()
            self.thread = tk.StringVar()
            self.thread.trace_add('write', self.updateProgressBarLabel) #Write to "self.thread" to call updateProBar -> Changes label text.
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

            # GRID
            self.columnconfigure(0, weight=1)
            self.columnconfigure(1, weight=2)
            self.label_progbar.grid(row=0, column=0, sticky="nsw")
            self.progbar.grid(row=0, column=1, sticky="nsew")

        def updateProgressBarLabel(self, *args):  # when self.thread var is changed - this menthod is called.
            # LEGACY> self.label_progbar.config(text=self.thread)
            pass

        def updateProgressBar(self, *args):
            # LEGACY> self.progbar.config(value=self.progbar_intvar)
            pass

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

#RUN
case_datastore = CaseDatastore()
#Other Engine Code Here...
Gui(case_datastore)