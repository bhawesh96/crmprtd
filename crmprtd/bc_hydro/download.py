''' Downloads data from BC hyrdo

BC Hydro posts a rolling window (3 months) observing hourly data
once a week. Data is in txt files.

It is recommended to run this script once a week to collect
updated available data, supplemented with monitoring and alerting
for errors. If the script is run less than once every 3 months
you will miss data.
'''

import pysftp
import logging
import os
import sys
import re
from zipfile import ZipFile
from argparse import ArgumentParser
from datetime import date, timedelta
from functools import partial
from tempfile import TemporaryDirectory

from crmprtd import logging_args, setup_logging

log = logging.getLogger(__name__)


def download(username, gpg_private_key, ftp_server, ftp_dir, start_date,
             end_date):

    # Connect FTP server and retrieve directory
    try:
        sftp = pysftp.Connection(ftp_server, username=username,
                                 private_key=gpg_private_key)

    except Exception:
        log.exception("Invalid ftp authentication")

    # Add files to temporary directory then print contents to stdout
    try:
        with TemporaryDirectory() as tmp_dir:

            """ Walktree has 4 required arguements, 3 of which are
             functions with form: func(filename)"""
            no_op = lambda x: None
            callback = partial(matchFile, start_date, end_date,
                               sftp, tmp_dir)
            sftp.walktree(ftp_dir, callback, no_op, no_op)

            for filename in os.listdir(tmp_dir):
                file_path = tmp_dir + '/' + filename

                zip_file = ZipFile(file_path, 'r')
                for name in zip_file.namelist():
                    txt_file = zip_file.open(name)
                    sys.stdout.buffer.write(txt_file.read())

    except IOError:
        log.exception("Unable to download or open some files")


# Add files within date range to tmp dir
def matchFile(start_date, end_date, sftp, tmp_dir, filename):
    match = re.search(r'[0-9]{6}', filename)
    if match:
        date = int(match.group(0))

        # Get filename, but not directory
        match = re.search(r'/[^/]*.zip$', filename)
        if match and date >= int(start_date) and date <= int(end_date):
            name = match.group(0)
            file_path = os.path.join(tmp_dir + name)
            sftp.get(filename, file_path)


def main():
    desc = globals()['__doc__']
    parser = ArgumentParser(description=desc)
    parser = logging_args(parser)
    parser.add_argument('-u', '--username',
                        default='pcic',
                        help=('Username for the ftp server '))
    parser.add_argument('-f', '--ftp_server',
                        default='sftp2.bchydro.com',
                        help=('Full uri to BC Hydro\'s ftp server'))
    parser.add_argument('-F', '--ftp_dir',
                        default=('pcic'),
                        help=('FTP Directory containing BC hydro\'s '
                              'data files'))
    parser.add_argument('-g', '--gpg_private_key',
                        required=True,
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
