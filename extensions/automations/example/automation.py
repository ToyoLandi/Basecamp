# Example Title
# Basecamp Extension
# Written by Author

# **REQUIRED IMPORTS
import os
import json
from optparse import OptionParser

# **REQUIRED METHOD
def __bcamp_main__(target_file_path, local_path_of_target, user_options):
    '''
    This is the "Main" method or "Runner" of the Automation. The UI calls this
    method explictly when an Automation is selected by the user for a target
    file in the "FileBrowser".
    '''
    filename = os.path.basename(target_file_path)
    debug_vars = False #Enable/Disable printing the "run(vars)"" to termial.

    if debug_vars:
        print("***", "\n",
            "filename:", filename, "\n"
            "target_file_path:", target_file_path, "\n",
            "local_path_of_target:", local_path_of_target, "\n",
            "user_options:", user_options, "\n",
            "***")

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

    