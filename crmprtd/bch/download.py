import logging

from crmprtd.download import main_download_by_station

log = logging.getLogger(__name__)

main = main_download_by_station(
    'https://www.bchydro.com/info/res_hydromet/data/{}.txt',
    'crmprtd.bch',
    'BCH',
    log
)

if __name__ == "__main__":
    main()
