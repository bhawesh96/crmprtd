'''Downloads data from BC hyrdo
'''

# Standard module
import logging
import logging.config
import sys
from argparse import ArgumentParser

#used
import pysftp
from tempfile import TemporaryDirectory
import os

from crmprtd import logging_args, setup_logging, common_auth_arguments

log = logging.getLogger(__name__)


def download(username, auth_key, ftp_server, ftp_dir):
    sftp = pysftp.Connection(ftp_server, username = username, 
                            private_key = auth_key)
    with TemporaryDirectory() as tmp_dir:
        print('created temporary directory', tmp_dir)
        sftp.get_r(ftp_dir, tmp_dir)
        print(os.listdir(tmp_dir))
        os.chdir(os.path.expanduser(tmp_dir + '/' + ftp_dir))
        print(os.getcwd())

    # try:
    #     sftp = pysftp.Connection(ftp_server, username = username, 
    #                         private_key = auth_key)
    #     #sftp.get_r(ftp_dir, )
    #     sftp.close()  
    # except Exception as e:
    #     print("Unable to process ftp")
def main():
    desc = globals()['__doc__']
    parser = ArgumentParser(description=desc)
    parser = logging_args(parser)
    parser = common_auth_arguments(parser)
    parser.add_argument('-f', '--ftp_server',
                        default='sftp2.bchydro.com',
                        help=('Full uri to BC Hydro\'s ftp '
                              'server'))
    parser.add_argument('-F', '--ftp_dir',
                        default=('pcic'),
                        help='FTP Directory containing BC hydro\'s data files')
    args = parser.parse_args()

    setup_logging(args.log_conf, args.log_filename, args.error_email,
                  args.log_level, 'crmprtd.bc_hydro')

    download(args.username, args.auth_key, args.ftp_server, args.ftp_dir)


if __name__ == "__main__":
    main()