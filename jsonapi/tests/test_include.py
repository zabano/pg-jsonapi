import random

import pytest

from jsonapi.tests.util import *


def _check_user(user):
    check_user(user)
    articles = assert_relationship(user, 'articles')
    for article in articles:
        assert_object(article, 'article')
    bio = assert_relationship(user, 'bio')
    if bio:
        assert_object(bio, 'user-bio')
    return bio is not None or len(articles) > 0


def _check_included(json):
    assert 'included' in json
    for obj in json['included']:
        assert obj['type'] in ('article', 'comment', 'reply', 'user-bio')
        if obj['type'] == 'article':
            check_article(obj)
            for comment in assert_relationship(obj, 'comments'):
                assert_object(comment, 'comment')
        elif obj['type'] == 'comment':
            check_comment(obj)
            for reply in assert_relationship(obj, 'replies'):
                assert_object(reply, 'reply')
        elif obj['type'] == 'reply':
            check_reply(obj)
            assert 'relationships' not in obj
        elif obj['type'] == 'user-bio':
            check_user_bio(obj)
            assert 'relationships' not in obj


@pytest.mark.asyncio
async def test_1(users, superuser_id, user_count):
    for user_id in random.sample(range(1, user_count), 10):
        async with get_object(users, user_id,
                              {'include': 'articles.comments.replies,bio'},
                              login=superuser_id) as json:
            included = _check_user(json['data'])
            if included:
                _check_included(json)


@pytest.mark.asyncio
async def test_2(users, user_1_id):
    async with get_collection(users,
                              {'include': 'articles.comments.replies,bio'},
                              login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        included = False
        for user in json['data']:
            inc = _check_user(user)
            if inc:
                included = True
        if included:
            _check_included(json)


@pytest.mark.asyncio
async def test_3(articles, superuser_id, article_count):
    for article_id in random.sample(range(1, article_count), 10):
        async with get_related(articles, article_id, 'author',
                               {'include': 'articles.comments.replies,bio'},
                               login=superuser_id) as json:
            included = _check_user(json['data'])
            if included:
                _check_included(json)
