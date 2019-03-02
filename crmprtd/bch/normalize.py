import logging
from itertools import tee, islice
import re

# Installed libraries
import pytz
from dateutil.parser import parse

# Local
from crmprtd import Row

log = logging.getLogger(__name__)

# Headers in a BCH file look like this:
#           **   BC HYDRO - GENERATION AND HYDROMETEOROLOGIC INFORMATION  **
#
# CLIMATE, SNOW AND/OR SURFACE WATER STATION: Aiken Lake (AKN)
#
# Note: Data are provided for information only.
#       BC Hydro does not guarantee their accuracy.
#       Data are based on automated readings which are from time to time inaccurate. # noqa
#
#       Date    Time	     TA	     PC	     SW	     SD	     YB
# (yyyy/mm/dd) (PST)	 (degC)	   (mm)	   (mm)	   (cm)	    (V)


def decoded(stream):
    for line in stream:
        yield line.decode('utf-8')


def normalize(file_stream):
    log.info('Starting BCH data normalization')

    file_stream = decoded(file_stream)

    header, rest = tee(file_stream)
    header = [row for row in islice(header, 0, 10)]
    rest = islice(rest, 10, None)

    station_id = re.search("STATION:.*\(([A-Z]{3})\)", header[2]).group(1)
    fieldnames = header[8].split()
    fieldunits = header[9].split()

    # Remove outer parens from units
    fieldunits = {name: re.search("\((.*)\)", unit).group(1) for
                  name, unit in zip(fieldnames, fieldunits)}

    tz = pytz.timezone('Canada/Pacific')
    assert fieldunits['Time'] == 'PST'

    for row in rest:

        # Skip rows that don't start with a date
        if not re.match('^[0-9]{4}(/[0-9]{2}){2} [0-9]{2}(:[0-9]{2}){2}', row):
            continue
        row = row.split()
        row = {name: val for name, val in zip(fieldnames, row)}

        try:
            date = parse("{} {}".format(row['Date'], row['Time']))
            date = date.replace(tzinfo=tz)
            del row['Date']
            del row['Time']
        except KeyError:
            log.warning('Skipping row', extra=row)
            continue
        except ValueError:
            log.error('Unable to convert date', extra={'date': date})
            continue

        for var_name, value in row.items():
            try:
                value = float(value)
            except ValueError:
                log.error('Unable to convert val to float',
                          extra={'value': value})
            yield Row(time=date,
                      val=value,
                      variable_name=var_name,
                      unit=fieldunits[var_name],
                      network_name='BCH',
                      station_id=station_id,
                      lat=None,
                      lon=None)
