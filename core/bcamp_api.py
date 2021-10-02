# Basecamp 0.2 BETA
# Written by Collin Spears, Network TSE

'''
Welcome to "bcamp_api". This module contains various general methods, and
classes that support the UI and Backend processes for Basecamp.

In the future, this may always be CLI calls to supplement automation.
'''

import os
import re
import stat
import json
import time
import queue
import shutil
import pickle
import pprint
import hashlib
import logging
import sqlite3
import pathlib
import datetime
import ctypes
import importlib
import threading
import webbrowser
import py_compile
import subprocess
import tkinter as tk
from tkinter import filedialog



'''
[ GLOBAL API  CONSTANTS ]
'''
# GLOBAL BCAMP VERSION STRING
BCAMP_VERSION = "DEV-Sep22"
# ROOT PATH CONSTANT FOR INSTALL DIR.
BCAMP_ROOTPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
# PROD. NAS PATH CONSTANT
BCAMP_PRODNAS = r'\\dnvcorpvf2.corp.nai.org\nfs_dnvspr'


''' 
[ Database Queries/Methods]

NOTE: Parameter markers can be used only for expressions, i.e., values.
You cannot use them for identifiers like table and column names. If a
query needs to be written with identifiers being a variable...

THIS "query" SHOULD NOT TAKE INPUT FROM USERS. DOING SO WILL EXPOSE THE
DB TO SQL INJECTION ATTACKS. DONT DROP THE TABLES >:)
'''
def open_dbshell():
    '''
    Opens a connection to the 'basecamp' sqllite DB and returns
    the 'cursor', and the connection.

    *NOTE: .close() the connection obj when complete.
    '''
    RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
    db_path = RPATH + "\\core\\basecamp.db"
    # Connecting to sqlite DB
    db_con = sqlite3.connect(db_path)
    db_cur = db_con.cursor()
    return db_cur, db_con

# ["bcamp_config"] Table Queries
def gen_bcamp_config():
    '''
    creates the inital values to populate the "bcamp_config" table.

    NOTE* Default paths, and UI templates defined here!
    '''
    # First, define values to be stored.
    global BCAMP_VERSION
    global BCAMP_PRODNAS
    version = BCAMP_VERSION
    root_path = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
    remote_root = BCAMP_PRODNAS
    download_root = root_path + r'\downloads'
    time_zone = str(time.tzname[0] + ":" + time.tzname[1])
    time_format = r"%m/%d/%y %H:%M"
    dev_mode = "False"
    notepad_path = r'C:\Program Files (x86)\Notepad++\notepad++.exe'
    ui_start_res = "1600x900"
    ui_render_top_menu = "True"
    ui_caseviewer_location = "left"
    ui_render_caseviewer = "True"
    ui_caseviewer_search_location = "top"
    ui_render_caseviewer_search = "True"
    ui_render_favtree = "True"
    user_texteditor = "logviewer"

    # Second, Execute the actual SQLite3 query.
    dbshell, dbcon = open_dbshell()

    dbshell.execute('''INSERT INTO bcamp_config (
        version,
        root_path,
        remote_root,
        download_root,
        time_zone,
        time_format,
        dev_mode,
        notepad_path,
        ui_start_res,
        ui_render_top_menu,
        ui_caseviewer_location,
        ui_render_caseviewer,
        ui_caseviewer_search_location,
        ui_render_caseviewer_search,
        ui_render_favtree,
        user_texteditor)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);''',
        (version,
        root_path,
        remote_root,
        download_root,
        time_zone,
        time_format,
        dev_mode,
        notepad_path,
        ui_start_res,
        ui_render_top_menu,
        ui_caseviewer_location,
        ui_render_caseviewer,
        ui_caseviewer_search_location,
        ui_render_caseviewer_search,
        ui_render_favtree,
        user_texteditor))

    dbcon.commit() # Save changes
    dbcon.close() # Close connection

def get_config(column):
    '''
    Returns the value of 'column' from the 1st/ONLY row in the config table.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + """
        FROM bcamp_config ORDER BY """ + column + """ ASC LIMIT 1;""")
    result = dbshell.fetchone()
    dbcon.close()
    return result[0] # Results are tuples, but we expect ONLY 1 value here.

def update_config(column, value):
    '''
    Updates the first/only row of the config table.
    '''
    dbshell, dbcon = open_dbshell()
    
    dbshell.execute("UPDATE bcamp_config SET " + column + " = (?)", (value,))
    dbcon.commit() # save changes
    dbcon.close()
    print("SQLite3: *bcamp_config*:", column, "=", value)


# ["case"] Table Queries
def new_import(new_import_dict, FileOpsQ):
    '''
    Creates a new row in the 'basecamp.cases' table, and generates the filesX
    table if the imported SR has uploads and/or local files. This is only 
    populated with the files from the "root" directories, to optimize import
    time. The nested dirs, and files will be scanned and added shortly in the
    Workspace methods.
    '''
    def finalize_import_data(import_dict):
        '''
        Returns a COMPLETE Dictionary table that is used to create a new row
        in the 'basecamp.cases' table. This method is written in a very 
        "expanded" way so it can scale if these vars need to be adjusted
        before import.
        '''
        def set_favorite():
            '''
            Based on the checkbox value of "Favorite" in the Import UI window.

            Sets the Casedata 'favorite' value to True or False.
            '''
            return import_dict['pinned']

        def set_tags():
            '''
            Using the tags defined in the "import" window, these strings are
            seperated by ',' and then stored as a list under...
            
            {<'SR_Number'>: {'tags': [<'here'>, <'and_here'>],}}
            '''
            tag_rstring = import_dict['tags_list']
            if tag_rstring == None:
                print("CaseData: No 'tags' Defined on import...")
            else:
                return tag_rstring

        def set_account():
            '''
            Using the 'account' defined in the "import" window, this string
            is stored under...
            
            {<'SR_Number'>: {'account': <'here'>,}}
            '''
            return import_dict['account']

        def set_time():
            '''
            Utilizing the 'datetime' library, the machine local time is captured, 
            converted to a readable format (Day, Month, 2-digit Year - TI:ME) and
            stored under...

            {<'SR_Number'>: {'last_ran_time': <'here'>,}}
            '''
            time = str(datetime.datetime.now())
            return time

        def set_paths():
            '''
            Returns the 'remote_path', and 'local_path'** of an SR number as a
            tuple (remote, local)
            '''
            # Getting values from config table in DB
            sr_num = import_dict['sr_number']
            remote_root = get_config('remote_root')
            local_root = get_config('download_root')
            # Generating SR's remote/local paths from cofing roots.
            remote_path = os.path.abspath((remote_root + "\\" + sr_num))
            local_path = os.path.abspath((local_root + "\\" + sr_num))
            # FUTURE - Custom Paths defined here.
            return remote_path, local_path

        def set_files_snapshot():
            '''
            Returns a dictionary that contains local, and remote file stat entries
            such as 'path' or 'creation_time'

            [Schema]
            'path': path,
            'type': _type,
            'size': file_stats.st_size,
            'creation_time': file_stats.st_ctime,
            'modified_time': file_stats.st_mtime,
            'date_range': None, # Set in "finalize" in UI    
            'location': None,   # Set in "finalize" in UI
            'favorite': False,  # Set in "finalize" in UI
            'notes': None,      # Set in "finalize" in UI
            '''
            remote_path, local_path = set_paths()
            # Getting Remote CaseData
            if os.access(remote_path, os.R_OK): #If file is read-able
                remote_file_table = get_snapshot(remote_path)
            else:
                remote_file_table = None
                
            
            # Getting Local CaseData
            if os.access(local_path, os.R_OK): #If file is read-able
                local_file_table = get_snapshot(local_path)
            else:
                local_file_table = None
        
            # Getting 'customs' CaseData
            customs_list = import_dict['customs_list']
            customs_dict = None
            if customs_list != None:
                for path in customs_list:
                    try:
                        customs_dict = get_snapshot(path)
                    except TypeError:
                        customs_dict = None
                    
            #Building 'files' Dict entry
            files_dict = {
                'remote': remote_file_table,
                'local': local_file_table,
                'customs': customs_dict
            }
            return files_dict

        def set_workspace():
            '''
            Returns the default workspace, if not set
            manually during import.
            '''
            return import_dict['workspace']

        def set_product():
            '''
            Returns the abbreviated product name (MWG, ePO, etc.) which is
            determined by the contents of the root Remote path, if not set
            manually during import.
            '''
            return import_dict['product']

        def set_bug():
            '''
            Unless specified, new imports have a default value of 'None'.

            A "TSNS" value can be set manually during import. If defined, we can 
            query JIRA later (when we update the 'files' dict for example) to 
            populate the remaining missing bug details
            '''
            return import_dict['bug_id']

        def set_notes():
            '''
            TO-DO DESCRIPTION
            '''
            return import_dict['notes']

        # 'new_import' RUN
        remote_path, local_path = set_paths()

        case_data = {
            "sr_number": import_dict['sr_number'],
            "notes": set_notes(),
            "bug_id": set_bug(),
            "pinned": set_favorite(),
            "account": set_account(),
            "product": set_product(),
            "workspace": set_workspace(),
            "remote_path": remote_path,
            "local_path": local_path,
            "last_ran_time": set_time(),
            "import_time": set_time(),
            # These vars will goto their own independent tables.
            "tags": set_tags(), #[List] of tags
            "files": set_files_snapshot() #{dict} of 'remote','local' file{}
            }
        
        return case_data

    # Complete case record from UI's partial 'new_import_dict'
    case = finalize_import_data(new_import_dict)
    # Open sqlite3 cursor
    dbshell, dbcon = open_dbshell()
    # Add 'case' values to 'cases' table in 'basecamp.db'
    dbshell.execute("""INSERT INTO cases (
        sr_number, 
        pinned, 
        product, 
        account, 
        bug_id,
        workspace, 
        notes,
        remote_path,
        local_path,
        import_time,
        last_ran_time)
        VALUES (?,?,?,?,?,?,?,?,?,?,?);""",
        (case['sr_number'], 
        case['pinned'],
        case['product'],
        case['account'],
        case['bug_id'],
        case['workspace'],
        case['notes'],
        case['remote_path'],
        case['local_path'],
        case['import_time'],
        case['last_ran_time']))

    # Generate New imports FilesX Table.
    table_id, files_table_query = create_files_table(case['sr_number'])
    dbshell.execute(files_table_query)
    # Update case record with files_table string.
    dbshell.execute("UPDATE cases SET files_table = (?) WHERE sr_number = (?)",
        (table_id, case['sr_number']))
 
    # Then populate it with results from set_files_snapshot here.
    # Remote files...
    if case['files']['remote'] != None:
        for file in case['files']['remote']:
            dbshell.execute("INSERT INTO " +  table_id + """(
                    name,
                    location,
                    path,
                    type,
                    size,
                    creation_time,
                    modified_time,
                    date_range,
                    favorite,
                    notes,
                    depth_index)
                VALUES (?,?,?,?,?,?,?,?,?,?,?);""",
                (file,
                "remote",
                case['files']['remote'][file]['path'],
                case['files']['remote'][file]['type'],
                case['files']['remote'][file]['size'],
                case['files']['remote'][file]['creation_time'],
                case['files']['remote'][file]['modified_time'],
                case['files']['remote'][file]['date_range'],
                case['files']['remote'][file]['favorite'],
                case['files']['remote'][file]['notes'],
                case['files']['remote'][file]['depth_index']))

    # And Local files...
    if case['files']['local'] != None:
        for file in case['files']['local']:
            dbshell.execute("INSERT INTO " +  table_id + """(
                    name,
                    location,
                    path,
                    type,
                    size,
                    creation_time,
                    modified_time,
                    date_range,
                    favorite,
                    notes,
                    depth_index)
                VALUES (?,?,?,?,?,?,?,?,?,?,?);""",
                (file,
                "remote",
                case['files']['local'][file]['path'],
                case['files']['local'][file]['type'],
                case['files']['local'][file]['size'],
                case['files']['local'][file]['creation_time'],
                case['files']['local'][file]['modified_time'],
                case['files']['local'][file]['date_range'],
                case['files']['local'][file]['favorite'],
                case['files']['local'][file]['notes'],
                case['files']['local'][file]['depth_index']))
    # If tags were added, append them to "tags" table
    if case['tags'] != None:
        for tag in case['tags']:
            # insert into tags table w/ sr appended (case['sr_number'])
            dbshell.execute("""INSERT INTO tags (tag, sr_number)
                VALUES (?, ?);""", (tag, case['sr_number']))

    # Finally, close connection
    dbcon.commit()
    dbcon.close()

    # Last, check if user defined download during import, and take action.
    if new_import_dict['download_flag'] == 0:
        pass # DO nothing.
    elif new_import_dict['download_flag'] == 1:
        # Send paths stored in DB to the FileOpsQueue.
        #print("$.API>", query_all_files_column(case['sr_number'], 'path'))
        for path in query_all_files_column(case['sr_number'], 'path'):
            FileOpsQ.add_download(case['sr_number'], path)

def drop_sr(key_val):
    '''
    Drops all related tables and rows for 'key_val'
    '''
    files_table = query_sr(key_val, 'files_table')
    dbshell, dbcon = open_dbshell()
    # Delete filesX table
    if files_table != None:
        dbshell.execute('DROP TABLE ' + files_table + ';')
    # Delete row in cases.
    dbshell.execute('DELETE FROM cases WHERE sr_number = (?)', (key_val,))
    # Remove tags
    dbshell.execute('DELETE FROM tags WHERE sr_number = (?)', (key_val,))
    dbcon.commit() # save changes
    dbcon.close() # close connection to DB.

def query_sr(key_val, column):
    '''
    Returns the value of 'column' from the 'key_val' row in the cases table.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + " FROM cases WHERE sr_number = (?);", 
        (key_val,))
    result = dbshell.fetchone()
    dbcon.close()
    return result[0] # Results are tuples, but we expect ONLY 1 value here.

