# LogGuru - Bringing Zen to the TSE workflow.
# Authored by Collin Spears, Network TSE.

'''
-- LogGuru Design Philosphy : a haiku -- 
        Bring Zen to your work
      Repeitition prevents flow
         Simplify the task
'''

# Private Imports
import LogGuru_extension
import config_test

# Public Imports
import os
import sys
import time
import queue
import atexit
import shutil
import socket
import zipfile
import threading
import subprocess
import logging
import datetime
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from datetime import datetime

# Enviromental Constants
LQ_USERNAME = os.getenv('username')
LQ_VERSION_TAG = "5.3.1 Beta v2"
LQ_NET_SHARE = config_test.config_netShare
LQ_LOCAL_DIR = config_test.config_localFolder
LQ_DEV_ENABLED = config_test.config_enableDevTools
LQ_AUTO_UPLOAD_ENABLED = config_test.config_autoUpload
LQ_SHORT_PATH_ENABLED = config_test.config_uds_shortPath
LQ_QUEUE = queue.PriorityQueue()
LQ_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Carefully crafted Globals. 
lq_thread_name = "We meet again!"
lq_thread_progress = 0
lq_server_online = False


class Core:
    '''
    This is where the GUI and main threads are defined for the core
    functionality of this tool. To promote modularity, classes and functions
    defined here are ALWAYS called and should not need to be modified by any
    product team. If you want to expand functionality, see "Automating YOUR
    Workflow" in the README.md
    '''

    class Gui():
        '''
        This is where the UI/UX layout is defined. 
        '''

        def __init__(self, master):
            self.master = master
            self.session_sr_history = []
            self.sr_entry = tk.StringVar()
            self.sr_entry.trace_add('write', self.srNumberVal)
            self.sub_Entry = tk.StringVar()
            self.sub_Entry.trace_add('write', self.subFolderVal)
            self.thread = tk.StringVar()
            self.thread.trace_add('write', self.updateProgressBarLabel) #Write to "self.thread" to call updateProBar -> Changes label text.
            self.progressbar_intvar = tk.IntVar()
            
            # Frame (Main Window) 
            self.master.title("LogQuery " + LQ_VERSION_TAG)
            self.master.geometry('650x537')
            self.master.resizable(False, False)
            self.master.grid_propagate(False)
            self.master.configure(bg='#222222')
            self.master.thumbnail = tk.PhotoImage(file="./Resources/Media/thumbnail.png")
            self.master.iconphoto(False, self.master.thumbnail)

            # Labels
            self.sr_number_label = tk.Label(self.master, text="SR Number", bg="#222222", fg='white', anchor="w")
            self.sr_number_label.grid(row=0, pady=2, padx=2)
            self.sr_number_label.grid_propagate(False)
            self.sub_folder_label = tk.Label(self.master, text="Sub-Folder (Optional)", bg="#222222", fg='white', anchor="w")
            self.sub_folder_label.grid(row=1, pady=2, padx=2)

            # Buttons
            self.download_button = tk.Button(self.master, state=tk.DISABLED, bg='#404040', text="Download", command=self.download_command, width=25)
            self.download_button.grid(row=2, column=0, columnspan=1, pady=2, padx=2)
            self.upload_button = tk.Button(self.master, text="Upload", state=tk.DISABLED, bg='#404040', command=self.upload_command, width=25)
            self.upload_button.grid(row=2, column=1, pady=2, padx=2)
            self.clear_entries_button = tk.Button(self.master, text="Clear Entries", command=self.clear_entries_command, bg='#FEDF64', width=15)
            self.clear_entries_button.grid(row=0, column=2, pady=2, padx=2)
            self.open_local_folder_button = tk.Button(self.master, text="Open Local Fol.", command=self.openLocalFolderBtn, bg='#C1F9FA', width=15)
            self.open_local_folder_button.grid(row=1, column=2, pady=2, padx=2)
            self.open_network_folder_button = tk.Button(self.master, text="Open Remote Fol.", state=tk.DISABLED, bg='#404040', command=self.openNetFolderBtn, width=15)
            self.open_network_folder_button.grid(row=2, column=2, pady=2, padx=2)

            # Entries
            self.sr_number_field = ttk.Combobox(self.master, width=27, textvariable=self.sr_entry, postcommand=self.getsession_sr_history)
            self.sr_number_field.grid(row=0, column=1)
            self.sub_folder_field = ttk.Combobox(self.master, width=27, textvariable=self.sub_Entry, postcommand=self.getLocalSubs)
            self.sub_folder_field.grid(row=1, column=1)

            # Progress Bar
            self.progressbar_label = tk.Label(self.master, textvariable=self.thread, width=30, bg='#222222', fg='#FEDF64')
            self.progressbar_label.grid(row=4, column=0, columnspan=1, padx=0, pady=1, sticky=tk.N+tk.S+tk.E+tk.W)
            self.progressbar_label.grid_propagate(False)
            self.progressbar = ttk.Progressbar(self.master, variable=self.progressbar_intvar, orient="horizontal", length=20, mode="determinate")
            self.progressbar.grid(row=4, column=1, columnspan=2, padx=2, pady=1, sticky=tk.N+tk.S+tk.E+tk.W)
            self.progressbar.grid_propagate(False)
            #//progressbar
            
            # Terminal Emulator
            self.log_viewer = tk.Text(self.master)
            self.log_viewer.grid(row=3, column=0, columnspan=3, pady=5, padx=2)
            try:
                self.log_viewer.config(wrap='none', bg=config_test.config_termnialBackgroundColor, fg=config_test.config_termnialTextColor)
                #self.log_viewer.config(wrap='none', bg=config_test.config_termnialBackgroundColor, fg=config_test.config_termnialTextColor, xscrollcommand=self.log_viewerScroll.set)
            except:
                self.log_viewer.config(wrap='none', bg='#1c2933', fg='#bfff70')

            # "Options" Drop-Down
            self.gui_menu = tk.Menu(self.master, bg='#454545')
            self.master.config(menu=self.gui_menu)
            self.gui_menu_options = tk.Menu(self.gui_menu, tearoff=False,)
            self.gui_menu_options.add_command(label="Clear Terminal", command=self.clearTerminalBtn)
            self.gui_menu_options.add_command(label="Launch Clean-up", command=self.cleanup_command)
            self.gui_menu_options.add_command(label="Settings and Rules", command=self.open_config_file)
            self.gui_menu.add_cascade(label="Options", menu=self.gui_menu_options)

            # "Dev Tools"Drop-Down 
            if LQ_DEV_ENABLED:
                self.dev_menu_options = tk.Menu(self.gui_menu, tearoff=False,)
                self.dev_menu_options.add_command(label="List Threads", command=self.list_threads)
                self.dev_menu_options.add_command(label="Dump Entries to /term", command=self.dump_inpus)
                self.dev_menu_options.add_command(label="Dump threadName > /term", command=self.dump_thread_name)
                self.gui_menu.add_cascade(label="Dev Tools", menu=self.dev_menu_options)
            
            #Functions to run on boot below...
            sys.stdout = Tools.PrintTerm(self.log_viewer, "stdout") #REDIRECTS *print TO TextRedirctor!

        def srNumberVal(self, *args): # self.sr_entry.get() only updated here when "SR Number" entry modified.
            if len(str(self.sr_entry.get())) == 13: #Validating SR input here...
                self.download_button.config(bg='#c9ffad', state=tk.NORMAL)
                self.upload_button.config(bg='#c9ffad', state=tk.NORMAL)
                self.open_network_folder_button.config(bg='#C1F9FA', state=tk.NORMAL)
            else:
                self.download_button.config(bg='#404040', state=tk.DISABLED)
                self.upload_button.config(bg='#404040', state=tk.DISABLED)
                self.open_network_folder_button.config(bg='#404040', state=tk.DISABLED)
            return str(self.sr_entry.get())

        def subFolderVal(self, *args):
            return self.sub_Entry.get()

        def updateProgressBarLabel(self, *args):  # when self.thread var is changed - this menthod is called.
            self.progressbar_label.config(text=self.thread)

        def updateProgressBar(self, *args):
            self.progressbar.config(value=self.progressbar_intvar)


        def download_command(self):
            lockedSr = self.sr_entry.get()
            lockedSub = self.sub_folder_field.get()

            for sr in self.session_sr_history:
                if sr != lockedSr:
                    self.session_sr_history.append(lockedSr)
            message = ''
            if LQ_AUTO_UPLOAD_ENABLED:
                print("Queuing-Up : Download w/ sync " + "[" + lockedSr + "]")
                LQ_QUEUE.put((0, Core.DownloadThread(self, lockedSr, lockedSub)))
                LQ_QUEUE.put((1, Core.UploadThread(self, lockedSr, lockedSub)))
                Mod.download(lockedSub, lockedSr)
                message = "download_au_pressed"
            else:
                print("Queuing-Up : Download " + "[" + lockedSr + "]")
                LQ_QUEUE.put((0, Core.DownloadThread(self, lockedSr, lockedSub)))
                Mod.download()
                message = "download_pressed"
            Tools.send_usage_log(message)
                    
        def upload_command(self):
            lockedSr = self.sr_entry.get()
            lockedSub = self.sub_folder_field.get()
            print("Queuing-Up : Upload " + "[" + lockedSr + "]")
            LQ_QUEUE.put((1, Core.UploadThread(self, lockedSr, lockedSub)))   
            Tools.send_usage_log("upload_pressed")

        def openNetFolderBtn(self):
            lockedSr = self.sr_entry.get()
            self.openNetFolder(lockedSr)
            Tools.send_usage_log("remoteFolder_pressed")

        def openLocalFolderBtn(self):
            lockedSr = self.sr_entry.get()
            lockedSubFolder = str(self.sub_folder_field.get())
            if len(lockedSr) != 13:
                localFolderPath = LQ_LOCAL_DIR + "\\" + lockedSubFolder
                if os.access(localFolderPath, os.R_OK):
                    try: 
                        os.startfile(localFolderPath) # WINDOWS ONLY. *NIX not supported.
                    except OSError as e:
                        print("[" + lockedSr + "]" + str(e))
            else:
                localFolderPath = LQ_LOCAL_DIR + "\\" + lockedSubFolder + "\\" + lockedSr
                if os.access(localFolderPath, os.R_OK):
                    try: 
                        self.openLocalFolder(lockedSr, lockedSubFolder)
                    except:
                        pass
                else:
                    self.makeLocalFolder(lockedSr, lockedSubFolder)
                    self.openLocalFolder(lockedSr, lockedSubFolder)      
            Tools.send_usage_log("localFolder_pressed")

        def clearTerminalBtn(self):
            self.log_viewer.delete(1.0, tk.END)

        def clear_entries_command(self):
            self.sr_number_field.delete(0, "end")
            self.sub_folder_field.delete(0, "end")
            
        def cleanup_command(self):
            print("Queuing-Up : Clean-up case data older than [" + str(config_test.config_cleanupAge) + "] days")
            LQ_QUEUE.put((2, Core.CleanUp(self)))
            Tools.send_usage_log("cleanup_pressed")
  
        def getsession_sr_history(self):
            if not self.subFolderVal() == '':
                try:
                    fileList = os.listdir(LQ_LOCAL_DIR + "\\" + self.sub_folder_field.get())
                except:
                    self.sr_number_field['values'] = self.session_sr_history
                    return
                cleanedList = []
                for file in fileList:
                    if "4-" in file:
                        cleanedList.append(file)
                self.sr_number_field['values'] = cleanedList
            else:
                self.sr_number_field['values'] = self.session_sr_history
    
        def getLocalSubs(self):
            #Get list of local sub folders NOT SR's...
            fileList = os.listdir(LQ_LOCAL_DIR)
            cleanedList = []
            for file in fileList:
                if not "4-" in file:
                    cleanedList.append(file)
            self.sub_folder_field['values'] = cleanedList

        def openLocalFolder(self, srNumber, localSubFolder):
            localFolderPath = LQ_LOCAL_DIR + "\\" + localSubFolder + "\\" + srNumber
            if os.access(localFolderPath, os.R_OK):
                try: 
                    os.startfile(localFolderPath) # WINDOWS ONLY. *NIX not supported.
                except OSError:
                    print("[" + srNumber + "]" + " Unable to open local Folder")

        def makeLocalFolder(self, srNumber, localSubFolder):
            localPathForSr = LQ_LOCAL_DIR + "\\" + localSubFolder + "\\" + srNumber
            print("[" + srNumber + "]" + " Local directory missing. Creating directory...")
            try:
                os.makedirs(localPathForSr)
            except:
                print("Unable to make local folder - exiting thread.")
                sys.exit()
                        
        def openNetFolder(self, srNumber):
            netFolderPath = LQ_NET_SHARE + "\\" + srNumber
            try:
                os.startfile(netFolderPath) # WINDOWS ONLY. *NIX not supported.
            except OSError:
                print("[" + srNumber + "]" + " Network Folder does not exist - No uploads?")

        def open_config_file(self):
            subprocess.call(['notepad.exe', 'config.py'])

        def checkConfigVars(self): #~&~ REMOVE THIS
            if not os.access(config_test.config_netShare, os.F_OK):
                print("CONFIG:" + " Network Share cannot be found")
            if not os.access(config_test.config_localFolder, os.F_OK):
                print("CONFIG:" + " Local directory missing. Creating directory...")
                try:
                    os.makedirs(config_test.config_localFolder)
                    print("CONFIG: Local directory created at " + config_test.config_localFolder)
                except:
                    print("CONFIG: Failed to create local directory at " + config_test.config_localFolder + " - Create this manually if the error persist.")
            #~&~
            if not os.access(config_test.config_nspReportTool, os.F_OK):
                print("CONFIG:" + " NSP Report Tool not properly defined in config.py - Please correct!")
            if not os.access(config_test.config_atdDecryptTool, os.F_OK):
                print("CONFIG:" + " ATD Decrypt Tool not properly defined in config.py - Please correct!")
            if not os.access(config_test.config_7zip, os.F_OK):
                print("CONFIG:" + " 7-zip not properly defined in config.py - Please correct!")
            #~&~
        
        def dump_inpus(self):
            print("DEV> getSr - " + self.sr_entry.get())
            print("DEV> getSubFolder - " + self.sub_folder_field.get())

        def dump_thread_values(self):
            print("DEV> thread_Alive -> " + str(self.thread_Alive))
            print("DEV> thread_Name -> " + str(self.thread_Name))

        def list_threads(self):
            queueSize = LQ_QUEUE.qsize()
            allThreads = threading.enumerate()
            print("DEV> " + str(queueSize))
            for thread in allThreads:
                print("DEV> lsThread : " + str(thread.name))

        def dump_thread_name(self):
            global lq_thread_name
            print("DEV> threadName -> " + lq_thread_name)
            print("DEV> self.thread -> " + self.thread)

    class Download(threading.Thread):
        '''
        What happens when user hits "Download".
        '''
        def __init__(self, gui, srNum, localSub):
            super().__init__()
            self.Gui = gui #needed for print() -> guiTerminalEmu
            self.lockedSrNumber = srNum
            self.lockedSubFolder = localSub
            if self.lockedSubFolder == '':
                self.name = "[ " + self.lockedSrNumber + " ]" + " Downloading..."
            else:
                self.name = "[ " + self.lockedSubFolder + "/"+ self.lockedSrNumber + " ]" + " Downloading..."
            self.priority = 0 #High
            #[~&~]
            self.encZipPathList = []
            self.binZipPathList = []
            #[~&~]
                
        def run(self):
            global lq_thread_progress
            Tools.set_progressbar_val(10)
            # STEP 1 - DOWNLOAD CONTENT
            downloadCount = self.Download(self.lockedSrNumber, self.lockedSubFolder)
            Tools.set_progressbar_val(50)
            #STEP 2 - PARSE UNPACKED CONTENT
            parser = Core.ParsingEngine(self.lockedSrNumber, self.lockedSubFolder)
            parser.run()
            Tools.set_progressbar_val(55)
            stackResults = " All done! Downloads-[" + str(downloadCount) + "] "
            #~&~
            if not downloadCount == 0:
                Tools.set_progressbar_val(70)
                Tools.set_progressbar_val(85)
                Tools.set_progressbar_val(100)
            else:
                zipCount = 0
                encCount = 0
                binCount = 0
                Tools.set_progressbar_val(80)
