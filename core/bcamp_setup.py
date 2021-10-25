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
import time
import logging
import pathlib
import sqlite3

BCAMP_ROOTPATH = bcamp_api.BCAMP_ROOTPATH


class CreateDirs:
    '''
    Creates the default folder structure on install. 
    '''
    def __init__(self):
        # Defining 'root' path
        self.RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
        # Defining folder path
        core_path = self.RPATH + "\\core"
        downloads_path = self.RPATH + "\\downloads"
        automations_path = self.RPATH + "\\extensions\\automations"
        logs_path = self.RPATH + "\\logs"
        if not os.access(core_path, os.R_OK):
            os.makedirs(core_path)
        if not os.access(downloads_path, os.R_OK):
            os.makedirs(downloads_path)
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
            print("SQLite3 started successfully! - Connected to DB.")
        else:
            print("Not Found. Generating new 'basecamp.db' file...")
            # Creating .db file
            file = open(db_path, "w+")
            file.close()
            print("Successfully created basecamp.db file")

        # Configure Environment Vars
        self.config_env()
        # Connecting to sqlite DB
        self.db_connection = sqlite3.connect(db_path)
        # Create default tables
        self.dbshell = self.db_connection.cursor()
        self.dbshell.execute(self.config_schema())
        self.dbshell.execute(self.automations_schema())
        self.dbshell.execute(self.cases_schema())
        self.dbshell.execute(self.tags_schema())
        self.dbshell.execute(self.favorite_files_schema())
        self.dbshell.execute(self.parser_schema())

        # Populate bCamp tables with default values
        try:
            bcamp_api.gen_bcamp_config()
        except sqlite3.IntegrityError:
            pass

        # Close connection - Jobs Done!
        self.db_connection.commit()
        self.dbshell.close()

    def config_env(self):
        os.environ['BCAMP'] = 'null'

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
                        notepad_path TEXT,
                        ui_start_res TEXT NOT NULL,
                        ui_render_top_menu TEXT NOT NULL,
                        ui_caseviewer_location TEXT NOT NULL,
                        ui_render_caseviewer TEXT NOT NULL,
                        ui_caseviewer_search_location TEXT NOT NULL,
                        ui_render_caseviewer_search TEXT NOT NULL,
                        ui_render_favtree TEXT NOT NULL,
                        user_texteditor TEXT NOT NULL                     
             ); """
        return query

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
                        product TEXT COLLATE NOCASE,
                        account TEXT COLLATE NOCASE,
                        notes TEXT,
                        bug_id TEXT COLLATE NOCASE,
                        workspace TEXT,
                        files_table TEXT,
                        import_time TEXT,
                        last_ran_time TEXT,
                        last_file_count TEXT,
                        jira_title TEXT,
                        jira_status TEXT,
                        jira_updated TEXT,
                        jira_description TEXT,
                        jira_sr_owner TEXT,
                        jira_comments TEXT,
                        jira_last_comment_time TEXT,
                        jira_linkedissues TEXT COLLATE NOCASE,
                        jira_project TEXT,
                        jira_priority TEXT,
                        jira_components TEXT,
                        jira_affected_ver TEXT,
                        jira_resolution TEXT,
                        jira_fix_ver TEXT,
                        jira_notify_flag INTEGER,
                        file_notify_flag INTEGER
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
                        enabled TEXT NOT NULL,
                        version TEXT NOT NULL,
                        exe_path TEXT NOT NULL,
                        exe_sha256 TEXT NOT NULL,
                        downloadFirst TEXT NOT NULL,
                        author TEXT,
                        description TEXT,
                        extensions TEXT,
                        user_options TEXT,
                        type TEXT
             ); """
        return query
    
    def template_files_schema(self):
        '''
        Defines how each SR's files table should be constructed! 
        '''
        query = """CREATE TABLE IF NOT EXISTS files_template (
                        name TEXT NOT NULL,
                        location TEXT NOT NULL,
                        path TEXT UNIQUE NOT NULL,
                        type TEXT NOT NULL,
                        size TEXT NOT NULL,
                        creation_time TEXT NOT NULL,
                        modified_time TEXT NOT NULL,
                        date_range TEXT NOT NULL,
                        favorite TEXT NOT NULL,
                        notes TEXT NOT NULL,
        ); """
        return query

    def favorite_files_schema(self):
        '''
        Schema that defines a users favorite "logs" and saves
        the name and paths for the UI to render.
        '''
        query = """CREATE TABLE IF NOT EXISTS bcamp_favfiles (
                        file_name TEXT NOT NULL,
                        root_path TEXT NOT NULL,
                        UNIQUE(file_name, root_path) ON CONFLICT IGNORE
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

    def parser_schema(self):
        '''
        Defines how each SR's files table should be constructed! 
        '''
        query = """CREATE TABLE IF NOT EXISTS bcamp_parser (
                        id TEXT UNIQUE NOT NULL,
                        type TEXT NOT NULL,
                        return TEXT NOT NULL,
                        target TEXT NOT NULL,
                        rule TEXT NOT NULL
        ); """
        return query


class CheckReqs:
    '''
    Checks the required packages are available for import.
    '''
    proxy_address = 'webgateway.itm.mcafee.com'
    proxy_port = '9090'
    missing_mods = []
    #3rd Party Bois
    try:
        import paramiko
    except:
        missing_mods.append('paramiko')
    try:
        from sshtunnel import SSHTunnelForwarder
    except:
        missing_mods.append('sshtunnel')
    try:
        import requests
    except:
        missing_mods.append('requests')
    
    if missing_mods != None:
        # Create file in install location containing commands...
        reqs_file = open((BCAMP_ROOTPATH + 'MISSING_REQUIREMENTS.txt'), 'w+')
        for item in missing_mods:
            pip_string = (
                'python -m pip install --proxy=http://username:password@' 
                + proxy_address 
                + ':' 
                + proxy_port
                + ' ' + item
            )
            
            reqs_file.write(pip_string)
            print("MISSING REQUIRED MODULE -", item, "- Install this using...")
            print("\tpython -m pip install", item)
            print("\tProxy?")
            print("\tpython -m pip install --proxy=http://[username:password]@proxyserver:port", item)
        # Close FILE
        reqs_file.close()

    # ITEMS ALL IN STDLIB
    ## Private imports
    #import bcamp_api
    #import bcamp_setup
    ## Public Imports
    #import io
    #import os
    #import re
    #import stat
    #import json
    #import time
    #import queue
    #import ctypes
    #import shutil
    #import pickle
    #import pprint
    #import hashlib
    #import logging
    #import sqlite3
    #import pathlib
    #import datetime
    #import importlib
    #import threading
    #import webbrowser
    #import py_compile
    #import subprocess
    #import tkinter as tk
    #import tkinter.font as tk_font
    #from tkinter import ttk, colorchooser, filedialog, dnd
    #from optparse import OptionParser