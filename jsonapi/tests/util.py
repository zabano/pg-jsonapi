import datetime as dt
import os
from urllib.parse import quote

from jsonapi.datatypes import DataType


def _parse_url_object(url):
    url_string = url.pop('url', '/')
    if len(url) == 0:
        return url_string
    fields = list()
    for name1, val1 in url.items():
        if isinstance(val1, dict):
            for name2, val2 in val1.items():
                fields.append('{}[{}]={}'.format(name1, name2, quote(str(val2))))
        else:
            fields.append('{}={}'.format(name1, quote(str(val1))))
    return '{}?{}'.format(url_string, '&'.join(fields))


async def get(cli, url, status=200, user_id=None):
    """
    Perform a GET request.

    :param cli: http client instant
    :param mixed url: url string or object
    :param status: expected http status code
    :param user_id: user_id to use for login
    :return:
    """

    if user_id is None:
        if 'JSONAPI_LOGIN' in os.environ:
            del os.environ['JSONAPI_LOGIN']
    else:
        os.environ['JSONAPI_LOGIN'] = str(user_id)

    url_string = _parse_url_object(url) if isinstance(url, dict) else str(url)
    response = await cli.get(url_string)
    assert response.status_code == status
    json = await response.json
    if status == 200:
        assert 'data' in json
    return json


####################################################################################################
# asserts
####################################################################################################


def assert_datatype(test_data, name, validator):
    json = test_data['data']['attributes']
    assert name in json
    assert validator(json[name]) is True


def assert_object(json, object_type, validator=None):
    assert 'type' in json
    assert json['type'] == object_type
    assert 'id' in json
    if validator is not None:
        assert validator(json['id'])


def assert_attribute(json, name, validator=None):
    assert 'attributes' in json
    attributes = json['attributes']
    assert name in attributes
    if validator is not None:
        assert validator(attributes[name]) is True


def assert_attribute_does_not_exist(json, name):
    assert 'attributes' in json
    attributes = json['attributes']
    assert name not in attributes


def assert_relationship(json, name, validate_length):
    assert 'relationships' in json
    relationships = json['relationships']
    assert name in relationships
    if validate_length is not None:
        assert validate_length(len(relationships[name])) is True


def assert_error(json, status, text=None):
    assert 'errors' in json
    assert len(json['errors']) == 1
    error = json['errors'][0]
    assert error['status'] == int(status)
    if text is not None:
        assert error['title'] is not None and text in error['title'].lower()


def assert_meta(json, name, validator=None):
    assert 'meta' in json
    assert name in json['meta']
    if validator is not None:
        assert validator(json['meta'][name])


def get_relationship(json, name):
    return json['relationships'][name]


def is_positive(v):
    return isinstance(v, int) and v >= 0


def check_user(user, validator=None):
    assert_object(user, 'user', validator)
    assert_attribute(user, 'email', lambda v: '@' in v)
    assert_attribute(user, 'name', lambda v: isinstance(v, str))
    assert_attribute(user, 'first', lambda v: isinstance(v, str))
    assert_attribute(user, 'last', lambda v: isinstance(v, str))
    assert user['attributes']['first'] + ' ' + user['attributes']['last'] == user['attributes']['name']
    assert_attribute(user, 'status', lambda v: v in ('active', 'pending'))
    assert_attribute(user, 'createdOn', lambda v: is_datetime(v))


def check_article(json, validator=None):
    assert_object(json, 'article', validator)
    assert_attribute(json, 'body', lambda v: isinstance(v, str) and len(v) > 0)
    assert_attribute(json, 'title', lambda v: isinstance(v, str) and len(v) > 0)
    assert_attribute(json, 'isPublished', lambda v: isinstance(v, bool))
    assert_attribute(json, 'createdOn', lambda v: is_datetime(v))
    assert_attribute(json, 'updatedOn', lambda v: is_datetime(v, nullable=True))


####################################################################################################
# Date & Time
####################################################################################################


def parse_date(v):
    if v is not None:
        return dt.datetime.strptime(v, DataType.FORMAT_DATE)


def parse_time(v):
    if v is not None:
        return dt.datetime.strptime(v, DataType.FORMAT_TIME)


def parse_datetime(v):
    if v is not None:
        return dt.datetime.strptime(v, DataType.FORMAT_DATETIME)


def _is_timestamp(v, parser):
    try:
        parser(v)
    except ValueError:
        return False
    else:
        return True


def is_date(v, nullable=False):
    if v is None:
        return nullable
    return _is_timestamp(v, parse_date)


def is_time(v, nullable=False):
    if v is None:
        return nullable
    return _is_timestamp(v, parse_time)


def is_datetime(v, nullable=False):
    if v is None:
        return nullable
    return _is_timestamp(v, parse_datetime)
