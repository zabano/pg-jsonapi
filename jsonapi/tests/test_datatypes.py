import pytest

from jsonapi.tests.util import *


#
# public access (no login)
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
