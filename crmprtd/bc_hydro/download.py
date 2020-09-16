# Downloads data from BC hyrdo


import pysftp
from tempfile import TemporaryDirectory, SpooledTemporaryFile
import logging
import os
import sys
from zipfile import ZipFile
from argparse import ArgumentParser

from crmprtd import logging_args, setup_logging, common_auth_arguments

log = logging.getLogger(__name__)


def download(username, auth_key, ftp_server, ftp_dir):
    # Connect FTP server and retrieve file
    try:
        sftp = pysftp.Connection(ftp_server, username = username, 
                                private_key = auth_key)
        with TemporaryDirectory() as tmp_dir:
            sftp.get_r(ftp_dir, tmp_dir)
            os.chdir(os.path.expanduser(tmp_dir + '/' + ftp_dir))

            with SpooledTemporaryFile(
                    max_size=int(os.environ.get('CRMPRTD_MAX_CACHE', 2**20)),
                    mode='r+') as tempfile:

                for filename in os.listdir(os.getcwd()):
                    name, extension = os.path.splitext(filename)
                    if extension == '.zip':
                        zip_file = ZipFile(filename, 'r')
                        zip_file.extractall()
                        for txt_file in os.listdir(os.getcwd()):
                            name, extension = os.path.splitext(txt_file)
                            if extension == '.txt':
                                file = open(txt_file, mode='r')
                                tempfile.write(file.read())
                                os.remove(os.getcwd() + '/' + txt_file)                
                        
                tempfile.seek(0)
                for line in tempfile.readlines():
                    sys.stdout.buffer.write(line.encode('utf-8'))

    except Exception as e:
        log.exception("Unable to process ftp")


def main():
    desc = globals()['__doc__']
    parser = ArgumentParser(description=desc)
    parser = logging_args(parser)
    parser = common_auth_arguments(parser)
    parser.add_argument('-f', '--ftp_server',
                        default='sftp2.bchydro.com',
                        help=('Full uri to BC Hydro\'s ftp server'))
    parser.add_argument('-F', '--ftp_dir',
                        default=('pcic'),
                        help=('FTP Directory containing BC hydro\'s data files'))
    args = parser.parse_args()

    setup_logging(args.log_conf, args.log_filename, args.error_email,
                  args.log_level, 'crmprtd.bc_hydro')

    download(args.username, args.auth_key, args.ftp_server, args.ftp_dir)

if __name__ == "__main__":
    main()