#DOWNLOAD THREAD BUILDS FINAL RESULTS HERE
            unpackMetrics = self.lockedSrNumber + ":" + "Downloads[" + str(downloadCount) + "]" + team_mods
            try:
                s.sendall(unpackMetrics.encode())  
            except:
                pass
            print("[" + self.lockedSrNumber + "]" + stackResults + extraStackResults)
            #DELAYING FOR DEBUG
            Tools.set_progressbar_val(100)

        def Download(self, srNumber, localSubFolder):
            downloadCounter = 0
            netFileList = [] #Files found in "LQ_NET_SHARE"
            localFileList = [] #Files found in the "LQ_LOCAL_DIR"

            #Building Network File List and Local File List
            netPathForSr = LQ_NET_SHARE + "\\" + srNumber
            if os.access(netPathForSr, os.R_OK):
                netFileList = os.listdir(netPathForSr) #Storing files from LQ_NET_SHARE into list "netPathForSr" if present
            else: 
                print("[" + self.lockedSrNumber + "]" + " No files have been uploaded for this SR")
                sys.exit()

            localPathForSr = LQ_LOCAL_DIR + "\\" + localSubFolder + "\\" + srNumber
            if not os.access(localPathForSr, os.R_OK):
                os.makedirs(localPathForSr)

            #Downloading missing content only.
            localFileList = os.listdir(localPathForSr) #Storing files from Local folder into "localFileList"
            deltaFileList = Tools.compare_list(netFileList, localFileList)
            totalCount = len(deltaFileList)
            if totalCount != 0:
                incrementValue = 40 / totalCount
            else:
                incrementValue = 40

            for file in deltaFileList:
                netFullPath = LQ_NET_SHARE + "\\" + srNumber + "\\" + file
                counterBump = str(downloadCounter + 1)
                print("[" + srNumber + "]" + " Downloading (" + counterBump + "/" + str(totalCount) + ") -> " + file)
                try:
                    shutil.copy2(netFullPath, localPathForSr)
                except PermissionError: #Thrown when downloading directory instead of file.
                    dirName = (netFullPath.rsplit("\\"))[0]
                    copyTreePath = localPathForSr + dirName
                    try:
                        shutil.copytree(netFullPath, copyTreePath)
                    except FileExistsError:
                        pass
                downloadCounter += 1
                Tools.incrementProBar(incrementValue)

            if downloadCounter >= 1:
                print("[" + srNumber + "]" + " All files downloaded...")
            else:
                print("[" + srNumber + "]" + " No new files to download...")
            return downloadCounter

    class Upload(threading.Thread): # What happens when user hits "Upload"
        def __init__(self, gui, srNum, localSub):
            super().__init__()
            self.Gui = gui #needed for print() -> guiTerminalEmu
            self.lockedSrNumber = srNum
            self.lockedSubFolder = localSub
            if self.lockedSubFolder == '':
                self.name = "[ " + self.lockedSrNumber + " ]" + " Uploading..."
            else:
                self.name = "[ " + self.lockedSubFolder + "/"+ self.lockedSrNumber + " ]" + " Uploading..."
            self.priorty = 1 #Medium

        def run(self):
            Tools.set_progressbar_val(10)
            self.uploadCount = self.Upload(self.lockedSrNumber, self.lockedSubFolder)
            self.uploadMetrics = "METRIC: " + str(datetime.utcnow()) +  ":" + LQ_USERNAME + ":" + self.lockedSrNumber + ":" + "Uploads[" + str(self.uploadCount) + "]"
            try:
                s.sendall(self.uploadMetrics.encode())
            except:
                pass
            if self.uploadCount != 0:
                print("[" + self.lockedSrNumber + "]" +  " All done! Uploaded " + "[" + str(self.uploadCount) + "]" + " files to Remote Share")
            else:
                print("[" + self.lockedSrNumber + "]" +  " All done! Nothing to upload.")
            Tools.set_progressbar_val(100)
            
        def Upload(self, srNumber, localSubFolder):
            uploadCounter = 0
            counterBump = str(uploadCounter + 1)
            localPathForSr = LQ_LOCAL_DIR + "\\" + localSubFolder + "\\" + srNumber
            netPathForSr = LQ_NET_SHARE + "\\" + srNumber

            #Building Network File List and Local File List
            netPathForSr = LQ_NET_SHARE + "\\" + srNumber
            if os.access(localPathForSr, os.R_OK):
                if os.access(netPathForSr, os.R_OK):
                    netFileList = os.listdir(netPathForSr) #Storing files from LQ_NET_SHARE into list "netPathForSr" if present
                else: 
                    print("[" + self.lockedSrNumber + "]" + "No previous uploads! Creating directory...")
                    try:
                        os.makedirs(netPathForSr)
                    except OSError as e:
                        print("ERROR: " + "Error! " + str(e))

                #Upload missing content only.
                localFileList = os.listdir(localPathForSr) #Storing files from Local folder into "localFileList"
                deltaFileList = Tools.compare_list(localFileList, netFileList)
                totalCount = len(deltaFileList)
                if totalCount != 0:
                    incrementVal = 90 / totalCount
                else:
                    incrementVal = 90
                
                for file in deltaFileList:
                    print("[" + srNumber + "]" + " Uploading (" + counterBump + "/" + str(totalCount) + ") -> " + file)
                    #print("UPLOAD: " + "Uploading " + "[" + file + "]" + " This may take a moment...")
                    localFullPath = localPathForSr + "\\" + file
                    netFullPath = LQ_NET_SHARE + "\\" + srNumber + "\\" + file
                    try: 
                        shutil.copy2(localFullPath, netFullPath)
                    except PermissionError:
                        try:
                            shutil.copytree(localFullPath, netFullPath)
                        except FileExistsError:
                            print([" + srNumber + "] + " Something went wrong uploading file...")
                        Tools.incrementProBar(incrementVal)
                        uploadCounter += 1
                return uploadCounter
            else:
                print("[" + srNumber + "]" + " No local content to upload. Try downloading content first.")

    class CleanUp(threading.Thread): # What happens when user hits "Launch Cleanup"
        def __init__(self, gui):
            super().__init__()
            self.Gui = gui #needed for print -> guiTerminalEmu
            self.name = "Cleaning-Up..."
            self.priorty = 2 #Low

        def run(self):
            localFileList = os.listdir(LQ_LOCAL_DIR) #Refreshing "localFileList"
            cleanUpList = []
            diskSpaceSaved = 0
            
            Tools.set_progressbar_val(10)
            for file in localFileList:
                path = LQ_LOCAL_DIR + "\\" + file
                fileAge = (time.time() - os.path.getmtime(path)) / 86400 #86400 seconds in a day - converts number to day metric
                if fileAge > config_test.config_cleanupAge:
                    cleanUpList.append(file)
            totalCount = len(cleanUpList)
            if totalCount != 0:
                incrementVal = 90 / totalCount
            else:
                incrementVal = 90
            for file in cleanUpList:
                print("Clean-Up: " + "[" + file + "]" + " to be deleted...")
                root_directory = Path(path)
                fileSize = (sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())) / (1024*1024*1024)
                diskSpaceSaved = diskSpaceSaved + fileSize #Bytes to Gb
                shutil.rmtree(path)
                Tools.incrementProBar(incrementVal)
                print("Clean-Up: " + "[" + file + "]" + " deleted")
            print("Clean-Up: All done! " + "[" + format(diskSpaceSaved, '.3f') + "GB" + "]" +  " freed!")
            Tools.set_progressbar_val(100)

    class ParsingEngine(threading.Thread):
        def __init__(self, srNum, localSub):
            self.locked_sr = srNum
            self.locked_subFolder = localSub
            self.sr_path = LQ_LOCAL_DIR + "\\" + self.locked_subFolder + "\\" + self.locked_sr
            self.all_files = os.scandir(self.sr_path)
            self.parsing_results = self.sr_path + "\\" + "ParsingResults.log"
            
        def run(self): #Called to execute Parsing engine "ParsingEngine.run()"
            self.createResultsLog() # Creates initial ParsingResults file in SR folder.
            files_to_parse = self.buildIndex() # Returns list [[Info_Collector], [Sensor_Trace], [ATD_bundle]].
            imported_rules = self.getRules()
            for rule in imported_rules:
                r_counter = 1
                r_type = rule.get('type')
                r_mode = rule.get('mode')
                r_path = rule.get('path')
                r_exp = rule.get('exp')
                if r_mode == "line":
                    if r_type == "nsm":
                        for file in files_to_parse[0]:
                            full_path = file + "\\" + r_path
                            self.lineParser(r_type, full_path,  r_exp, r_counter)
                    if r_type == "ips":
                        for file in files_to_parse[1]:
                            full_path = file + "\\" + r_path
                            self.lineParser(r_type, full_path,  r_exp, r_counter)
                    if r_type == "atd":
                        for file in files_to_parse[2]:
                            full_path = file + "\\" + r_path
                            self.lineParser(r_type, full_path,  r_exp, r_counter)
                #if mode == "regEx":
                    #self.regexParser(rtype, path, exp)
                r_counter += 1

        def buildIndex(self):
            master_list = []
            infoCollector_list = []
            trace_list = []
            bundle_list = []

            for file in self.all_files:
                if file.is_dir():
                    test_path = file.path
                    if os.access(test_path, os.R_OK):
                    # Storing InfoCollector
                        infoCollector_litmus = test_path + "\\" + "config" + "\\" + "ems.properties"
                        if os.access(infoCollector_litmus, os.R_OK):
                            infoCollector_list.append(test_path)
                    # Storing Sensor trace 
                        sensor_litmus = test_path + "\\" + "logstat.mgmt.log"
                        if os.access(sensor_litmus, os.R_OK):
                            trace_list.append(test_path)
                    # Storing Support bundles    
                        bin_litmus = test_path + "\\" "opt" + "\\" + "amas" + "\\" "version.txt"
                        if os.access(bin_litmus, os.R_OK):
                            bundle_list.append(test_path)
                    
            # Combine all list to "master_list".
            master_list.append(infoCollector_list)
            master_list.append(trace_list)
            master_list.append(bundle_list)
            return master_list

        def createResultsLog(self):
            f = open(self.parsing_results, "w+")
            f.write("---< SR Details >---")
            f.write("\r")
            f.write("SR Number: " + self.locked_sr)
            f.write("\n")
            f.write("Files Can Be Found Here: " + LQ_NET_SHARE + "\\" + self.locked_sr)
            f.write("\r")
            f.write("\r")
            f.write("---< User-Defined Parsing Rules >--")
            f.write("\n")
            f.close()

        def append(self, input):
            file = open(self.parsing_results, "a")
            file.write(input)
            file.close()
        
        def getRules(self):
            return config_test.config_parsingRules
        
        def lineParser(self, r_type, r_path,  r_exp, r_counter):
            # Formatting inputs for "parsingResults.txt".
            line_count = r_exp - 1 # Resetting to zero for proper alignment. 1 read as 0.
            if r_type == "nsm":
                log = "NSM log found on line " + str(r_exp) + "..."
            if r_type == "ips":
                log = "IPS log found on line " + str(r_exp) + "..."
            if r_type == "atd":
                log = "ATD log found on line " + str(r_exp) + "..."
            if LQ_SHORT_PATH_ENABLED:
