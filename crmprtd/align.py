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

# local
from pycds import Obs, History, Network, Variable, Station
import sys


log = logging.getLogger(__name__)


def create_station_and_history_entry(sesh, obs_tuple, network_id):
    stn = Station(native_id=obs_tuple.station_id, network_id=network_id)
    with sesh.begin_nested():
        sesh.add(stn)
    log.info('Created new station_id', extra={'stationd_id': stn.id})

    # FIXME: Need a way to have station name attribute
    lat = None
    lon = None

    if obs_tuple.lat and obs_tuple.lon:
        hist = History(station=stn,
                       lat=obs_tuple.lat,
                       lon=obs_tuple.lon)
    else:
        hist = History(station=stn)

    with sesh.begin_nested():
        sesh.add(hist)
    log.info('Created new history entry', extra={'hid': hist.id})
    sesh.commit()
    return hist.id


def align(sesh, obs_tuple):
    # place (network name, station id)
    log.info('Begin alignment on row')

    log.info('Check for network name')
    q = sesh.query(Network).filter(Network.name == obs_tuple.network_name)

    if q.count() == 0:
        log.error('Observation cannot be used without a valid network name', extra={'network_name': obs_tuple.network_name})
        return
    log.info('Found matching network name', extra={'network_name': q.first()})

    log.info('Check if station id in history')
    q = sesh.query(History.id).join(Station).join(Network).filter(and_(Network.name == obs_tuple.network_name, Station.native_id == obs_tuple.station_id))

    if q.count() == 0:
        log.info('No station found, creating new station', extra={'native_id': obs_tuple.station_id})
        network_id, = sesh.query(Network.id).filter(Network.name == obs_tuple.network_name).first()
        print('network_id {}'.format(network_id))
        hid = create_station_and_history_entry(sesh, obs_tuple, network_id)
        print('new hid: {}'.format(hid))
    # elif q.count() == 1:
    #     log.info('Matched station', extra={'history_id': q.first()})
    #     hid = q.first()
    #
    # elif q.count() >= 2:    # FIXME: This needs to be handled in some way
    #     log.info('Found multiple stations', extra={'num_matches': q.count(), 'hids': q.all()})

    # # thing (val, variable name, unit)
    # log.info('Check time')
    # if obs_tuple.time is None:
    #     log.error('Observation cannot be used without time')
    #     return
    # log.info('Observation has time')
    # time = obs_tuple.time
    #
    # log.info('Check data')
    # if obs_tuple.val is None:
    #     log.error('Observation cannot be used without value')
    #     return
    # log.info('Observation has value')
    # val = obs_tuple.val
    #
    # log.info('Check if variable name exists in database')
    # q = sesh.query(Variable).join(Network).filter(and_(Network.name == obs_tuple.network_name, Variable.name == obs_tuple.variable_name))
    #
    # if q.count() == 1:
    #     log.info('Observation variable matches', extra={'var_name': obs_tuple.variable_name})
    #     variable = q.first()
    # else:
    #     log.warning('No matching varible found', extra={'var_name': obs_tuple.variable_name})
    #     return

    # log.info('Check unit')
    # if obs_tuple.unit is None:
    #     log.info('No unit, converting')
    #     # q = sesh.query(Variable.unit).join(Network).filter(Network.name == obs_tuple.network_name).filter(Variable.name == obs_tuple.variable_name)
    # log.info('Observation has unit')
    # unit = obs_tuple.unit


    # q = sesh.query(Variable.unit).join(Network).filter(Network.name == obs_tuple.network_name).filter(Variable.name == obs_tuple.variable_name)
    # if q.first() != unit:
    #     log.info('Unit does not match, converting')
    #     # converting
    #
    # log.info('Units match')

    # check obs before creating object
    # if time and variable and hid:
    #     log.info('Observation accepted')
    #     # yield Obs(time=time, variable=variable, history=hid, datum=obs_tuple.val)
    # else:
    #     log.info('Observation rejected')
