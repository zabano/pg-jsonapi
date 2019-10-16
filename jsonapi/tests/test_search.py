import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_1(users, articles, user_count, article_count):
    async with search('John', {}, users, articles) as json:
        assert_meta(json, 'total', lambda v: v == user_count + article_count)
        assert_meta(json, 'searchType', lambda v: (v['user']['total'] == user_count and
                                                   v['article']['total'] == article_count))
        assert_collection(json, 'user')


@pytest.mark.asyncio
async def test_2(users, articles, user_1_id):
    async with search('John', {}, users, articles, login=user_1_id) as json:
        assert_collection(json, ('user', 'article'))


@pytest.mark.asyncio
async def test_3(users, articles, superuser_id):
    async with search('John', {}, users, articles, login=superuser_id) as json:
        assert_collection(json, ('user', 'article'))
