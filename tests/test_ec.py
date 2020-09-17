from pkg_resources import resource_filename
from datetime import datetime
from lxml.etree import LxmlError

from lxml.etree import fromstring, parse, XSLT
import pytest

from crmprtd.ec import makeurl, ns, OmMember


@pytest.mark.parametrize(('label', 'args', 'expected'), [
    ('daily-BC-EN',
     {'freq': 'daily',
      'province': 'BC',
      'language': 'e',
      'time': datetime(2016, 1, 15, 21)},
     ('http://dd.weatheroffice.ec.gc.ca/observations/xml/BC/yesterday/'
      'yesterday_bc_20160115_e.xml')
     ), ('hourly-BC-EN',
         {'freq': 'hourly',
          'province': 'BC',
          'language': 'e',
          'time': datetime(2016, 1, 15, 21)},
         ('http://dd.weatheroffice.ec.gc.ca/observations/xml/BC/hourly/'
          'hourly_bc_2016011521_e.xml')
         ), ('nofreq-BC-EN',
             {'province': 'BC',
              'language': 'e',
              'time': datetime(2016, 1, 15, 21)},
             ('http://dd.weatheroffice.ec.gc.ca/observations/xml/BC/yesterday/'
              'yesterday_bc_20160115_e.xml')
             ), ('hourly-noprov-EN',
                 {'freq': 'hourly',
                  'language': 'e',
                  'time': datetime(2016, 1, 15, 21)},
                 ('http://dd.weatheroffice.ec.gc.ca/observations/xml/BC/'
                  'hourly/hourly_bc_2016011521_e.xml')
                 ), ('hourly-BC-nolang',
                     {'freq': 'hourly',
                      'province': 'BC',
                      'time': datetime(2016, 1, 15, 21)},
                     ('http://dd.weatheroffice.ec.gc.ca/observations/xml/BC/'
                      'hourly/hourly_bc_2016011521_e.xml')
                     )
])
def test_makeurl(label, args, expected):
    assert makeurl(**args) == expected


def test_makeurl_no_time_hourly(mocker):
    t = datetime(2016, 1, 15, 21)
    fmt = '%Y%m%d%H'

    with mocker.patch('crmprtd.ec.now', return_value=t):
        url = makeurl(freq='hourly')

    assert url == ('http://dd.weatheroffice.ec.gc.ca/observations/xml/BC/'
                   'hourly/hourly_bc_{}_e.xml').format(t.strftime(fmt))


def test_makeurl_no_time_daily(mocker):
    t = datetime(2016, 1, 15, 21)
    fmt = '%Y%m%d'

    with mocker.patch('crmprtd.ec.now', return_value=t):
        url = makeurl()

    assert url == ('http://dd.weatheroffice.ec.gc.ca/observations/xml/BC/'
                   'yesterday/yesterday_bc_{}_e.xml').format(t.strftime(fmt))


@pytest.mark.parametrize(('x', 'expected'), [
    (fromstring(b'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<om:ObservationCollection xmlns="http://dms.ec.gc.ca/schema/point-observation/2.1" xmlns:gml="http://www.opengis.net/gml" xmlns:om="http://www.opengis.net/om/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <om:member>
    <om:Observation>
      <om:result>
        <elements>
          <element name="tendency_amount" uom="kPa" value="0.12"></element>
          <element name="tendency_characteristic" uom="code" value="falling"></element>
        </elements>
      </om:result>
    </om:Observation>
  </om:member>
</om:ObservationCollection>'''), '-0.12'), # noqa
    (fromstring(b'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<om:ObservationCollection xmlns="http://dms.ec.gc.ca/schema/point-observation/2.1" xmlns:gml="http://www.opengis.net/gml" xmlns:om="http://www.opengis.net/om/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <om:member>
    <om:Observation>
      <om:result>
        <elements>
          <element name="tendency_amount" uom="kPa" value="0.12"></element>
          <element name="tendency_characteristic" uom="code" value="rising"></element>
        </elements>
      </om:result>
    </om:Observation>
  </om:member>
</om:ObservationCollection>'''), '0.12') # noqa
])
def test_xsl_transform_tendency_amount(x, expected):
    # Apply the transform
    xsl = resource_filename('crmprtd', 'data/ec_xform.xsl')
    transform = XSLT(parse(xsl))
    et = transform(x)

    # Locate changed element
    e = et.xpath(".//mpo:element", namespaces=ns)

    assert len(e) == 1
    assert e[0].attrib['value'] == expected


@pytest.mark.parametrize(('x', 'expected'), [
    (fromstring(b'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<om:ObservationCollection xmlns="http://dms.ec.gc.ca/schema/point-observation/2.1" xmlns:gml="http://www.opengis.net/gml" xmlns:om="http://www.opengis.net/om/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <om:member>
    <om:Observation>
      <om:result>
        <elements>
          <element name="wind_direction" uom="code" value="W"/>
        </elements>
      </om:result>
    </om:Observation>
  </om:member>
</om:ObservationCollection>'''), '270'), # noqa
    (fromstring(b'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<om:ObservationCollection xmlns="http://dms.ec.gc.ca/schema/point-observation/2.1" xmlns:gml="http://www.opengis.net/gml" xmlns:om="http://www.opengis.net/om/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <om:member>
    <om:Observation>
      <om:result>
        <elements>
          <element name="wind_direction" uom="code" value="SE"/>
        </elements>
      </om:result>
    </om:Observation>
  </om:member>
</om:ObservationCollection>'''), '135') # noqa
])
def test_xsl_transform_wind_direction(x, expected):
    # Apply the transform
    xsl = resource_filename('crmprtd', 'data/ec_xform.xsl')
    transform = XSLT(parse(xsl))
    et = transform(x)

    # Locate changed element
    e = et.xpath(".//mpo:element", namespaces=ns)

    assert e[0].attrib['value'] == expected


