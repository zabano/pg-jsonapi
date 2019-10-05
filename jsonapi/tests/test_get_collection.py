import pytest

from jsonapi.tests.util import *


#
# public access (no login)
#


@pytest.mark.asyncio
async def test_1(cli, user_count):
    json = await get(cli, '/users/')
    assert isinstance(json['data'], list)
    assert len(json['data']) == user_count
    check_user(json['data'][0])
    check_user(json['data'][-1])


@pytest.mark.asyncio
async def test_2(cli):
    json = await get(cli, '/articles/')
    assert isinstance(json['data'], list)
    assert len(json['data']) == 0


#
# logged in access
#


@pytest.mark.asyncio
async def test_logged_in_1(cli, user_1_id, article_count):
    json = await get(cli, '/articles/', 200, user_1_id)
    assert isinstance(json['data'], list)
    assert 0 < len(json['data']) < article_count


@pytest.mark.asyncio
async def test_logged_in_2(cli, user_2_id, article_count):
    json = await get(cli, '/articles/', 200, user_2_id)
    assert isinstance(json['data'], list)
    assert 0 < len(json['data']) < article_count


#
# superuser access
#

@pytest.mark.asyncio
async def test_superuser_1(cli, superuser_id, article_count):
    json = await get(cli, '/articles/', 200, superuser_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) == article_count
