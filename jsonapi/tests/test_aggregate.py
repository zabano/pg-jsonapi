import pytest

from jsonapi.tests.util import *


def _check_user(user):
    assert_object(user, 'user')
    assert_attribute(user, 'email')
    assert_attribute(user, 'articleCount', lambda v: is_positive(v))
    assert_attribute_does_not_exist(user, 'status')
    assert_attribute_does_not_exist(user, 'createdOn')


@pytest.mark.asyncio
async def test_1(cli, user_1_id):
    json = await get(cli, dict(
        url='/articles/',
        fields=dict(
            article='title,created-on,keyword-count,comment-count'
        )), 200, user_1_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for article in json['data']:
        assert_object(article, 'article')
        assert_attribute(article, 'title')
        assert_attribute(article, 'createdOn')
        assert_attribute(article, 'commentCount', lambda v: is_positive(v))
        assert_attribute(article, 'keywordCount', lambda v: is_positive(v))
        assert_attribute_does_not_exist(article, 'body')
        assert_attribute_does_not_exist(article, 'isPublished')
        assert_attribute_does_not_exist(article, 'updatedOn')


@pytest.mark.asyncio
async def test_2(cli, user_1_id):
    json = await get(cli, dict(
        url='/users/{}'.format(user_1_id),
        fields=dict(
            user='email,article-count'
        )), 200, user_1_id)
    assert isinstance(json['data'], dict)
    _check_user(json['data'])


@pytest.mark.asyncio
async def test_3(cli, user_1_id):
    json = await get(cli, dict(
        url='/users/',
        fields=dict(
            user='email,article-count'
        )), 200, user_1_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for user in json['data']:
        _check_user(user)


@pytest.mark.asyncio
async def test_4(cli, user_1_id):
    json = await get(cli, dict(
        url='/articles/',
        include='author',
        fields=dict(
            user='email,article-count'
        )), 200, user_1_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for user in json['included']:
        _check_user(user)


@pytest.mark.asyncio
async def test_5(cli, user_1_id):
    qs = 'fields[user]=email,article-count'
    json = await get(cli, dict(
        url='/articles/52/author',
        fields=dict(
            user='email,article-count'
        )), 200, user_1_id)
    assert isinstance(json['data'], dict)
    _check_user(json['data'])


@pytest.mark.asyncio
async def test_6(cli, user_1_id):
    json = await get(cli, dict(
        url='/articles/',
        fields=dict(
            article='title,author-count'
        )), 400, user_1_id)
    assert_error(json, 400)
