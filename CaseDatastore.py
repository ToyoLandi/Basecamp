import os
import stat
import json
import datetime
import threading


'''
Values from Config Simulated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''
config_netShare = "\\\\dnvcorpvf2.corp.nai.org\\nfs_dnvspr"
config_localFolder = "C:\\Users\\cspears1\\Desktop\\CaseContent"
LQ_NET_SHARE = config_netShare
LQ_LOCAL_DIR = config_localFolder

'''
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 
.~~~~~~~~~~~~~~~~~~~~~~~~~
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
        print("get_dir - Start")
        if os.path.isdir(path):
            dir_entry_list = []
            with os.scandir(path) as scanner:
                for entry in scanner:
                    dir_entry_list.append(entry)
            print("get_dir - Fin")
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
                print(debug_val + "[", file_obj.name, "] > " + file_location)                

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
                    file_dict.update(single_file_table)
            final_file_table = file_dict
            print("DEBUG> Done scanning " + debug_val)
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
                print(debug_val + "[", file_obj.name, "] > " + file_location)                

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
            print("DEBUG> Done scanning " + debug_val)
            return final_file_table

class Data(object):
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
            "notes": "" #Defined later by user...
            }
        
        #Adding to Datastore with sr_number as primary key
        self.case_datastore.add_casedata(self.sr_number, self.case_data)

    def set_favorite(self):
        '''
        Based on the checkbox value of "Favorite" in the Import UI window.

        Sets the Casedata 'favorite' value to True or False.
        '''
        return self.import_dict['important_bool']

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
            return tag_rstring

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
        time = str(datetime.datetime.now())
        return time

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
        customs_list = self.import_dict['customs_list']

        #Building Dict for {<key_value>: 'dirs':{<here>}}
        dirs_dict = {
            'remote': self.remote_path,
            'local': self.local_path,
            'customs': customs_list
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
        if os.access(self.remote_path, os.R_OK): #If file is read-able
            remote_file_table = Utilities.get_snapshot(self.remote_path, debug_val="rSnapshot")
        else:
            remote_file_table = {}
        
        # Getting Local Data
        if os.access(self.local_path, os.R_OK): #If file is read-able
            local_file_table = Utilities.get_snapshot(self.local_path, debug_val="lSnapshot")
        else:
            local_file_table = {}
        
        # Getting 'customs' Data
        customs_list = self.import_dict['customs_list']
        customs_dict = None
        if customs_list != None:
            for path in customs_list:
                try:
                    customs_dict = Utilities.get_snapshot(path, debug_val="cSnapshot")
                except TypeError:
                    customs_dict = None
                
        #Building 'files' Dict entry
        files_dict = {
            'remote': remote_file_table,
            'local': local_file_table,
            'customs': customs_dict
        }
        return files_dict

    def set_workspace(self):
        '''
        Returns the default workspace, if not set
        manually during import.
        '''
        return self.import_dict['workspace_string']

    def set_product(self):
        '''
        Returns the abbreviated product name (MWG, ePO, etc.) which is
        determined by the contents of the root Remote path, if not set
        manually during import.
        '''
        return self.import_dict['product_string']

    def set_bug(self):
        '''
        Unless specified, new imports have a default value of 'None'.

        A "TSNS" value can be set manually during import. If defined, we can 
        query JIRA later (when we update the 'files' dict for example) to 
        populate the remaining missing bug details
        '''
        return self.import_dict['bug_string']

class Datastore:
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
        print("Connecting to 'datastore.json'...")
        # Try to open exisiting 'datastore.json'
        if os.access("datastore.json", os.R_OK):
            print("Datastore Exist!")
        else:
            print("Not Found. Generating new 'datastore.json' file...")
            self.root_dict ={
                'version': '0.1 Alpha',
                'created': str(datetime.datetime.now())
            }
            with open("datastore.json", "w") as write_file:
                json.dump(self.root_dict, write_file, indent=4)

    def check_key(self, key_value):
        '''
        Checks the "CaseDatastore" if the defined key_value" is present.
        If key is present, return "True", otherwise return "None".
        '''
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            if key_value in self.master_dict.keys():
                return True
            else:
                return None

    def add_casedata(self, key_value, case_dict):
        try:
            with open("datastore.json", "r") as read_file:
                self.master_dict = json.load(read_file)
                self.master_dict[key_value] = case_dict
                print("IMPORT: Successfully appended <" + key_value + "> Case to Datastore.")
                #Call JSON serializer to backup new changes.
                with open("datastore.json", "w") as write_file:
                    json.dump(self.master_dict, write_file, indent=4)
        except:
            print("Unable to add Case to Datastore.")

    # Query/Get methods
    def get_master_dict(self):
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            return self.master_dict

    def query_files(self, key_value):
        '''
        Returns a Dict of {<key_value>: 'files': <File Stats>}

        First, check if 'key_value' exist in the Datastore. If present,
        fetch the entire sub-Dict of <key_value> files. If <key_value>
        is not present, returns None
        '''
        if self.check_key(key_value):
            with open("datastore.json", "r") as read_file:
                self.master_dict = json.load(read_file)
                file_dict = self.master_dict[key_value] ['files']
                return file_dict
        else:
            print("DS: <" + key_value + "> does not exist in Datastore.")
            return None
        
    def query_tags(self, key_value):
        '''
        Returns <key_value> : "tags" from Datastore.
        '''
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            return self.master_dict[key_value]['tags']

    def query_workspace(self, key_value):
        '''
        Returns <key_value> : "workspace" from Datastore.
        '''
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            return self.master_dict[key_value]['workspace']

    def query_for(self, key_value, element_name):
        '''
        Returns <key_value> : <element_name> from Datastore.
        '''
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            return self.master_dict[key_value][element_name]

    # Modifying Existing Data methods
    def update_for(self, key_value, sub_key, arg):
        '''
        Used to update root key values for under a target SR Number defined by
        'key_value'. Overwriting the original.

        - 'key_value' : Target SR Number - a string
        - 'sub_key' : The key to update like 'last_ran_time' - a string
        - 'arg' : Overwrites the previous value with this argument. - any
        '''
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            self.master_dict[key_value][sub_key] = arg
            with open("datastore.json", "w") as write_file:
                json.dump(self.root_dict, write_file, indent=4)

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
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            self.master_dict[key_value]['files'][file_name][file_key] = arg
            with open("datastore.json", "w") as write_file:
                json.dump(self.master_dict, write_file, indent=4)
        
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
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            converted_arg = os.path.abspath(arg)
            self.master_dict[key_value]['paths']['custom'] = converted_arg
            with open("datastore.json", "w") as write_file:
                json.dump(self.master_dict, write_file, indent=4)
    
    def update_bug_for(self, key_value, arg):
        '''
        Used to update the nested 'bug' key value for 'support_id' under a 
        target SR Number defined by 'key_value'. Overwriting the original.

        - 'key_value' : Target SR Number - a string
        - 'arg' : Overwrites the previous value with this argument. - a string
        '''
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            self.master_dict[key_value]['bug']['support_id'] = arg
            with open("datastore.json", "w") as write_file:
                json.dump(self.master_dict, write_file, indent=4)

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
        with open("datastore.json", "r") as read_file:
            self.master_dict = json.load(read_file)
            self.master_dict[key_value]['files'] = file_stats_dict
            with open("datastore.json", "w") as write_file:
                json.dump(self.master_dict, write_file, indent=4)
    
    def test_method(self, key_value):
        return (key_value + " would be ran...")
 