def query_all_sr(key_val):
    '''
    Returns the value of all columns from 'key_val' row in the cases table.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT * FROM cases WHERE sr_number = (?);", 
        (key_val,))
    result = dbshell.fetchall()
    dbcon.close()
    return result[0] # Results is a tuple in order of SQL column index

def query_cases(column):
    '''
    Returns ALL values in 'column' in the cases table.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + " FROM cases;")
    result = dbshell.fetchall()
    dbcon.close()

    return result # Results are tuples.

def query_cases_distinct(column):
    '''
    Returns unique values in 'column' in the cases table. Duplicates are
    removed from the result.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT DISTINCT " + column + " FROM cases;")
    result = dbshell.fetchall()
    dbcon.close()
    return_list = []
    for value in result:
        if value[0] != None: # Omit NONE values from list.
            return_list.append(value[0])
    return return_list

def query_case_exist(key_val):
    '''
    Returns a bool if 'key_val' exist in the cases table.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("""SELECT EXISTS(
        SELECT 1 FROM cases WHERE sr_number=(?));""", 
        (key_val,))
    result = dbshell.fetchone()
    dbcon.close()
    # Formatting result to True/False Bool.
    if result[0] == 1:
        return True
    else:
        return False

def update_sr(key_val, column, value):
    '''
    Updates a single column value for a key_value in the cases table.
    '''
    dbshell, dbcon = open_dbshell()
    # Update Cases table
    dbshell.execute("UPDATE cases SET "
        + column + """ = (?)
        WHERE sr_number = (?);""",
        (value, key_val))

    dbcon.commit() # Save changes
    dbcon.close() # Close connection
    print("SQLite3: *cases*:", key_val, "->", column, "updated.")

def update_case_record(key_val, new_values):
    '''
    Updates the cases table for key_val when a case record is modified, 
    as well as the tags table for key_val.
    '''
    dbshell, dbcon = open_dbshell()
    # Update Cases table
    dbshell.execute("""UPDATE cases SET
        account = (?),
        product = (?),
        bug_id = (?),
        pinned = (?)
        WHERE sr_number = (?);""",
        (new_values['account_string'],
        new_values['product_string'],
        new_values['bug_string'],
        new_values['important_bool'],
        key_val))

    # Update Tags Table
    # First, drop all exisiting tags for kay_val.
    dbshell.execute("DELETE from tags WHERE sr_number = (?)",
        (key_val,))
    
    # Then update record with new values
    if new_values['tags_list'] != None:
        for tag in new_values['tags_list']:
            dbshell.execute("""INSERT INTO tags(
                tag,
                sr_number) 
                VALUES (?,?);""",
                (tag, key_val))

    dbcon.commit() # Save changes
    dbcon.close() # Close connection
    print("SQLite3: *bcamp_tags*: updated for", key_val)

def parse_filter_search(raw_query, cur_filterset):
    '''
    Seperates words by spaces unless they are encapsulated with ('),
    and returns the results as a list.
    '''
    # Will be populated when the raw_query is parsed.
    query_list = [] 
    # Used for multiple strings seperated from the strip method to compile the
    # full string back together for a clean query when the "expected" format
    # is not used.
    temp_str = ""
    stripped_query = raw_query.strip() # Remove leading whitespace

    # Seperate each string into a list.
    q_items = stripped_query.split(" ") 

    # And then iterate,format and append results to query_list
    long_str_flag = False # sets if item -> temp_str [OR] -> query_list
    for item in q_items:
        if long_str_flag == False:
            # Checking if this is a single query, or a long string 
            # encapsulated by "'" that must be compiled
            if "'" == item[0]:
                # Start of new long string, clear previous compilation.
                temp_str = "" 
                temp_str = item.replace("'", "") # remove leading "'"
                # Setting long_str mode to redirect results to the temp str 
                # until we see an exit "'" to close the string.
                long_str_flag = True
            else: 
                # Simply add as a 'custom' item in query_list.
                formatted_query = item
                query_list.append(formatted_query)

        elif long_str_flag == True:
            # Checking for an exit character
            if "'" == item[-1]:
                temp_str = temp_str + " " + item.replace("'", "")
                # Setting long_str mode to redirect results to the temp str 
                # until we see an exit "'" to close the string.
                formatted_query = temp_str
                query_list.append(formatted_query)
                long_str_flag = False #exit long str mode on next iter in for.
            else:
                # item needs to be added to temp_str.
                temp_str = temp_str + " " +  item
    
    cur_filterset['custom'] = cur_filterset['custom'] + query_list

    return cur_filterset

## [ Search Engine found in CaseViewer ]
def search_cases(f_set):
    '''
    Parses the f_set provided from the CaseViewer.cur_filterset, searches
    through the DB for the items defined, and returns a CaseViewer_index list
    of the cases that should be shown that match

    For specs. on the search engine behind User text into the Search entry,
    see the 'custom_search' sub-method. 
    '''
    def account_search(target):
        dbshell, dbcon = open_dbshell()
        dbshell.execute("SELECT sr_number FROM cases WHERE account = (?);",
            (target,))
        raw_result = dbshell.fetchall()
        dbcon.close()
        # format results.
        f_res = []
        for item in raw_result:
            f_res.append(item[0])
        return f_res

    def product_search(target):
        dbshell, dbcon = open_dbshell()
        dbshell.execute("SELECT sr_number FROM cases WHERE product = (?);",
            (target,))
        raw_result = dbshell.fetchall()
        dbcon.close()
        # format results.
        f_res = []
        for item in raw_result:
            f_res.append(item[0])
        return f_res
        
    def tag_search(target):
        dbshell, dbcon = open_dbshell()
        dbshell.execute("SELECT sr_number FROM tags WHERE tag = (?);",
            (target,))
        raw_result = dbshell.fetchall()
        dbcon.close()
        # format results.
        f_res = []
        for item in raw_result:
            f_res.append(item[0])
        return f_res

    def custom_search(target):
        '''
        Search sub-method utilized for user-defined strings. This combines the
        logic of the account, product, and tag search methods with changes the
        actual queries used and some extra parsers methods. The "c_x_search"
        variants use the SQLite3 'LIKE' exception, to return items that are 
        partial string matches as well. 
        '''
        # [ SPECIAL SEARCH METHODS ONLY FOR CUSTOM STRINGS ]
        ### SR Search for user SR submissions to return the submitted item.
        def c_account_search(target):
            dbshell, dbcon = open_dbshell()
            dbshell.execute("SELECT sr_number FROM cases WHERE account LIKE ?;",
                ('%'+target+'%',))
            raw_result = dbshell.fetchall()
            dbcon.close()
            # format results.
            f_res = []
            for item in raw_result:
                f_res.append(item[0])
            return f_res

        def c_product_search(target):
            dbshell, dbcon = open_dbshell()
            dbshell.execute("SELECT sr_number FROM cases WHERE product LIKE ?;",
                ('%'+target+'%',))
            raw_result = dbshell.fetchall()
            dbcon.close()
            # format results.
            f_res = []
            for item in raw_result:
                f_res.append(item[0])
            return f_res
            
        def c_tag_search(target):
            dbshell, dbcon = open_dbshell()
            dbshell.execute("SELECT sr_number FROM tags WHERE tag LIKE ?;",
                ('%'+target+'%',))
            raw_result = dbshell.fetchall()
            dbcon.close()
            # format results.
            f_res = []
            for item in raw_result:
                f_res.append(item[0])
            return f_res

        def sr_search(target):
            dbshell, dbcon = open_dbshell()
            dbshell.execute("SELECT sr_number FROM cases WHERE sr_number = (?);",
                (target,))
            raw_result = dbshell.fetchall()
            dbcon.close()
            # format results.
            f_res = []
            for item in raw_result:
                f_res.append(item[0])
            return f_res
        # [ /SPECIAL SEARCH METHODS ONLY FOR CUSTOM STRINGS ]        

        # DRIVER CODE FOR 'custom_search'
        # Send sample to each search module, and collect the results.
        print("$>", target)
        account_return = c_account_search(target)
        product_return = c_product_search(target)
        tag_return = c_tag_search(target)
        sr_return = sr_search(target)

        # Then add the list together to get a aggregate list of SR's.
        aggregate_list = (
            account_return 
            + product_return 
            + tag_return 
            + sr_return
        )

        print("$aggr_lst", aggregate_list)
        # Finally, return result to be filtered through...
        return aggregate_list
    
    def filter_results(a_lst, p_lst, t_lst, c_lst):
        '''
        Returns a list of SR's that exist in ALL search results.

        a_lst = Account Result List.
        p_list = Product Result List.
        t_lst = Tag Result List.
        c_lst = Custom Result List.
        '''
        def noneIsInfinite(value):
            if value is None:
                return float("inf")
            else:
                return value

        # First, get lengths of all result_list.
        a_len = len(a_lst)
        p_len = len(p_lst)
        t_len = len(t_lst)
        c_len = len(c_lst)

        # Then check if the lengths are greater <= 1. Any list length that is
        # 0 should be converted to None vals.``
        if a_len == 0:
            a_len = None
        if p_len == 0:
            p_len = None
        if t_len == 0:
            t_len = None
        if c_len == 0:
            c_len = None        
        length_set = [a_len, p_len, t_len, c_len]  

        # Determine which lst is the Smallest. 
        min_val = min(length_set, key=noneIsInfinite)
        min_index = length_set.index(min_val)
        if min_index == 0:
            smallest_set = a_lst
        if min_index == 1:
            smallest_set = p_lst
        if min_index == 2:
            smallest_set = t_lst
        if min_index == 3:
            smallest_set = c_lst

        # Iterate through 'smallest_set' and compare items to items in
        # sister list. 
        return_list = []
        for item in smallest_set:
            # Account Test
            if a_len != None:
                if item in a_lst:
                    a_litmus = True
                else:
                    a_litmus = False
            else:
                # Return true, set excluded.
                a_litmus = True

            # product Test
            if p_len != None:
                if item in p_lst:
                    p_litmus = True
                else:
                    p_litmus = False
            else:
                # Return true, set excluded.
                p_litmus = True

            # Tag Test
            if t_len != None:
                if item in t_lst:
                    t_litmus = True
                else:
                    t_litmus = False
            else:
                # Return true, set excluded.
                t_litmus = True

            #  Custom Test
            if c_len != None:
                if item in c_lst:
                    c_litmus = True
                else:
                    c_litmus = False
            else:
                # Return true, set excluded.
                c_litmus = True
            
            # Test if a,p,t,c litmus is true. 
            if a_litmus and p_litmus and t_litmus and c_litmus:
                print("ADDING...", item, " to RESULTS.")
                return_list.append(item)
            else:
                # Item not in all list, to not add to results.
                pass
            
        return return_list

    account_res = []
    product_res = []
    tag_res = []
    temp_custom_sets = []
    custom_res = []

    # Iterate through each key in the 'f_set' and see val to sub-methods to
    # crawl through the DB.

    for item in f_set['account']:
        sr_set = account_search(item)
        # Formatting sr_set list into result list
        for item in sr_set:
            account_res.append(item)

    for item in f_set['product']:
        sr_set = product_search(item)
        # Formatting sr_set list into result list
        for item in sr_set:
            product_res.append(item)

    for item in f_set['tag']:
        sr_set = tag_search(item)
        # Formatting sr_set list into result list
        for item in sr_set:
            tag_res.append(item)

    for item in f_set['custom']:
        sr_set = custom_search(item)
        # Save results from all custom string matches to be filtered.
        temp_custom_sets.append(sr_set)

    if len(temp_custom_sets) > 1:
        # Pre-filter custom results if user gives multiple strings.
        # Get largest lst in temp_custom_sets, returns as (index, lst)
        source_tup = max(enumerate(temp_custom_sets), key = lambda tup: len(tup[1]))
        # Remove largest item from temp_sets.
        temp_custom_sets.pop(source_tup[0])
        # Only return matches that exist in both source_tup and iter lst.
        for lst in temp_custom_sets:
            for item in lst:
                print("\n*****\n$item....", item)
                print("$lst....", lst)
                print("$...SOURCE", source_tup[1], "\n*****")
                if item in source_tup[1]: # item in largest list.
                    custom_res.append(item) 
    elif len(temp_custom_sets) == 1: # Only single items in temp_set.
        ## Formatting sr_set list into result list
        for item in sr_set:
            custom_res.append(item)

    #print("** SEARCH RESULTS **")
    #print("account>", account_res)
    #print("product>", product_res)
    #print("tag>", tag_res)
    #print("custom>", custom_res)

    # Checking results from ALL search list above, and appending SR's that are
    # present in all list. 
    
    # First, determine what result set is the SMALLEST, we will iterate through
    # this list and compare it to the others for the fastest comparison.

    return filter_results(account_res, product_res, tag_res, custom_res)

