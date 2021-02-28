vertical_name = "network"
version = "1.0"

'''
    This is the place to plug-in functionality beyond the core app. 

    1. team_mods.config() - Called at the end of "Core.Setup.config()".
    2. team_mods.download() - Called after download thread is put in queue. "Core.Gui.download_button()".
    3. team_mods.upload() - Called after upload thread is put in queue. "Core.Gui.upload_button()".

    If you wish to update the progress bar, the task must be ran as a 
    "threading.Thread" that has been placed into the QueueDaemon. 

    Priority : 0 [High]   1 [Med]   2 [Low]   and so on...
    Syntax : LQ_QUEUE.put((<Priority Value>, <thread_obj>.start()))
'''

def config(self):
    #Add network Vars here
    pass

def download(self, sub_folder, sr_number):
    # Called after download thread is put in queue. Which means there may
    # be an empty dir when this function is first called. If you are trying
    # do do any work with the newly downloaded case data, you will want to
    # run that code as a thread function.
    # 
    # ex.) unpacker = threading.Thread(target=engine.zip, name=(base_thread_name + "[Unzipping...]"))
    base_thread_name = sub_folder + "/" + sr_number + " "
    

    # I am choosing to use the same format as the core app, but you can 
    # honestly name your threads whatever you want. Just remember it will
    # show up in the bottom left corner while its running.
    
    engine = self.NetworkTools(sub_folder, sr_number)
    # Defining NetworkTools functions as threads to run after download.
    zip_engine = threading.Thread(target=engine.zip, name=(base_thread_name + "[Unzipping...]"))
    enc_engine = threading.Thread(target=engine.enc, name=(base_thread_name + "[Decrypting...]"))
    bin_engine = threading.Thread(target=engine.bin, name=(base_thread_name + "[Unpacking...]"))
    # Putting the threads defined above into the queue with priorty.
    # Priority : 0 [High]   1 [Med]   2 [Low]   and so on...
    # Syntax : LQ_QUEUE.put((<int>, <thread_obj>.start()))
    LQ_QUEUE.put(0, zip_engine.start())
    LQ_QUEUE.put(0, enc_engine.start())
    LQ_QUEUE.put(0, bin_engine.start())

def upload(self, sub_folder, sr_number):
    #Called after upload thread is put into queue
    pass

def final_result(self):
    # Added to final result output in terminal. 
    pass

def final_usage_log(self):
    # Added to final result message sent to the usage server. 
    # Used mainly by management to see work done through the app.
    pass


'''
    If you wish to write addtional functions or classes they should be 
    defined below. For example, The Network Team builds a class called
    NetworkTools which contains all of their decryption/unpacking 
    functions for ATD, and NSP log formats.
'''

