import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_one_to_one(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count):
        async with get_object(users, user_id,
                              {'include': 'bio'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'user', lambda v: int(v) == user_id)
            check_included(json, json['data'], 'bio', 'user-bio',
                           lambda size: size <= 1,
                           lambda v: int(v) == user_id)


@pytest.mark.asyncio
async def test_many_to_one(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_object(articles, article_id,
                              {'include': 'author'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'article', lambda v: int(v) == article_id)
            check_included(json, json['data'], 'author', 'user', lambda size: size == 1)


@pytest.mark.asyncio
async def test_one_to_many(users, user_count, superuser_id):
    for user_id in sample_integers(1, user_count):
        async with get_object(users, user_id,
                              {'include': 'articles'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'user', lambda v: int(v) == user_id)
            check_included(json, json['data'], 'articles', 'article', lambda size: size >= 0)


@pytest.mark.asyncio
async def test_many_to_many(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count, 10):
        async with get_object(articles, article_id,
                              {'include': 'keywords'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'article', lambda v: int(v) == article_id)
            check_included(json, json['data'], 'keywords', 'keyword', lambda size: size >= 0)


@pytest.mark.dev
@pytest.mark.asyncio
async def test_1_multiple(users, superuser_id, user_count):
    for user_id in sample_integers(1, user_count, 1):
        async with get_object(users, user_id,
                              {'include': 'articles.comments.replies,'
                                          'articles.keywords,'
                                          'articles.author,'
                                          'articles.publisher,'
                                          'bio'},
                              login=superuser_id) as json:
            assert_object(json['data'], 'user')
            for bio in assert_relationship(json['data'], 'bio'):
                assert_object(bio, 'user-bio')
                assert_included(json, article)
            for article in assert_relationship(json['data'], 'articles'):
                assert_object(article, 'article')
                assert_included(json, article)
            for included in json['included']:
                if included['type'] == 'article':
                    for author in assert_relationship(included, 'author'):
                        assert_object(author, 'user')
                        assert_included(json, author)
                    for publisher in assert_relationship(included, 'publisher'):
                        assert_object(publisher, 'user')
                        assert_included(json, publisher)
                    for comment in assert_relationship(included, 'comments'):
                        assert_object(comment, 'comment')
                        assert_included(json, comment)
                    for keyword in assert_relationship(included, 'keywords'):
                        assert_object(keyword, 'keyword')
                        assert_included(json, comment)
                elif included['type'] == 'comment':
                    for reply in assert_relationship(included, 'replies'):
                        assert_object(reply, 'reply')
                        assert_included(json, reply)
