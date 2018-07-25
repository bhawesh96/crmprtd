#!/usr/bin/env python

# Standard module
from argparse import ArgumentParser
from pkg_resources import resource_filename
from itertools import tee

# Local
from crmprtd.ec import logging_setup
from crmprtd.ec.download import download
from crmprtd.ec.normalize import normalize
from crmprtd import iterable_to_stream


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--province', required=True,
                        help='2 letter province code')
    parser.add_argument('-g', '--language', default='e',
                        choices=['e', 'f'],
                        help="'e' (english) | 'f' (french)")
    parser.add_argument('-F', '--frequency', required=True,
                        choices=['daily', 'hourly'],
                        help='daily|hourly')
    parser.add_argument('-t', '--time',
                        help=("Alternate *UTC* time to use for downloading "
                              "(interpreted using "
                              "format=YYYY/MM/DD HH:MM:SS)"))
    parser.add_argument('-T', '--threshold', default=1000,
                        help=('Distance threshold to use when matching '
                              'stations.  Stations are considered a match if '
                              'they have the same id, name, and are within '
                              'this threshold'))
    parser = common_script_arguments(parser)
    args = parser.parse_args()
    log = logging_setup(args.log_conf, args.log,
                        args.error_email, args.log_level)

    download_iter = download(args)

    if args.cache_file:
        download_iter, cache_iter = tee(download_iter)
        with open(args.cache_file, 'wb') as f:
            stream = iterable_to_stream(cache_iter)
            f.write(stream.read())

    stream = iterable_to_stream(download_iter)
    for line in normalize(stream):
        print(line)
