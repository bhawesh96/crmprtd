from pkg_resources import resource_filename
from datetime import datetime

from lxml.etree import fromstring, parse, XSLT
import pytest
import pytz

from pycds import Obs, Station, History
from crmprtd.moti import process, url_generator, slice_timesteps, check_history

bctz = pytz.timezone('America/Vancouver')


def test_check_history(test_session):
    stn_id = '666'
    check_history(stn_id, test_session)
    q = test_session.query(History)
    assert q.count() == 9


def test_data(test_session, moti_sawr7110_xml):
    c1 = test_session.query(Obs).count()

    process(test_session, moti_sawr7110_xml)
    test_session.commit()
    q = test_session.query(Obs)
    obs = q.all()
    assert len(obs) - c1 == 2


def test_catch_duplicates(test_session, moti_sawr7110_xml):
    """Original test of duplicates that didn't check what actually got
    committed to the database."""
    rv = process(test_session, moti_sawr7110_xml)
    assert rv == {'failures': 0, 'successes': 2, 'skips': 2}
    rv = process(test_session, moti_sawr7110_xml)
    assert rv == {'failures': 0, 'successes': 0, 'skips': 4}


def test_duplicates(test_session, moti_sawr7110_xml_2a, moti_sawr7110_xml_2b):
    """Test that duplicates are skipped, and that skipping them does not
    cause preceding or following non-duplicate inserts to be abandoned."""

    # Insert initial observation set, no duplicates
    rv = process(test_session, moti_sawr7110_xml_2a)
    assert rv == {'failures': 0, 'successes': 1, 'skips': 0}

    # Insert next observation set, with duplicate of first bracketed by
    # non-duplicates before and after
    rv = process(test_session, moti_sawr7110_xml_2b)
    assert rv == {'failures': 0, 'successes': 2, 'skips': 1}

    # Check that all non-duplicates actually got commited
    # to the database and not rolled back due to the duplicate
    test_session.commit()
    q = (
        test_session.query(Obs)
        .join(History)
        .join(Station)
        .filter(Station.native_id == '11091')
    )
    print('Commited observations')
    for obs in q.all():
        print(obs.time)
    assert q.count() == 3


xml = {'no_obs': b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091</id>
      </origin>
    </observation-series>
  </data>
</cmml>''', # noqa
       'no_valid_time': b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <data>
    <observation-series>
      <origin type="station">
	<id type="client">11091</id>
      </origin>
      <observation>
	<pressure index="1" type="atmospheric">
	  <value units="mb">964
	  </value>
	</pressure>
      </observation>
    </observation-series>
  </data>
       </cmml>''', # noqa
       'bad_value': b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <data>
    <observation-series>
      <origin type="station">
	    <id type="client">11091</id>
      </origin>
      <observation>
        <pressure index="1" type="atmospheric">
	      <value units="mb">Not Convertible to a number</value>
        </pressure>
      </observation>
    </observation-series>
  </data>
       </cmml>''', # noqa
       'no_value': b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <data>
    <observation-series>
      <origin type="station">
	    <id type="client">11091</id>
      </origin>
      <observation>
        <pressure index="1" type="atmospheric">
        </pressure>
      </observation>
    </observation-series>
  </data>
       </cmml>''', # noqa
       'no_units': b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <data>
    <observation-series>
      <origin type="station">
	    <id type="client">11091</id>
      </origin>
      <observation>
        <pressure index="1" type="atmospheric">
	      <value>2.0</value>
        </pressure>
      </observation>
    </observation-series>
  </data>
 </cmml>'''} # noqa


@pytest.mark.parametrize(('xml'), xml.values(), ids=list(xml.keys()))
def test_broken_obs(test_session, xml):
    xml = fromstring(xml)
    n_obs_before = test_session.query(Obs).count()
    process(test_session, xml)
    n_obs_after = test_session.query(Obs).count()
    assert n_obs_before == n_obs_after


def test_missing_client_id(test_session):
    et = fromstring(b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
  </head>
  <data>
    <observation-series>
      <origin type="station" />
    </observation-series>
  </data>
</cmml>''') # noqa
    e = pytest.raises(Exception, process, test_session, et)
    assert ("Could not detect the station id: xpath search "
            "'//observation-series/origin/id[@type='client']' "
            "return no results") in str(e)


def test_url_generator():
    urls = url_generator('1', bctz.localize(
        datetime(2010, 1, 1)), bctz.localize(datetime(2010, 3, 1)))
    actual = [url for url in urls]
    expected = [('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-01-01/00&to=2010-01-07/00'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-01-07/01&to=2010-01-13/01'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-01-13/02&to=2010-01-19/02'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-01-19/03&to=2010-01-25/03'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-01-25/04&to=2010-01-31/04'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-01-31/05&to=2010-02-06/05'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-02-06/06&to=2010-02-12/06'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-02-12/07&to=2010-02-18/07'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-02-18/08&to=2010-02-24/08'),
                ('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-02-24/09&to=2010-03-01/00')]
    assert actual == expected


