''' Downloads data from BC hyrdo

BC Hydro posts a rolling window (3 months) observing hourly data
once a week. Data is in txt files.

It is recommended to run this script once every 3 months to collect
all available data, supplemented with aggressive monitoring and
alerting for errors. If the script is run less than 3 months you
will miss data.
'''

import pysftp
from tempfile import TemporaryDirectory
import logging
import os
import sys
import re
from zipfile import ZipFile
from argparse import ArgumentParser
from datetime import date, timedelta

from crmprtd import logging_args, setup_logging, common_auth_arguments

log = logging.getLogger(__name__)


def download(username, gpg_private_key, ftp_server, ftp_dir, start_date, end_date):

    # Connect FTP server and retrieve file
    try:
        sftp = pysftp.Connection(ftp_server, username=username,
                                 private_key=gpg_private_key)
    except AuthenticationException:
        log.exception("Invalid ftp authentication")
        sys.exit(1)

    try:
        with TemporaryDirectory() as tmp_dir:
            os.chdir(os.path.expanduser(tmp_dir))
            range = DateRange(int(start_date), int(end_date), sftp)
            sftp.walktree(ftp_dir, range.matchFile, matchDir, unknownType)
            for filename in os.listdir(os.getcwd()):
                name, extension = os.path.splitext(filename)
                if extension == '.zip':
                    zip_file = ZipFile(filename, 'r')
                    for name in zip_file.namelist():
                        txt_file = zip_file.open(name)
                        sys.stdout.buffer.write(txt_file.read())

    except IOError:
        log.exception("Unable to download or open files")
        sys.exit(1)


class DateRange():


    def __init__(self, start_date, end_date, sftp):
        self.start_date = start_date
        self.end_date = end_date
        self.sftp = sftp

    # Add files within date range to temp dir
    def matchFile(self, filename):
        match = re.search(r'[0-9]{6}', filename)
        if match:
            date = int(match.group(0))
        if date >= self.start_date and date <= self.end_date:
            self.sftp.get(filename)


def matchDir(dir):
    pass


def unknownType(file):
    pass


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
    today = date.today()
    end = today.strftime("%y%m%d")
    lastMonth = date.today() - timedelta(days=28)
    start = lastMonth.strftime("%y%m%d")
    parser.add_argument('-s', '--start_date',
                        default=(start),
                        help=('Download data beginning from this day '
                            '(yymmdd). Defaults to 1 month ago.'))
    parser.add_argument('-e', '--end_date',
                        default=(end),
                        help=('Download data ending from this day '
                            '(yymmdd). Defaults to today.'))
    args = parser.parse_args()

    setup_logging(args.log_conf, args.log_filename, args.error_email,
                  args.log_level, 'crmprtd.bc_hydro')

    download(args.username, args.gpg_private_key, args.ftp_server,
             args.ftp_dir, args.start_date, args.end_date)


if __name__ == "__main__":
    main()
