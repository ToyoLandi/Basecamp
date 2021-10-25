# NSP-SensorUnpack v0.1
# Basecamp Extension
# Written by Collin Spears, Network TSE
 
'''
Welcome to the 'example' unpacker. This is designed to be a sample "unpacker"
to give you an idea of how these should be organized/written.
'''
# **REQUIRED IMPORTS
import os
import json
from optparse import OptionParser

# Custom Imports
import subprocess

def __bcamp_main__(target_file_path, local_path_of_target, user_options):
    # Debug Logging
    print("***", "\n",
        "target_file_path:", target_file_path, "\n",
        "local_path_of_target:", local_path_of_target, "\n",
        "user_options:", user_options, "\n",
        "***")

    # Saving *only* exe stored in "user_options" dict under 'NSP REPORT TOOL'
    external_exe = user_options['NSP Report Tool']['val']

    # LETS GET TO UNPACKING
    tempEnc = os.path.basename(local_path_of_target)
    tempTgz = (os.path.splitext(local_path_of_target)[0]) + ".tgz"
    print("ENC: Unpacking " + "[" + tempEnc + "]" + ". Please be patient!")

    # PASSING FILEPATH TO UNPACKER EXE
    subprocess.call([external_exe, "-t", local_path_of_target])
    print("ENC: JOBS DONE for " + tempEnc + "")

    # CLEANING UP LEFTOVERS
    print("ENC: " + "cleaning up temp .tgz file")
    try:
        os.remove(tempTgz)
    except:
        print("ENC: " + "Unable to remove .tgz file. You may want to delete this manually.")
    print("ENC: " + "cleaning up OG .ENC file...")
    try:
        os.remove(local_path_of_target)
    except:
        print("ENC: " + "Unable to remove OG .ENC file. You may want to delete this manually.")
    
    # UPLOADING RESULTS BACK TO REMOTE SHARE. 
    #unpacked_local_path = os.path.splitext(local_target_path)[0]
    #unpacked_remote_path = os.path.splitext(remote_target_path)[0]
    #print("Updating Remote Share with unpacked file...")
    ## using shutil.copytree as result is a Dir. 
    ## https://docs.python.org/3/library/shutil.html
    #shutil.copytree(unpacked_local_path, unpacked_remote_path)
    #print("Unpacked file UPLOADED to REMOTE!")
    #print("UNPACKER COMPLETED SUCCESSFULLY! HAPPY HUNTING")

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
    
    