# ["tags"] Table Queries
def insert_tags(key_val, tag):
    '''
    Adds new tags to the tags table for key_val. tag/sr_number must be unique.
    '''
    dbshell, dbcon = open_dbshell()
    # Delete all previous tags
    dbshell.execute("DELETE FROM tags WHERE sr_number = (?);", (key_val))
    # Add new tags, which contains the old tags by default.
    dbshell.execute("""INSERT INTO tags(
                tag,
                sr_number) 
                VALUES (?,?);""",
                (tag, key_val))
    dbcon.commit()
    dbcon.close()

def query_tags(key_val):
    '''
    Returns all tags for key_val
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT tag FROM tags WHERE sr_number = (?);", 
        (key_val,))
    result = dbshell.fetchall()
    dbcon.close()
    return_list = []
    for value in result:
        return_list.append(value[0])
    return return_list


'''
[Filebrowser Logic]

The below methods crawl through the local and remote dirs, extracting file
metadata (File Size, Creation time, Paths). The resulting data has two 
purposes.

1 - Being rendered within the UI (Basecamp.Tk_Filebrowser)
2 - Stored in the SQLite3 DB for future rendering, and references.

The "FileOpsQueue" class is a *Queue* daemon that manages *Threading.threads*
utilized by the Basecamp.Tk_Filebrowser class for downloads, uploads, and
Automations. This queue (FIFO) is global, meaning all open cases use the same
queue. This is to optimize performance by reducing disk chaos.
'''

class FileOpsQueue:
    '''
    Master Queue for Unpack/Download operations for ALL filebrowsers.
    '''
    def __init__(self):
        setup_log("fileops.log")
        self.log_fileops = logging.getLogger('fileops.log')
        self.q = queue.Queue()

        # Vars used for Progressbar updates. Callbacks are registered in UI.
        self.queue_size = 0
        self.queue_callback = callbackVar()
        self.progress_obj = callbackVar()

        threading.Thread(target=self.worker_thread, name="FileOps-Daemon", daemon=True).start()

    def worker_thread(self):
        '''
        Daemon Thread for FileOpsQueue
        '''
        self.log_fileops.info("STARTING FILEOPSQUEUE")
        while True: # Infin. Loop
            item = self.q.get()
            item.start() # Starting thread_obj
            # Enter nested while until 'item' thread is complete.
            while item.is_alive():
                time.sleep(1)
            # Exit and go to next item in Queue if any.
            self.q.task_done()

            # Reduce queue_size by 1 if NOT refresh thread.
            root_item_name = ((item.name).rsplit(":")[2]).strip()
            if root_item_name != "local_refresh" or root_item_name != "remote_refresh":
                if self.queue_size > 0:
                    self.queue_size -= 1
                else:
                    self.queue_size = 0
        
            # self.Gui.fb_queue_string.value = str(self.queue_size) + ": Queue"
            self.progress_obj.value = {'mode': None} # Clearing Complete.
            self.queue_callback.value = self.queue_size

    # Download Methods
    def start_download(self, key_val, target_file):
        '''
        Logic for Download operations for Files.
        '''
        self.log_fileops.info("Launching 'FileOpsQueue.start_download'")

        # Defining local vars for 'target_file'
        file_name = os.path.basename(target_file)
        size_mb = os.path.getsize(target_file)
        local_dir = (get_config('download_root')
            + "\\" + key_val)
        full_local_path = local_dir + "\\" + file_name

        # Checking if file already downloaded...
        if os.access(full_local_path, os.R_OK):
            self.log_fileops.info(file_name + " already Downloaded. Exiting...")
            return

        # Testing Local folder for existence
        if os.access(local_dir, os.R_OK):
            self.log_fileops.info("Local Dir for " + str(key_val) + " exist!")
        else:
            self.log_fileops.info("Local Dir for " + str(key_val) + " missing. Creating it...")
            os.mkdir(local_dir)
            self.log_fileops.info("Local Dir for " + str(key_val) + " created successfully!")


        self.log_fileops.info("\n***\nSrc: " + target_file + "\nDst: " + full_local_path +"\n***")
        self.log_fileops.info("Downloading [" + target_file + "] @ " + str(size_mb) + " bytes")
        self.log_fileops.info("Local Path> " + full_local_path)
        self.log_fileops.info("Remote Path> " + target_file)

        # Downloading File HERE.
        if os.path.isfile(target_file):
            self.log_fileops.info("Type is FILE")
            # *** TRACKING PROGRESS OF COPY ***
            def update_progress_val(bytescopied):
                ''' 
                Creates download dictionary object
                '''
                update_dict = {
                    'mode': 'download',
                    'curbytes': bytescopied,
                    'totalbytes': size_mb,
                    'srcpath': os.path.abspath(target_file),
                    'sr': key_val
                }
                # Update the progess object with the new value.
                self.progress_obj.value = update_dict 
        
            # Open files in binary mode.
            source_path = os.path.abspath(target_file)
            dest_path = os.path.abspath(full_local_path)
            fsrc = open(source_path, mode='rb') # read/binary mode
            fdst = open(dest_path, mode='wb')   # write/binary mode

            # *** COPYING HERE ***
            self.copyfileobj(fsrc, fdst, update_progress_val)

        # TODO - HOW DO YOU WANT TO TRACK DIR DOWNLOAD PROG?
        elif os.path.isdir(target_file):
            self.log_fileops.info("Type is DIR")
            # *** OR HERE IF DIR ***
            shutil.copytree(target_file, full_local_path)
        
        # Clean-up/Last Words.
        self.log_fileops.info(file_name + " Downloaded Successfully!")
        self.log_fileops.info("Exiting 'FileOpsQueue.start_download'")
    
    def add_download(self, key_val, target_path):
        '''
        Converts 'input' to a thread object, and then puts it into the 
        'worker_thread' Daemon via self.q.put(X)
        '''
        #Getting base file name of target_file
        file_name = os.path.basename(target_path)
        #Converting to thread obj with args.
        thread_obj = threading.Thread(target=self.start_download, 
            args=(key_val, target_path),
            name=("download::" + key_val + "::" + file_name))
        self.q.put(thread_obj)
        #increment queue_size 
        self.queue_size += 1
        self.queue_callback.value = self.queue_size
    
    # Upload Methods
    def start_upload(self, key_val, target_file):
        '''
        Logic for Upload operations for Files.
        '''
        self.log_fileops.info("Launching 'FileOpsQueue.start_upload'")

        # Defining Remote path of target_file.
        file_name = os.path.basename(target_file)
        remote_dir = (get_config("remote_root")
            + "\\" + key_val)
        full_remote_path = remote_dir + "\\" + file_name

        # Checking if file already uploaded...
        if os.access(full_remote_path, os.R_OK):
            self.log_fileops.info(file_name + " already Uploaded. Exiting...")
            return

        # Testing Remote folder for existence
        if os.access(remote_dir, os.R_OK):
            self.log_fileops.info("Remote Dir for " + str(key_val) + " exist!")
        else:
            self.log_fileops.info("Remote Dir for " + str(key_val) + " missing. Creating it...")
            os.mkdir(remote_dir)
            self.log_fileops.info("Remote Dir for " + str(key_val) + " created successfully!")


        self.log_fileops.info("\n***\nSrc: " + target_file + "\nDst: " + full_remote_path +"\n***")
        size_mb = os.path.getsize(target_file)
        self.log_fileops.info("Uploading [" + target_file + "] @ " + str(size_mb) + " bytes")
        self.log_fileops.info("Local Path> " + full_remote_path)
        self.log_fileops.info("Remote Path> " + target_file)

        # shutil.copy2 for files, shutil.copytree for Dirs.
        # Upload use shutil.copy2 - preserve metadata.
        if os.path.isfile(target_file):
            self.log_fileops.info("Type is FILE")
            # NOTE LEGACY/shutil.copy2(target_file, full_remote_path)

            # *** TRACKING PROGRESS OF COPY ***
            def update_progress_val(bytescopied):
                ''' Creates upload dictionary object
                '''
                update_dict = {
                    'mode': 'upload',
                    'curbytes': bytescopied,
                    'totalbytes': size_mb,
                    'srcpath': os.path.abspath(target_file),
                    'sr': key_val
                }
                # Updating with Gui w/ update dictionary
                self.progress_obj.value = update_dict 
        
            # Open files in binary mode.
            source_path = os.path.abspath(target_file)
            dest_path = os.path.abspath(full_remote_path)
            fsrc = open(source_path, mode='rb') # read/binary mode
            fdst = open(dest_path, mode='wb')   # write/binary mode

            # *** COPYING HERE ***
            self.copyfileobj(fsrc, fdst, update_progress_val)

        # TODO - HOW DO YOU WANT TO TRACK DIR Upload PROG?
        elif os.path.isdir(target_file):
            self.log_fileops.info("Type is DIR")
            # *** OR HERE IF DIR ***
            shutil.copytree(target_file, full_remote_path)
        
        # Clean-up/Last Words.
        self.log_fileops.info(file_name + " Uploaded Successfully!")
        self.log_fileops.info("Exiting 'FileOpsQueue.start_upload'")

    def add_upload(self, key_val, target_path):
        '''
        Converts 'input' to a thread object, and then puts it into the 
        'worker_thread' Daemon via self.q.put(X)
        '''
        #Getting base file name of target_file
        file_name = os.path.basename(target_path)
        #Converting to thread obj with args.
        thread_obj = threading.Thread(target=self.start_upload, 
            args=(key_val, target_path),
            name=("download::" + key_val + "::" + file_name))
        self.q.put(thread_obj)
        #increment queue_size 
        self.queue_size += 1
        self.queue_callback.value = self.queue_size
        #self.Gui.fb_queue_string.value = str(self.queue_size) + " : Queue"

    # Automation methods
    def add_automation(self, key_val, iid, target_automation):
        '''
        Converts 'input' to a thread object, and then puts it into the 
        'worker_thread' Daemon via self.q.put(X)
        '''

        def unpack_automation(key_val, iid, target_automation):
            '''
            If target_automation type is "unpack", this method is called.

            This checks the existence of previously unpacked files based on 
            the IID (Explicit path) provided from the file browser - and
            determine if the automation needs to be ran, or if the work is
            already complete.
            '''
            # Defining Vars based on key_val.
            file_name = os.path.basename(iid)
            remote_path = query_sr(key_val, 'remote_path')
            local_path = query_sr(key_val, 'local_path')
            full_remote_path = remote_path + "\\" + os.path.splitext(file_name)[0]
            full_local_path = local_path + "\\" + file_name

            # First, test Remote Result folder for existence
            if os.access(full_remote_path, os.R_OK):
                self.log_fileops.info(key_val + "/" + file_name + " has already been unpacked! Exiting...")
                # TODO HOW TO HANDLE ALREADY UNPACKED - TAKE USER TO FILE?")
                return
            
            # Second, test Local folder for existence
            if os.access(local_path, os.R_OK):
                self.log_fileops.info("Local Dir for " + str(key_val) + " exist!")
            else:
                self.log_fileops.info("Local Dir for " + str(key_val) + " missing. Creating it...")
                os.mkdir(local_path)
                self.log_fileops.info("Local Dir for " + str(key_val) + " created successfully!")

            # Third, Test for file existence in local folder
            self.log_fileops.info("Checking if file already downloaded...")
            unpacked_path = os.path.splitext(full_local_path)[0]
            if os.access(unpacked_path, os.R_OK):
                self.log_fileops.info(file_name + " has already been UNPACKED.")
                self.log_fileops.info("Exiting 'start_automation'")
                return
            elif os.access(full_local_path, os.R_OK):
                self.log_fileops.info(file_name + " has already been DOWNLOADED.")
            else:
                downloadFirst = query_automation(target_automation, 'downloadFirst')
                if downloadFirst == '1':
                    print("Starting download. TARGET:", full_remote_path)
                    self.add_download(key_val, iid)
    
            # Finally, start the automation
                thread_obj = threading.Thread(target=self.start_automation, 
                    args=(key_val, iid, target_automation),
                    name=(key_val 
                        + "::" 
                        + target_automation
                        + "::" 
                        + os.path.basename(iid)))
                self.q.put(thread_obj)
                # Increment Queue Size
                self.queue_size += 1
                self.queue_callback.value = self.queue_size         


        def custom_automation(key_val, iid, target_automation):
            '''
            If the automation type is "custom", this method is called.

            Different from "unpack" types, these automations are not placed
            into the FileOps queue, but are called in individual child threads
            to complete the defined task. Use case for this type would be
            automations that do not need to download or extract the contents 
            of a target file - such as sending a file to a rep-lab.
            '''
            print("Would launch custom_auto w/ : ",  key_val, iid, target_automation)

        # Determine Automation 'type' by querying DB
        auto_type = query_automation(target_automation, 'type')
      
        # If type is "unpack" - send to unpack method.
        if auto_type == "unpack":
            unpack_automation(key_val, iid, target_automation)
        elif auto_type == "custom":
            custom_automation(key_val, iid, target_automation)

    def start_automation(self, key_val, iid, target_automation):
        '''
        Threaded process that is called when a user selects "Unpack"
        for a supported file type. 
        '''
        self.log_fileops.info("Launching 'FileOpsQueue.start_automation'")
        
        # Update Progressbar String
        update_dict = {
            'mode': 'automation',
            'srcpath': os.path.abspath(iid),
            'sr': key_val
        }
        # Updating Gui w/ update dictionary
        self.progress_obj.value = update_dict

        # Defining Vars
        file_name = os.path.basename(iid)
        local_path = query_sr(key_val, 'local_path')
        file_local_path = local_path + "\\" + file_name
        automation_path = query_automation(target_automation, 'py_path')
        binary_exe_list = query_automation(target_automation, 'exe_paths')
        
        # Converting 'binary_exe_list' to Python list obj
        # That will be passed as a var from the 
        automation_exe_list = pickle.loads(binary_exe_list)
        
        # Importing the target automation Module
        self.log_fileops.info("Importing " + target_automation)
        spec = importlib.util.spec_from_file_location(
            (target_automation), automation_path)
        automation_py = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(automation_py)

        # Starting the automation.run() main method.
        self.log_fileops.info("Start your engines " + target_automation + "!")
        print("$.lst", automation_exe_list)
        automation_py.run(iid, file_local_path, automation_exe_list)

    ## ADDING FROM STACK - Get percentage complete based on src/dst size.
    # https://stackoverflow.com/questions/29967487/get-progress-back-from-shutil-file-copy-thread
    def copyfileobj(self, fsrc, fdst, callback, length=0):
        try:
            # check for optimisation opportunity
            if "b" in fsrc.mode and "b" in fdst.mode and fsrc.readinto:
                return self._copyfileobj_readinto(fsrc, fdst, callback, length)
        except AttributeError:
            # one or both file objects do not support a .mode or .readinto attribute
            pass

        if not length:
            length = shutil.COPY_BUFSIZE

        fsrc_read = fsrc.read
        fdst_write = fdst.write

        copied = 0
        while True:
            buf = fsrc_read(length)
            if not buf:
                break
            fdst_write(buf)
            copied += len(buf)
            callback(copied)

    def _copyfileobj_readinto(self, fsrc, fdst, callback, length=0):
        """readinto()/memoryview() based variant of copyfileobj().
        *fsrc* must support readinto() method and both files must be
        open in binary mode.
        """
        # differs from shutil.COPY_BUFSIZE on platforms != Windows
        READINTO_BUFSIZE = 1024 * 1024

        fsrc_readinto = fsrc.readinto
        fdst_write = fdst.write

        if not length:
            try:
                file_size = os.stat(fsrc.fileno()).st_size
            except OSError:
                file_size = READINTO_BUFSIZE
            length = min(file_size, READINTO_BUFSIZE)

        copied = 0
        with memoryview(bytearray(length)) as mv:
            while True:
                n = fsrc_readinto(mv)
                if not n:
                    break
                elif n < length:
                    with mv[:n] as smv:
                        fdst.write(smv)
                else:
                    fdst_write(mv)
                copied += n
                callback(copied)

    def put(self, item):
        self.q.put(item)

# General Methods used by the UI
def generate_file_record(self, key_val):
    '''
    Threaded generator that scans the remote, local paths in order of nested
    dir "depth"*. The resulting dictionary object is then sent to the
    'update_files' method to update the 'files_X' x = key_val in the DB.

    dir depth : The Subdirs of 'FILE1' and 'FILE2' will be inserted into Tree 
    before the Sub/Sub/dirs of 'FILE1' are inserted.
    '''

    def gen_fstats(location, depth_index):
        '''
        Iterating through the inherited 'generate_file_record.dir_list' list
        object, which contains directory paths - whos children files metadata
        will be extracted using the 'os.scandir' library. 

        The 'dir_list' variable begins at either the 'remote' or 'local' root
        path. Any child directories that are found are added to the 
        'temp_dirs' list which will be appended to the 'dir_list' variable, to
        be iterated through in the next round by the parent methods generator,
        which is determined by 'depth_index'.

        Example dir_list = [[root_path], [path1, path2], etc.]
        '''
        # Temp Container for dir_paths @ 'depth_index'
        temp_dirs = []
        # For paths at this *depth_index*
        for path in dir_list[depth_index]:
            with os.scandir(path) as scanner:
                for dirEntry in scanner:
                    # Add any dirs paths to temp_dirs
                    if dirEntry.is_dir():
                        # Save to temp_dirs for next iteration
                        temp_dirs.append(dirEntry.path)
                        # Create record in stream, effort to reduce N*
                        create_fstats_dict(location, dirEntry.path, depth_index)
                    if dirEntry.is_file():
                        create_fstats_dict(location, dirEntry.path, depth_index)

        # Prevent adding empty temp_dir list for infin loop.
        if len(temp_dirs) != 0:
            dir_list.append(temp_dirs)
            yield temp_dirs

    def create_fstats_dict(location, path, depth_index):
        '''
        Used by *gen_fstats* to create a dictionary record for
        Dir paths found.
        '''
        # Get os.stat values for *path*
        file_stats = os.stat(path)
        # Set 'type'
        if stat.S_ISDIR(file_stats.st_mode):
            _type = "dir"
        else:
            _type = os.path.splitext(path)[1]
            # TODO if type is '.1' or '.2', etc, see if its actually .log here...

        # Create record using *file_stats*
        record = {
            os.path.basename(path): {
                    'location': location,
                    'path': path,
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
        # Appending record dict obj. to new_file_record dict.
        new_file_record.update(record)
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


    remote_exist = False
    local_exist = False
    new_file_record = {} # Dictionary object appened, and returned.

    # First, Check if we can access remote root path, and key_val remote
    if os.access(get_config('remote_root'), os.R_OK):
        if not os.access(query_sr(key_val, "remote_path"), os.R_OK):
            print("No files uploaded to Remote Share.")
        else:
            remote_exist = True
            remote_root = query_sr(key_val, "remote_path")
    else:
        print("ERROR - UNABLE TO LOCATE REMOTE ROOT FOLDER : CHECK VPN")

    # Second, check if there are local files for key_val.
    if not os.access(query_sr(key_val, "local_path"), os.R_OK):
        print("No files available in Local Share.")
    else:
        local_exist = True
        local_root = query_sr(key_val, "local_path")

    # Generator Loops to iterate through files in order of Depth.
    # We attempt the remote path first, then the local. "Returned"
    # results from this generator are then passed to the child methods.

    if remote_exist:
        dir_list = [[remote_root]]
        depth_index = -1 # Offset for generator incrementation.
        while True:
            gen_fstats('remote', depth_index)
            depth_index += 1
            # Recursive call here, if EOF, stopIter thrown.
            try:
                next(gen_fstats('remote', depth_index))
            except StopIteration:
                print("Remote dir finished scanning")
    
    # #if local_exist:
    # #    dir_list = [[local_root]]
    # #    depth_index = -1 # Offset for generator incrementation.
    # #    while True:
    # #        fstats_gen('local', depth_index)
    # #        depth_index += 1
    # #        # Recursive call here, if EOF, stopIter thrown.
    # #        try:
    # #            next(fstats_gen('local', depth_index))
    # #        except StopIteration:
    # #            print("Local dir finished scanning")
    
    # At this point, the "new_file_record" dictionary object contains all
    # information needed to update the "files_X" DB table.
    # Updating DB on seperate thread for performance optimization.
    threading.Thread(target=update_files, 
    args=(self.key_value, new_file_record)).start()

def open_customTextEditor(file_path):
    '''
    FUTURE : Execute custom_TextEditor.py file
    '''
    print("$CustomTextEditor ** UNDER CONSTRUCTION ** // Exiting method")
    return

def open_notepad(file_path):
    '''
    Opens the target "file_path" in Notepad++
    '''
    iid = file_path
    # Get path to configured text editor.
    notepad_path = get_config('notepad_path')
    # Launch file with assigned path.
    if os.access(notepad_path, os.X_OK):
        subprocess.Popen([notepad_path, iid])

def open_in_windows(file_path):
    '''
    Attempts to open the target "file_path" using os.startfile() sending the
    path to windows.
    '''
    try:
        os.startfile(file_path)
    except OSError:
        print("*bcamp_api*: WINDOWS ERROR - No default application associated.")

def download_all_files(key_val, FileOpsQ, FileBrowser):
    '''
    Querys the DB for all files in the remote location, and puts a 'download' 
    thread into the FileOpsQ for each one that is not present in the local 
    folder. The FileBrowser is passed so we can refresh the UI after each
    download.
    '''
    # Get all file paths in remote folder saved in DB.
    rfiles = query_all_files_remote(key_val, 'path')
    print("$api.", rfiles)
    # Iter. paths and submit using FOQ
    for fpath in rfiles:
        FileOpsQ.add_download(key_val, fpath)
        # Now add refresh to update UI
        FileBrowser.refresh_file_record(mode='local', enableParser=False)

def upload_all_files(key_val, FileOpsQ, FileBrowser):
    '''
    Querys the DB for all files in the local location, and puts a 'upload' 
    thread into the FileOpsQ for each one that is not present in the remote 
    folder. The FileBrowser is passed so we can refresh the UI after each
    upload.
    '''
    # Get all file paths in remote folder saved in DB.
    lfiles = query_all_files_local(key_val, 'path')
    print("$api.", lfiles)
    # Iter. paths and submit using FOQ
    for fpath in lfiles:
        FileOpsQ.add_upload(key_val, fpath)
        # Now add refresh to update UI
        FileBrowser.refresh_file_record(mode='remote', enableParser=False)

# ["files_X"] Table Queries 
def create_files_table(key_val):
    '''
    Creates a filesX table for 'key_val'. Default Schema defined here.
    '''
    table_name = "files" + str(key_val).replace('-', '')
    query = "CREATE TABLE IF NOT EXISTS " + table_name + """(
                            name TEXT NOT NULL,
                            location TEXT NOT NULL,
                            path TEXT NOT NULL,
                            type TEXT NOT NULL,
                            size TEXT NOT NULL,
                            creation_time TEXT NOT NULL,
                            modified_time TEXT NOT NULL,
                            date_range TEXT,
                            favorite TEXT NOT NULL,
                            notes TEXT,
                            depth_index TEXT NOT NULL,
                            UNIQUE(path, location) ON CONFLICT IGNORE
            ); """
    return table_name, query

def update_files(key_val, updated_record):
    '''
    Converts 'file_vals' dictionary to a row in 'key_vals' filesX table.

    [filesX Schema]
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        path TEXT NOT NULL,
        type TEXT NOT NULL,
        size TEXT NOT NULL,
        creation_time TEXT NOT NULL,
        modified_time TEXT NOT NULL,
        date_range TEXT NOT NULL,
        favorite TEXT NOT NULL,
        notes TEXT NOT NULL
        ? ADD DEPTH VAL?
    '''
    # Get file_table of key_val
    table_id = query_sr(key_val, 'files_table')
    dbshell, dbcon = open_dbshell()
    for file in updated_record:
        dbshell.execute("INSERT INTO " + table_id + """(
            name,
            location, 
            path, 
            type, 
            size, 
            creation_time,
            modified_time, 
            date_range,
            favorite,
            notes,
            depth_index)
            VALUES (?,?,?,?,?,?,?,?,?,?,?);""",
            (file,
            updated_record[file]['location'],
            updated_record[file]['path'],
            updated_record[file]['type'],
            updated_record[file]['size'],
            updated_record[file]['creation_time'],
            updated_record[file]['modified_time'],
            updated_record[file]['date_range'],
            updated_record[file]['favorite'],
            updated_record[file]['notes'],
            updated_record[file]['depth_index'],))

    dbcon.commit() # Save changes
    dbcon.close() # Close connection
    print(key_val, "*files* table updated in DB")

def update_file(key_val, column, file_name, value):
    '''
    Updates a SINGLE value for file in key_val.
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    dbshell, dbcon = open_dbshell()
    dbshell.execute("UPDATE " + table_name + " SET " + column + " = (?) WHERE path = (?)", (value, file_name))
    dbcon.commit() # Save changes
    dbcon.close() # Close connection
    print(key_val, "*files* table updated in DB")

