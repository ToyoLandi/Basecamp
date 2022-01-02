# Basecamp Launcher!
'''
Welcome to Basecamp.py, I hope you like what we have done with the place.
This is the main file. Executing this file will start the Application UI, AND
the SQLite3 DB. If this is your first time, this file will also create the
initial dirs and log files using this file location as "root".

Read some comments, read some code - email me at "Collin_Spears@mcafee.com" if you
have any questions!

-Made with love in Durango, Colorado!
'''

import os
import sys
import getpass
import pathlib
import subprocess
import urllib.parse

if __name__ == "__main__":

    BCAMP_ROOTPATH = str(pathlib.Path(__file__).parent.absolute()).rpartition('\\')[0]
    BCAMP_PRODNAS = r'\\dnvcorpvf2.corp.nai.org\nfs_dnvspr'

    def check_reqs():
        '''
        Checks the required packages are available for import, returns list of missing mods.
        '''
        proxy_address = 'webgateway.itm.mcafee.com'
        proxy_port = '9090'
        missing_mods = []
        #3rd Party Bois
        try:
            import paramiko
        except:
            missing_mods.append('paramiko')
        try:
            from sshtunnel import SSHTunnelForwarder
        except:
            missing_mods.append('sshtunnel')
        try:

            import requests
        except:
            missing_mods.append('requests')
        
        if len(missing_mods) != 0:
            # Create file in install location containing commands...
            reqs_file = open((BCAMP_ROOTPATH + '\\MISSING_REQUIREMENTS.txt'), 'w+')
            # Set proxy commands for VPN 
            http_proxystr = ('set http_proxy=your_username:your_password@'                
                    + proxy_address 
                    + ':' 
                    + proxy_port
                )
            https_proxystr = ('set https_proxy=your_username:your_password@'                
                    + proxy_address 
                    + ':' 
                    + proxy_port
                )
            reqs_file.write('- Basecamp Requirements - \n\n')
            reqs_file.write('Run these commands from Windows CMD, after Python is installed.\n')
            reqs_file.write('Make sure you replace "your_username" and "your_password" with their actual values!\n\n\n')
            reqs_file.write(http_proxystr + '\n')
            reqs_file.write(https_proxystr + '\n')
            for item in missing_mods:
                pip_string = (
                    'python -m pip install' 
                    + ' ' + item
                    + '\n'
                )
                reqs_file.write(pip_string)
                #print("MISSING REQUIRED MODULE -", item, "- Install this using...")
                #print("\tpython -m pip install", item)
                #print("- Behind a Proxy? Run these commands in Windows CMD - ")
                #print("\tset http_proxy=http://your_username:your_password@webgateway.itm.mcafee.com:9090", item)
                #print("\tset https_proxy=http://your_username:your_password@webgateway.itm.mcafee.com:9090", item)
                #print("\tpython -m pip install", item)
            # Close FILE
            reqs_file.close()
        
        return missing_mods

    def pip_install(proxy_authstr, package):
        subprocess.check_call([sys.executable, "-m", "pip", "install", ("--proxy="+proxy_authstr), package])

    def pip_install_noproxy(package):
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    def autoinstaller(missing_imports):
        '''
        Guided CLI installer for extra Python Packages needed to launch bcamp!
        '''
        # Prompt user for password - needs to be encoded for special chars.
        username = os.getlogin()
        print('\nNOTE:Corpzone Password is hidden while typed.')
        proxysecret = getpass.getpass()
        en_proxysecret = urllib.parse.quote(proxysecret)

        # Default Proxy vals
        proxy_address = 'webgateway.itm.mcafee.com'
        proxy_port = '9090'
        proxy_socket = proxy_address + ':' + proxy_port
        proxy_authstr = (
            'http://'
            + username + ':' + en_proxysecret
            + '@'
            + proxy_socket
        )
        # Check if connected to VPN by testing remoteshare connection.
        if os.access(BCAMP_PRODNAS, os.R_OK):
            # Set proxy_vars
            print('Setting Proxy -->', proxy_socket)
            # Install packages using pip
            for package in missing_imports:
                print('\n')
                pip_install(proxy_authstr, package)
        else:
            # Install packages using pip
            for package in missing_imports:
                print('\n')
                pip_install_noproxy(package)            


    missing_imports = check_reqs()
    if len(missing_imports) != 0:
        print('\nBasecamp AutoInstaller')
        print('   * Missing required packages *')
        for item in missing_imports:
            print('       >', item)
        yes_opts = ['y', 'Y', 'yes', 'Yes', 'YES']
        if input('\nWould you like to install these packages automatically? (y/n)') not in yes_opts:
            exit() # Exit Application!
        else:
            autoinstaller(missing_imports)

    else:
        # Import bcamp_files.
        import bcamp_api
        import bcamp_setup
        import bcamp_ui
        # Create Folder Structure
        bcamp_setup.CreateDirs()
        # Configuring main log...
        bcamp_api.create_mainlog()
        # Creating "basecamp.db" if not available.
        bcamp_setup.CreateDB()
        # Starting UI
        bcamp_ui.Gui()