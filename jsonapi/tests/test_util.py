import pytest

from jsonapi.tests.util import *


@pytest.fixture('module')
def rec():
    return {'id': '1', 'type': 'test',
            'attributes':
                {'testBool': True,
                 'testInt': 1,
                 'testSmallInt': 1,
                 'testBigInt': 1,
                 'testFloat': 1.5,
                 'testDouble': 1.5,
                 'testNumeric': 12.3456,
                 'testChar': 'char      ',
                 'testVarchar': 'varchar',
                 'testText': 'text',
                 'testEnum': 'active',
                 'testTime': '09:59:30',
                 'testDate': '2019-09-01',
                 'testTimestamp': '2019-09-01T09:59:30Z',
                 'testTimestampTz': '2019-09-01T09:59:30Z',
                 'testJson': {'string': 'This is a test.', 'integer': '1', 'float': '1.5',
                              'bool': 'true', 'date': '2019-09-01', 'time': '10:00:00',
                              'datetime': '2019-09-01T10:00:00Z'},
                 'testJsonB': {'bool': True, 'date': '2019-09-01', 'time': '10:00:00',
                               'float': 1.5, 'string': 'This is a test.', 'integer': 1,
                               'datetime': '2019-09-01T10:00:00Z'}}}


def test_assert_object(rec):
    assert_object(rec, 'test')
    assert_object(rec, 'test', lambda v: int(v) == 1)
    with pytest.raises(AssertionError):
        assert assert_object(rec, 'user')
    with pytest.raises(AssertionError):
        assert assert_object(rec, 'user', lambda v: int(v) == 1)
    with pytest.raises(AssertionError):
        assert assert_object(rec, 'test', lambda v: int(v) == 2)


def test_assert_attribute(rec):
    assert_attribute(rec, 'testInt')
    assert_attribute(rec, 'testInt', lambda v: v == 1)
    assert_attribute(rec, 'testFloat')
    assert_attribute(rec, 'testFloat', lambda v: v == 1.5)
    with pytest.raises(AssertionError):
        assert assert_attribute(rec, 'testDoesNotExist')
    with pytest.raises(AssertionError):
        assert assert_attribute(rec, 'testINT')
    with pytest.raises(AssertionError):
        assert assert_attribute(rec, 'testInt', lambda v: int(v) == 2)


def test_assert_attribute_does_not_exist(rec):
    assert_attribute_does_not_exist(rec, 'testDoesNotExist')
    assert_attribute_does_not_exist(rec, 'testINT')
    with pytest.raises(AssertionError):
        assert assert_attribute_does_not_exist(rec, 'testFloat')
    with pytest.raises(AssertionError):
        assert assert_attribute_does_not_exist(rec, 'testInt')
