import datetime as dt
import random
from contextlib import asynccontextmanager
from json import dumps as json_dumps

from inflection import camelize, underscore

import jsonapi.model
from jsonapi.datatypes import DataType
from jsonapi.log import logger
from jsonapi.tests.auth import login, logout


def log_json(data):
    logger.info(json_dumps(data, indet=4, sort_keys=True))


def field_name(name):
    return camelize(underscore(name), False)


####################################################################################################
# model interface
####################################################################################################

def login_user(user_id):
    if user_id is not None:
        login(user_id)
    return user_id


def logout_user(user_id):
    if user_id is not None:
        logout()


@asynccontextmanager
async def get_object(args, model, object_id, **kwargs):
    user_id = login_user(kwargs.pop('login', None))
    try:
        yield await model.get_object(args, object_id)
    finally:
        logout_user(user_id)


@asynccontextmanager
async def get_collection(args, *models, **kwargs):
    user_id = login_user(kwargs.pop('login', None))
    try:
        if len(models) == 1:
            yield await models[0].get_collection(args, search=kwargs.pop('search', None))
        else:
            yield await jsonapi.model.get_collection(args, *models)
    finally:
        logout_user(user_id)


@asynccontextmanager
async def get_related(args, model, object_id, name, **kwargs):
    user_id = login_user(kwargs.pop('login', None))
    try:
        yield await model.get_related(args, object_id, name, search=kwargs.pop('search', None))
    finally:
        logout_user(user_id)


@asynccontextmanager
async def search(args, term, *models, **kwargs):
    user_id = login_user(kwargs.pop('login', None))
    try:
        yield await jsonapi.model.search(args, term, *models)
    finally:
        logout_user(user_id)


####################################################################################################
# asserts
####################################################################################################

def assert_object(obj, object_type, validator=None, nullable=True):
    if not nullable or obj is not None:
        assert 'type' in obj
        if isinstance(object_type, str):
            assert obj['type'] == object_type
        else:
            assert obj['type'] in object_type
        assert 'id' in obj
        if validator is not None:
            assert validator(obj['id'])
        return obj


def assert_attribute(obj, name, validator=None):
    name = field_name(name)
    assert 'attributes' in obj
    assert name in obj['attributes']
    if validator is not None:
        assert validator(obj['attributes'][name]) is True
    return obj['attributes'][name]


def assert_no_attribute(json, name):
    assert 'attributes' in json
    attributes = json['attributes']
    assert name not in attributes


def assert_collection(json, object_type, validate_length=None, validator=None):
    assert 'data' in json
    assert isinstance(json['data'], list)
    if validate_length is not None:
        assert validate_length(len(json['data']))
    return [assert_object(obj, object_type, validator) for obj in json['data']]


def assert_relationship(obj, name, validate_length=None):
    assert 'relationships' in obj
    relationships = obj['relationships']
    name = field_name(name)
    assert name in relationships
    if validate_length is not None:
        if isinstance(relationships[name], list):
            assert validate_length(len(relationships[name])) is True
        else:
            assert validate_length(1)
    return relationships[name]


def assert_included(json, obj):
    assert 'included' in json
    for included in json['included']:
        if included['type'] == obj['type'] and included['id'] == obj['id']:
            return included
    assert False


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
    return json['meta'][name]


def assert_field(obj, name):
    name = field_name(name)
    if name == 'id':
        return obj['id']
    if 'attributes' in obj and name in obj['attributes']:
        return obj['attributes'][name]
    if 'relationships' in obj and name in obj['relationships']:
        return obj['relationships'][name]
    assert False


def assert_sorted(json, attr_name, object_type, reverse=False, validator_length=None):
    data = [assert_field(user, attr_name) for user in assert_collection(
        json, object_type, validator_length)]
    assert data == sorted(data,
                          key=lambda x: int(x) if attr_name == 'id' else x,
                          reverse=reverse)


####################################################################################################
# check resources
####################################################################################################

def check_user(user, validator=None):
    assert_object(user, 'user', validator)
    assert_attribute(user, 'email', lambda v: '@' in v)
    assert_attribute(user, 'name', lambda v: is_string(v))
    assert_attribute(user, 'first', lambda v: is_string(v))
    assert_attribute(user, 'last', lambda v: is_string(v))
    assert user['attributes']['name'] == '{first} {last}'.format(**user['attributes'])
    assert_attribute(user, 'status', lambda v: v in ('active', 'pending'))
    assert_attribute(user, 'createdOn', lambda v: is_datetime(v))


def check_article(article, validator=None):
    assert_object(article, 'article', validator)
    assert_attribute(article, 'body', lambda v: is_string(v))
    assert_attribute(article, 'title', lambda v: is_string(v))
    assert_attribute(article, 'isPublished', lambda v: isinstance(v, bool))
    assert_attribute(article, 'createdOn', lambda v: is_datetime(v))
    assert_attribute(article, 'updatedOn', lambda v: is_datetime(v, nullable=True))


def check_comment(comment, validator=None):
    assert_object(comment, 'comment', validator)
    assert_attribute(comment, 'body', lambda v: is_string(v))
    assert_attribute(comment, 'createdOn', lambda v: is_datetime(v))
    assert_attribute(comment, 'updatedOn', lambda v: is_datetime(v, nullable=True))


def check_reply(reply, validator=None):
    assert_object(reply, 'reply', validator)
    assert_attribute(reply, 'body', lambda v: is_string(v))
    assert_attribute(reply, 'createdOn', lambda v: is_datetime(v))
    assert_attribute(reply, 'updatedOn', lambda v: is_datetime(v, nullable=True))


def check_user_bio(bio, validator=None):
    assert_object(bio, 'user-bio', validator)
    assert_attribute(bio, 'summary', lambda v: is_string(v, nullable=True))
    assert_attribute(bio, 'birthday', lambda v: is_date(v, nullable=True))


def check_included(json, obj, rel_name, rel_type, validator=None, object_validator=None):
    relationship = assert_relationship(obj, rel_name, validator)
    if not isinstance(relationship, list):
        relationship = [relationship]
    for related in relationship:
        if related is not None:
            assert_object(related, rel_type, object_validator)
            assert_included(json, related)


####################################################################################################
# date and time
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


####################################################################################################
# other
####################################################################################################

def is_size(v):
    return isinstance(v, int) and v >= 0


def is_string(v, nullable=False):
    if v is None:
        return nullable
    return isinstance(v, str) and len(v) > 0


def sample_integers(min_, max_, sample_size=3):
    return random.sample(range(min_, max_), sample_size)
