'''Downloads met data from the BC Capital Regional District (CRD)

The CRD operates a network of automated weather and hydrology stations
in the Greater Victoria Water Supply Area. The default data request
returns all data for the past 28 days. Theorettically, any date range
which does not exceed 28 days, can also be requested and downloaded.

It is recommended to run this script once per one or two weeks to
collect all available data (plus, presumably some duplicate data from
the last run). If the script is run less than once per month, you will
miss data.

Downloading doesn't require authentication, per se, but each user of
CRD's data has a unique and pseudo-secret client ID. This client id
can be supplied as the username in the authentication file or via the
--username paramenter. No password is necessary.
'''

import sys
from argparse import ArgumentParser
import logging
from datetime import timedelta

import dateutil.parser

import crmprtd.download
from crmprtd import logging_args, setup_logging, common_auth_arguments

log = logging.getLogger(__name__)


def xnor(sdate, edate):  # pragma: no cover
    return bool(sdate) == bool(edate)


def verify_dates(sdate, edate):
    assert xnor(sdate, edate), \
        "Date range must include both ends of the range or neither"

    if sdate and edate:
        timediff = edate - sdate
        assert timediff > timedelta(0) and timediff <= timedelta(days=28), \
            "Date range cannot be negative and must be no more than 28 days"


def make_url(client_id, sdate=None, edate=None):
    date_fmt = "%Y%m%d%H%M"

    time_range = ""
    if sdate and edate:
        time_range = f"{sdate.strftime(date_fmt)}-{edate.strftime(date_fmt)}"

    return (f"https://webservices.crd.bc.ca/weatherdata/{client_id}/"
            f"{time_range}")


def download(client_id, start_date, end_date):  # pragma: no cover
    url = make_url(client_id, start_date, end_date)
    try:
        crmprtd.download.https_download(url, 'https', log)

    except IOError:
        log.exception("Unable to download or open JSON data")
        sys.exit(1)


def main():  # pragma: no cover
    desc = globals()['__doc__']
    parser = ArgumentParser(description=desc)
    parser = logging_args(parser)
    parser = common_auth_arguments(parser)
    parser.add_argument('-S', '--start_time',
                        type=dateutil.parser.parse,
                        help=("Optional start time to use for downloading "
                              "(interpreted with dateutil.parser.parse)."
                              "Defaults to one day prior to now"))
    parser.add_argument('-E', '--end_time',
                        type=dateutil.parser.parse,
                        help=("Optional end time to use for downloading "
                              "(interpreted with dateutil.parser.parse)."
                              "Defaults to now."))
    args = parser.parse_args()

    setup_logging(args.log_conf, args.log_filename, args.error_email,
                  args.log_level, 'crmprtd.crd')

    verify_dates(args.start_time, args.end_time)

    auth_yaml = open(args.auth_fname, 'r').read() if args.auth_fname else None
    auth = crmprtd.download.extract_auth(args.username, None,
                                         auth_yaml, args.auth_key)

    download(auth['u'], args.start_time, args.end_time)


if __name__ == "__main__":
    main()
