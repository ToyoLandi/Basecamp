# NSP-SensorUnpack v0.1
# Basecamp Extension
# Written by Collin Spears, Network TSE
 
'''
Welcome to the 'example' unpacker. This is designed to be a sample "unpacker"
to give you an idea of how these should be organized/written.
'''
import os
import subprocess

def run(target_file_path, local_path_of_target, exe_lst):
    # Debug Logging
    print("***", "\n",
        "target_file_path:", target_file_path, "\n",
        "local_path_of_target:", local_path_of_target, "\n",
        "exe_lst:", exe_lst, "\n",
        "***")

    # Saving *only* exe stored in "exe_lst" which is Python List obj.
    external_exe = exe_lst[0]['path']

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

    
    
