# Installed libraries
import pytz
import logging
import itertools
from dateutil.parser import parse
import re
import csv

# Local
from crmprtd import Row


log = logging.getLogger(__name__)


def decoder(binary_stream):
    for line in binary_stream:
        yield line.decode('utf-8')


def csv_normalizer(network_name, fieldnames, substitutions=[], skip_rows=0):
    '''
    network_name(str): the name of the network corresponding to the CRMP
                       database
    fieldnames(list): list of strings matching the fieldnames in the csv
                      must include the following: 'time', 'val',
                      'variable_name', 'unit', 'station_id'
    substitutions(list): a list of pair/tuples of unit substitutions (src,
                         dest)

    skip_rows(int): the number of rows to skip at the beginning of the file
                    stream (default 0)

    Returns: a *function* that normalizes and file_stream
    '''
    def normalize(file_stream):
        log.info('Starting {} data normalization'.format(network_name))

        file_stream = decoder(file_stream)
        reader = csv.DictReader(
            itertools.islice(file_stream, skip_rows, None),
            fieldnames
        )
        for row in reader:
            try:
                value = float(row['val'])
            except ValueError:
                log.error('Unable to convert val to float',
                          extra={'value': row['val']})
                continue

            try:
                tz = pytz.timezone('Canada/Pacific')
                dt = parse(row['time']).replace(tzinfo=tz)
            except ValueError:
                log.error('Unable to convert date string to datetime',
                          extra={'time': row['time']})
                continue

            for src, dest in substitutions:
                if row['unit'] == src:
                    row['unit'] = re.sub(src, dest, row['unit'])

            yield Row(time=dt,
                      val=value,
                      variable_name=row['variable_name'],
                      unit=row['unit'],
                      network_name=network_name,
                      station_id=row['station_id'],
                      lat=None,
                      lon=None)
    return normalize
