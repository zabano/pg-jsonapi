import random

import pytest

from jsonapi.tests.util import *


def _check_user(json, user, validator=None):
    check_user(user, validator)
    for article in assert_relationship(user, 'articles'):
        assert_object(article, 'article')
        assert_included(json, article)
    for bio in assert_relationship(user, 'bio'):
        assert_object(bio, 'user-bio')
        assert_included(json, bio)


@pytest.mark.asyncio
async def test_1(users, superuser_id, user_count):
    for user_id in random.sample(range(1, user_count), 3):
        async with get_object(users, user_id,
                              {'include': 'articles.comments.replies,bio'},
                              login=superuser_id) as json:
            _check_user(json, json['data'])


@pytest.mark.asyncio
async def test_2(users, user_1_id):
    async with get_collection(users,
                              {'include': 'articles.comments.replies,bio',
                               'filter[id:lt]': '100'},
                              login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for user in json['data']:
            _check_user(json, user, lambda v: int(v) < 100)


@pytest.mark.asyncio
async def test_3(articles, superuser_id, article_count):
    for article_id in random.sample(range(1, article_count), 3):
        async with get_related(articles, article_id, 'author',
                               {'include': 'articles.comments.replies,bio'},
                               login=superuser_id) as json:
            _check_user(json, json['data'])


@pytest.mark.asyncio
async def test_4(articles, user_1_id):
    async with get_collection(articles,
                              {'include': 'keywords'},
                              login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
