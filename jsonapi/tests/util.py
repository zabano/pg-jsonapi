import datetime as dt
import os
import re
from urllib.parse import quote

from jsonapi.datatypes import DATETIME_FORMAT


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


def parse_datetime(datetime):
    if datetime is not None:
        return dt.datetime.strptime(datetime, DATETIME_FORMAT)


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


def assert_relationship(json, name, length):
    assert 'relationships' in json
    relationships = json['relationships']
    assert name in relationships
    assert len(relationships[name]) == length


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


def is_date(v):
    return v is not None and \
           re.match('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$', v) is not None


def is_positive(v):
    return isinstance(v, int) and v >= 0


def check_user(user, user_id=None):
    assert_object(user, 'user', None if user_id is None else lambda uid: uid == str(user_id))
    assert_attribute(user, 'email', lambda v: '@' in v)
    assert_attribute(user, 'status', lambda v: v in ('active', 'pending'))
    assert_attribute(user, 'createdOn', lambda v: is_date(v))


def check_article(json):
    assert_object(json, 'article')
    assert_attribute(json, 'body', lambda v: isinstance(v, str) and len(v) > 0)
    assert_attribute(json, 'title', lambda v: isinstance(v, str) and len(v) > 0)
    assert_attribute(json, 'isPublished', lambda v: isinstance(v, bool))
    assert_attribute(json, 'createdOn', lambda v: is_date(v))
    assert_attribute(json, 'updatedOn', lambda v: is_date(v) or v is None)
