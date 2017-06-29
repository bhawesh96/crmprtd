import logging
from datetime import datetime
import csv
from pkg_resources import resource_stream

import pytz
from dateutil.parser import parse
import yaml

from crmprtd.db import mass_insert_obs
from pycds import Network, Station, History, Obs, Variable

tz = pytz.timezone('Canada/Pacific')


def create_station_mapping(sesh, rows):
    '''Create a names -> history object map for the set of stations that are
       contained in the rows
    '''
    # Each row (observation) is attributed with a station
    # individually, so start by creating a set of unique stations in
    # the file. Minimize round-trips to the database.
    stn_ids = {row['EMS_ID'] for row in rows}

    def lookup_stn(ems_id):
        q = sesh.query(History).join(Station).join(Network)\
                .filter(Station.native_id == ems_id)
        # FIXME: Handle multiple history_ids and failed searches
        return q.first()
    mapping = [(ems_id, lookup_stn(ems_id)) for ems_id in stn_ids]

    # Filter out EMS_IDs for which we have no station metadata
    return {ems_id: hist for ems_id, hist in mapping if hist}


def create_variable_mapping(sesh, rows):
    '''Create a names -> history object map for the set of observations that are
       contained in the rows
    '''
    var_names = {row['PARAMETER'] for row in rows}

    def lookup_var(v):
        q = sesh.query(Variable).join(Network)\
                .filter(Network.name == 'ENV-AQN').filter(Variable.name == v)
        return q.first()
    mapping = [(var_name, lookup_var(var_name)) for var_name in var_names]

    return {var_name: var_ for var_name, var_ in mapping if var_}


def process_obs(sesh, row, log=None, histories={}, variables={}):
    """Take a list of dictionary based observations and return a list of
    pycds.Obs objects

    data - list of dictionaries given by csv.DictReader with keys:
    DATE_PST,EMS_ID,STATION_NAME,PARAMETER,AIR_PARAMETER,INSTRUMENT,
    RAW_VALUE,UNIT,STATUS,AIRCODESTATUS,STATUS_DESCRIPTION,
    REPORTED_VALUE
    """
    if not log:
        log = logging.getLogger(__name__)

    if row['EMS_ID'] not in histories:
        raise Exception('Could not find station {EMS_ID}/{STATION_NAME}'
                        ' in the db'.format(**row))
    else:
        hist = histories[row['EMS_ID']]

    if row['PARAMETER'] not in variables:
        raise Exception('Could not find variable {} in the db'
                        .format(row['PARAMETER']))
    else:
        var = variables[row['PARAMETER']]

    # Parse the date
    d = parse(row['DATE_PST']).replace(tzinfo=tz)

    value = float(row['REPORTED_VALUE'])

    # Create and return the object
    return Obs(time=d, variable=var, history=hist, datum=value)


class DataLogger(object):
    def __init__(self, log=None):
        self.bad_rows = []
        self.bad_obs = []
        if not log:
            self.log = logging.getLogger(__name__)

    def add_row(self, data=None, reason=None):
        # handle single observations
        if type(data) == dict:
            data['reason'] = reason
            self.bad_rows.append(data)

    def archive(self, out_file):
        """
        Archive the unsuccessfull additions in a manner that allows
        easy re-insertion attempts.
        """
        order = 'DATE_PST,EMS_ID,STATION_NAME,PARAMETER,AIR_PARAMETER,'\
                    'INSTRUMENT,RAW_VALUE,UNIT,STATUS,AIRCODESTATUS,'\
                    'STATUS_DESCRIPTION,REPORTED_VALUE'.split(',')
        w = csv.DictWriter(out_file, fieldnames=order)
        w.writeheader()
        w.writerows(self.data)

        return

    @property
    def data(self):
        import itertools
        for row in itertools.chain(self.bad_rows, self.bad_obs):
            yield row


def setup_logging(level, filename=None, email=None):
    '''Read in the logging configuration and return a logger object
    '''
    log_conf = yaml.load(resource_stream('crmprtd', '/data/logging.yaml'))
    if filename:
        log_conf['handlers']['file']['filename'] = filename
    else:
        filename = log_conf['handlers']['file']['filename']
    if email:
        log_conf['handlers']['mail']['toaddrs'] = email
    logging.config.dictConfig(log_conf)
    log = logging.getLogger('crmprtd.wamr')
    if level:
        log.setLevel(level)

    return log


def rows2db(sesh, rows, error_file, log, diagnostic=False):
    '''
    Args:
        sesh (sqlalchemy.Session): The first parameter.
        rows ():
        error_file ():
        log (): The second parameter.

    '''
    dl = DataLogger(log)

    sesh.begin_nested()

    try:
        log.debug('Processing observations')
        histories = create_station_mapping(sesh, rows)
        variables = create_variable_mapping(sesh, rows)

        obs = []
        for row in rows:
            try:
                obs.append(process_obs(sesh, row, log, histories, variables))
            except Exception as e:
                dl.add_row(row, e.args[0]) # FIXME: no args here

        log.info("Starting a mass insertion of %d obs", len(obs))
        n_insertions = mass_insert_obs(sesh, obs, log)
        log.info("Inserted %d obs", n_insertions)

        if diagnostic: 
            log.info('Diagnostic mode, rolling back all transactions')
            sesh.rollback()
        else:
            log.info('Commiting the sesh')
            sesh.commit()

    except Exception as e: # FIXME: sqlalchemy.exc.OperationalError? (cannot connect to db) sqlalchemy.exc.InternalError (read-only transaction)
        dl.add_row(rows, 'preproc error')
        sesh.rollback()
        data_archive = dl.archive(error_file)
        log.critical('''Error data preprocessing.
                            See logfile at {l}
                            Data saved at {d}
                            '''.format(l=args.log, d=data_archive), exc_info=True) # FIXME: no args here
        sys.exit(1)
    finally:
        sesh.commit()
        sesh.close()

    #dl.archive(error_file)


def file2rows(file_, log):
    try:
        reader = csv.DictReader(file_)
    except csv.Error as e:
        log.critical('Unable to load data from local file', exc_info=True)
        sys.exit(1)

    return [row for row in reader], reader.fieldnames


def ftp2rows(host, path, log):
    log.info('Fetching file from FTP')
    log.info('Listing {}/{}'.format(host, path))

    try:
        ftpreader = FTPReader(host, None,
                              None, path, log)
        log.info('Opened a connection to {}'.format(host))
        reader = ftpreader.csv_reader(log)
        log.info('instantiated the reader and downloaded all of the data')
    except ftplib.all_errors as e:
        log.critical('Unable to load data from ftp source', exc_info=True)
        sys.exit(1)

    return [row for row in reader], reader.fieldnames