#TO-DO - Finish formatting of file_name to "../file/log"
                file_name = (r_path.rsplit("\\"))[1] + (r_path.rsplit("\\"))[0]
            else:
                file_name = r_path

            # Fetching file creation date for r_path

            # Parsing line from file...
            file_open = open(r_path)
            file_content = file_open.read()
            file_output = file_content.splitlines()[int(line_count)]

            # Results stored to "file_output". Creating rule text block here...


# Do this on one line... like one append statement.
            self.append("Rule-" + str(r_counter) + " : " + log)
            self.append("\r")
            self.append("\t" + "[" + file_name + "]" + " >>")
            self.append("\r")
            self.append("\t" + ".")
            self.append("\r")
            self.append("\t" + "." + "\t" + file_output)
            self.append("\r")
            self.append("\n")      

    class Setup():
        '''
        Setup manages building required files for app functionality such as 
        "config.py" to simplify the installaton process. If "config.py" is 
        missing in the root directory, Setup.config() builds a default 
        "config.py" file. Mod.config() is then called to populate any 
        needed items beyond the core content.
        '''
#TO-DO - Complete Setup.config()
        def config(self):
            # Run Space
            try:
                import config_auto
            except:
                self.build_config()
            Mod.config()
            # End of Run Space

            def append(input):
                file = open("config.py", "a")
                file.write(input)
                file.close()

            def build_config():
                # Builds config.py from scratch.
                file = open("config_auto.py", "w+")
                file.write(
                    "'''\r"
                    + r'READ-ME - How to use this file' + "\r"
                    + r'1. Any changes below may require you to relaunch LogQuery'
                    + r'2. "\\\\" is read as "\" - Keep in mind when defining file and executeable paths or you will run into errors' + "\r"
                    + r'3. If you need a laugh. Hell, we all do - https://xkcd.com/2259/' + "\r"
                    + "'''\r"
                    + "\r"
                    + r'#Enviromental variables' + "\r"
                    + r'config_netShare = "\\\\dnvcorpvf2.corp.nai.org\\nfs_dnvspr"' + "\r"
                    + r'config_localFolder = "C:\\Users\\' + LQ_USERNAME + r'\\Desktop\\CaseContent"' + "\r"
                    + r'config_nspReportTool = "C:\\Program Files (x86)\\Nsp Report\\nsp_report.exe"' + "\r"
                    + r'config_atdDecryptTool = "C:\\Program Files (x86)\\Nsp Report\\atd-decryptfile.exe"' + "\r"
                    + r'config_7zip = "C:\\Program Files\\7-Zip\\7z.exe"' + "\r"
                    + r'#Clean-up Settings' + "\r"
                    + r'config_cleanupAge = 90 #Days' + "\r"
                    + r'#Options' + "\r"
                    + r'config_autoUpload = True #After files have been downloaded and unpacked, upload content back to the Netshare' + "\r"
                )
                file.close()

            def add_config():
                # Adds to a pre-exisiting config.py.
                pass
            
            def check_config():
                # Reads config.py and checks needed options are "defined"
                pass
                
