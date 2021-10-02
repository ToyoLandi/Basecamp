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
import os
import shutil
import subprocess

def run(target_file_path, local_path_of_target, exe_lst):
    file_name = os.path.basename(target_file_path)
    # [0] is whole path, minus '.bin' due to os.splitext()
    result_path = os.path.splitext(local_path_of_target)[0]
    # .exe list in JSON, atd-unpacker.exe and 7-zip for ZIP decryption.
    atd_unpacker = exe_lst[0]['path']
    zip_exe = exe_lst[1]['path']

    # Debug Logging
    print("***", "\n",
        "target_file_path:", target_file_path, "\n",
        "local_path_of_target:", local_path_of_target, "\n",
        "exe_paths:", exe_lst, "\n",
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


