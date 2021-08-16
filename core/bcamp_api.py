# Basecamp 0.2 BETA
# Written by Collin Spears, Network TSE

'''
Welcome to "bcamp_api". This module contains various general methods, and
classes that support the UI and Backend processes for Basecamp.

In the future, this may always be CLI calls to supplement automation.
'''

import os
import stat
import json
import time
import queue
import shutil
import pprint
import logging
import sqlite3
import pathlib
import datetime
import importlib
import threading
import subprocess

# Defining GLOBAL BCAMP VERSION STRING
BCAMP_VERSION = "DEV-Aug.9"

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
    version = BCAMP_VERSION
    root_path = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
    remote_root = r'\\dnvcorpvf2.corp.nai.org\nfs_dnvspr'
    download_root = root_path + r'\downloads'
    time_zone = str(time.tzname[0] + ":" + time.tzname[1])
    time_format = r"%m/%d/%y %H:%M"
    dev_mode = "False"
    ui_start_res = "1366x800"
    ui_render_top_menu = "True"
    ui_caseviewer_location = "left"
    ui_render_caseviewer = "True"

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
        ui_start_res,
        ui_render_top_menu,
        ui_caseviewer_location,
        ui_render_caseviewer)
        VALUES (?,?,?,?,?,?,?,?,?,?,?);''',
        (version,
        root_path,
        remote_root,
        download_root,
        time_zone,
        time_format,
        dev_mode,
        ui_start_res,
        ui_render_top_menu,
        ui_caseviewer_location,
        ui_render_caseviewer))

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
    Returns the value of 'column' from the 1st/ONLY row in the config table.
    '''
    dbshell, dbcon = open_dbshell()
    
    dbshell.execute("UPDATE bcamp_config SET " + column + " = (?)", (value,))
    result = dbshell.fetchone()
    dbcon.commit() # save changes
    dbcon.close()
    print("SQLite3: *bcamp_config*:", column, "=", value)

# ["favorite_files"] Table Queries
def get_fav_files():
    '''
    Returns all files and paths with the favorite_files table.
    '''
    dbshell, dbcon = open_dbshell()
    dbshell.execute("SELECT * FROM favorite_files;")
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

    print("$add_fav_file>", fname, root_path)

    # Add to SQLite3 "favorite_files" table.
    # TODO

def remove_fav_file(file_path):
    '''
    Removes row containing file name, and root path from the "favorite_files"
    table.
    '''
    fname = os.path.basename(file_path)
    dbshell, dbcon = open_dbshell()
    dbshell.execute("DELETE FROM favorite_files WHERE file_name = (?);", (fname,))
    dbcon.commit() # save changes
    dbcon.close()

# ["logviewer_supported_ext"] Table Queries
#TODO

# ["case"] Table Queries
def new_import(new_import_dict):
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
            # Getting values from config.json
            sr_num = import_dict['sr_number']
            remote_root = get_config('remote_root')
            local_root = get_config('download_root')
            # Generating SR's remote/local paths from config.json vals
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

    # If remote or local files exist for SR, create an independent 
    # *sr_num*_files table
    if os.access(case['remote_path'], os.R_OK) or os.access(case['local_path'], os.R_OK):
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
    print(key_val, "*cases* table updated in DB")

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
    if new_values['tags_list'] != None:
        print("Updating tags record for " + key_val)
        for tag in new_values['tags_list']:
            dbshell.execute("""INSERT INTO tags(
                tag,
                sr_number) 
                VALUES (?,?);""",
                (tag, key_val))

    dbcon.commit() # Save changes
    dbcon.close() # Close connection
    print(key_val, "*files* table updated in DB")

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

