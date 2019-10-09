import pytest

from jsonapi.tests.util import *


def _check_user(user):
    assert_object(user, 'user')
    assert_attribute(user, 'email')
    assert_attribute(user, 'articleCount', lambda v: is_size(v))
    assert_attribute_does_not_exist(user, 'status')
    assert_attribute_does_not_exist(user, 'createdOn')


@pytest.mark.asyncio
async def test_1(articles, user_1_id):
    async with get_collection(articles,
                              {'fields[article]': 'title,created-on,keyword-count,comment-count'},
                              login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'title')
            assert_attribute(article, 'createdOn')
            assert_attribute(article, 'commentCount', lambda v: is_size(v))
            assert_attribute(article, 'keywordCount', lambda v: is_size(v))
            assert_attribute_does_not_exist(article, 'body')
            assert_attribute_does_not_exist(article, 'isPublished')
            assert_attribute_does_not_exist(article, 'updatedOn')


@pytest.mark.asyncio
async def test_2(users, user_1_id):
    async with get_object(users, user_1_id,
                          {'fields[user]': 'email,article-count'},
                          login=user_1_id) as json:
        assert isinstance(json['data'], dict)
        _check_user(json['data'])


@pytest.mark.asyncio
async def test_3(users, user_1_id):
    async with get_collection(users,
                              {'fields[user]': 'email,article-count'},
                              login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for user in json['data']:
            _check_user(user)


@pytest.mark.asyncio
async def test_4(articles, user_1_id):
    async with get_collection(articles,
                              {'include': 'author',
                               'fields[user]': 'email,article-count'},
                              login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for user in json['included']:
            _check_user(user)


@pytest.mark.asyncio
async def test_5(articles, superuser_id):
    async with get_related(articles, 52, 'author',
                           {'fields[user]': 'email,article-count'},
                           login=superuser_id) as json:
        assert isinstance(json['data'], dict)
        _check_user(json['data'])

