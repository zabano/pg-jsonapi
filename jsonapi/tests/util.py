import datetime as dt
from contextlib import asynccontextmanager

from jsonapi.datatypes import DataType
from jsonapi.tests.auth import login, logout


####################################################################################################
# model interface
####################################################################################################

def login_user(**kwargs):
    user_id = kwargs.pop('login', None)
    if user_id is not None:
        login(user_id)
    return user_id


def logout_user(user_id):
    if user_id is not None:
        logout()


@asynccontextmanager
async def get_object(model, object_id, args=None, **kwargs):
    user_id = login_user(**kwargs)
    try:
        yield await model.get_object(args, object_id)
    finally:
        logout_user(user_id)


@asynccontextmanager
async def get_collection(model, args=None, **kwargs):
    user_id = login_user(**kwargs)
    try:
        yield await model.get_collection(args)
    finally:
        logout_user(user_id)


@asynccontextmanager
async def get_related(model, object_id, name, args=None, **kwargs):
    user_id = login_user(**kwargs)
    try:
        yield await model.get_related(args, object_id, name)
    finally:
        logout_user(user_id)


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


def is_size(v):
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