def query_all_files(key_val):
    '''
    Returns ALL rows and values for each file in key_val in order of file
    'depth_index' with 0 = root, and '3' representing files found 3 dirs deep
    in ANY parent file. Tk_Filebrowser handles putting the correct files under
    the right parent tree.
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    # DB contents
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT * FROM " + table_name + " ORDER BY depth_index ASC, type DESC;")
    result = dbshell.fetchall()
    dbcon.close()
    return result # Results are tuples containing all columns per tuple.

def query_all_files_column(key_val, column):
    '''
    Returns a list of the value found in 'column' for a target 'key_val' 
    in the 'filesX' table of the DB.
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + " FROM " + table_name + " ;")
    result = dbshell.fetchall()
    dbcon.close()
    # Correct result formatting into a direct list obj.
    final_result = []
    for item in result:
        final_result.append(item[0])

    return final_result # Results are tuples containing all columns per tuple.

def query_all_files_remote(key_val, column):
    '''
    Returns a list of the value found in 'column' for a target 'key_val' 
    in the 'filesX' table of the DB filtered by remote files ONLY.
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " 
        + column 
        + " FROM " 
        + table_name 
        + " WHERE location = (?) ;",
        ('remote',))
    result = dbshell.fetchall()
    dbcon.close()
    # Correct result formatting into a direct list obj.
    final_result = []
    for item in result:
        final_result.append(item[0])

    return final_result # Results are tuples containing all columns per tuple.

def query_all_files_local(key_val, column):
    '''
    Returns a list of the value found in 'column' for a target 'key_val' 
    in the 'filesX' table of the DB filtered by local files ONLY.
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " 
        + column 
        + " FROM " 
        + table_name 
        + " WHERE location = (?) ;",
        ('local',))
    result = dbshell.fetchall()
    dbcon.close()
    # Correct result formatting into a direct list obj.
    final_result = []
    for item in result:
        final_result.append(item[0])

    return final_result # Results are tuples containing all columns per tuple.

