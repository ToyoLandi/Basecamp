# Logflow 0.1 Alpha
# Written by Collin Spears, Network TSE
 
'''
Welcome to the 'atd-supportbundle.py' unpacker. This is a CUSTOM unpacker
written for the Network Support team to handle unpacking ATD support-bundles
as this process is... painful. 

ATD has many 3 steps to go from an encrypted file, to a readable format.
1 - bundle.bin to a pass-protected ZIP
2 - Pass-protected ZIP -> final.zip file.
3 - Unzip final.zip to access Folders/Logs.

'''
# **REQUIRED IMPORTS
import os
import json
from optparse import OptionParser

# Custom Imports
import shutil
import subprocess

def __bcamp_main__(target_file_path, local_path_of_target, user_options):
    file_name = os.path.basename(target_file_path)
    # [0] is whole path, minus '.bin' due to os.splitext()
    result_path = os.path.splitext(local_path_of_target)[0]
    # .exe list in JSON, atd-unpacker.exe and 7-zip for ZIP decryption.
    atd_unpacker = user_options['ATD Unpacker']['path']
    zip_exe = user_options['7-ZIP']['path']

    # Debug Logging
    print("***", "\n",
        "target_file_path:", target_file_path, "\n",
        "local_path_of_target:", local_path_of_target, "\n",
        "exe_paths:", user_options, "\n",
        "***")

    # Unpack the local file with subprocess. 
    # [Step 1] - bundle.bin -> bundle_temp.zip (password protected)
    tempDir = result_path + "_temp"
    try:
        os.mkdir(tempDir)
    except FileExistsError:
        pass
    subprocess.call([atd_unpacker, local_path_of_target, (tempDir + "\\decrypted.zip")])

    # [Step 2] - bundle_temp.zip (password protected) -> final.zip
    decrypted_zip = (tempDir + "\\decrypted.zip")
    if os.access(decrypted_zip, os.R_OK):
        print("decrypted.zip created successfully.")
    print("DEBUG1")

    subprocess.call([zip_exe, "e", "-tzip", "-y", ("-o" + (tempDir + "\\" + "extracted.zip")), "-pJun0601", (tempDir + "\\" + "decrypted.zip")])

    # [Step 3] - final.zip -> Readable Dir in newly created dir
    os.mkdir(result_path)
    print("DEBUG2")
    subprocess.call([zip_exe, "x", "-y", ("-o" + result_path), (tempDir + "\\" + "extracted.zip")])

    # CLEANUP LEFTOVERS
    shutil.rmtree(tempDir, ignore_errors=True)

    print("JOBS DONE!")
    return

# **REQUIRED BOOTSTRAP FOR .PY->.EXE
if __name__ == "__main__":
    parser = OptionParser()
    # Switches based on user-defined options in UI.
    parser.add_option('-i','--input-params', dest = 'input_params',
                      help="Parameters used by the '__bcamp_main__' method")
    (options,args) = parser.parse_args()
    # Getting Params from .exe optional params.
    params = json.loads(options.input_params)
    print(params)
    # Passing params to '__bcamp_main__' - Method called through UI.
    __bcamp_main__(
        target_file_path=params['target_path'],
        local_path_of_target=params['local_target_path'], 
        user_options=params['options']
    )

