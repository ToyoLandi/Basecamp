# SFTP-Transfer v0.1
# Basecamp Extension
# Written by Collin Spears, Network TSE

# Required Imports
import os
import json
from optparse import OptionParser

# Custom Imports
# NOTE: We must use third-party modules to create the SSH/SFTP connection.
import paramiko
from sshtunnel import SSHTunnelForwarder


class Mod_ParamikoSFTP(paramiko.SFTPClient):
    '''
    Originally from Stack
    https://stackoverflow.com/questions/4409502/directory-transfers-with-paramiko
    '''
    def put_dir(self, source, target):
        ''' Uploads the contents of the source directory to the target path. The
            target directory needs to exists. All subdirectories in source are 
            created under target.
        '''
        for item in os.listdir(source):
            if os.path.isfile(os.path.join(source, item)):
                self.put(os.path.join(source, item), '%s/%s' % (target, item))
            else:
                self.mkdir('%s/%s' % (target, item), ignore_existing=True)
                self.put_dir(os.path.join(source, item), '%s/%s' % (target, item))

    def mkdir(self, path, mode=511, ignore_existing=False):
        ''' Augments mkdir by adding an option to not fail if the folder exists  '''
        try:
            super(Mod_ParamikoSFTP, self).mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise

    
class SFTP_FileTransfer:
    '''
    Creates an SSH tunnel to the SSH Jumphost server within the RepLab 
    environment and uploads the local_target_file to the defined SFTP server.
    '''
    def __init__(self, JUMP_SERVER, SFTP_SERVER, SFTP_USERNAME, SFTP_SECRET, 
        SFTP_DIR, SSH_USR, SSH_SEC, target_path):
        self._JUMP_SERVER = JUMP_SERVER
        self._SFTP_SERVER = SFTP_SERVER # Default port is 22.
        self._SFTP_USERNAME = SFTP_USERNAME
        self._SFTP_SECRET = SFTP_SECRET
        self._SFTP_DIR = SFTP_DIR
        self._SSH_USR = SSH_USR
        self._SSH_SEC = SSH_SEC
        self._target_path = target_path
        
        print('\t*SFTP*', self._JUMP_SERVER, self._SFTP_SERVER, 
            self._SFTP_DIR, self._SFTP_USERNAME, self._SFTP_SECRET, 
            self._target_path)

        # Intialize Tunnel to JumpServer
        self.TUNNEL = self.open_tunnel()
        # Then connect to Local-forwarded server defined in Tunnel.
        self.SFTP = self.open_sftp_channel()
        self.start_transfer()
        self.close_tunnel()

    def open_tunnel(self):
        server = SSHTunnelForwarder(
            self._JUMP_SERVER,
            ssh_username=self._SSH_USR,
            ssh_password=self._SSH_SEC,
            remote_bind_address=self._SFTP_SERVER,
            local_bind_address=('127.0.0.1', 6512)
        )
        server.start()
        return server
    
    def open_sftp_channel(self):
        host = '127.0.0.1'                   
        port = 6512
        transport = paramiko.Transport((host, port))  
        transport.connect(username=self._SFTP_USERNAME, password=self._SFTP_SECRET)
        sftp = Mod_ParamikoSFTP.from_transport(transport)
        return sftp
    
    def start_transfer(self):
        '''
        Using the FTP protocol, the 'local_path_of_target' is copied to the 
        user-defined FTP server IP, and path - as saved in the DB.
        '''
        def byte_count(xfer, to_be_xfer):
            '''
            Submethod to print Progress of Upload to Terminal.
            '''
            print(os.path.basename(self._target_path) 
            + " transferred: {0:.0f} %".format((xfer / to_be_xfer) * 100))
            
        print("\t*SFTP* start_transfer", self.SFTP)
        self.SFTP.chdir(self._SFTP_DIR)
        print(self.SFTP.listdir())
        print('Source ->', self._target_path)
        if os.path.isfile(self._target_path):
            self.SFTP.put(self._target_path, 
                os.path.basename(self._target_path), 
                callback=byte_count
                )
        elif os.path.isdir(self._target_path):
            base_dir = os.path.dirname(self._target_path)
            print("\t*SFTP*-basedir", base_dir)
            self.SFTP.mkdir(base_dir, ignore_existing=True)
            self.SFTP.put_dir(self._target_path, base_dir)

    def close_tunnel(self):
        print("* STOPPING SERVER *")
        self.TUNNEL.close()
        print("* SERVER CLOSED *")


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

    # Begin User Defined Code
    if os.environ['BCAMP'] == 'null':
        print('*SFTP* Authentication Failed, exiting.')
        return
    else:
        SFTP_FileTransfer(
            JUMP_SERVER = user_options['Jump Server Address']['val'],
            SFTP_SERVER = (user_options['SFTP Server Address']['val'], 22),
            SFTP_DIR = user_options['Directory']['val'],
            SFTP_USERNAME = 'nas',
            SFTP_SECRET = 'admin123',
            SSH_USR = ("corpzone\\" + os.getlogin()),
            SSH_SEC = os.environ['BCAMP'],
            target_path = local_path_of_target
        )

###DEBUG RUN SPACE
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

    