def query_all_files_formatted(key_val):
    '''
    TODO 

    Returns ALL rows and values for each file in key_val in order of file
    'depth_index' with 0 = root, and '3' representing files found 3 dirs deep
    in ANY parent file. Tk_Filebrowser handles putting the correct files under
    the right parent tree.

    The formatted variant returns the results as a python dict object.
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    # DB contents
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT * FROM " + table_name + " ORDER BY depth_index ASC, type DESC;")
    result = dbshell.fetchall()
    dbcon.close()
    return result # Results are tuples containing all columns per tuple.

def query_file(key_val, column, file_name):
    '''
    Returns a SINGLE value for file in key_val.
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + " FROM " + table_name + " WHERE path = (?)", (file_name,))
    result = dbshell.fetchone()
    dbcon.close()
    if result == None:
        return result
    return result[0] # Results are tuples containing all columns per tuple.

def query_dump_notes(key_val, column):
    '''
    Returns a all rows* using a filter.

    dbshell.execute("SELECT " + column + " FROM " + table_name + " WHERE = (?)", sql_filter)
    '''
    # Remove "-" from key_val
    form_key_val = str(key_val).replace("-", "")
    table_name = "files" + form_key_val
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + " FROM " + table_name + " WHERE notes IS NOT NULL")
    result = dbshell.fetchall()
    dbcon.close()
    return result # Results are tuples containing all columns per tuple.

# ["favorite_files"] Table Queries
def get_fav_files():
    '''
    Returns all files and paths with the favorite_files table.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT * FROM bcamp_favfiles;")
    result = dbshell.fetchall()
    dbcon.close()
    return result

def add_fav_file(key_val, file_path):
    '''
    Converts the full file_path into two parts, the filename and root path
    *AFTER* the SR Number. The idea is to only the explicit path found to that
    file for any SR. 

    ex.) 4-XXX/logs/etc/favFile.log becomes logs/etc/favFile.log
    '''
    # Extract File Name from path
    fname = os.path.basename(file_path)
    # Extract root path without SR number/key_val
    dir_path = os.path.dirname(file_path)
    root_path = dir_path.replace(key_val, '', 1) # Only remove key_val once.

    # Add to SQLite3 "favorite_files" table.
    dbshell, dbcon = open_dbshell()
    
    dbshell.execute("""INSERT INTO bcamp_favfiles (file_name, root_path) 
        VALUES (?,?);""", (fname, root_path))

    dbcon.commit() # save changes
    dbcon.close()
    print("SQLite3: *bcamp_favfiles*:", fname, "added to DB.")

def remove_fav_file(file_path):
    '''
    Removes row containing file name, and root path from the "favorite_files"
    table.
    '''
    fname = os.path.basename(file_path)
    dbshell, dbcon = open_dbshell()
    dbshell.execute("DELETE FROM bcamp_favfiles WHERE file_name = (?);", (fname,))
    dbcon.commit() # save changes
    dbcon.close()


'''
[Automations]

This section contains classes and methods needed to import user-defined python
extensions - called "Automations". This allows for bCamp to scale as 
functionality can be expanded, adapting bCamp for any engineers workflow.

