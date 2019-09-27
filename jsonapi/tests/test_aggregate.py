import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_aggregate_get_keyword_and_comment_counts_as_user_1(cli, user_1_id):
    qs = 'fields[article]=title,created-on,keyword-count,comment-count'
    json = await get(cli, '/articles/?{}'.format(qs), 200, user_1_id)
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
async def test_aggregate_get_article_count_as_user_1(cli, user_1_id):
    qs = 'fields[user]=email,article-count'
    json = await get(cli, '/users/{}?{}'.format(user_1_id, qs), 200, user_1_id)
    assert isinstance(json['data'], dict)
    assert_object(json['data'], 'user')
    assert_attribute(json['data'], 'email')
    assert_attribute(json['data'], 'articleCount', lambda v: is_positive(v))
    assert_attribute_does_not_exist(json['data'], 'status')
    assert_attribute_does_not_exist(json['data'], 'createdOn')


@pytest.mark.asyncio
async def test_aggregate_get_users_article_count_as_user_1(cli, user_1_id):
    qs = 'fields[user]=email,article-count'
    json = await get(cli, '/users/?{}'.format(qs), 200, user_1_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for user in json['data']:
        assert_object(user, 'user')
        assert_attribute(user, 'email')
        assert_attribute(user, 'articleCount', lambda v: is_positive(v))
        assert_attribute_does_not_exist(user, 'status')
        assert_attribute_does_not_exist(user, 'createdOn')


@pytest.mark.asyncio
async def test_aggregate_get_articles_count_as_user_1(cli, user_1_id):
    qs = 'include=author&fields[user]=email,article-count'
    json = await get(cli, '/articles/?{}'.format(qs), 200, user_1_id)
    assert isinstance(json['data'], list)
    assert len(json['data']) > 0
    for user in json['included']:
        assert_object(user, 'user')
        assert_attribute(user, 'email')
        assert_attribute(user, 'articleCount', lambda v: is_positive(v))
        assert_attribute_does_not_exist(user, 'status')
        assert_attribute_does_not_exist(user, 'createdOn')


@pytest.mark.asyncio
async def test_aggregate_get_author_article_count_as_user_1(cli, user_1_id):
    qs = 'fields[user]=email,article-count'
    json = await get(cli, '/articles/52/author?{}'.format(qs), 200, user_1_id)
    assert isinstance(json['data'], dict)
    assert_object(json['data'], 'user')
    assert_attribute(json['data'], 'email')
    assert_attribute(json['data'], 'articleCount', lambda v: is_positive(v))
    assert_attribute_does_not_exist(json['data'], 'status')
    assert_attribute_does_not_exist(json['data'], 'createdOn')


@pytest.mark.asyncio
async def test_aggregate_get_author_count_as_user_1(cli, user_1_id):
    qs = 'fields[article]=title,author-count'
    json = await get(cli, '/articles/?{}'.format(qs), 400, user_1_id)
    assert_error(json, 400)
