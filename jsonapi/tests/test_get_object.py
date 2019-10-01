import pytest

from jsonapi.tests.util import *


#
# public access (no login)
#


@pytest.mark.asyncio
async def test_1(cli, user_1_id):
    json = await get(cli, '/users/{}'.format(user_1_id))
    assert isinstance(json['data'], dict)
    check_user(json['data'], user_1_id)


@pytest.mark.asyncio
async def test_2(cli, user_1_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_1_id), 200)
    assert_relationship(json['data'], 'articles', 0)
    assert 'included' not in json


@pytest.mark.asyncio
async def test_forbidden(cli):
    json = await get(cli, '/articles/1', 403)
    assert_error(json, 403, 'access denied')


@pytest.mark.asyncio
async def test_not_found(cli):
    json = await get(cli, '/articles/5000', 404)
    assert_error(json, 404, 'not found')


def _check_articles(json, id_list):
    assert_relationship(json['data'], 'articles', len(id_list))
    for article in get_relationship(json['data'], 'articles'):
        assert_object(article, 'article', lambda obj_id: int(obj_id) in id_list)
    assert 'included' in json
    for article in json['included']:
        check_article(article)


#
# logged in access
#


@pytest.mark.asyncio
async def test_logged_in_1(cli, user_1_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_1_id), 200, user_1_id)
    _check_articles(json, (52, 53, 54, 55))


@pytest.mark.asyncio
async def test_logged_in_2(cli, user_1_id, user_2_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_2_id), 200, user_1_id)
    _check_articles(json, (263,))


@pytest.mark.asyncio
async def test_logged_in_3(cli, superuser_id, user_1_id):
    json = await get(cli, '/users/{}?include=articles'.format(superuser_id), 200, user_1_id)
    assert_relationship(json['data'], 'articles', 0)
    assert 'included' not in json


#
# superuser access
#

@pytest.mark.asyncio
async def test_superuser_1(cli, superuser_id, user_1_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_1_id), 200, superuser_id)
    _check_articles(json, (52, 53, 54, 55))


@pytest.mark.asyncio
async def test_superuser_2(cli, superuser_id, user_2_id):
    json = await get(cli, '/users/{}?include=articles'.format(user_2_id), 200, superuser_id)
    _check_articles(json, (260, 261, 262, 263, 264))
