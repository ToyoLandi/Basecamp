# Basecamp 0.2 BETA
# Written by Collin Spears, Network TSE

'''
Welcome to 'bcamp_extensions_manager'. This is the class that is called when
a user hits 'unpack' on a target file, and other misc. extension management
processes.
'''
import os
import json
import shutil
import bcamp_api 
import inspect
import pathlib
import logging
import py_compile
import importlib.util


def debug_caller():
    '''
    Short-cut to get string of "Caller method"

    Call inspect.stack() to access the stack of the currently running process.
    This stack is ordered in first-in-first-out such that the most recently 
    called methods will be earlier on in an array of call stack frame. Access
    the stack frame of the caller method using inspect.stack()[1]. Select the
    third element of this tuple to access the name of the method.

    Source: https://www.kite.com/python/answers/how-to-get-the-caller's-method
    -name-from-the-called-method-in-python
    '''
    stack = inspect.stack()
    sframe= stack[1]
    caller = sframe[3]
    return ("--DEBUG--\n\n", caller, "\n\n-- :D --")


class Automations:
    '''
    Sub-Manager for the Automation User extensions
    '''
    def __init__(self):
        self.RPATH = (str(pathlib.Path(__file__).parent.absolute())).rpartition('\\')[0]
        # Configuring logging
        bcamp_api.setup_log('automations.log')
        self.log = logging.getLogger('automations.log')
        self.avail_imports = self.scan_automations()

    def scan_automations(self):
        '''
        Getting all file 'stats' in /../automations
        that comply with the expected format of
        'name'/ [example.py], [properties.json]
        '''
        temp_file_dict = {}
        temp_list = [] # Tuple: (name, path, prop path)
        # Getting temp_list values
        self.log.info("Scanning './extensions/automations/' folder...")
        with os.scandir(self.RPATH + "\\extensions\\automations") as folder:
            for file in folder:
                if file.is_dir and os.access(file.path + "\\properties.json", os.R_OK):
                    self.log.info("Found " + file.name + "!")
                    temp_list.append((file.name, file.path + "\\automation.py", file.path + "\\properties.json"))

        # Testing unpacker.py for errors via compile. IF an error occurs, this
        # path is removed from "temp_list" before reading the properties.json.
        for index, val in enumerate(temp_list):
            self.log.info("Checking " + "[" + val[0] + "]")
            try:
                # val[1]: Explicit Path / Optimize:2 Remove __debug__, asserts
                # and docstrings, do_raise: Raises errors from nested .py to 
                # this file.
                py_compile.compile(val[1], optimize=2, doraise=True)
                self.log.info("Successfully compiled! - " + "[" + val[0] + "]")
                self.log.info("Deleting temporary .pyc file for" + "[" + val[0] + "]")
                #converting val[1] to py_cache folder and deleting it.
                delete_path = val[1].rpartition("\\")[0] + "\\__pycache__"
                shutil.rmtree(delete_path)
                self.log.info("Successfully removed temporary .pyc - " + "[" + val[0] + "]")
            except Exception as error:
                self.log.info("---< COMPILATION ERROR " + str("[" + val[0] + "]") + " >---\n\n" 
                    + str(error)
                    + "\n"
                    )
                temp_list.pop(index)


        # Getting properties.json for each tuple in temp_list
        # [(name, properties.json path)]
        for index, val in enumerate(temp_list):
            with open(val[2], 'r') as read_file:
                props = json.load(read_file)
                # Adding to temp_file_dict which is returned...
                if isinstance(props, dict):
                    temp_file_dict[val[0]] = props
                    self.log.info("Successfully imported 'properties.json' for " + "[" + val[0] + "]")
                else:
                    self.log.info("Failed to open 'properties.json' for " + "[" + val[0] + "]")
        
        return temp_file_dict

    def get(self):
        '''
        Simple in name, mighty in use. "Get" is called by the UI to populate
        the available automations. If a user enables an automation, the lf_ui class
        will look at the properties file, and build the config.py for the
        checked in unpackers.
        '''
        updated_dict = self.scan_automations()
        return updated_dict