class Daemon:
    ''' 
    Threaded task that run beside mainThread. Used to manage "Thread Queue" 
    and networking without hanging the MainThread where the GUI is running. 
    These are started on launch and close when the application is exited.
    '''

    def __init__(self):
        self.Queue = self.QueueDaemon # Daemon.Queue()
        self.Network = self.NetworkDaemon # Daemon.Network()

    class QueueDaemon(threading.Thread): # Handling and organizing threaded processes  
        def __init__(self):
            super().__init__()
            self.daemon = True
            self.name = "Queue-Daemon"

        def run(self):
            global lq_thread_name #global for GUI
            global lq_thread_progress #global for GUI
            while True:
                try:
                    item = LQ_QUEUE.get()
                    item[1].start()
                    while item[1].is_alive():
                        formatedName = (str(item[1]).split("("))[1].replace('>', '').split(",")[0]
                        threadName =  formatedName
                        time.sleep(0.2)
                    LQ_QUEUE.task_done()
                    threadName = "Jobs Done!"
                    Tools.flushProBar()
                except:
                    #print("ERROR - Unable to retreive item from queue.")
                    pass

    class NetworkDaemon(threading.Thread): # Maintaining Socket connection to Telemetry server
        def __init__(self):
            super().__init__()
            self.daemon = True
            self.name="Network-Daemon"

        def run(self):
            while True: 
                global serverOnline
                if LQ_DEV_ENABLED:
                    host = "127.0.0.1"
                    port = 8998
                else:
                    host = "10.45.122.71" 
                    port = 8998 
                counter = 0
                while not lq_server_online:
                    retryCount = 3
                    while counter < retryCount:
                        try:
                            s.connect((host,port))
                            intialHandshake = "CLIENT: " + str(datetime.utcnow()) +  ":" + LQ_USERNAME + ":" + "Connected using [" + LQ_VERSION_TAG + "]"
                            s.sendall(intialHandshake.encode())
                            Tools.set_online_state(True)
                        except:
                            counter += 1           

