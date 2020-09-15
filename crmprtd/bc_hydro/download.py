'''Downloads data from BC hyrdo
'''

# Standard module
import os
import logging
import logging.config
import ftplib
import sys
from tempfile import SpooledTemporaryFile
from argparse import ArgumentParser
#new
from ssh2.session import Session
from ssh2.sftp import LIBSSH2_FXF_READ, LIBSSH2_SFTP_S_IRUSR, LIBSSH2_FXF_WRITE
import ssh2.sftp as sftp
import socket

# Local
from crmprtd.download import retry, ftp_connect
from crmprtd.download import FTPReader, extract_auth
from crmprtd import logging_args, setup_logging, common_auth_arguments

log = logging.getLogger(__name__)


def download(username, auth_key, ftp_server):
    host = ftp_server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, 22))

    session = Session()
    session.handshake(sock)
    session.userauth_publickey_fromfile(username, auth_key)
    sftp = session.sftp_init()
    sftp_handle = sftp.opendir('pcic')
    for file in sftp_handle.readdir_ex():
        print(file[1])


#     try:
#         # Connect FTP server and retrieve file
#         ftpreader = ftp_connect(BCHFTPReader, ftp_server, ftp_file,
#                                 log, auth)

#         with SpooledTemporaryFile(
#                 max_size=int(os.environ.get('CRMPRTD_MAX_CACHE', 2**20)),
#                 mode='r+') as tempfile:
#             def callback(line):
#                 tempfile.write('{}\n'.format(line))

#             for filename in ftpreader.filenames:
#                 log.info("Downloading %s", filename)
#                 ftpreader.connection.retrlines('RETR {}'
#                                                .format(filename),
#                                                callback)
#             tempfile.seek(0)
#             for line in tempfile.readlines():
#                 sys.stdout.buffer.write(line.encode('utf-8'))

#     except Exception as e:
#         log.exception("Unable to process ftp")


# class BCHFTPReader(FTPReader):
#     '''Glue between the FTP_TLS class methods (which are callback based)
#        and the csv.DictReader class (which is iteration based)
#     '''

#     def __init__(self, host, user, password, filename, log=None):
#         self.filenames = [filename]

#         @retry(ftplib.error_temp, tries=4, delay=3, backoff=2, logger=log)
#         def ftp_connect_with_retry(host, user, password):
#             return ftplib.FTP_TLS(host, user, password)

#         self.connection = ftp_connect_with_retry(host, user, password)


def main():
    desc = globals()['__doc__']
    parser = ArgumentParser(description=desc)
    parser = logging_args(parser)
    parser = common_auth_arguments(parser)
    parser.add_argument('-f', '--ftp_server',
                        default='sftp2.bchydro.com',
                        help=('Full uri to BC Hydro\'s ftp '
                              'server'))
    args = parser.parse_args()

    setup_logging(args.log_conf, args.log_filename, args.error_email,
                  args.log_level, 'crmprtd.bc_hydro')

    download('pcic', '/home/csanders/code/ssh/id_rsa_pcic_at_bchydro', 'sftp2.bchydro.com')


if __name__ == "__main__":
    main()