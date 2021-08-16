# ZIP-Unpack v0.1
# Basecamp Extension
# Written by Collin Spears, Network TSE

#Import Section
import os
import zipfile 

def run(target_file_path, local_path_of_target, exe_paths):
    '''
    This is the "Main" method or "Runner" of the Automation. The UI calls this
    method explictly when an Automation is selected by the user for a target
    file in the "FileBrowser".
    '''
    filename = os.path.basename(target_file_path)
    debug_vars = True #Enable/Disable printing the "run(vars)"" to termial.

    if debug_vars:
        print("***", "\n",
            "filename:", filename, "\n"
            "target_file_path:", target_file_path, "\n",
            "local_path_of_target:", local_path_of_target, "\n",
            "exe_paths:", exe_paths, "\n",
            "***")

    # Begin User Defined Code
    unzip(target_file_path, local_path_of_target)
    
def unzip(target_file, dest_path):
    print("ZIP-Unpack:", target_file, "to ->", dest_path)
    with zipfile.ZipFile(target_file, 'r') as zip_ref:
        zip_ref.extractall(dest_path)
    print("ZIP-Unpack:", target_file, "completed successfully")