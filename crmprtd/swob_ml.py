# Standard module
import logging

# Installed libraries
from lxml.etree import parse, XSLT
from dateutil.parser import parse as dateparse

# Local
from pkg_resources import resource_stream
from crmprtd import Row, iterable_to_stream
from crmprtd.ec import ns, OmMember


log = logging.getLogger(__name__)


def parse_xml(iterable, xsl=None):
    if xsl is None:
        xsl = resource_stream('crmprtd', 'data/ec_xform.xsl')

    # Parse and transform the xml
    file = iterable_to_stream(iterable)
    et = parse(file)
    transform = XSLT(parse(xsl))
    return transform(et)


def normalize(file_stream, network_name,
              station_id_attr='climate_station_number'):
    et = parse_xml(file_stream)

    members = et.xpath('//om:member', namespaces=ns)
    log.info('Starting %s data normalization', network_name)

    for member in members:
        om = OmMember(member)
        vars = om.observed_vars()

        for var in vars:
            try:
                ele = om.member.xpath(
                        "./om:Observation/om:result//mpo:element[@name='%s']" %
                        var, namespaces=ns)[0]
                val = float(ele.get('value'))
            # This shouldn't every be empty based on our xpath for selecting
            # elements, however I think that it _could_ be non-numeric and
            # still be valid XML
            except ValueError as e:
                log.error('Unable to convert value',
                          extra={'val': (ele.get('value'))})
                continue

            try:
                log.debug("Finding Station attributes")
                station_id = member.xpath(
                    ".//mpo:identification-elements/mpo:element[@name='{}']"
                    .format(station_id_attr), namespaces=ns)[0].get('value')
                lat, lon = map(float, member.xpath(
                    './/gml:pos', namespaces=ns)[0].text.split())
                obs_time = member.xpath(
                    './om:Observation/om:samplingTime//gml:timePosition',
                    namespaces=ns)[0].text
                log.debug('Found station info',
                          extra={'station_id': station_id,
                                 'lon': lon,
                                 'lat': lat,
                                 'time': obs_time})
            # An IndexError here means that the member has no station_name or
            # climate_station_number (or identification-elements), lat/lon,
            # or obs_time in which case we don't need to process this item
            except IndexError:
                log.warning("This member does not appear to be a station")
                continue

            try:
                date = dateparse(obs_time)
            except ValueError as e:
                log.error('Unable to parse date', extra={'exception': e})
                continue

            yield Row(time=date,
                      val=val,
                      variable_name=var,
                      unit=om.member_unit(var),
                      network_name=network_name,
                      station_id=station_id,
                      lat=lat,
                      lon=lon)
