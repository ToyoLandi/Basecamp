# logGuru - *Bringing Zen to the TSE workflow.*
*Authored by Collin Spears, Network TSE.*

# Overview and Design Philosphy
Project Philosophy : a Haiku
> Bring Zen to *YOUR* work  
> Repeitition prevents flow     
> Simplify the task  

**logGuru is a GUI and/or CLI tool with the goal to automate the repeatable and often tedious tasks for TSE's supporting McAfee Enterprise Products.** The *Engine* behind **logGuru** has been designed to fundamentally promote the *Project Philosophy* and allow the project to scale to the limits of Engineer's imaginations and needs. With the modular framework of the *Engine*, users are able to "expand" the functionality of **logGuru** to adapt to THEIR workflow by writing their own code in **Extension**. Allowing **logGuru** to serve any Engineer's needs, while providing an elegant, powerful, and feature-rich base. Finally, It is important that **logGuru** remains Open-source and true to the *Project Philosophy* - I personally feel this will keep this project aligned to the original intent, "Bringing Zen to the *TSE* workflow."

# Engine Layout and Design
```
                +=====================================================================================+  
                |                                                                                     |  
                |   [GUI Event] -->                                                                   |
                |           [SR Number, Sub_Folder*, and "Workflow"] --> Calls Root.Stack."Workflow"  |  
                |   [API Command] -->                                                                 |
                |                                                                                     |
                |   Stack."Workflow" is a predefined list of *Task*'s to run in order. See            |
                |       Stack.Download below for trace of how the Download "workflow" is              |
                |       Defined.                                                                      |
                |                                                                                     |
                |        +-----------------------------+                                              |
                |        |  ROOT                       |                                              |
                |        |  +----------------------+   |      +-----------------------------+         |
                |        |  | Workflow.Download    |   |      |  EXTENSION                  |         |
                |        |  |   CheckContents()    |   |      |  +-----------------------+  |         | 
                |        |  |   Download()         |   |      |  |  Download()              |         |
                |        |  |   ZipUnpacker()      |   |      |  |   *User-Written Code  |  |         |
                |        |  |   **Extension_Task** |  <~~~~~~~~~ +-----------------------+  |         |
                |        |  |   ParsingEngine()    |   |      |                             |         |
                |    +~~~~~ +----------------------+   |      |  +-----------------------+  |         |
                |    :   |                             |      |  |   Other "Workflow"    |  |         |
                |    :   |  +----------------------+   |      |  |      Functions        |  |         |
                |    :   |  | GUI                  |   |      |  +-----------------------+  |         |
                |    :   |  |   UI Elements        |   |      +-----------------------------+         |
                |    :   |  |   Daemons            |   |                                              |
                |    :   |  |   Launch             |   |      +-----------------------------+         |                              
                |    :   |  +----------------------+   |      |  API                        |         |
                |    :   |                             |      |  +-----------------------+  |         | 
                |    :   |  +----------------------+   |      |  | Download(sub_fol, sr) |  |         |                        
                |    :   |  |     Other "Task"     |   |   +~~~~~~~~>   *code from root  |  |         |                               
                |    :   |  |      Functions       |   |   :  |  +-----------------------+  |         |                          
                |    :   |  +----------------------+   |   :  |                             |         | 
                |    :   +-----------------------------+   :  |  +-----------------------+  |         |                           
                |    :                                     :  |  |   Other "Workflow"    |  |         |                  
                |    +~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+  |  |      Functions        |  |         |
                |                                             |  +-----------------------+  |         |
                |                                             +-----------------------------+         |
                |                                                                                     |
                +=====================================================================================+
```
**Task** 
> A function that is ran during a *Workflow*  
> Often I/O operations for *Case Data* such as "ParsingEngine"

**Workflow**
> A list of *Task* that are ran in order, when a user interacts with certain GUI elements, or a particular "lguru.py -Argument".  
> A *Workflow* will ALWAYS contain a target *SR Number* and optional *Sub Directory*  

**Root** 
> All of the main elements of logGuru. This includes the *GUI*, *Framework Logic*, and *Tasks* Classes 

**Extension**
> Contains *user* defined *Task* or code to extend functionality of logGuru. Following "Bring Zen to *YOUR* work"

**API** 
> A fully-featured CLI to call "Workflows", providing a powerful alternative to the GUI by sharing **Root**, and **Extension** code.

# **Root** 
All of the main elements of logGuru are found in "logGuru_beta.py", called "Root" through this guide. This file is organized into three types of classes, *GUI*, *Engine*, and *Task*. 

**GUI**
> Code only needed to provide a UI and run *Workflow*'s.  
> This includes daemons that maintain Threading and Metric Server connectivity without hanging the UI state.  
> **logGuru** uses the native Tkinter/Tcl library in Python3 to render GUI elements.  

**Engine**
> All code related to constructing the default "logGuru_extension.py" and "logGuru_config.py" files on install.  
> Logic that safely handles User written code.  
> Exposes functionality added in "Extension" to the "API"   
> All "Workflow" Definitions  

**Task**
> Functions that are called to complete a *Workflow*  
> Examples include "Download" and "Zip_Unpacker"  
> Often I/O operations  


# **Extension** 
As each product team has a different approach to unpacking case data. "Extension.py" has been designed to extend functionality beyond the core elements found in "Root". This design also provides some seperation between the core project, and the possibly hundreds of different configurations. Allowing *some* sanity when troubleshooting bugs by only being responsible for maintaining the **Root** project. To do this, **Extension** has hooks throughout **Root**, to run the "extension" code at the right time... 


# "API" 
The API is a "wrapper" that allows Engineers to call the same *Workflows* defined in **Root** through a CLI. Besides the obvious benefit of appealing to Engineers who prefer CLI applications, this also helps adhere to the *Project Philosophy* by letting other applications or scripts use the automation pre-built into the tool.
