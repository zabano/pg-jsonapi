import datetime as dt

import pytest

from jsonapi.datatypes import parse_bool, parse_date, parse_datetime, parse_time
from jsonapi.tests.util import assert_datatype, is_date, is_datetime, is_time


#
# test data
#


@pytest.mark.asyncio
async def test_bool(test_data):
    assert_datatype(test_data, 'testBool', lambda v: isinstance(v, bool))


@pytest.mark.asyncio
async def test_small_int(test_data):
    assert_datatype(test_data, 'testSmallInt', lambda v: isinstance(v, int))


@pytest.mark.asyncio
async def test_int(test_data):
    assert_datatype(test_data, 'testInt', lambda v: isinstance(v, int))


@pytest.mark.asyncio
async def test_big_int(test_data):
    assert_datatype(test_data, 'testBigInt', lambda v: isinstance(v, int))


@pytest.mark.asyncio
async def test_float(test_data):
    assert_datatype(test_data, 'testFloat', lambda v: isinstance(v, float))


@pytest.mark.asyncio
async def test_double(test_data):
    assert_datatype(test_data, 'testDouble', lambda v: isinstance(v, float))


@pytest.mark.asyncio
async def test_numeric(test_data):
    assert_datatype(test_data, 'testNumeric', lambda v: isinstance(v, float))


@pytest.mark.asyncio
async def test_char(test_data):
    assert_datatype(test_data, 'testChar', lambda v: isinstance(v, str) and len(v) == 10)


@pytest.mark.asyncio
async def test_varchar(test_data):
    assert_datatype(test_data, 'testVarchar', lambda v: isinstance(v, str))


@pytest.mark.asyncio
async def test_text(test_data):
    assert_datatype(test_data, 'testText', lambda v: isinstance(v, str))


@pytest.mark.asyncio
async def test_enum(test_data):
    assert_datatype(test_data, 'testEnum', lambda v: isinstance(v, str))


@pytest.mark.asyncio
async def test_time(test_data):
    assert_datatype(test_data, 'testTime', lambda v: is_time(v))


@pytest.mark.asyncio
async def test_date(test_data):
    assert_datatype(test_data, 'testDate', lambda v: is_date(v))


@pytest.mark.asyncio
async def test_timestamp(test_data):
    assert_datatype(test_data, 'testTimestamp', lambda v: is_datetime(v))


@pytest.mark.asyncio
async def test_timestamp_tz(test_data):
    assert_datatype(test_data, 'testTimestampTz', lambda v: is_datetime(v))


@pytest.mark.asyncio
async def test_json(test_data):
    assert_datatype(test_data, 'testJson', lambda v: isinstance(v, dict))


@pytest.mark.asyncio
async def test_json_b(test_data):
    assert_datatype(test_data, 'testJsonB', lambda v: isinstance(v, dict))


#
# parsers
#


@pytest.mark.asyncio
async def test_parse_bool():
    for val in ('t', 'T', 'true', 'True', 'TRUE', '1', 'on', 'On', 'ON', 'yes', 'Yes', 'YES'):
        assert parse_bool(val) is True
    for val in ('f', 'F', 'false', 'False', 'FALSE', '0', 'off', 'Off', 'OFF', 'no', 'No', 'NO'):
        assert parse_bool(val) is False


@pytest.mark.asyncio
async def test_parse_bool_error():
    for val in ('tt', 'FF', False, True, 0, 1, 2):
        try:
            parse_bool(val)
        except ValueError:
            assert True
        else:
            assert False


test_input = dict(
    other=('foo', True, 0, 1, 2),
    date=dict(
        good=('2019-09-01', '2019-9-1', '2019-09-1', '2019-9-01', '2019-09', '2019-9'),
        bad=('2019/09/01', '2019-Sep-01', '09-01-19', 'September 1st, 2019', 'Sep 1/19',
             '2019-09-32', '2019-13-01', '19-09-01')
    ),
    time=dict(
        good=('16:09:00', '16:09', '4:09 PM', '16:09', '4:09 PM', '4:09PM',
              '16:9:00', '16:9', '4:9 PM', '16:9', '4:9 PM', '4:9PM'),
        bad=('60:00:00', '14:01:31 PM', '09:91', '16:35 PM')
    ),
    datetime=dict(
        good=('2019-09-01T16:09:00Z',
              '2019-09-01T16:09:00', '2019-09-01T16:09',
              '2019-09-01 16:09:00', '2019-09-01 16:09',
              '2019-09-01 4:09:00PM', '2019-09-01 4:09:00 PM', '2019-09-01 4:09PM', '2019-09-01 4:09 PM',
              '2019-09-01 4:09:00pm', '2019-09-01 4:09:00 pm', '2019-09-01 4:09pm', '2019-09-01 4:09 pm',
              '2019-09-01 16:9:00', '2019-09-01 16:9',
              '2019-09-01 4:9:0PM', '2019-09-01 4:9PM'),
        bad=('2019/09/01 16:09:00', '2019-Sep-01 16:09:00', '09-01-19 16:09:00',
             'September 1st, 2019 16:09:00', 'Sep 1/19 16:09pm',
             '2019-09-32 16:09:00', '2019-13-01 16:09:00', '19-09-01 16:09:00')
    )
)


@pytest.mark.asyncio
async def test_parse_date():
    for val in test_input['date']['good']:
        assert parse_date(val) == dt.date(2019, 9, 1)


@pytest.mark.asyncio
async def test_parse_date_error():
    for val in (*test_input['date']['bad'],
                *test_input['time']['good'],
                *test_input['time']['bad'],
                *test_input['datetime']['good'],
                *test_input['datetime']['bad'],
                *test_input['other']):
        try:
            parse_date(val)
        except ValueError:
            assert True
        else:
            assert False


@pytest.mark.asyncio
async def test_parse_time():
    for val in test_input['time']['good']:
        assert parse_time(val) == dt.time(16, 9)


@pytest.mark.asyncio
async def test_parse_time_error():
    for val in (*test_input['time']['bad'],
                *test_input['date']['good'],
                *test_input['date']['bad'],
                *test_input['datetime']['good'],
                *test_input['datetime']['bad'],
                *test_input['other']):
        try:
            parse_time(val)
        except ValueError:
            assert True
        else:
            assert False


@pytest.mark.asyncio
async def test_parse_datetime():
    for val in test_input['datetime']['good']:
        assert parse_datetime(val) == dt.datetime(2019, 9, 1, 16, 9)
    for val in test_input['date']['good']:
        assert parse_datetime(val) == dt.datetime(2019, 9, 1)


@pytest.mark.asyncio
async def test_parse_datetime_error():
    for val in (*test_input['datetime']['bad'],
                *test_input['time']['good'],
                *test_input['time']['bad'],
                *test_input['date']['bad'],
                *test_input['other']):
        try:
            parse_datetime(val)
        except ValueError:
            assert True
        else:
            assert False
