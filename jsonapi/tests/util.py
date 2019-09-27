import os
import re


async def get(cli, url, status=200, user_id=None):

    if user_id is None:
        if 'JSONAPI_LOGIN' in os.environ:
            del os.environ['JSONAPI_LOGIN']
    else:
        os.environ['JSONAPI_LOGIN'] = str(user_id)

    response = await cli.get(url)
    assert response.status_code == status
    json = await response.json
    if status == 200:
        assert 'data' in json
    return json


def assert_object(json, object_type, object_id=None):
    assert 'type' in json
    assert json['type'] == object_type
    assert 'id' in json
    if object_id is not None:
        if isinstance(object_id, (list, tuple)):
            assert json['id'] in (str(x) for x in object_id)
        else:
            assert json['id'] == str(object_id)


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


def get_relationship(json, name):
    return json['relationships'][name]


def is_date(v):
    return v is not None and \
           re.match('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$', v) is not None


def is_positive(v):
    return isinstance(v, int) and v >= 0


def check_user(user, user_id=None):
    assert_object(user, 'user', user_id)
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
