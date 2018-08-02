from crmprtd.moti.normalize import normalize
from io import BytesIO
import pytest


def test_normalize_good_data():
    lines = b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
    <product operational-mode="official">
      <title>Observation from BC Meteorological Stations</title>
      <field>meteorological </field>
      <category>observation</category>
      <creation-date refresh-frequency="PT1H">2013-11-29T13:22:57-08:00</creation-date>
    </product>
    <source>
      <production-center>British Columbia Ministry of Transportation
        <sub-center>AWP</sub-center>
      </production-center>
    </source>
  </head>
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091 </id>
        <id type="network">BC_MoT_11091 </id>
      </origin>
      <observation valid-time="2012-01-01T00:00:00-08:00">
        <pressure index="1" type="atmospheric">
          <value units="mb">964</value>
        </pressure>
        <temperature index="1" type="air-temperature">
          <value units="degC">-2.368</value>
        </temperature>
      </observation>
      <observation valid-time="2012-01-01T01:00:00-08:00">
        <temperature index="1" type="air-temperature">
          <value units="degC">-2.417</value>
        </temperature>
        <temperature index="1" type="dew-point">
          <value units="degC">-4</value>
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>'''
    f = BytesIO(lines)
    rows = [row for row in normalize(f)]
    assert len(rows) == 4


def test_normalize_missing_stn_indexerror():
    lines = b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
    <product operational-mode="official">
      <title>Observation from BC Meteorological Stations</title>
      <field>meteorological </field>
      <category>observation</category>
      <creation-date refresh-frequency="PT1H">2013-11-29T13:22:57-08:00</creation-date>
    </product>
    <source>
      <production-center>British Columbia Ministry of Transportation
        <sub-center>AWP</sub-center>
      </production-center>
    </source>
  </head>
  <data>
    <observation-series>
      <origin type="station">
        <id type="network">BC_MoT_11091 </id>
      </origin>
      <observation valid-time="2012-01-01T00:00:00-08:00">
        <pressure index="1" type="atmospheric">
          <value units="mb">964</value>
        </pressure>
        <temperature index="1" type="air-temperature">
          <value units="degC">-2.368</value>
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>'''
    f = BytesIO(lines)
    rows = [row for row in normalize(f)]
    assert len(rows) == 0


def test_normalize_missing_time():
    lines = b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
    <product operational-mode="official">
      <title>Observation from BC Meteorological Stations</title>
      <field>meteorological </field>
      <category>observation</category>
      <creation-date refresh-frequency="PT1H">2013-11-29T13:22:57-08:00</creation-date>
    </product>
    <source>
      <production-center>British Columbia Ministry of Transportation
        <sub-center>AWP</sub-center>
      </production-center>
    </source>
  </head>
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091 </id>
        <id type="network">BC_MoT_11091 </id>
      </origin>
      <observation>
        <pressure index="1" type="atmospheric">
          <value units="mb">964</value>
        </pressure>
        <temperature index="1" type="air-temperature">
          <value units="degC">-2.368</value>
        </temperature>
      </observation>
      <observation valid-time="2012-01-01T01:00:00-08:00">
        <temperature index="1" type="air-temperature">
          <value units="degC">-2.417</value>
        </temperature>
        <temperature index="1" type="dew-point">
          <value units="degC">-4</value>
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>'''
    f = BytesIO(lines)
    rows = [row for row in normalize(f)]
    assert len(rows) == 2


def test_normalize_bad_time(moti_sawr7110_xml):
    lines = b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
    <product operational-mode="official">
      <title>Observation from BC Meteorological Stations</title>
      <field>meteorological </field>
      <category>observation</category>
      <creation-date refresh-frequency="PT1H">2013-11-29T13:22:57-08:00</creation-date>
    </product>
    <source>
      <production-center>British Columbia Ministry of Transportation
        <sub-center>AWP</sub-center>
      </production-center>
    </source>
  </head>
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091 </id>
        <id type="network">BC_MoT_11091 </id>
      </origin>
      <observation valid-time="BAD_TIME">
        <pressure index="1" type="atmospheric">
          <value units="mb">964</value>
        </pressure>
        <temperature index="1" type="air-temperature">
          <value units="degC">-2.368</value>
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>'''
    f = BytesIO(lines)
    rows = [row for row in normalize(f)]
    assert len(rows) == 0


def test_normalize_missing_var_name():
    lines = b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
    <product operational-mode="official">
      <title>Observation from BC Meteorological Stations</title>
      <field>meteorological </field>
      <category>observation</category>
      <creation-date refresh-frequency="PT1H">2013-11-29T13:22:57-08:00</creation-date>
    </product>
    <source>
      <production-center>British Columbia Ministry of Transportation
        <sub-center>AWP</sub-center>
      </production-center>
    </source>
  </head>
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091 </id>
        <id type="network">BC_MoT_11091 </id>
      </origin>
      <observation valid-time="2012-01-01T01:00:00-08:00">
        <temperature>
          <value units="degC">-2.417</value>
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>'''
    f = BytesIO(lines)
    rows = [row for row in normalize(f)]
    assert len(rows) == 0


def test_normalize_missing_value():
    lines = b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
    <product operational-mode="official">
      <title>Observation from BC Meteorological Stations</title>
      <field>meteorological </field>
      <category>observation</category>
      <creation-date refresh-frequency="PT1H">2013-11-29T13:22:57-08:00</creation-date>
    </product>
    <source>
      <production-center>British Columbia Ministry of Transportation
        <sub-center>AWP</sub-center>
      </production-center>
    </source>
  </head>
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091 </id>
        <id type="network">BC_MoT_11091 </id>
      </origin>
      <observation valid-time="2012-01-01T00:00:00-08:00">
        <pressure index="1" type="atmospheric">
          <value units="mb">964</value>
        </pressure>
        <temperature index="1" type="air-temperature">
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>'''
    f = BytesIO(lines)
    rows = [row for row in normalize(f)]
    assert len(rows) == 1


def test_normalize_bad_value():
    lines = b'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<cmml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="..\Schema\CMML.xsd" version="2.01">
  <head>
    <product operational-mode="official">
      <title>Observation from BC Meteorological Stations</title>
      <field>meteorological </field>
      <category>observation</category>
      <creation-date refresh-frequency="PT1H">2013-11-29T13:22:57-08:00</creation-date>
    </product>
    <source>
      <production-center>British Columbia Ministry of Transportation
        <sub-center>AWP</sub-center>
      </production-center>
    </source>
  </head>
  <data>
    <observation-series>
      <origin type="station">
        <id type="client">11091 </id>
        <id type="network">BC_MoT_11091 </id>
      </origin>
      <observation valid-time="2012-01-01T00:00:00-08:00">
        <pressure index="1" type="atmospheric">
          <value units="mb">bad_value</value>
        </pressure>
        <temperature index="1" type="air-temperature">
        </temperature>
      </observation>
    </observation-series>
  </data>
</cmml>'''
    f = BytesIO(lines)
    rows = [row for row in normalize(f)]
    assert len(rows) == 0