As of the Beta, Automations are only called against Files within the
filebrowser. Some examples include "ATD-Unpack" that decrypts "SupportBundle"
log bundles, into a readable file for an engineer to review. A process that
manually takes 5+ mins of file operations and terminal commands.
'''


class Automations:
    '''
    Main class to interact with "Automations" stored in the...
    bcamp_root/extensions/automations directory. 

    This includes compiling user-defined Python code to check for errors, and
    updating the "basecamp.automations" table.
    '''
    def __init__(self):
        self.RPATH = (str(pathlib.Path(__file__).parent.absolute())).rpartition('\\')[0]
        # Configuring logging
        setup_log('automations.log')
        self.log = logging.getLogger('automations.log')

        # Generate DB record of available imports during Init.
        self.gen_automations_db()

    def scan_automations(self):
        '''
        Getting all file 'stats' in /../automations
        that comply with the expected format of
        'name'/ [example.py], [properties.json]
        '''
        results_list = []
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
        # [(name, py path, properties.json path)]
        for index, val in enumerate(temp_list):
            with open(val[2], 'r') as read_file:
                props = json.load(read_file)
                if isinstance(props, dict):
                    # Populate auto_details, a dict containing details 
                    # for each Automation that will be added to results_dict.
                    #
                    # We also have to convert exe_paths to a binary format,
                    # for easy iteration through the list of paths, even if
                    # there is only one external exe.
                    #
                    # Empty exe_paths, i.e something that does not need to
                    # leverage an external app, will be stored as an empty
                    # list converted to binary format. 

                    # Converting list to binary with pickle! :)
                    exe_list = props['exe']
                    binary_exe_list = pickle.dumps(exe_list)

                    # Creating source dictionary for DB import.
                    auto_details = {
                        'name': val[0],
                        'enabled': "False", # Default is False,
                        'version': props['version'],
                        'py_path': val[1],
                        'py_md5': calc_md5(val[1]),
                        'downloadFirst': props['downloadFirst'],
                        'author': props['author'],
                        'description': props['description'],
                        'extensions': str(props['extensions']),
                        'exe_paths': binary_exe_list,
                        'type': props['type']
                    }
                    # Finally, add details to results_dict
                    results_list.append(auto_details)
                    self.log.info("Successfully imported 'properties.json' for " + "[" + val[0] + "]")
                else:
                    self.log.info("Failed to open 'properties.json' for " + "[" + val[0] + "]")
        
        return results_list

    def gen_automations_db(self):
        '''
        '''
        # To prevent DB drift from reality, ALL prev. records are removed 
        # first before rebuilding Columns in the 'bcamp_automations' table.
        # Before we delete the records, store any enabled automations to be
        # re-enabled following scan.
        prev_enabled_autos, prev_disabled_autos = get_automations()
        print("$.prev", prev_enabled_autos)


        # Open connection to DB
        dbshell, dbcon = open_dbshell()
        dbshell.execute('''DELETE FROM bcamp_automations;''')
        print("SQLite3: 'bcamp_automations' Purged for Refresh.")
        # Iterate through list of Automation Details stored in dict...
        avail_automations = self.scan_automations()
        for auto in avail_automations:
            # Execute the actual SQLite3 query for each item in list.
            try:
                dbshell.execute('''INSERT INTO bcamp_automations (
                    name,
                    enabled,
                    version,
                    py_path,
                    py_md5,
                    downloadFirst,
                    author,
                    description,
                    extensions,
                    exe_paths,
                    type)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?);''',
                    (
                    auto['name'],
                    auto['enabled'],
                    auto['version'],
                    auto['py_path'],
                    auto['py_md5'],
                    auto['downloadFirst'],
                    auto['author'],
                    auto['description'],
                    auto['extensions'],
                    auto['exe_paths'],
                    auto['type']
                    ))
            except sqlite3.IntegrityError:
                pass # Thrown for unique constraint failues/Dupes
        dbcon.commit() # Save changes
        dbcon.close() # Close connection

        # Now, get automations once more and enable items that still exist in
        # the extensions folder.
        new_enabled_autos, new_disabled_autos = get_automations()
        print("$.new(dis/en)", new_disabled_autos, new_enabled_autos)
        for item in new_disabled_autos:
            if item in prev_enabled_autos:
                update_automation(item, 'enabled', 'True')

        print("SQLite3: 'bcamp_automations' Populated with Avail Automations.")

    def get_avail(self):
        '''
        Called when the UI is initalized to scan the Automations dir,
        and populate the DB with any available automations that have not been
        added yet. 
        '''
        # Get dictionary of Automations...
        print("...Fetching Automation's from DB...")
        pprint.pprint(dump_automations())


# ["bcamp_automations"] Table Queries
def dump_automations():
    '''
    Returns all rows and columns within the Automations table
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT * FROM bcamp_automations;")
    result = dbshell.fetchall()
    dbcon.close()
    return result    

def get_automations():
    '''
    Returns two list, enabled_autos and disabled_autos based on the 'enabled'
    column value for successfully imported Automations.

    Returned list only contain the "name" of each Automation.
    '''
    # Create connection to DB
    dbshell, dbcon = open_dbshell()

    # Get enabled autos...
    dbshell.execute("SELECT name FROM bcamp_automations WHERE enabled = (?);", 
        ('True',))
    enabled_result = dbshell.fetchall()
    enabled_return = []
    for item in enabled_result:
        enabled_return.append(item[0])

    # Get disabled autos...
    dbshell.execute("SELECT name FROM bcamp_automations WHERE enabled = (?);", 
        ('False',))
    disabled_result = dbshell.fetchall()
    disabled_return = []
    for item in disabled_result:
        disabled_return.append(item[0])

    # Close connection to DB and return results.
    dbcon.close()
    return enabled_return, disabled_return # Results are tuples

def query_automation(target_auto, column):
    '''
    Returns a single column from the Automations table for the defined
    target automations.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + " FROM bcamp_automations WHERE name = (?);", 
        (target_auto,))
    result = dbshell.fetchone()
    dbcon.close()
    return result[0] # Results are tuples, but we expect ONLY 1 value here.

def update_automation(target_auto, column, value):
    '''
    Updates a column value for a specific target automation with the new 
    'value' variable
    '''
    dbshell, dbcon = open_dbshell()
    
    dbshell.execute("UPDATE bcamp_automations SET " + column + " = (?) WHERE name = (?)", (value, target_auto))
    dbcon.commit() # save changes
    dbcon.close()
    print("SQLite3: *bcamp_automations*:",target_auto, column, "=", value)


'''
[SimpleParser Engine]