@pytest.mark.parametrize(('x', 'expected'), [
    (fromstring(b'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<om:ObservationCollection xmlns="http://dms.ec.gc.ca/schema/point-observation/2.1" xmlns:gml="http://www.opengis.net/gml" xmlns:om="http://www.opengis.net/om/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <om:member>
    <om:Observation>
      <om:result>
        <elements>
          <element name="total_cloud_cover" uom="code" value="8"/>
        </elements>
      </om:result>
    </om:Observation>
  </om:member>
</om:ObservationCollection>'''), '8') # noqa
])
def test_xsl_transform_cloud_cover(x, expected):
    # Apply the transform
    xsl = resource_filename('crmprtd', 'data/ec_xform.xsl')
    transform = XSLT(parse(xsl))
    et = transform(x)

    # Locate changed element
    e = et.xpath(".//mpo:element", namespaces=ns)

    assert e[0].attrib['uom'] == 'percent'
    assert e[0].attrib['value'] == expected


def test_OmMember_index_error_handle(ec_session):
    et = fromstring(b'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<om:member xmlns="http://dms.ec.gc.ca/schema/point-observation/2.1" xmlns:gml="http://www.opengis.net/gml" xmlns:om="http://www.opengis.net/om/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <om:Observation>
    <om:metadata>
      <set>
        <general>
          <author build="build.4063" name="MSC-DMS-PG-WXO-Summary" version="2.4"/>
          <dataset name="mscobservation/atmospheric/surface_weather/wxo_dd_hour_summary-1.0-ascii/"/>
          <phase name="product-wxo_xml-1.0/"/>
          <id xlink:href="/data/msc/observation/atmospheric/surface_weather/wxo_dd_hour_summary-1.0-ascii/product-wxo_xml-1.0/20160528024500000/bc/intermediate/en"/>
          <parent xlink:href="/data/msc/observation/atmospheric/surface_weather/wxo_dd_hour_summary-1.0-ascii/product-wxo_xml-1.0/20160528024500000/bc/intermediate/en"/>
        </general>
        <identification-elements>
          <element name="station_name" uom="unitless" value="Stewart Airport"/>
          <element name="latitude" uom="degree" value="55.933333"/>
          <element name="longitude" uom="degree" value="-129.983333"/>
          <element name="transport_canada_id" uom="unitless" value="ZST"/>
          <element name="observation_date_utc" uom="unitless" value="2016-05-28T02:00:00.000Z"/>
          <element name="observation_date_local_time" uom="unitless" value="2016-05-27T19:00:00.000 PDT"/>
          <element name="climate_station_number" uom="unitless" value="1067741"/>
          <element name="wmo_station_number" uom="unitless" value=""/>
        </identification-elements>
      </set>
    </om:metadata>
    <om:samplingTime>
      <gml:TimeInstant>
        <gml:timePosition>2016-05-28T02:00:00.000Z</gml:timePosition>
      </gml:TimeInstant>
    </om:samplingTime>
    <om:resultTime>
      <gml:TimeInstant>
        <gml:timePosition>2016-05-28T02:00:00.000Z</gml:timePosition>
      </gml:TimeInstant>
    </om:resultTime>
    <om:procedure xlink:href="msc/observation/atmospheric/surface_weather/wxo_dd_hour_summary-1.0-ascii/product-wxo_xml-1.0/20160528024500000/bc/intermediate/en"/>
    <om:observedProperty gml:remoteSchema="/schema/point-observation/2.0.xsd"/>
    <om:featureOfInterest>
      <gml:FeatureCollection>
        <gml:location>
          <gml:Point>
            <gml:pos>55.933333 -129.983333</gml:pos>
          </gml:Point>
        </gml:location>
      </gml:FeatureCollection>
    </om:featureOfInterest>
    <om:result>
      <elements>
        <element name="present_weather" uom="code" value=""/>
        <element name="mean_sea_level" uom="kPa" value="101.4"/>
        <element name="tendency_amount" uom="kPa" value="-0.03"/>
        <element name="tendency_characteristic" uom="code" value=""/>
        <element name="horizontal_visibility" uom="km" value=""/>
        <element name="air_temperature" uom="Celsius" value="13.8"/>
        <element name="dew_point" uom="Celsius" value="7.4"/>
        <element name="relative_humidity" uom="percent" value="65"/>
        <element name="wind_speed" uom="km/h" value="16"/>
        <element name="wind_direction" uom="code" value="SSW"/>
        <element name="wind_gust_speed" uom="km/h" value="29"/>
        <element name="total_cloud_cover" uom="code" value=""/>
        <element name="wind_chill" uom="unitless" value=""/>
        <element name="humidex" uom="unitless" value=""/>
      </elements>
    </om:result>
  </om:Observation>
</om:member>''') # noqa
    o = OmMember(et)
    with pytest.raises(LxmlError):
        o.member_unit('doese_not_exist')