def test_url_generator_truncates():
    urls = url_generator('1', bctz.localize(
        datetime(2010, 1, 1, 1, 1)),
        bctz.localize(datetime(2010, 1, 1, 23, 55)))
    actual = [url for url in urls]
    expected = [('https://prdoas2.apps.th.gov.bc.ca/saw-data/sawr7110?request='
                 'historic&station=1&from=2010-01-01/01&to=2010-01-01/23')]
    assert actual == expected


def test_url_generator_backwards_dates():
    urls = url_generator('1', bctz.localize(
        datetime(2012, 1, 1)), bctz.localize(datetime(2010, 1, 1)))
    actual = [url for url in urls]
    expected = []
    assert actual == expected


def test_var_transforms(moti_sawr7110_xml):
    xsl = resource_filename('crmprtd', 'data/moti.xsl')
    transform = XSLT(parse(xsl))
    et = transform(moti_sawr7110_xml)
    # Make sure that we can find some of the things to which we transformed
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "temperature[@type='CURRENT_AIR_TEMPERATURE1']"))
    assert et.xpath("/cmml/data/observation-series/observation/"
                    "temperature/value[@units='celsius']")
    assert et.xpath("/cmml/data/observation-series/observation/"
                    "pressure[@type='ATMOSPHERIC_PRESSURE']")


def test_var_transforms_all(moti_sawr7100_large):
    xsl = resource_filename('crmprtd', 'data/moti.xsl')
    transform = XSLT(parse(xsl))
    et = transform(moti_sawr7100_large)
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "pressure[@type='ATMOSPHERIC_PRESSURE']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "wind[@type='MEASURED_WIND_SPEED1']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "wind[@type='MEASURED_WIND_DIRECTION1']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "wind[@type='WIND_DIRECTION_STD_DEVIATION1']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "temperature[@type='CURRENT_AIR_TEMPERATURE1']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "temperature[@type='DEW_POINT']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "precipitation[@type='HOURLY_PRECIPITATION']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "humidity[@type='RELATIVE_HUMIDITY1']"))
    assert et.xpath(("/cmml/data/observation-series/observation/"
                     "snow[@type='HEIGHT_OF_SNOW']"))


def test_timestep_slices():
    d1 = bctz.localize(datetime(2010, 1, 1))
    d2 = bctz.localize(datetime(2010, 1, 15))
    results = [x for x in slice_timesteps(d1, d2)]
    expected = [(bctz.localize(datetime(2010, 1, 1)),
                bctz.localize(datetime(2010, 1, 8))),
                (bctz.localize(datetime(2010, 1, 8, 1)),
                bctz.localize(datetime(2010, 1, 15)))]
    assert results == expected


def test_skipped_vars(test_session):
    xml = fromstring(b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091</id>
        <id type="network">BC_MoT_11091</id>
      </origin>
      <observation valid-time="2011-04-07T01:00:00-07:00">
        <pavement index="1" type="temperature">
          <qualifier units="unitless" type="lane-number">1</qualifier>
          <value units="degC">1.7</value>
        </pavement>
        <pavement index="2" type="temperature">
          <qualifier units="unitless" type="lane-number">1</qualifier>
          <value units="degC">2.6</value>
        </pavement>
        <pavement index="1" type="freeze-point">
          <qualifier units="unitless" type="lane-number">1</qualifier>
          <value units="degC">-21.1</value>
        </pavement>
        <pavement index="1" type="surface-status">
          <qualifier type="categorical-table" units="string">BC-MoT-pavement-surface-condition-code</qualifier>
          <value units="code">24</value>
        </pavement>
        <subsurface index="1" type="temperature">
          <qualifier units="unitless" type="lane-number">1</qualifier>
          <qualifier units="cm" type="sensor-depth">25</qualifier>
          <value units="degC">6.7</value>
        </subsurface>
        <extension index="2">
          <qualifier units="string" type="name">bcmot-precipitation-detection-ratio</qualifier>
          <value units="unitless">.079</value>
        </extension>
      </observation>
    </observation-series>
  </data>
</cmml>''') # noqa
    n_obs_before = test_session.query(Obs).count()
    r = process(test_session, xml)
    assert r == {'failures': 0, 'successes': 0, 'skips': 6}

    n_obs_after = test_session.query(Obs).count()
    assert n_obs_before == n_obs_after

    # TODO: need to actually check no warnings logged for var lookups


def test_unknown_var(test_session, caplog):
    xml = fromstring(b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091</id>
        <id type="network">BC_MoT_11091</id>
      </origin>
      <observation valid-time="2011-04-07T01:00:00-07:00">
        <temperature index="1" type="tree-temperature">
          <value units="degC">-.813</value>
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>''') # noqa
    n_obs_before = test_session.query(Obs).count()
    r = process(test_session, xml)
    assert r == {'failures': 0, 'successes': 0, 'skips': 1}

    n_obs_after = test_session.query(Obs).count()
    assert n_obs_before == n_obs_after

    t = ('Could not find variable in the database. Skipping this observation.')
    assert t == caplog.records[0].msg

    # TODO: need to actually check log warning
