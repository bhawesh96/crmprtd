from lxml.etree import LxmlError
from datetime import datetime
import logging


log = logging.getLogger(__name__)
ns = {
    'om': 'http://www.opengis.net/om/1.0',
    'mpo': "http://dms.ec.gc.ca/schema/point-observation/2.1",
    'gml': "http://www.opengis.net/gml",
    'xlink': "http://www.w3.org/1999/xlink",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance"
}


def now():  # Dumb to be its own function, but this makes it mockable
    return datetime.utcnow()


def no_ns_element(name):
    '''returns the xpath string to search for and element of name "name"
       without a namespace'''
    return "*[local-name()='{}']".format(name)


def makeurl(freq='daily', province='BC', language='e', time=None):
    """Construct a URL for fetching the data file
    freq: daily|hourly
    province: 2 letter province code
    language: 'e' (english) | 'f' (french)
    time: datetime object of the time for which you want to fetch obs
    """
    if time is None:
        time = now()
    fmt = '%Y%m%d%H' if freq == 'hourly' else '%Y%m%d'
    freq = 'yesterday' if freq == 'daily' else freq
    fname = '{}_{}_{}_{}.xml'.format(
        freq, province.lower(), time.strftime(fmt), language)
    str = 'http://dd.weatheroffice.ec.gc.ca/observations/xml/'
    return str + '{}/{}/{}'.format(province.upper(), freq, fname)


class OmMember(object):
    def __init__(self, member):
        self.member = member

    def member_unit(self, v):
        '''Returns the unit of the element measuring the quantity v
           If v is not one of the elements, raises LxmlError
        '''
        try:
            xpath = (
                "./om:Observation/om:result/{}/{}"
                "[@name='{}']".format(
                    no_ns_element('elements'),
                    no_ns_element('element'),
                    v)
            )
            return self.member.xpath(xpath, namespaces=ns)[0].get('uom')
        except IndexError:
            raise LxmlError(
                "%s is not one of the mpo:elements in this om:member" % v)

    def observed_vars(self):
        '''Returns the names of all quantities specified by this member
        '''
        return [
            e.get('name') for e in self.member.xpath(
                ".//om:result/{}/{}[@name!=''][@value!='']".format(
                    no_ns_element('elements'),
                    no_ns_element('element')
                ),
                namespaces=ns)
        ]