def populate_filetrees(self, key_val):
    '''
    Threaded generator that scans the remote, 
    local paths in order of nested dir "depth"*.

    mode('remote') - Starts scanning from 'self.remote_path'
    mode('local') - Starts scanning from 'self.local_path'

    ** The Subdirs of 'FILE1' and 'FILE2' will be inserted 
    into Tree before the Sub/Sub/dirs of 'FILE1' are inserted.
    '''

    def fstats_gen(location, depth_index):
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
                        create_db_record(location, dirEntry.path, depth_index)
                    if dirEntry.is_file():
                        create_db_record(location, dirEntry.path, depth_index)

        # Prevent adding empty temp_dir list for infin loop.
        if len(temp_dirs) != 0:
            dir_list.append(temp_dirs)
            yield temp_dirs

    def create_db_record(location, path, depth_index):
        '''
        Used by *tree_gen* to create a dictionary record for
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

        # Enough data for tree record now, insert here...
        insert_to_tree(path, file_stats, _type)

        # Determine if file is "favorited"
        #if self.config_record['favorites'] != None:
        #    if os.path.basename(path) in self.config_record['favorites']:
        #        # Pass to 'insert_to_favtree' with vars
        #        insert_to_favtree(path, file_stats, _type)

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

    ''''populate_filetrees' Run Space'''

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
            fstats_gen('remote', depth_index)
            depth_index += 1
            # Recursive call here, if EOF, stopIter thrown.
            try:
                next(fstats_gen('remote', depth_index))
            except StopIteration:
                print("Remote dir finished scanning")
    
    if local_exist:
        dir_list = [[local_root]]
        depth_index = -1 # Offset for generator incrementation.
        while True:
            fstats_gen('local', depth_index)
            depth_index += 1
            # Recursive call here, if EOF, stopIter thrown.
            try:
                next(fstats_gen('local', depth_index))
            except StopIteration:
                print("Local dir finished scanning")
    
    # At this point, the "new_file_record" dictionary object contains all
    # information needed to update the "files_X" DB table.
    # Updating DB on seperate thread for performance optimization.
    threading.Thread(target=update_files, 
    args=(self.key_value, new_file_record)).start()

# Step 3a
def insert_to_tree(treeview_widget, path, _stats, _type):
    # Build Var's for Treeview insert
    # Check *path* (head,) string via os.path.split
    split_path = os.path.split(path)
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
            _stats.st_ctime)).strftime(get_config('time_format'))

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
                    iid=path, 
                    text=tree_text,
                    values=(tree_ctime, tree_size),
                    tags=(tree_tag))
            except tk.TclError:
                # Passing - Error thrown on dupes which is expected.
                #print(mode, "Passing " + os.path.basename(path) + " : Already in Tree")
                pass

        else:
            # Create New Parent Row
            try:
                self.file_tree.insert(
                    tree_root, 
                    'end', 
                    iid=path, 
                    text=tree_text, 
                    values=(tree_ctime, tree_size), 
                    tags=(tree_tag))
            except tk.TclError:
                #print(mode, "Passing " + os.path.basename(path) + " : Already in Tree")
                pass
    except tk.TclError:
        pass
        #print("No file_tree yo!")

# Step 3b
def insert_to_favtree(treeview_widget, path, _stats, _type):
    '''
    Very Similar to 'insert_to_tree' with edits to comply
    with expected "favorites" format from generators.
    '''
    # Build Var's for Treeview insert
    split_path = path.split(self.key_value + "\\", 1)
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
        #print("**result**", "\n", "parent_tree:", parent[0], "\n", "fav_tree_text:", parent[1], "\n", "fav_tree_iid:", path, "\n")
        # Inserting Files into *self.fav_tree*
        try:
            self.fav_tree.insert(
                os.path.dirname(path), 
                'end', 
                iid=path, 
                text=parent[1],
                values=(tree_ctime, tree_size, tree_range),
                tags=(tree_tag))
        except tk.TclError as e:
            try:
                self.fav_tree.insert(
                    '', 
                    'end', 
                    iid=os.path.dirname(path), 
                    text=parent[0],
                    tags=('dir_color'),
                    open=True)
                self.fav_tree.insert(
                    os.path.dirname(path), 
                    'end', 
                    iid=path, 
                    text=parent[1],
                    values=(tree_ctime, tree_size, tree_range),
                    tags=(tree_tag))
            except tk.TclError:
                #print(mode, "Passing " + os.path.basename(path) + " : Already in Tree")
                pass

    else:
        #print("**result**", "\n", "parent_tree:", 'none/root', "\n", "fav_tree_text:", parent[0], "\n", "fav_tree_iid:", path, "\n")
        # Create New Parent Row
        try:
            self.fav_tree.insert(
                '', 
                'end', 
                iid=path, 
                text=parent[0], 
                values=(tree_ctime, tree_size, tree_range), 
                tags=(tree_tag))
        except tk.TclError:
            #print(mode, "Passing " + os.path.basename(path) + " : Already in Tree")
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
        'path': path,
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


class FileOpsQueue:
    '''
    Master Queue for Unpack/Download operations for ALL filebrowsers.
    '''
    def __init__(self, Gui):
        setup_log("fileops.log")
        self.Gui = Gui
        self.log_fileops = logging.getLogger('fileops.log')
        self.q = queue.Queue()
        self.queue_size = 0

        threading.Thread(target=self.worker_thread, name="FileOps-Daemon", daemon=True).start()

    def worker_thread(self):
        '''
        Daemon Thread for FileOpsQueue
        '''
        self.log_fileops.info("STARTING FILEOPSQUEUE")
        while True: # Infin. Loop
            item = self.q.get()
            #self.log_fileops.info(f'Working on {item}')
            item.start() # Starting thread_obj
            while item.is_alive():
                time.sleep(1)
            #self.log_fileops.info(f'Finished {item}')
            self.q.task_done()

            # Reduce queue_size by 1 if NOT refresh thread.
            root_item_name = ((item.name).rsplit(":")[2]).strip()
            print("    >", root_item_name)
            if root_item_name != "local_refresh" or root_item_name != "remote_refresh":
                if self.queue_size > 0:
                    self.queue_size -= 1
                else:
                    self.queue_size = 0
        
            self.Gui.fb_queue_string.value = str(self.queue_size) + ": Queue"
            self.Gui.fb_progress_val.value = {'mode': None} # Clearing Complete.

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
        self.Gui.fb_queue_string.value = str(self.queue_size) + " : Queue"
    
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
        self.Gui.fb_queue_string.value = str(self.queue_size) + " : Queue"

    def start_download(self, key_val, target_file):
        '''
        Logic for Download operations for Files.
        '''
        self.log_fileops.info("Launching 'FileOpsQueue.start_download'")

        # Defining local path of target_file.
        file_name = os.path.basename(target_file)
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
        size_mb = os.path.getsize(target_file)
        self.log_fileops.info("Downloading [" + target_file + "] @ " + str(size_mb) + " bytes")
        self.log_fileops.info("Local Path> " + full_local_path)
        self.log_fileops.info("Remote Path> " + target_file)

        # shutil.copy2 for files, shutil.copytree for Dirs.
        # Download use shutil.copy2 - preserve metadata.
        if os.path.isfile(target_file):
            self.log_fileops.info("Type is FILE")
            # NOTE LEGACY/shutil.copy2(target_file, full_local_path)

            # *** TRACKING PROGRESS OF COPY ***
            def update_progress_val(bytescopied):
                ''' Creates download dictionary object
                '''
                update_dict = {
                    'mode': 'download',
                    'curbytes': bytescopied,
                    'totalbytes': size_mb,
                    'srcpath': os.path.abspath(target_file),
                    'sr': key_val
                }
                # Updating with Gui w/ update dictionary
                self.Gui.fb_progress_val.value = update_dict 
        
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

    def start_upload(self, key_val, target_file):
        '''
        Logic for Upload operations for Files.
        '''
        self.log_fileops.info("Launching 'FileOpsQueue.start_upload'")

        # Defining Remote path of target_file.
        file_name = os.path.basename(target_file)
        remote_dir = (get_config("remote_root")
            + "\\" + key_val)
        print("$", remote_dir)
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
                self.Gui.fb_progress_val.value = update_dict 
        
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

    def add_automation(self, key_val, iid, target_automation):
        '''
        Converts 'input' to a thread object, and then puts it into the 
        'worker_thread' Daemon via self.q.put(X)
        '''
        # Defining Vars based on key_val.
        file_name = os.path.basename(iid)
        remote_path = (get_config("remote_root")
            + "\\" + key_val)
        local_path = (get_config("download_root")
            + "\\" + key_val)
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
            # Get dictionary object of automation from config.json for target_automation
            print("$Would check if downloadFirst = true here for auto.")
            #for auto in config_json["automations"]:
            #    if auto["name"] == target_automation:
            #        automationDict = auto
            #        print("   $", automationDict)
            #        if "downloadFirst" in automationDict:
            #            if automationDict["downloadFirst"]:
            #                self.add_download(key_val, iid)
                

        #thread_obj = threading.Thread(target=self.start_automation, 
        #    args=(key_val, iid, target_automation),
        #    name=(key_val 
        #        + "::" 
        #        + target_automation
        #        + "::" 
        #        + os.path.basename(iid)))
        #self.q.put(thread_obj)
        ## Increment Queue Size
        #self.queue_size += 1
        #self.Gui.fb_queue_string.value = str(self.queue_size) + " : Queue"

    def start_automation(self, key_val, iid, target_automation):
        '''
        Threaded process that is called when a user selects "Unpack"
        for a supported file type. 
        '''
        self.log_fileops.info("Launching 'FileOpsQueue.start_automation'")

        # Get dictionary object of automation from config.json for target_automation
        config_json = self.ConfigQueue.get_config_nowait()
        for auto in config_json["automations"]:
            if auto["name"] == target_automation:
                automationDict = auto

        # Update Progressbar String
        update_dict = {
            'mode': 'automation',
            'srcpath': os.path.abspath(iid),
            'sr': key_val
        }
        # Updating Gui w/ update dictionary
        self.Gui.fb_progress_val.value = update_dict

        # Defining Vars
        # target_automation is a dict obj.
        RPATH = str(pathlib.Path(__file__).parent.absolute()
                    ).rpartition('\\')[0]
        automation_path = (
            RPATH
            + "\\extensions\\automations\\"
            #+ target_automation['name']
            + target_automation
            + "\\automation.py"
        )
        file_name = iid.rpartition("\\")[2]
        remote_path = (config_json['remote_path'] 
            + "\\" + key_val)
        local_path = (config_json['local_path'] 
            + "\\" + key_val)
        full_remote_path = remote_path + "\\" + os.path.splitext(file_name)[0]
        full_local_path = local_path + "\\" + file_name

        # Importing the target automation Module
        self.log_fileops.info("Importing " + automationDict['name'])
        spec = importlib.util.spec_from_file_location(
            (automationDict['name']), automation_path)
        unpack_py = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(unpack_py)

        # Starting the automation.run() main method.
        self.log_fileops.info("Start your engines " + automationDict['name'] + "!")
        unpack_py.run(iid, full_local_path, automationDict['exe'])

    def put(self, obj):
        '''
        Simple method to put *obj* into self.q
        '''
        #print("DEBUG/put: Caught", obj)
        self.q.put(obj)

    ## ADDING FROM STACK
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

