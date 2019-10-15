import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_no_fieldset(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count):
        async with get_object(articles, article_id, login=superuser_id) as json:
            article = assert_object(json['data'], 'article', lambda v: int(v) == article_id)
            assert_attribute(article, 'title')
            assert_attribute(article, 'body')
            assert_attribute(article, 'is-published')
            assert_attribute(article, 'created-on')
            assert_attribute(article, 'updated-on')
            assert_no_attribute(article, 'comment-count')
            assert_no_attribute(article, 'keyword-count')


@pytest.mark.asyncio
async def test_fieldset(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count):
        async with get_object(articles, article_id,
                              {'fields[article]': 'title'},
                              login=superuser_id) as json:
            article = assert_object(json['data'], 'article')
            assert_attribute(article, 'title')
            assert_no_attribute(article, 'body')
            assert_no_attribute(article, 'is-published')
            assert_no_attribute(article, 'created-on')
            assert_no_attribute(article, 'updated-on')
            assert_no_attribute(article, 'comment-count')
            assert_no_attribute(article, 'keyword-count')


@pytest.mark.asyncio
async def test_include_fieldset(articles, article_count, superuser_id):
    for article_id in sample_integers(1, article_count):
        async with get_object(articles, article_id,
                                  {'include': 'author',
                                   'fields[article]': 'title,comment-count',
                                   'fields[user]': 'email'},
                                  login=superuser_id) as json:
            article = assert_object(json['data'], 'article')
            assert_attribute(article, 'title')
            assert_no_attribute(article, 'body')
            assert_no_attribute(article, 'is-published')
            assert_no_attribute(article, 'created-on')
            assert_no_attribute(article, 'updated-on')
            assert_attribute(article, 'comment-count')
            assert_no_attribute(article, 'keyword-count')

            author = assert_relationship(article, 'author')
            assert_object(author, 'user')
            included = assert_included(json, author)
            assert_attribute(included, 'email')
            assert_no_attribute(included, 'first')
            assert_no_attribute(included, 'last')
            assert_no_attribute(included, 'name')
            assert_no_attribute(included, 'status')
            assert_no_attribute(included, 'created-on')
            assert_no_attribute(included, 'article-count')
