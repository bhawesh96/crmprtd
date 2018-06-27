#!/usr/bin/env python

'''
Script to download data from the BC Ministry of Environment Air Quality Branch

Water and Air Monitoring and Reporting? (WAMR)

This is largely lifted and modified from the hourly_wmb.py script
'''

# Standard library module
import sys
import csv
import os

from datetime import datetime
from argparse import ArgumentParser
from pkg_resources import resource_stream

# Installed libraries
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Local
from crmprtd.wamr import setup_logging, rows2db
from crmprtd.wamr import file2rows, ftp2rows


def cache_rows(file_, rows, fieldnames):
    copier = csv.DictWriter(file_, fieldnames=fieldnames)
    copier.writeheader()
    copier.writerows(rows)


def main():
    # Process the command line arguments
    parser = ArgumentParser()
    # Database options
    parser.add_argument('-x', '--connection_string',
                        help='PostgreSQL connection string')
    parser.add_argument('-D', '--diag',
                        default=False, action="store_true",
                        help="Turn on diagnostic mode (no commits)")

    # Logging options
    parser.add_argument('-L', '--log_conf',
                        default=resource_stream(
                            'crmprtd', '/data/logging.yaml'),
                        help=('YAML file to use to override the default '
                              'logging configuration'))
    parser.add_argument('-l', '--log',
                        default=None,
                        help='Override the default log filename')
    parser.add_argument('-m', '--error_email',
                        default=None,
                        help=('Override the default e-mail address to which '
                              'the program should report critical errors'))
    parser.add_argument('--log_level',
                        choices=['DEBUG', 'INFO',
                                 'WARNING', 'ERROR', 'CRITICAL'],
                        help=('Set log level: DEBUG, INFO, WARNING, ERROR, '
                              'CRITICAL.  Note that debug output by default '
                              'goes directly to file'))

    # FTP options
    parser.add_argument('-f', '--ftp_server',
                        default='ftp.env.gov.bc.ca',
                        help=('Full hostname of Water and Air Monitoring and '
                              'Reporting\'s ftp server'))
    parser.add_argument('-F', '--ftp_dir',
                        default=('pub/outgoing/AIR/Hourly_Raw_Air_Data/'
                                 'Meteorological/'),
                        help='FTP Directory containing WAMR\'s data files')

    # File input option(s)
    parser.add_argument('-i', '--input_file',
                        default=None,
                        help='')

    # File output options
    parser.add_argument('-c', '--cache_file',
                        default=None,
                        help=('Full path of file in which to put downloaded '
                              'observations (--cache_dir will be ignored)'))
    parser.add_argument('-C', '--cache_dir',
                        default='./',
                        help=('Directory in which to put downloaded '
                              'observations (filename will be autogenerated)'))
    parser.add_argument('-e', '--error_file',
                        default=None,
                        help=('Full path of file in which to put data that '
                              'could not be added to the database '
                              '(--error_dir will be ignored)'))
    parser.add_argument('-E', '--error_dir',
                        default='./',
                        help=('Directory in which to put data that could not '
                              'be added to the database '
                              '(filename will be autogenerated)'))

    args = parser.parse_args()

    # Open up any resources that we need for the program

    # Logging
    log = setup_logging(args.log_level, args.log, args.error_email)
    log.info('Starting WAMR rtd')

    # Database connection
    try:
        engine = create_engine(args.connection_string)
        Session = sessionmaker(engine)
        sesh = Session()
    except Exception as e:
        log.critical('Error with Database connection', exc_info=True)
        sys.exit(1)

    # Output files
    if args.error_file:
        error_file = open(args.error_file, 'a')
    else:
        error_filename = 'wamr_errors_{}.csv'.format(datetime.strftime(
            datetime.now(), '%Y-%m-%dT%H-%M-%S'))
        error_file = open(os.path.join(args.cache_dir, error_filename), 'a')

    if args.input_file:
        with open(args.input_file) as f:
            rows, fieldnames = file2rows(f, log)
    else:  # FTP
        rows, fieldnames = ftp2rows(args.ftp_server, args.ftp_dir, log)

        if not args.cache_file:
            args.cache_file = 'wamr_download_{}.csv'.format(datetime.strftime(
                datetime.now(), '%Y-%m-%dT%H-%M-%S'))
        with open(args.cache_file, 'w') as cache_file:
            cache_rows(cache_file, rows, fieldnames)

    log.info('observations read into memory', extra={'num_obs': len(rows)})

    # Hand the row off to the database processings/insertion part of the script
    rows2db(sesh, rows, error_file, log, args.diag)


if __name__ == '__main__':
    main()
