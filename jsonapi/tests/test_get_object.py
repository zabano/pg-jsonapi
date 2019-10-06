import random

import pytest

from jsonapi.exc import Forbidden, NotFound
from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_1(users, user_1_id):
    async with get_object(users, user_1_id) as json:
        check_user(json['data'], lambda v: int(v) == user_1_id)
        assert_attribute_does_not_exist(json['data'], 'article-count')


@pytest.mark.asyncio
async def test_2(users, user_2_id):
    async with get_object(users, user_2_id, {'include': 'articles'}) as json:
        assert_object(json['data'], 'user', lambda v: int(v) == user_2_id)
        assert_relationship(json['data'], 'articles', lambda size: size == 0)
        assert 'included' not in json


@pytest.mark.asyncio
async def test_forbidden(articles, article_count):
    for article_id in random.sample(range(1, article_count), 10):
        with pytest.raises(Forbidden):
            await articles.get_object({}, article_id)


@pytest.mark.asyncio
async def test_not_found(articles, article_count):
    with pytest.raises(NotFound):
        await articles.get_object({}, article_count + 1)


#
# logged in access
#


@pytest.mark.asyncio
async def test_logged_in_1(users, user_1_id):
    async with get_object(users, user_1_id, {'include': 'articles'}, login=user_1_id) as json:
        assert_object(json['data'], 'user', lambda v: int(v) == user_1_id)
        assert_relationship(json['data'], 'articles', lambda size: size > 0)
        for article in get_relationship(json['data'], 'articles'):
            assert_object(article, 'article')
        assert 'included' in json
        assert len(json['included']) > 0
        for article in json['included']:
            check_article(article)


@pytest.mark.asyncio
async def test_logged_in_2(users, user_2_id):
    async with get_object(users, user_2_id, {'include': 'articles'}, login=user_2_id) as json:
        assert_object(json['data'], 'user', lambda v: int(v) == user_2_id)
        assert_relationship(json['data'], 'articles', lambda size: size == 0)
        assert 'included' not in json


@pytest.mark.asyncio
async def test_logged_in_3(articles, user_1_id, user_1_article_id_readable):
    async with get_object(articles, user_1_article_id_readable, login=user_1_id) as json:
        check_article(json['data'], lambda v: int(v) == user_1_article_id_readable)


#
# superuser access
#

@pytest.mark.asyncio
async def test_superuser_1(users, superuser_id, user_1_id):
    async with get_object(users, user_1_id, {'include': 'articles'}, login=superuser_id) as json:
        assert_relationship(json['data'], 'articles', lambda size: size > 0)
        assert 'included' in json


@pytest.mark.asyncio
async def test_superuser_2(users, superuser_id, user_2_id):
    async with get_object(users, user_2_id, {'include': 'articles'}, login=superuser_id) as json:
        assert_relationship(json['data'], 'articles', lambda size: size == 0)
        assert 'included' not in json


@pytest.mark.asyncio
async def test_superuser_3(users, superuser_id):
    async with get_object(users, superuser_id, {'include': 'articles'}, login=superuser_id) as json:
        assert_relationship(json['data'], 'articles', lambda size: size > 0)
        assert 'included' in json
