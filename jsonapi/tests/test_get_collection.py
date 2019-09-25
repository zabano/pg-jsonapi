import pytest

from jsonapi.tests.util import *


#
# public access (no login)
#


@pytest.mark.asyncio
async def test_get_users(cli, user_count):
    json = await get(cli, '/users/')
    assert isinstance(json['data'], list)
    assert len(json['data']) == user_count
    check_user(json['data'][0])
    check_user(json['data'][-1])


@pytest.mark.asyncio
async def test_get_articles(cli):
    json = await get(cli, '/articles/')
    assert isinstance(json['data'], list)
    assert len(json['data']) == 0


#
# logged in access
#


@pytest.mark.asyncio
async def test_get_articles_as_user_1(cli, user_1_id, article_count):
    json = await get(cli, '/articles/', 200, user_1_id)
    assert 0 < len(json['data']) < article_count


@pytest.mark.asyncio
async def test_get_articles_as_user_2(cli, user_2_id, article_count):
    json = await get(cli, '/articles/', 200, user_2_id)
    assert 0 < len(json['data']) < article_count


#
# superuser access
#

@pytest.mark.asyncio
async def test_get_articles_as_superuser(cli, superuser_id, article_count):
    json = await get(cli, '/articles/', 200, superuser_id)
    assert len(json['data']) == article_count

