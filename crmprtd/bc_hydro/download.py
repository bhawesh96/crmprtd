# Downloads data from BC hyrdo

import pysftp
from tempfile import TemporaryDirectory
import logging
import os
import sys
from zipfile import ZipFile
from argparse import ArgumentParser

from crmprtd import logging_args, setup_logging, common_auth_arguments

log = logging.getLogger(__name__)


def download(username, gpg_private_key, ftp_server, ftp_dir):
    # Connect FTP server and retrieve file
    try:
        sftp = pysftp.Connection(ftp_server, username=username,
                                 private_key=gpg_private_key)
        with TemporaryDirectory() as tmp_dir:
            sftp.get_r(ftp_dir, tmp_dir)
            os.chdir(os.path.expanduser(tmp_dir + '/' + ftp_dir))

            for filename in os.listdir(os.getcwd()):
                name, extension = os.path.splitext(filename)
                if extension == '.zip':
                    zip_file = ZipFile(filename, 'r')
                    for name in zip_file.namelist():
                        txt_file = zip_file.open(name)
                        sys.stdout.buffer.write(txt_file.read())

    except Exception:
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
                        help=('FTP Directory containing BC hydro\'s '
                              'data files'))
    parser.add_argument('-g', '--gpg_private_key',
                        help=('Path to file with GPG private key'))
    args = parser.parse_args()

    setup_logging(args.log_conf, args.log_filename, args.error_email,
                  args.log_level, 'crmprtd.bc_hydro')

    download(args.username, args.gpg_private_key, args.ftp_server,
             args.ftp_dir)


if __name__ == "__main__":
    main()
