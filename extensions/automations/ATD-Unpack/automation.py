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
import os
import shutil
import zipfile
import subprocess

def run(local_target_path, remote_target_path, unpacker_dict):
    file_name = os.path.basename(remote_target_path)
    # [0] is whole path, minus '.bin' due to os.splitext()
    result_path = os.path.splitext(local_target_path)[0]
    # .exe list in JSON, atd-unpacker.exe and 7-zip for ZIP decryption.
    atd_unpacker = unpacker_dict[0]
    zip_exe = unpacker_dict[1]


    # DEBUG PRINT - Check your VARS, be a good codemonkey.
    print("***\nlocal_target_path:", local_target_path,
    "\nremote_target_path:", remote_target_path,
    "\nexe_path:", unpacker_dict[0],
    "\nexe_path1:", unpacker_dict[1],
    "\nfile_name:", file_name,
    "\nd_path:", result_path,
    "\n***")

    # Unpack the local file with subprocess. 
    # [Step 1] - bundle.bin -> bundle_temp.zip (password protected)
    tempDir = result_path + "_temp"
    try:
        os.mkdir(tempDir)
    except FileExistsError:
        pass
    subprocess.call([atd_unpacker, local_target_path, (tempDir + "\\decrypted.zip")])

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