class Tools:
    '''
        Functions to bridge elements from GUI and the other threads or
        running processes. There are also general I/O operations such as
        "compareList" to help with common manipulation of variables.
    '''
    #TO-DO - Reaplce PrintTerm with https://stackoverflow.com/questions/13318742/python-logging-to-tkinter-text-widget
    class PrintTerm(object): # Sends print() to terminal
        def __init__(self, widget, tag="stdout"):
            self.widget = widget
            self.tag = tag

        def write(self, str):
            #self.widget.configure(state="normal")
            self.widget.insert("end", str, (self.tag,))
            self.widget.see("end")
            self.widget.update_idletasks()

        def flush(self):
            pass

    # Short-Cuts : Common blocks of code needed.
    def no_x(path):
        return os.path.splitext(path)[0]
        #r.partition(".")[0] could also work?

    def compare_list(list1, list2):
        return (list(set(list1) - set(list2)))

    def send_usage_log(log):
            log_message =  (
                "METRIC: " 
                + str(datetime.utcnow()) 
                + ":" 
                + LQ_USERNAME   
                + ":" 
                + log
            )
            try:
                LQ_SOCKET.sendall(log_message.encode())  
            except:
                Tools.set_online_state(False)

    def set_online_state(state): # Safely sets "LQ_SERVER_ONLINE" - NetworkDaemon polls for changes to this var.
        global LQ_SERVER_ONLINE
        if isinstance(state, bool):
            LQ_SERVER_ONLINE = state
        else:
            logging.critical("Oops! Tried to set_online_state to non-boolean")

    def updateWindow(): # Elements that need to be polled/redrawn automatically are stored here. 
        global lq_thread_name
        global lq_thread_progress
        main_ui.thread.set(str(lq_thread_name))
        main_ui.progressbar_label.update_idletasks()
        main_ui.progressbar_intvar.set(int(lq_thread_progress))
        main_ui.progressbar.update_idletasks()
        root.after(200, Tools.updateWindow) #looping 1/sec

    def incrementProBar(value): # Safely increases progressBar by float(value)
        global lq_thread_progress
        currentVal = lq_thread_progress
        if isinstance(value, float) or isinstance(value, int):
            if currentVal == 100:
                print("DEBUG> Progressbar at 100")
            else:
                lq_thread_progress = currentVal + value
        else:
            print("DEBUG> incrementProBar not given number")

    def set_progressbar_val(value): # Safely sets progressBar to float(value) - used to mark "chunks" in threads run().
        global lq_thread_progress
        if isinstance(value, float) or isinstance(value, int):
            lq_thread_progress = value
        else:
            print("DEBUG> Tools.set_progressbar_val not given number")

    def flushProBar(): # Resets progressBar to zero
        global lq_thread_progress
        lq_thread_progress = 0



    def closeSocket():
        try:
            finalHandshake = "CLIENT: " + str(datetime.utcnow()) +  ":" + LQ_USERNAME + ":" + "Disconnected from Server"
            s.sendall(finalHandshake.encode())
            s.close()
        except:
            pass

class Launch:
    '''
    Called in mainThread to start app. This should be the ONLY item called in
    the "global" application space.
    '''
    # Checking installation...
    Core.Setup.config()

    # Starting UI on mainThread..
    root = tk.Tk()
    main_ui = Core.Gui(root) # Must be below "root" line for best performance.
    Tools.updateWindow() # Intial call. Once started, updateWindow() is called by "root.mainloop"
    root.mainloop()

    # Starting Daemons...
    Daemon.QueueDaemon.start()
    Daemon.NetworkDaemon.start()
    atexit.register(Tools.closeSocket)

# Launching Application! 
Launch()