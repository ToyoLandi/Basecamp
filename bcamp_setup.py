# Basecamp 0.2 BETA
# Written by Collin Spears, Network TSE

'''
Welcome to 'bcamp_setup.py'. This class file handles the installation process,
and automatically generates a "config.json" file based on user preferences.
'''
#Private Imports
import bcamp_api

#Public Imports
import os
import json
import time
import logging
import pathlib
import sqlite3


class CreateDirs():
    '''
    Creates the default folder structure on install. 
    '''
    def __init__(self):
        # Defining 'root' path
        self.RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
        # Defining folder path
        core_path = self.RPATH + "\\core"
        downloads_path = self.RPATH + "\\downloads"
        unpackers_path = self.RPATH + "\\extensions\\unpackers"
        workpanes_path = self.RPATH + "\\extensions\\workpanes"
        automations_path = self.RPATH + "\\extensions\\automations"
        logs_path = self.RPATH + "\\logs"
        if not os.access(core_path, os.R_OK):
            os.makedirs(core_path)
        if not os.access(downloads_path, os.R_OK):
            os.makedirs(downloads_path)
        #if not os.access(unpackers_path, os.R_OK):
        #    os.makedirs(unpackers_path)
        #if not os.access(workpanes_path, os.R_OK):
        #    os.makedirs(workpanes_path)
        if not os.access(logs_path, os.R_OK):
            os.makedirs(logs_path)
        if not os.access(automations_path, os.R_OK):
            os.makedirs(automations_path)

class CreateDB:
    '''
    Creates the 'basecamp.db' SQLite3 File - and populates it with the 
    default schema. 

    NOTE: Parameter markers can be used only for expressions, i.e., values.
    You cannot use them for identifiers like table and column names. If a
    query needs to be written with identifiers being a variable, THIS "query"
    SHOULD NOT TAKE INPUT FROM USERS. THIS WILL EXPOSE THE DB TO SQL
    INJECTION. 
    '''

    def __init__(self):
        self.RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
        db_path = self.RPATH + "\\core\\basecamp.db"
        print("Connecting to 'basecamp.db'...")
        # Try to open exisiting 'datastore.json'
        if os.access(db_path, os.R_OK):
            print("Datastore Exist!")
        else:
            print("Not Found. Generating new 'basecamp.db' file...")
            # Creating .db file
            file = open(db_path, "w+")
            file.close()
            print("Successfully created basecamp.db file")

        # Connecting to sqlite DB
        self.db_connection = sqlite3.connect(db_path)
        # Create default tables
        self.dbshell = self.db_connection.cursor()
        self.dbshell.execute(self.config_schema())
        self.dbshell.execute(self.automations_schema())
        self.dbshell.execute(self.cases_schema())
        self.dbshell.execute(self.tags_schema())
        self.dbshell.execute(self.logviewer_supported_ext_schema())
        self.dbshell.execute(self.favorite_files_schema())
        # Populate bCamp tables with default values
        try:
            bcamp_api.gen_bcamp_config()
        except sqlite3.IntegrityError:
            pass

        print("$ config generated?")
        # Close connection - Jobs Done!
        self.db_connection.commit()
        self.dbshell.close()

    def cases_schema(self):
        '''
        Main table that contains all imported SRs with their local data such
        as Notes, Account strings, bug_ids, etc.
        '''
        query = """ CREATE TABLE IF NOT EXISTS cases (
                        sr_number TEXT UNIQUE,
                        remote_path TEXT NOT NULL,
                        local_path TEXT NOT NULL,
                        pinned INTEGER NOT NULL,
                        product TEXT,
                        account TEXT,
                        notes TEXT,
                        bug_id TEXT,
                        workspace TEXT,
                        files_table TEXT,
                        import_time TEXT,
                        last_ran_time TEXT
             ); """
        return query
    
    def config_schema(self):
        '''
        The table that defines user choices, and general application config
        data such as root paths, UI defaults, etc.
        '''
        query = """ CREATE TABLE IF NOT EXISTS bcamp_config (
                        version TEXT UNIQUE,
                        root_path TEXT NOT NULL,
                        remote_root TEXT NOT NULL,
                        download_root  TEXT NOT NULL,
                        time_zone TEXT NOT NULL,
                        time_format TEXT NOT NULL,
                        dev_mode TEXT NOT NULL,
                        ui_start_res TEXT NOT NULL,
                        ui_render_top_menu TEXT NOT NULL,
                        ui_caseviewer_location TEXT NOT NULL,
                        ui_render_caseviewer TEXT NOT NULL                       
             ); """
        return query

    def automations_schema(self):
        '''
        The table that defines user-defined Add-ons called Automations.

        These store the values defined by the Automation Dev found in 
        properties.json
        '''
        query = """ CREATE TABLE IF NOT EXISTS bcamp_automations (
                        name TEXT UNIQUE,
                        version TEXT NOT NULL,
                        author TEXT,
                        description TEXT,
                        extensions TEXT,
                        downloadFirst TEXT,
                        exe_path TEXT
             ); """
        return query
    
    def template_files_schema(self):
        '''
        Defines how each SR's files table should be constructed! 
        '''
        query = """CREATE TABLE IF NOT EXISTS files_template (
                        name TEXT NOT NULL,
                        location TEXT NOT NULL,
                        path TEXT NOT NULL,
                        type TEXT NOT NULL,
                        size TEXT NOT NULL,
                        creation_time TEXT NOT NULL,
                        modified_time TEXT NOT NULL,
                        date_range TEXT NOT NULL,
                        favorite TEXT NOT NULL,
                        notes TEXT NOT NULL,
                        UNIQUE(name, location) ON CONFLICT IGNORE
        ); """
        return query

    def favorite_files_schema(self):
        '''
        Schema that defines a users favorite "logs" and saves
        the name and paths for the UI to render.
        '''
        query = """CREATE TABLE IF NOT EXISTS favorite_files (
                        file_name TEXT NOT NULL,
                        root_path TEXT NOT NULL,
                        UNIQUE(file_name, root_path) ON CONFLICT IGNORE
        ); """
        return query
    
    def logviewer_supported_ext_schema(self):
        '''
        Schema that defines supported file extensions to render in 
        LogViewer within the UI.
        '''
        query = """CREATE TABLE IF NOT EXISTS logviewer_supported_ext (
                        extension TEXT UNIQUE NOT NULL
        ); """
        return query

    def tags_schema(self):
        '''
        Schema to store Tags assigned to each SR. These are rendered by the 
        UI.
        '''
        query = """CREATE TABLE IF NOT EXISTS tags (
                        tag TEXT NOT NULL,
                        sr_number TEXT NOT NULL,
                        UNIQUE(tag, sr_number) ON CONFLICT IGNORE
        ); """
        return query