The below class provides further scalability of bCamp by leveraging 
"user-defined parsing rules". The goal of this parser is to provide a simple
configuration of keyword, line, or regex rules for a target file. Automating
some of the effort for common data such as versioning.
'''


class SimpleParser():
    '''
    This class is initalized *EVERYTIME* a file-record is refreshed for a 
    particular SR number. The methods defined here provide a simple 
    configuration of keyword, line, or regex rules for a target file that may
    be discovered during refresh. The rules themselves are user specific and
    are stored in the DB in the "bcamp_parser" table.

    REQs.
        + Rules should be import/exportable. JSON?? XML??
        + Allow for Regex expressions, keyword, or line count rules.
        + Keyword should have an option to return first line or ALL lines.
        + Results saved to SimpleParser.results (a .txt file)

    DB Concept
        id (Primary Key) - 0001, 0002, 0012, etc.
        type - regex, line, keyword
        return - first, all
        target - filename of target file
        rule - Raw rule definition string.
            > regex : Raw Regex string
            > line : Line number to extract (starts at 0)
            > keyword : Keyword phrase to extract from file
    '''
    def __init__(self, key_val, init_Filebrowser):
        print("SimpleParser: Starting seperate thread...")
        self.key_val = key_val
        self.filebrowser = init_Filebrowser
        thread_name = 'SimpleParser-' + str(key_val)

        # STARTING THREAD!
        try:
            threading.Thread(
                target=self.master_thread, name=thread_name
            ).start()
        except:
            print("SimpleParser: FATAL - Unable to start thread.")
            # Exit Parser. 
            return

    def master_thread(self):
        '''
        Core "runner" of the SimpleParser engine, that creates its own 
        seperate thread to prevent UI hanging.
        '''
        allfiles = query_all_files_column(self.key_val, 'path')
        print("\n\n")
        print("$.allfiles", allfiles)
        print("\n\n")
        ruleset = dump_parser() # Python Dict of rules saved DB.

        target_file_lst = [] # Simplified list of target files to search for.
        found_targets = [] # Resulting 'full path' of found files.
        res_item_set = [] # Resulting set of filepaths, and rule params.
        # List of Parsing Results
        line_results = []
        keyword_results = []
        regex_results = []

        #Iterating through 'ruleset' to populate 'target_file_lst'
        for rule in ruleset:
            target_file_lst.append(
                os.path.normpath(ruleset[rule]['target'])
                )

        # Iterator that looks at each dictionary entry in the 
        # "updated_file_record" provided by the 
        # "Tk_Filebrowser.refresh_file_record" method when a SR is refreshed.
        # Searching for target files defined in the users parser ruleset.
        for file in allfiles:
            # Remove the remote/local root from the file path.
            # Pre-formatting for the comparison to the ruleset definitions.
            scrubbed_root, scrubbed_path = scrub_fpath(file, self.key_val)

            # Comparing scrubbed_path to target_file_list for non-root files.
            #
            # Example -> netshare\ParentDir\TargetFile.log
            #
            if scrubbed_path in target_file_lst:
                print("SimpleParser: Matched [", file ,"]")
                fpath_set = (file, scrubbed_path)
                # Appending 'fpath_set' to 'found_targets'
                found_targets.append(fpath_set)
            
            # And for 'root' files, we just compare the scrubbed_root.
            #
            #   Example -> netshare\Targetfile.log
            #
            if scrubbed_root in target_file_lst:
                print("SimpleParser: Matched [", file ,"]")
                fpath_set = (file, scrubbed_root)
                # Appending 'fpath_set' to 'found_targets'
                found_targets.append(fpath_set)

        # With the resulting file_paths, we iterate through the 
        # 'found_targets' again to compile the 'res_item_set'
        #  This is iterated through again here to reduce N* in the for' loop above.
        for item in found_targets:
            for rule in ruleset:
                if ruleset[rule]['target'] == item[1]:
                    #print(item[0], "matched rule >", rule)
                    ruleParams = {
                        'id': rule,
                        'type': ruleset[rule]['type'],
                        'return': ruleset[rule]['return'],
                        'target': item[0],
                        'rule': ruleset[rule]['rule']          
                    }
                    res_item_set.append(ruleParams)


        # Iterating through final 'res_item_set' to send to the defined parser.
        for item in res_item_set:
            if item['type'] == "LINE":
                line_results.append(self.line_parser(item))
            if item['type'] == "KEYWORD":
                keyword_results.append(self.keyword_parser(item))
            if item['type'] == "REGEX":
                regex_results.append(self.regex_parser(item))


        # Now with results from ALL engines, send data to 'gen_results_file'
        self.gen_results_file(line_results, keyword_results, regex_results)

        # Now to update the Filebrowser tree to show the resulting data!
        self.filebrowser.refresh_file_record('local', False)
        print("SimpleParser: Jobs done! Exiting.")

    def line_parser(self, item_params):
        '''
        The main method for parsing files by line count.
        '''
        print("SimpleParser-line: Scanning [", item_params['target'], "]")

        # First, Store critical Paramaters to vars.
        r_target = item_params['target'] # Target file to open and scan.
        r_rule = int(item_params['rule']) # Line to extract from 'r_target'
        
        # Second, open file, and enumerate until defined line is reached.
        with open(r_target) as fileObj:
            for line_num, line_content in enumerate(fileObj):
                if line_num == r_rule:
                    # Defined line reached, generate result to be saved.
                    parser_result = {
                        'id': item_params['id'],
                        'rule': item_params['rule'],
                        'target': item_params['target'],
                        'result': line_content
                    }
                    return parser_result
                elif line_num > r_rule: # Exit if we pass the defined line num
                    break

    def keyword_parser(self, item_params):
        '''
        The main method for parsing files by keyword.
        '''
        print("SimpleParser-keyword: Scanning [", item_params['target'], "]")

        # First, Store critical Paramaters to vars.
        r_target = item_params['target'] # Target file to open and scan.
        r_rule = item_params['rule'] # Line to extract from 'r_target'
        r_return = item_params['return'] # return 'first', or 'all' matches
        temp_results = [] # For storing multi-line matches.

        # Second, open file, and enumerate until defined line is reached.
        with open(r_target) as fileObj:
            for line_num, line_content in enumerate(fileObj):
                if r_rule in line_content:
                    print("line matches ruleset, saving to 'temp_results'")
                    temp_results.append((line_num, line_content))

        # Result formated determined by 'r_return' value
        if r_return == 'ALL':
            parser_result = {
                'id': item_params['id'],
                'rule': item_params['rule'],
                'target': item_params['target'],
                'result': temp_results
            }
            return parser_result
        elif r_return == 'FIRST':
            parser_result = {
                'id': item_params['id'],
                'rule': item_params['rule'],
                'target': item_params['target'],
                'result': temp_results[0]
            }
            return parser_result                

    def regex_parser(self, item_params):
        '''
        The main method for parsing files using a regex definition.
        '''
        print("SimpleParser-regex: Scanning [", item_params['target'], "]")

        # First, Store critical Paramaters to vars.
        r_target = item_params['target'] # Target file to open and scan.
        r_rule = item_params['rule'] # Line to extract from 'r_target'
        r_return = item_params['return'] # return 'first', or 'all' matches
        temp_results = [] # For storing multi-line matches.

        # Second, open file, and enumerate lines searching for regex match.
        with open(r_target) as fileObj:
            for line_num, line_content in enumerate(fileObj):
                match = re.search(r_rule, line_content)
                if match:
                    print("$regex_result>", line_num, match.group())
                    temp_results.append((line_num, match.group()))

        # Result formated determined by 'r_return' value
        if r_return == 'ALL':
            parser_result = {
                'id': item_params['id'],
                'rule': item_params['rule'],
                'target': item_params['target'],
                'result': temp_results
            }
            return parser_result
        elif r_return == 'FIRST':
            parser_result = {
                'id': item_params['id'],
                'rule': item_params['rule'],
                'target': item_params['target'],
                'result': temp_results[0]
            }
            return parser_result

    def gen_results_file(self, line_dict, keyword_dict, regex_dict):
        '''
        Compiles the results from all parsing engines together into a 
        human-readable format and save the results to an output file saved 
        within the 'downloads/*key_value*' folder for the scanned SR.
        '''
        # Generating 'bCampParser.results' file.
        #print("\n\n\n")
        #print("$line_dict", line_dict)
        #print("$keyword_dict", keyword_dict)
        #print("$regex_dict", regex_dict)
        
        global BCAMP_ROOTPATH
        result_file_path = (BCAMP_ROOTPATH 
            + "\\downloads\\" 
            + self.key_val
            + "\\BasecampParser.results"
        )
        results_file = open(result_file_path, "w")

        # Getting timestamp of file generation.
        new_ran_time = datetime.datetime.now()
        new_ran_time.strftime("%Y-%m-%d %H:%M:%S.%f")

        # Formatting results and writing to file.
        results_file.write("->     Basecamp Parser Results     <-\n")
        results_file.write("\n")
        results_file.write("Date : " + str(new_ran_time) + "\n")
        results_file.write("SR Number : " + self.key_val + "\n")
        results_file.write("Directory : " + query_sr(self.key_val, 'remote_path') + "\n")
        results_file.write("\n\n")

        # ** LINE RESULTS ** 
        results_file.write("[Line Parser Results]" + "\n")
        results_file.write("\n")
        for rule in line_dict:
            results_file.write("ID : " + rule['id'] + "\n")
            results_file.write("Rule(Line Number) : " + rule['rule'] + "\n")
            results_file.write("Target : " + rule['target'] + "\n")
            results_file.write("Result :\n\t" + rule['result'] + "\n")
            results_file.write("\n")

        # ** KEYWORD RESULTS
        results_file.write("[Keyword Parser Results]" + "\n")
        results_file.write("\n")
        for rule in keyword_dict:
            results_file.write("ID : " + rule['id'] + "\n")
            results_file.write("Target : " + rule['target'] + "\n")
            results_file.write("Rule(Keyword) : " + rule['rule'] + "\n")
            #Iterating through results list.
            results_file.write("Result :\n\t")
            for output in rule['result']:
                results_file.write("line:" + str(output[0]) + "  " + output[1])
                results_file.write("\n\t")
            results_file.write("\n")

        # ** REGEX RESULTS ** 
        results_file.write("[Regex Parser Results]" + "\n")
        results_file.write("\n")
        for rule in regex_dict:
            results_file.write("ID : " + rule['id'] + "\n")
            results_file.write("Target : " + rule['target'] + "\n")
            results_file.write("Rule(Regex) : " + rule['rule'] + "\n")
            #Iterating through results list.
            results_file.write("Result :\n\t")
            for output in rule['result']:
                results_file.write("line:" + str(output[0]) + "  " + output[1])
                results_file.write("\n\t")
            results_file.write("\n")


# DB methods
def query_parser(rule_id, column):
    '''
    Returns a single column from the Automations table for the defined
    target automations.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT " + column + " FROM bcamp_parser WHERE id = (?);", 
        (rule_id,))
    result = dbshell.fetchone()
    dbcon.close()
    return result[0] # Results are tuples, but we expect ONLY 1 value here.

def update_parser(rule_id, column, value):
    '''
    Updates a column value for a specific parsing rule with the new 
    'value' variable
    '''
    dbshell, dbcon = open_dbshell()
    
    dbshell.execute("UPDATE bcamp_parser SET " + column + " = (?) WHERE id = (?)", (value, rule_id))
    dbcon.commit() # save changes
    dbcon.close()
    print("SQLite3: *bcamp_parser*:", rule_id, column, "=", value)

def dump_parser():
    '''
    Returns ALL records in the 'bcamp_parser' table as a python dict Obj.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT * FROM bcamp_parser;")
    result = dbshell.fetchall()
    dbcon.close()

    # Extracting Ruleset parameters for each rule.
    # all values are strings, even if saved as int. 
    conv_ruleset = {}
    for parsing_rule in result:
        r_id = parsing_rule[0]
        r_type = parsing_rule[1]
        r_return = parsing_rule[2]
        r_target = parsing_rule[3]
        r_rule = parsing_rule[4]

        # Appending to 'conv_ruleset'
        dictContent = {
            'type': r_type,
            'return': r_return,
            'target': r_target,
            'rule': r_rule
        }
        conv_ruleset[r_id] = dictContent
    
    # Returning finalized conv_ruleset Dict.
    return conv_ruleset

def create_parser_rule(rule_dict):
    '''
    DB query that takes values from the UI, and populates a new row in the
    'bcamp_parser' table
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("""INSERT INTO bcamp_parser(
                id,
                type,
                return,
                target,
                rule) 
                VALUES (?,?,?,?,?);""",
                (
                rule_dict['id'], 
                rule_dict['type'],
                rule_dict['return'],
                rule_dict['target'],
                rule_dict['rule']
                )
            )
    dbcon.commit() # Save Changes
    dbcon.close()

    print("SQLite3: *bcamp_parser* updated!")

def update_parser_rule(rule_id, rule_dict):
    '''
    Updates all columns for a specific rule_id based on what was configured
    within the UI by the user.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute('''UPDATE bcamp_parser SET
        type = (?),
        return = (?),
        target = (?),
        rule = (?) WHERE id = (?)''',
        (rule_dict['type'],
        rule_dict['return'],
        rule_dict['target'],
        rule_dict['rule'],
        rule_id)
        )
    dbcon.commit() # save changes
    dbcon.close()
    print("SQLite3: *bcamp_parser*:", rule_id, "updated with new values.")

def del_parser_rule(rule_id):
    '''
    Drops all columns for the specified 'rule_id' primary key in the 
    'bcamp_parser' table. Used mainly by settings menu when users delete rules
    from their ruleset.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute('''DELETE FROM bcamp_parser WHERE id = (?)''',
        (rule_id,))
    dbcon.commit() # Save Changes
    dbcon.close()
    print("SQLite3: *bcamp_parser* rule", rule_id, "deleted!")

def get_max_prule():
    '''
    Convenience method to return the highest value in the 'id' column of the
    'bcamp_parser' table for new rule generation.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute('''SELECT MAX(id) FROM bcamp_parser''')
    result = dbshell.fetchone()
    dbcon.close()

    return result[0]


'''
[Note Output Methods]

These methods define the format for the 'allnotes_X' and 'casenotes_X' text
files generated when a user wants to export their notes from the UI.
'''

def gen_casenotes(key_val, outfile):
    '''
    Defines the format of the CaseNotes within the output file.
    '''
    #Case Notes Stack
    outfile.write("[Case Notes]")
    outfile.write("\n\n")
    # Getting saved case notes in DB.
    casenotes_val = query_sr(key_val, 'notes')
    # Writing to outfile
    if casenotes_val != None:
        casenotes_linesplit = casenotes_val.splitlines()
        for newline in casenotes_linesplit:
            outfile.write(newline)
    else:
        outfile.write("\tn/a")
        outfile.write("\n")

def gen_filenotes(key_val, outfile):
    '''
    Defines the format of the FileNotes within the output file.
    '''
 #File Notes Stack
    # Store local_path for later.
    local_path = query_sr(key_val, 'local_path')

    outfile.write("\n")    
    outfile.write("\n")    
    outfile.write("[File Notes]")
    outfile.write("\n")    
    # Get a list of tuples containing all file details, with "notes"
    filenotes_dump = query_dump_notes(key_val, "*")
    # Format ouput for each file.
    for file_details in filenotes_dump:
        fname = file_details[0]
        fmod_time = datetime.datetime.fromtimestamp(float(file_details[5])).strftime('%H:%M:%S %m/%d/%Y') #TODO FORMAT
        fpath = file_details[2]
        fnotes = file_details[9]

        #Check if 'fname' contains local path, if so replace it.
        if local_path in fname:
            fname = fname.replace((local_path + "\\"), 'Local.')


        outfile.write("> " + fname)
        outfile.write("\n")                
        outfile.write("| Last Modified (24 Hour): " + fmod_time)
        outfile.write("\n")
        outfile.write("| Path: " + fpath)
        outfile.write("\n")
        outfile.write("| Notes: ")
        outfile.write("\n")

        fnotes_linesplit = fnotes.splitlines()
        for newline in fnotes_linesplit:
            outfile.write(newline + "\n")
        outfile.write("\n\n\n")

def create_casenotes_file(key_val):
    '''
    Queries the DB and returns the Casenotes for the target 'key_val'
    '''
    # Define Outfile by prompting user
    save_file = filedialog.asksaveasfile(
        initialdir="/",
        title="Basecamp - CaseNotes Exporter",
        initialfile=("casenotes_" + key_val),
        defaultextension=".txt"
    )

    # Writing CaseNotes to the outfile.
    gen_casenotes(key_val, save_file)

    # Saving and closing outfile!
    save_file.close()

def create_allnotes_file(key_val):
    '''
    Generates the allnotes_X file containing Case Notes and all filenotes
    in a human-readable format.
    '''
    # Define result string
    save_file = filedialog.asksaveasfile(
        initialdir="/",
        title="Basecamp - AllNotes Exporter",
        initialfile=("allnotes_" + key_val),
        defaultextension=".txt"
        )

    # Writing CaseNotes to the outfile.
    gen_casenotes(key_val, save_file)

    # Writing FileNotes to the outfile.
    gen_filenotes(key_val, save_file)
 
    # Saving and closing outfile!
    save_file.close()


'''
[Windows Clipboard Methods]

