# logGuru - *Bringing Zen to the TSE workflow.*
*Authored by Collin Spears, Network TSE.*

# Overview and Design Philosphy
Project Philosophy : a Haiku
> Bring Zen to *YOUR* work  
> Repeitition prevents flow     
> Simplify the task  

Formally known as "LogQuery", **"logGuru" is a GUI and/or CLI automation engine with the goal to automate the repeatable and often tedious tasks for TSE's working with McAfee Enterprise Products.** This app, tool, engine, script, whatever you want to call it - can be divided into three parts. *Root*, *Extension*, and *API"* which we will discuss more in a moment. Lastly, you will see the word *Task* - italized and capilitzed throughout this guide; a *Task* is any code block (Class, Function, etc.) 

* **Root** - All of the main elements of logGuru. This includes the *GUI*, *Framework Logic*, and *Tasks* Classes 
* **Extension** - Contains *user* defined *Task* or code to extend functionality of logGuru. Following "Bring Zen to *YOUR* work"
* **API** - A fully-featured CLI to call the *Task*'s defined in Root. Providing a powerful alternative to the GUI by sharing **Root**, and **Extension** code.

Example of Engine Structure
```
+=====================================================================================+  
|                                                                                     |  
|   [GUI Event] -->                                                                   |
|           [SR Number, Sub_Folder*, and "Workflow"] --> Calls Root.Stack."Workflow"  |  
|   [API Command] -->                                                                 |
|                                                                                     |
|      Stack."Workflow" is a predefined list of *Task*'s to run in order.             |
|       Here is an example of a the default *Download* "workflow"...                  |
|                                                                                     |
|        +-----------------------------+                                              |
         |  ROOT                       |                                              |
|        |  +----------------------+   |                                              |
|        |  | Stack.Download       |   |                                              |
|        |  |   CheckContents()    |   |                                              |
|        |  |   Download()         |   |                                              |
|        |  |   ZipUnpacker()      |   |                                              |
|        |  |   **Extension_Task** |   |                                              |
|        |  |   ParsingEngine()    |   |                                              |
|        |  +----------------------+   |                                              |
|        |                             |                                              |
|        |  +----------------------+   |                                              |
|        |  | GUI                  |   |                                              |
|        |  |   UI Elements        |   |                                              |
|        |  |   Daemons            |   |                                              |
|        |  |   Launch             |   |                                              |
|        |  +----------------------+   |                                              |
|        +-----------------------------+                                              |
|                                                                                     |
|                                                                                     |
|                                                                                     |
|                                                                                     |
|                                                                                     |
+=====================================================================================+
```

# "root" 
"logGuru_beta' is 'root' and is where the main functionality of the engine is defined. The Graphic User-Interface (Gui), Download, Upload, Parsing, and Cleanup classes, all core elements of are defined here. 

Gui(tK) - This is where the UI is built. The window, buttons, dropdown boxes, .etc are defined here. As well as what commands are called when elements are interacted with. 
Download(thread) - A threaded process that intelligently downloads SR data from the remote "support_case_server", to a local folder called "Case Data"(User-Defined). There is built-in logic to only download files or directories that have not already been fetched. A "Download thread" is created whenever an Engineer clicks download, or calls the "download" module via the CLI. A "Download thread" is always intialized with two string args, "sub_folder" and a "sr_number" in that order. 
Upload(Thread) - The same design as Download, just uploading files from "Case Data"(User-Defined) back to the remote "suport_case_server". 
Parsing(Thread) - Users can define parsing rules within "config.py" that will automatically parse data from keyworded files to a formatted .txt file stored within each SR's data folder. From a currently limited set, users can choose parsing "modes" such as line number, and simple regEx expressions. This engine is ran by default, after an Engineer clicks Download, when "Download thread" and "autoLogs_extension.download" have been called. 
CleanUp(Thread) - Users can define an "X" number of days since modified for content within "Case Data"(User-Defined) to be marked for deletion. I would love to expand this module with the ability to query Insight for SR state, But for now, the default is 90 days. 

And if you made it through all that text, now lets talk about "Extension" and "API". Grab some beer or some tea, as this will be a bit more programming focused... 

# "Extension" 
As each product team has a different approach to unpacking case data. "Extension.py" has been designed to extend functionality beyond the core elements decribed in 'root'. This design also provides some seperation between the core project, and the possibly hundreds of different configurations. Allowing some* sanity when troubleshooting bugs, by only being responsible for maintaining the 'root' framework. To do this, "Extension" has hooks throughout 'root', to run the "extension" code at the right time... 

    logGuru_extension.config() - Called at the end @ "Core.Setup.config()". 
    logGuru_extension.download() - Called after download thread is put in queue. @ "Core.Gui.download_button()". 
    logGuru_extension.upload() - Called after upload thread is put in queue. @ "Core.Gui.upload_button()". 
    logGuru_extension.final_result() - This should return a string thatcontains the results of work completed on case data. This is appended @ Core.Download.run.stack_results 
    logGuru_extension.final_usage_log() - This should return a string that contains the results message sent to the "log" server. This is appended @ Core.Download.run.unpack_metrics 

- Adding classes, functions, and other code - 
    With the design philosphy in mind, you can write anything you can think of here. If its python code, it should run. If you are not quite sure what you would put here, the Network team (where I work) uses the extension file to define unpacking functions that handle NSP/ATD encrypted logs. Very similar to "zip_engine" found @core.ZipEngine. 

- Some important considerations - 
    Because "Extension" is imported into 'root', the file cannot be renamed. It is recommended to change the "version" number declared at the top of the python file to keep track of changes and aid you in troubleshooting. The "LGE" version is show in 'root's GUI or can be shown when running "python3 lguru.py -e" or "--lge_version" 

    If you want to do work on files that were just downloaded, or If you wish to update the progress bar tag, the task must be ran as a "thread". 'root' handles most of this for you, but you will need to know how to call it correctly... 

    Declaring a function a "thread" 
        thread_obj = threading.Thread(target=<func_name>, name=<"string" or var>) 

    Calling/Starting the "thread" 
        "LQ_QUEUE.put((<Priority Value>, <thread_obj>.start()))" 

    Priority Values can be : 0 [High] 1 [Med] 2 [Low] and so on... 
        This value determines the order in which task are ran in the Queue. 
        Download thread's priority value is 0 
        Upload thread's priority value is 1 
        Cleanup thread's priority value is 2 

# "API" 
This should be much shorter than the above descriptions. "API" which is actually named "lguru.py" in the root directory, is another way to work with LogGuru. "API" does not provide a GUI, instead, users can call "API" via command-prompt with arguments to that mirror the functionality of using the guided interface. This allows Engineers to leverage the features found in LogGuru to third party applications. Here is an example of a download request with a subfolder defined. 
    cmd> cd /path/to/LogGuru 
    cmd> python3 lguru.py -d 4-22234571621 -s Collins_Guitar_Repair 

    This funtionality will grow over-time, but for more specifics, see... cmd> python3 lguru.py -h
