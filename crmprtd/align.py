"""align.py

The align module handles the Align phase of the crmprtd pipeline. This
phase consists of performing database consistency checks required to
insert the incoming data records. Do the stations already exist or do
we need to create them? Do the variables exist or can we create them?
Etc. The input is a stream tuples and the output is a stream of
pycds.Obs objects. This phase is common to all networks.
"""

import logging
from sqlalchemy import and_
from pint import UnitRegistry

# local
from pycds import Obs, History, Network, Variable, Station
from crmprtd.ec import closest_stns_within_threshold


log = logging.getLogger(__name__)
ureg = UnitRegistry()
Q_ = ureg.Quantity


def convert_unit(val, src_unit, dst_unit):
    log.debug('Converting units', extra={'src_unit': src_unit,
                                         'dst_unit': dst_unit})
    try:
        val = Q_(val, ureg.parse_expression(src_unit))  # src
        val = val.to(dst_unit).magnitude  # dest
    except Exception:
        log.error('Unable to convert units', extra={'src_unit': src_unit,
                                                    'dst_unit': dst_unit,
                                                    'exception': e})
    log.debug('Converted units')
    return val


def unit_db_check(unit_obs, unit_db, val):
    log.debug('Check if units match')
    if unit_obs != unit_db:
        try:
            val_conv = convert_unit(val, unit_obs, unit_db)
        except Exception as e:
            log.error('Unable to convert units',
                      extra={'src_unit': unit_obs,
                             'dst_unit': unit_db,
                             'exception': e})
            return None
        return val_conv
    else:
        return val


def unit_check(sesh, unit_obs, unit_db, val):
    log.debug('Check if there are units to compare')
    if not unit_obs and not unit_db:
        return None
    else:
        return unit_db_check(unit_obs, unit_db, val)


def match_station_with_active(sesh, obs_tuple, histories):
    log.debug('Search for active stations')
    for history in histories:
        hist = sesh.query(History).filter(
            and_(History.id == history.id,
                 History.sdate != None,
                 History.edate == None))

        if hist.count() == 1:
            log.debug('Matched history',
                      extra={'station_name': hist.first().station_name})
            return hist.first()

    log.warning('Could not find match',
                extra={'network_name': obs_tuple.network_name,
                       'native_id': obs_tuple.station_id})
    return None


def match_station_with_location(sesh, obs_tuple, histories):
    log.debug('Find matching station with location')
    close_stns = closest_stns_within_threshold(sesh, obs_tuple.lon,
                                               obs_tuple.lat, 800)

    if len(close_stns) == 0:
        log.debug('No station nearby')
        return create_station_and_history_entry(sesh, obs_tuple)

    for id in close_stns:
        for history in histories:
            if id == history.id:
                log.debug('Matched history',
                          extra={'station_name': history.station_name})
                return history


def match_station(sesh, obs_tuple, history):
    if obs_tuple.lat and obs_tuple.lon:
        return match_station_with_location(sesh, obs_tuple, history)
    else:
        return match_station_with_active(sesh, obs_tuple, history)


def create_station_and_history_entry(sesh, obs_tuple):
    network = sesh.query(Network).filter(
        Network.name == obs_tuple.network_name)

    network = network.first()
    stn = Station(native_id=obs_tuple.station_id, network=network)
    with sesh.begin_nested():
        sesh.add(stn)
    log.info('Created new station entry',
             extra={'native_id': stn.native_id, 'network_name': network.name})

    hist = History(station=stn,
                   lat=obs_tuple.lat,
                   lon=obs_tuple.lon)

    with sesh.begin_nested():
        sesh.add(hist)
    log.info('Created new history entry',
             extra={'history': hist.id, 'network_name': obs_tuple.network_name,
                    'lat': obs_tuple.lat, 'lon': obs_tuple.lon})
    sesh.commit()
    return hist


def get_variable(sesh, network_name, variable_name):
    log.debug('Get variable from db', extra={'var_name': variable_name,
                                             'network_name': network_name})
    variable = sesh.query(Variable).join(Network).filter(and_(
        Network.name == network_name,
        Variable.name == variable_name)).first()

    if not variable:
        log.debug('Unable to match variable')
        return None

    return variable


def get_history(sesh, obs_tuple):
    log.debug('Find history entry')
    history = sesh.query(History).join(Station).join(Network).filter(and_(
        Network.name == obs_tuple.network_name,
        Station.native_id == obs_tuple.station_id))

    if history.count() == 0:
        return create_station_and_history_entry(sesh, obs_tuple)
    elif history.count() == 1:
        return history.first()
    elif history.count() >= 2:
        return match_station(sesh, obs_tuple, history)


def is_network(sesh, network_name):
    log.debug('Check if network in db', extra={'network_name': network_name})
    network = sesh.query(Network).filter(
        Network.name == network_name)
    return network.count() != 0


def align(sesh, obs_tuple):
    log.info('Begin alignment')
    # Without these items an Obs object cannot be produced
    if not obs_tuple.network_name or not obs_tuple.time or not obs_tuple.val \
            or not obs_tuple.variable_name:
        log.warning('Observation missing critical information',
                    extra={'network_name': obs_tuple.network_name,
                           'time': obs_tuple.time,
                           'val': obs_tuple.val,
                           'variable_name': obs_tuple.variable_name})
        return None

    if not is_network(sesh, obs_tuple.network_name):
        log.warning('Network does not exist in db',
                    extra={'network_name': obs_tuple.network_name})
        return None

    history = get_history(sesh, obs_tuple)
    variable = get_variable(sesh, obs_tuple.network_name,
                            obs_tuple.variable_name)

    # Necessary attributes for Obs object
    if not history or not variable:
        log.warning('Could not retrieve necessary information from db',
                    extra={'history': history, 'variable': variable})
        return None

    datum = unit_check(sesh, obs_tuple.unit, variable.unit, obs_tuple.val)
    if not datum:
        log.warning('Unable to confirm data units',
                    extra={'unit_obs': obs_tuple.unit,
                           'unit_db': variable.unit,
                           'data': obs_tuple.val})
        return None

    log.info('Completed align')
    return Obs(history=history,
               time=obs_tuple.time,
               datum=datum,
               variable=variable)
