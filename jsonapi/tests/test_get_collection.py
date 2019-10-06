import pytest

from jsonapi.tests.util import *


#
# public access (no login)
#


@pytest.mark.asyncio
async def test_1(users, user_count):
    async with get_collection(users) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == user_count
        check_user(json['data'][0])
        check_user(json['data'][-1])


@pytest.mark.asyncio
async def test_2(articles):
    async with get_collection(articles) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 0


#
# logged in access
#


@pytest.mark.asyncio
async def test_logged_in_1(articles, user_1_id, article_count):
    async with get_collection(articles, login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert 0 < len(json['data']) < article_count


@pytest.mark.asyncio
async def test_logged_in_2(articles, user_2_id, article_count):
    async with get_collection(articles, login=user_2_id) as json:
        assert isinstance(json['data'], list)
        assert 0 < len(json['data']) < article_count


#
# superuser access
#

@pytest.mark.asyncio
async def test_superuser_1(articles, superuser_id, article_count):
    async with get_collection(articles, login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == article_count