class Unpackers:
    '''
    Sub-Manager for the Unpackers extensions
    '''
    def __init__(self):
        self.RPATH = (str(pathlib.Path(__file__).parent.absolute())).rpartition('\\')[0]
        # Configuring logging
        bcamp_api.setup_log('unpackers.log')
        self.log = logging.getLogger('unpackers.log')
        self.avail_imports = self.scan_unpackers()

    def scan_unpackers(self):
        '''
        Getting all file 'stats' in /../unpackers
        that comply with the expected format of
        'name'/ [example.py], [properties.json]
        '''
        temp_file_dict = {}
        temp_list = [] # Tuple: (name, path, prop path)
        # Getting temp_list values
        self.log.info("Scanning './extensions/unpackers/' folder...")
        with os.scandir(self.RPATH + "\\extensions\\unpackers") as folder:
            for file in folder:
                if file.is_dir and os.access(file.path + "\\properties.json", os.R_OK):
                    self.log.info("Found " + file.name + "!")
                    temp_list.append((file.name, file.path + "\\unpacker.py", file.path + "\\properties.json"))

        # Testing unpacker.py for errors via compile. IF an error occurs, this
        # path is removed from "temp_list" before reading the properties.json.
        for index, val in enumerate(temp_list):
            self.log.info("Checking " + "[" + val[0] + "]")
            try:
                # val[1]: Explicit Path / Optimize:2 Remove __debug__, asserts
                # and docstrings, do_raise: Raises errors from nested .py to 
                # this file.
                py_compile.compile(val[1], optimize=2, doraise=True)
                self.log.info("Successfully compiled! - " + "[" + val[0] + "]")
                self.log.info("Deleting temporary .pyc file for" + "[" + val[0] + "]")
                #converting val[1] to py_cache folder and deleting it.
                delete_path = val[1].rpartition("\\")[0] + "\\__pycache__"
                shutil.rmtree(delete_path)
                self.log.info("Successfully removed temporary .pyc - " + "[" + val[0] + "]")
            except Exception as error:
                self.log.info("---< COMPILATION ERROR " + str("[" + val[0] + "]") + " >---\n\n" 
                    + str(error)
                    + "\n"
                    )
                temp_list.pop(index)


        # Getting properties.json for each tuple in temp_list
        # [(name, properties.json path)]
        for index, val in enumerate(temp_list):
            with open(val[2], 'r') as read_file:
                props = json.load(read_file)
                # Adding to temp_file_dict which is returned...
                if isinstance(props, dict):
                    temp_file_dict[val[0]] = props
                    self.log.info("Successfully imported 'properties.json' for " + "[" + val[0] + "]")
                else:
                    self.log.info("Failed to open 'properties.json' for " + "[" + val[0] + "]")
        
        return temp_file_dict

    def get(self):
        '''
        Simple in name, mighty in use. "Get" is called by the UI to populate
        the available unpackers. If a user enables an unpacker, the lf_ui class
        will look at the properties file, and build the config.py for the
        checked in unpackers.
        '''
        updated_dict = self.scan_unpackers()
        return updated_dict


class Workpanes:
    '''
    "Workpanes" is responsible for checking the /../example.py signature, and
    safely importing the code written within. This class will provide list of
    available workpanes to the UI, which the user can render in a Workspace.
    These are the "apps" you see within a Workspace, such as the Notepad or 
    Filebrowser. This class is intialized in "lf_core" and then passed to the 
    lf_ui.Gui to actually draw the window. 
    '''
    def __init__(self):
        self.RPATH = (str(pathlib.Path(__file__).parent.absolute())).rpartition('\\')[0]
        # Configuring logging
        bcamp_api.setup_log('workpanes.log')
        self.log = logging.getLogger('workpanes.log')
        self.avail_imports = self.scan_workpanes()

    def scan_workpanes(self):
        '''
        Getting all file 'stats' in /../workpanes
        that comply with the expected format of
        'name'/ [example.py], [properties.json]
        '''
        temp_file_dict = {}
        temp_list = [] # Tuple: (name, path, prop path)
        # Getting temp_list values
        self.log.info("Scanning './extensions/workpanes/' folder...")
        with os.scandir(self.RPATH + "\\extensions\\workpanes") as folder:
            for file in folder:
                if file.is_dir and os.access(file.path + "\\properties.json", os.R_OK):
                    self.log.info("Found " + file.name + "!")
                    temp_list.append((file.name, file.path + "\\workpane.py", file.path + "\\properties.json"))

        # Testing Workpane.py for errors via compile. IF an error occurs, this
        # path is removed from "temp_list" before reading the properties.json.
        for index, val in enumerate(temp_list):
            self.log.info("Checking " + "[" + val[0] + "]")
            try:
                # val[1]: Explicit Path / Optimize:2 Remove __debug__, asserts
                # and docstrings, do_raise: Raises errors from nested .py to 
                # this file.
                py_compile.compile(val[1], optimize=2, doraise=True)
                self.log.info("Successfully compiled! - " + "[" + val[0] + "]")
                self.log.info("Deleting temporary .pyc file for" + "[" + val[0] + "]")
                #converting val[1] to py_cache folder and deleting it.
                delete_path = val[1].rpartition("\\")[0] + "\\__pycache__"
                shutil.rmtree(delete_path)
                self.log.info("Successfully removed temporary .pyc - " + "[" + val[0] + "]")
            except Exception as error:
                self.log.info("---< COMPILATION ERROR " + str("[" + val[0] + "]") + " >---\n\n" 
                    + str(error)
                    + "\n"
                    )
                temp_list.pop(index)


        # Getting properties.json for each tuple in temp_list
        # [(name, properties.json path)]
        for index, val in enumerate(temp_list):
            with open(val[2], 'r') as read_file:
                props = json.load(read_file)
                # Adding to temp_file_dict which is returned...
                if isinstance(props, dict):
                    temp_file_dict[val[0]] = props
                    self.log.info("Successfully imported 'properties.json' for " + "[" + val[0] + "]")
                else:
                    self.log.info("Failed to open 'properties.json' for " + "[" + val[0] + "]")
        
        return temp_file_dict

    def get(self):
        '''
        Simple in name, mighty in use. "Get" is called by the UI to populate
        the available workpanes. If a user enables a pane in the UI, the GUI
        class will update the config.json record.
        '''
        updated_dict = self.scan_workpanes()
        return updated_dict