class NetworkTools:
    '''
        NSP and ATD, the two products Network Supports, utilize .zip, .enc, 
        and .bin file formats for customer logs, which must be decrypted by
        external tools. These tools are defined in "/config.py". Below are the
        engines that unpack, and decrypt the files to a readable format.
    '''

    def __init__(self, sub_folder, sr_number):
        self.sub_folder = sub_folder
        self.sr_number = sr_number
        self.zip = self.zip_engine()
        self.enc = self.enc_engine()
        self.bin = self.bin_engine()
        self.enc_leftovers = [] #enc files found in zip files
        self.bin_leftovers = [] #bin files found in zip files
        self.master_path = LQ_LOCAL_DIR + "\\" + self.sub_folder + "\\" + self.sr_number

    def zip_engine(self):
        '''
        zip_engine scans the local SR directory for files ending in ".zip" and
        unpacks them using the zipfile library. The resulting directories are 
        then scaned for .bin or .enc files typical of customer upload habits.
        If any of these files are found, they are appended to self.bin_leftovers,
        and self.enc_leftovers respectively.
        '''
    
        lap_counter = 0
        total_zip_count = 0
        unworked_file_list = []
        master_file_list = os.scandir(self.master_path) #all files with full path stored here.
        master_file_list.close()

        for file in master_file_list:
            if zipfile.is_zipfile(file.path):
                with zipfile.ZipFile(file.path, "r") as zip_file:
                    test_zip_result = zip_file.testzip
                    if test_zip_result is None:
                        unworked_file_list.append(file)
                        total_zip_count += 1
                    else:
                        logging.info(file.name + " is damaged. " + test_zip_result)

        for file in unworked_file_list: 
            with zipfile.ZipFile(file.path, "r") as zip_file:
                logging.info("Unzipping (" + str(lap_counter + 1) + "/" + str(total_zip_count) + ") -> " + file.name)
                zip_dir = file.path.rsplit(".")[0] # Removing file extension
                zip_file.extractall(zip_dir)
                unzipped_dir = os.scandir(zip_dir)
                for file in unzipped_dir:
                    if file.path.endswith(".enc"):
                        self.enc_leftovers.append(file)
                    if file.path.endswith(".bin"):
                        self.bin_leftovers.append(file)

        lap_counter += 1
        return lap_counter

    def enc_engine(self):
        '''
        EncEngine scans the local SR directory for files ending in ".enc" and
        unpacks them using a subprocess call to an external NSP decrypting tool.
        Once trace files are decrypted, the residual .tgz files from the tool
        are deleted to keep "Case Content" clutter free.
        '''
        
        lap_counter = 0 # Counting times loop was ran.
        total_enc_count = 0 
        unworked_file_list = []
        unworked_file_list.extend(self.enc_leftovers)          
        master_file_list = os.scandir(self.master_path) #all files stored as DirEntry
        master_file_list.close() #recommend explict close in os.scandir() docs
        nsp_report_tool = config_test.mod_nsp_report_tool

        for file in master_file_list:
            if file.name.endswith(".enc") or file.name.endswith(".tgz"):
                final_dir_path = Tools.no_x(file.path)
                if not os.access(final_dir_path, os.R_OK):
                    total_enc_count += 1
                    unworked_file_list.append(file)

        for file in unworked_file_list:
            logging.info("Unpacking (" 
                + str(lap_counter + 1) 
                + "/" 
                + str(total_enc_count) 
                + ") -> " 
                + file.name)
            tgz_leftover_path = (Tools.no_x(file) + ".tgz") # trace.tgz is added to dir when a .enc is unpacked.        
            nsp_report_result = subprocess.run(
                [nsp_report_tool, 
                "-t", 
                file.path], 
                shell=False, 
                text=True
                )
            if nsp_report_result.returncode == 0: #Ran succesfully
                os.remove(tgz_leftover_path)
            else:
                logging.info("NspReportTool ran into an issue -> " + nsp_report_result.stderr)
        lap_counter += 1
        return lap_counter

    def bin_engine(self):
        '''
        BinEngine scans the local SR directory for files ending in ".bin" and
        unpacks them using a subprocess call to an external ATD decrypting tool.
        Once support bundles are decrypted, BinEngine uses the zipFile library to
        complete the unpacking process. This can be outlined as...

        1. file.bin decrypted to using ATD tool -> ./file_temp/password.zip
        2. password.zip unzipped using Zipfile -> ./file_temp/final.zip
        3. final.zip unzipped using ZipFile -> ./file
        4. os.remove
        '''
    
        lap_counter = 0
        total_bin_count = 0
        unworked_file_list = []
        unworked_file_list.extend(self.bin_leftovers)          
        master_file_list = os.scandir(self.master_path) #all files with full path stored here.
        master_file_list.close()
        self.atd_decrypt = config_test.config_nspReportTool

        for file in master_file_list:
            if file.name.endswith(".bin"):
                if not os.access(file.path, os.R_OK):
                    total_bin_count += 1
                    unworked_file_list.append(file)

        for file in unworked_file_list: #./supBundle.bin
            logging.info("Unpacking (" + str(lap_counter + 1) + "/" + str(total_bin_count) + ") -> " + file.name)

            #Building variable list for unpacking.
            file_path_wo_extension = Tools.no_x(file.path) #./supBundle
            decrypt_temp_dir = (file_path_wo_extension + "_temp") #./supBundle_temp
            password_zip_file = decrypt_temp_dir + "\\" + "password.zip" #./supBundle_temp/password.zip
            final_zip_file = decrypt_temp_dir + "\\" + "final.zip" #./supBundle_temp/final.zip

            #Begin Unpacking
            os.mkdir(decrypt_temp_dir) # Creating temp dir that will be deleted later     
            atd_decrypt_result = subprocess.run(
                [self.atd_decrypt, file.name, password_zip_file], 
                shell=False, 
                text=True
                )
            if atd_decrypt_result.returncode == 0: # Ran succesfully
                if zipfile.is_zipfile(password_zip_file):
                    with zipfile.ZipFile(password_zip_file, "r") as zip_file:
                        zip_file.extractall(pwd="Jun0601")
                    with zipfile.ZipFile(final_zip_file, "r") as zip_file:
                        os.mkdir(file_path_wo_extension) # Creating dest. dir
                        zip_file.extractall(path=file_path_wo_extension)
                        shutil.rmtree(decrypt_temp_dir)
                    lap_counter += 1
                else:
                    logging.info("zipFile tried unpacking a non-zip file -> " + password_zip_file)
            else:
                os.rmdir(decrypt_temp_dir)
                logging.info("AtdDecryptTool ran into an issue -> " + atd_decrypt_result.stderr)

        return lap_counter
