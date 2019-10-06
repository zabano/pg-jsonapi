import pytest

from jsonapi.exc import Forbidden
from jsonapi.tests.util import *


#
# public access (no login)
#

@pytest.mark.asyncio
async def test_1(users, user_1_id):
    async with get_related(users, user_1_id, 'articles') as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 0


@pytest.mark.asyncio
async def test_2(users, user_2_id):
    async with get_related(users, user_2_id, 'articles') as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 0


@pytest.mark.asyncio
async def test_3(articles, user_1_id):
    with pytest.raises(Forbidden):
        await articles.get_related({}, user_1_id, 'author')


#
# logged in access
#


@pytest.mark.asyncio
async def test_logged_in_1(users, user_1_id):
    async with get_related(users, user_1_id, 'articles', login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for article in json['data']:
            check_article(article)


@pytest.mark.asyncio
async def test_logged_in_2(users, user_2_id):
    async with get_related(users, user_2_id, 'articles', login=user_2_id) as json:
        assert len(json['data']) == 0


#
# superuser access
#

@pytest.mark.asyncio
async def test_superuser_1(users, superuser_id, user_1_id):
    async with get_related(users, user_1_id, 'articles', login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for article in json['data']:
            check_article(article)


@pytest.mark.asyncio
async def test_superuser_2(users, superuser_id, user_2_id):
    async with get_related(users, user_2_id, 'articles', login=superuser_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == 0


@pytest.mark.asyncio
async def test_superuser_3(articles, superuser_id):
    async with get_related(articles, 1, 'author', login=superuser_id) as json:
        check_user(json['data'])
