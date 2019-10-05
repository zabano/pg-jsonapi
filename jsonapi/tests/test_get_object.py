import pytest

from jsonapi.tests.util import *


#
# public access (no login)
#


@pytest.mark.asyncio
async def test_1(cli, user_1_id):
    json = await get(cli, '/users/{}'.format(user_1_id))
    check_user(json['data'], lambda v: int(v) == user_1_id)
    assert_object(json['data'], 'user', lambda v: int(v) == user_1_id)
    assert_attribute(json['data'], 'email', lambda v: '@' in v)
    assert_attribute(json['data'], 'status', lambda v: v in ('active', 'pending'))
    assert_attribute(json['data'], 'createdOn', lambda v: is_datetime(v))
    assert_attribute_does_not_exist(json['data'], 'article-count')


@pytest.mark.asyncio
async def test_2(cli, user_2_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_2_id), 200)
    assert_object(json['data'], 'user', lambda v: int(v) == user_2_id)
    assert_relationship(json['data'], 'articles', lambda size: size == 0)
    assert 'included' not in json


@pytest.mark.asyncio
async def test_forbidden(cli, user_1_article_id_forbidden):
    json = await get(cli, '/articles/{}'.format(user_1_article_id_forbidden), 403)
    assert_error(json, 403, 'access denied')


@pytest.mark.asyncio
async def test_not_found(cli, article_count):
    json = await get(cli, '/articles/{}'.format(article_count + 1), 404)
    assert_error(json, 404, 'not found')


#
# logged in access
#


@pytest.mark.asyncio
async def test_logged_in_1(cli, user_1_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_1_id), 200, user_1_id)
    assert_object(json['data'], 'user', lambda v: int(v) == user_1_id)
    assert_relationship(json['data'], 'articles', lambda size: size > 0)
    for article in get_relationship(json['data'], 'articles'):
        assert_object(article, 'article')
    assert 'included' in json
    assert len(json['included']) > 0
    for article in json['included']:
        check_article(article)


@pytest.mark.asyncio
async def test_logged_in_2(cli, user_2_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_2_id), 200, user_2_id)
    assert_object(json['data'], 'user', lambda v: int(v) == user_2_id)
    assert_relationship(json['data'], 'articles', lambda size: size == 0)
    assert 'included' not in json


@pytest.mark.asyncio
async def test_logged_in_3(cli, user_1_id, user_1_article_id_readable):
    json = await get(cli, '/articles/{}'.format(user_1_article_id_readable), 200, user_1_id)
    check_article(json['data'], lambda v: int(v) == user_1_article_id_readable)


@pytest.mark.asyncio
async def test_logged_in_4(cli, user_1_id, user_1_article_id_readable):
    json = await get(cli, '/articles/{}?include=articles'.format(user_1_article_id_readable),
                     200, user_1_id)
    assert_object(json['data'], 'article', lambda v: int(v) == user_1_article_id_readable)
    check_article(json['data'])


#
# superuser access
#

@pytest.mark.asyncio
async def test_superuser_1(cli, superuser_id, user_1_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_1_id), 200, superuser_id)
    assert_relationship(json['data'], 'articles', lambda size: size > 0)
    assert 'included' in json


@pytest.mark.asyncio
async def test_superuser_2(cli, superuser_id, user_2_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_2_id), 200, superuser_id)
    assert_relationship(json['data'], 'articles', lambda size: size == 0)
    assert 'included' not in json


@pytest.mark.asyncio
async def test_superuser_3(cli, superuser_id):
    json = await get(cli, '/users/{}?include=articles'.format(superuser_id), 200, superuser_id)
    assert_relationship(json['data'], 'articles', lambda size: size > 0)
    assert 'included' in json