Best-effort to interact with the windows clipboard using ONLY stdlib. 
'''
def to_win_clipboard(text):
    '''
    Saves "text" to the windows clipboard Safely.
    Call as an Thread to prevent UI stutter. Example...
        threading.Thread(target=bcamp_api.to_win_clipboard,
            args=[self.sr_id]).start()
    '''
    # Converting string to bytes for subprocess call.
    byte_form = text.encode('utf-8')
    subprocess.Popen(['clip'], stdin=subprocess.PIPE).communicate(byte_form)
    print(text, " copied to Windows Clipboard")

def from_win_clipboard_str():
    CF_TEXT = 1

    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32 = ctypes.windll.user32
    user32.GetClipboardData.restype = ctypes.c_void_p

    user32.OpenClipboard(0)
    try:
        if user32.IsClipboardFormatAvailable(CF_TEXT):
            data = user32.GetClipboardData(CF_TEXT)
            data_locked = kernel32.GlobalLock(data)
            text = ctypes.c_char_p(data_locked)
            value = text.value
            kernel32.GlobalUnlock(data_locked)
            de_value = value.decode('ascii')
            de_value = de_value.replace('\r', ' ')
            de_value = de_value.replace('\n', ' ')
            return de_value
    finally:
        user32.CloseClipboard()


'''
[General API Methods]

Shortcuts to make life easy, and save some sanity!
'''

class callbackVar:
    '''
    Registers Var as a callback method. Used for 'events' throughout the UI.
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

def smart_grid(parent, *args, **kwargs): # *args are the widgets!
    '''
    UI method that allows child widgets to be moved to the next row if they no
    longer fit due to resizing.

    - Parent : A frame widget that will contain the child widgets
    - *args : This should be a list of widgets to be drawn in the frame.
    - *kwargs : Only defines sticky location of widgets.
    '''
    divisions   = kwargs.pop('divisions', 100)
    force_f     = kwargs.pop('force', True)
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
                
def bulk_importer(import_item):
    '''
    Method used to import multiple
    '''
    def start_bulk_import(import_item, sr_num, product, account):
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
        import_item.value = new_import_dict

    # Prompt user for file to import from.
    src_file = filedialog.askopenfilename(
        initialdir="/",
        title="Basecamp Bulk Importer - Select a source import file!",
        filetypes=[("Text files",
                    "*.txt*")])

    # Open resulting file
    print("USER SELECTED IMPORT FILE:", src_file)
    ifile = open(src_file, 'r')
    ifile_content = ifile.readlines()
    # Read lines of "ifile" and import one, by one.
    for line in ifile_content:
        print("-->", line)
        # Splitting string to parse for account, and product vals.
        split_line = line.split(', ')
        # Order -> Sr_Num, Product, Account S
        start_bulk_import(import_item, split_line[0], split_line[1], split_line[2])

def destroy_sr(key_val):
    '''
    Deletes all tables, UI elements and files stored locally for a target SR 
    defined by key_val.
    '''
    global BCAMP_ROOTPATH

    print("BCAMP-API : Destorying all content for [", key_val, "]")
    # Remove items from DB
    drop_sr(key_val)
    # Removing Downloaded files.
    try:
        #os.removedirs((self.RPATH + "\\downloads\\" + self.key_value))
        shutil.rmtree((BCAMP_ROOTPATH + "\\downloads\\" + key_val))
    except:
        print("ERROR - Unable to delete *downloads* dir for " + key_val)

def search_w_google(sel_str):
    '''
    Launches a webbrowser window and uses google query formatting to search
    the internet for the selection highlighted in a text widget
    '''
    base_url = "https://www.google.com/search?q="
    search_query = base_url + sel_str
    webbrowser.open(search_query)

def search_w_jira(sel_str):
    base_url = "https://jira-lvs.prod.mcafee.com/secure/QuickSearch.jspa?searchString="
    search_query = base_url + sel_str
    webbrowser.open(search_query)

def get_snapshot(path):
    '''
    Returns a single nested {<file_name>: {'path', 'type', etc.},} for all files
    in a directory, by utilizing os.scandir and iterating through the resulting
    dir_entries.
    '''
    # Start iterating through dirs...
    dir_entries = get_dir_entries(path)
    snapshot_dict = {}
    if dir_entries != None:
        for file_obj in dir_entries:
            # Getting stats for each file...
            file_stats = file_obj.stat()

            # Building dict table...
            if file_obj.is_file():
                file_type = os.path.splitext(file_obj.path)[1]
            elif file_obj.is_dir():
                file_type = 'dir'
            single_file_table = {
                file_obj.name: {
                        'path': file_obj.path,
                        'type': file_type,
                        'size': file_stats.st_size,  # Bytes -> kB
                        'creation_time': file_stats.st_ctime,
                        'modified_time': file_stats.st_mtime,
                        'date_range': None, # Set in "finalize" in UI
                        'favorite': False,  # Set in "finalize" in UI
                        'notes': None,      # Set in "finalize" in UI
                        'depth_index': 0    # Assuming root depth.
                }
            }
            snapshot_dict.update(single_file_table)

        return snapshot_dict

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

def findkeys(node, key_val):
    if isinstance(node, list):
        for i in node:
            for x in findkeys(i, key_val):
                yield x
    elif isinstance(node, dict):
        if key_val in node:
            yield node[key_val]
        for j in node.values():
            for x in findkeys(j, key_val):
                yield x

def setup_log(logger_name, level=logging.INFO):
    '''
    General 'logging' factory function to generate a new logging file named
    "logger_name.log" which is stored in the /logs folder. Here is an example
    of how to use this method...
    # Setup Logger  
    setup_logger('extensions')  
    extensions = logging.getLogger('extensions')  
    
    # Writing a message...  
    extensions.info("Oh no, It broke!")  
    
    '''
    # Creating standarized path...
    # Getting 'root path' or install location
    RPATH = (str(pathlib.Path(__file__).parent.absolute())).rpartition('\\')[0]
    # Adding "logs" folder structure
    log_file = RPATH + "\\logs\\" + logger_name + ".log"
    # Configuring Logger...
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',)
    fileHandler = logging.FileHandler(filename=log_file, mode='a')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    l.setLevel(level)
    l.addHandler(fileHandler)
    l.addHandler(streamHandler)

def calc_dir_size(dir_path):
    '''
    Calculates size of nested files and dirs in *dir_path*, 
    returns size of *dir_path* in BYTES.
    '''
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

def calc_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def create_mainlog():
    RPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
    if os.access((RPATH + '\\logs\\main.log'), os.R_OK):
        logging.basicConfig(filename=(RPATH + '\\logs\\main.log'), encoding='utf-8', level=logging.DEBUG)
    else:
        # create empty setup.log file
        file = open((RPATH + '\\logs\\main.log'), "w+")
        file.close()
        logging.basicConfig(filename=(RPATH + '\\logs\\main.log'), encoding='utf-8', level=logging.DEBUG)

def scrub_fpath(file_path, key_val):
    '''
    Returns a tuple of the "root" folder and the path to file, without local
    or remote dir noise. This allows for accurate primary keys in the DB, and
    prevents overwrites of identical file names, but with a different path.
    '''
    # Determine 'clean_path' - This is the parent file *AFTER* the 
    # remote/local dir.
    r_root = query_sr(key_val, 'remote_path')
    l_root = query_sr(key_val, 'local_path')
    print("$.scrub", file_path)

    if r_root in file_path:
        clean_path = (file_path.replace(r_root, "").split("\\", 1)[1])

    elif l_root in file_path:
        clean_path = (file_path.replace(l_root, "").split("\\", 1)[1])

    
    # Partition 'clean_path' to get file_root
    partitionResult = clean_path.partition("\\")
    file_root = partitionResult[0]
    file_name = partitionResult[1] + partitionResult[2]
    return file_root, file_name

def check_newfiles(key_val):
    '''
    Method that scans the root directory of a target SR number, counting the
    number of files found - omiting any subdirs or files - using the os lib.
    The resulting number is then compared to the SR's "last_file_count" record
    stored in the DB. 
    
    If the result is '>' than the "last_file_count", this method returns True. 
    '''
    #First, store the "last_file_count" number from the DB.
    og_count = query_sr(key_val, 'last_file_count')
    print("$\nog>", og_count)

    #Second, count the number of files or dirs present at root only.
        #Getting key_val root path
    rootpath = query_sr(key_val, 'remote_path')
        #Counting...
    try:
        fresh_count = len(os.listdir(rootpath))
    except FileNotFoundError:
        fresh_count = 0

    print("$\nnew cnt>", fresh_count)
    #Finally, compare results and return Bool
    try:
        if fresh_count > og_count:
            return True
        elif fresh_count <= og_count:
            return False
    except TypeError: #Seen on new imports where value is None
        return False

def set_devMode(enable_bool):
    '''
    If a user enabled Dev mode through the secret-sauce in the UI, this method
    is called to update the DB with the right parameters, and generates the
    local '_testing_nas' remote dir.
    '''
    if enable_bool == False:
        #Updating DB config var for 'dev_mode' and 'remote_root'
        global BCAMP_PRODNAS
        update_config('dev_mode', "False")
        update_config('remote_root', BCAMP_PRODNAS)
        print("devMode> DISABLED! Setting remote server to production.")

    elif enable_bool == True:
        # Creating local "remote" dir to source imports. This removes the 
        # requirement to be connected to the enterprise enviorment because we
        # replicate the remote server.
        global BCAMP_ROOTPATH
        dev_nas = BCAMP_ROOTPATH + "\\_dev_nas"
        sample_sr = dev_nas + "\\4-11111111111"

        if not os.access(dev_nas, os.R_OK):
            print("devMode> Creating local 'remote' folder titled '_dev_nas'")
            os.mkdir(dev_nas)
            print("devMode> '_dev_nas' created in bCamp install location.")

        # Creating sample 'SR' folder as it would be in prod.
        if not os.access(sample_sr, os.R_OK):
            print("devMode> Creating sample SR folder titled '4-11111111111")
            os.mkdir(sample_sr)
            print("devMode> Sample SR dir created! - be sure to populate it.")

        #Updating DB config var for 'dev_mode' and 'remote_root'
        update_config('dev_mode', "True")
        update_config('remote_root', dev_nas)
        print("devMode> ENABLED! Setting remote server to '\_dev_nas'")

# EOF