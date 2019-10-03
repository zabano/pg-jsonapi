import pytest

from jsonapi.tests.util import *


#
# public access (no login)
#


@pytest.mark.asyncio
async def test_1(cli, user_1_id):
    json = await get(cli, '/users/{}/articles/'.format(user_1_id))
    assert isinstance(json['data'], list)
    assert len(json['data']) == 0


@pytest.mark.asyncio
async def test_2(cli, user_2_id):
    json = await get(cli, '/users/{}/articles/'.format(user_2_id))
    assert isinstance(json['data'], list)
    assert len(json['data']) == 0


@pytest.mark.asyncio
async def test_3(cli, user_1_id):
    json = await get(cli, '/articles/{}/author'.format(user_1_id), 403)
    assert_error(json, 403, 'access denied')


#
# logged in access
#


@pytest.mark.asyncio
async def test_logged_in_1(cli, user_1_id):
    json = await get(cli, '/users/{}/articles/'.format(user_1_id), 200, user_1_id)
    assert len(json['data']) > 0
    for article in json['data']:
        check_article(article)


@pytest.mark.asyncio
async def test_logged_in_2(cli, user_2_id):
    json = await get(cli, '/users/{}/articles/'.format(user_2_id), 200, user_2_id)
    assert len(json['data']) == 0


#
# superuser access
#

@pytest.mark.asyncio
async def test_superuser_1(cli, superuser_id, user_1_id):
    json = await get(cli, '/users/{}/articles/'.format(user_1_id), 200, superuser_id)
    assert len(json['data']) > 0
    for article in json['data']:
        check_article(article)


@pytest.mark.asyncio
async def test_superuser_2(cli, superuser_id, user_2_id):
    json = await get(cli, '/users/{}/articles/'.format(user_2_id), 200, superuser_id)
    assert len(json['data']) == 0


@pytest.mark.asyncio
async def test_superuser_3(cli, superuser_id):
    json = await get(cli, '/articles/1/author', 200, superuser_id)
    assert isinstance(json['data'], dict)
    check_user(json['data'])
