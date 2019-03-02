import logging
from argparse import ArgumentParser

from crmprtd import logging_args, setup_logging
from crmprtd.download import https_download

log = logging.getLogger(__name__)


def download(url_template, station):
    log.info("Starting BCH Download")
    url = url_template.format(station.lower())
    scheme, _ = url.split(':', 1)
    https_download(url, scheme, log)


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-u', '--url_template',
        default='https://www.bchydro.com/info/res_hydromet/data/{}.txt',
        help='URL with a single parameter for station ID'
    )
    parser.add_argument(
        '-s', '--station_id', required=True,
        help="Station ID for which to download data")
    parser = logging_args(parser)
    args = parser.parse_args()

    setup_logging(args.log_conf, args.log_filename, args.error_email,
                  args.log_level, 'crmprtd.bch')

    download(args.url_template, args.station_id)


if __name__ == "__main__":
    main()
