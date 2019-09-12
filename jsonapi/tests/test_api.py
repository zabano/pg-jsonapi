import pytest
from jsonapi.tests.app import app
from collections.abc import Sequence


async def _get(cli, url):
    response = await cli.get(url)
    assert response.status_code == 200
    json = await response.json
    assert 'data' in json
    return json


def _check_object(data, object_type, object_id, *attributes):
    assert 'type' in data and data['type'] == object_type
    assert 'id' in data
    assert data['id'] in (str(x) for x in object_id) if isinstance(object_id, Sequence) else \
        data['id'] == str(object_id)
    assert 'attributes' in data
    for name in attributes:
        assert name in data['attributes']


@pytest.fixture()
def cli():
    return app.test_client()


@pytest.mark.asyncio
async def test_get_users(cli):
    json = await _get(cli, '/users/')
    assert len(json['data']) == 2
    for rec in json['data']:
        _check_object(rec, 'user', [1, 2])


@pytest.mark.asyncio
async def test_get_users_include(cli):
    json = await _get(cli, '/users/?include=articles.comments.author,name&fields[name]=first,last')
    assert len(json['data']) == 2
    for rec in json['data']:
        _check_object(rec, 'user', [1, 2])
        assert 'relationships' in rec
        assert 'articles' in rec['relationships']
        articles = rec['relationships']['articles']
        assert isinstance(articles, list)
        for article in articles:
            assert isinstance(article, dict) and len(article) == 2
            assert 'id' in article and 'type' in article and article['type'] == 'article'
        assert 'name' in rec['relationships']
        name = rec['relationships']['name']
        assert isinstance(name, dict) and len(name) == 2
        assert 'id' in name and 'type' in name and name['type'] == 'name'
    assert 'included' in json
    for rec in json['included']:
        assert 'type' in rec and rec['type'] in ('article', 'comment', 'name', 'user')
        assert 'id' in rec and isinstance(rec['id'], str)
        assert 'attributes' in rec
        if rec['type'] == 'article':
            assert 'relationships' in rec
            assert 'comments' in rec['relationships'] \
                   and isinstance(rec['relationships']['comments'], list)
        if rec['type'] == 'name':
            assert 'attributes' in rec
            assert 'first' in rec['attributes'] and 'last' in rec['attributes']
            assert 'full' not in rec['attributes']
        if rec['type'] == 'comment':
            assert 'relationships' in rec
            assert 'author' in rec['relationships']
            assert rec['relationships']['author'] is not None
            assert rec['relationships']['author']['type'] == 'user'
            assert rec['relationships']['author']['id'] in ('1', '2')


@pytest.mark.asyncio
async def test_get_user_1(cli):
    json = await _get(cli, '/users/1')
    _check_object(json['data'], 'user', 1, 'email', 'status')


@pytest.mark.asyncio
async def test_get_user_1_name(cli):
    json = await _get(cli, '/users/1/name')
    _check_object(json['data'], 'name', 1, 'first', 'last')


@pytest.mark.asyncio
async def test_get_user_1_articles(cli):
    json = await _get(cli, '/users/1/articles/')
    assert len(json['data']) == 3
    for rec in json['data']:
        _check_object(rec, 'article', (1, 2, 4), 'title', 'body')


@pytest.mark.asyncio
async def test_get_articles(cli):
    json = await _get(cli, '/articles/')
    assert len(json['data']) == 5
    for rec in json['data']:
        _check_object(rec, 'article', (1, 2, 3, 4, 5), 'title', 'body')


@pytest.mark.asyncio
async def test_get_article_1_author(cli):
    json = await _get(cli, '/articles/1/author')
    _check_object(json['data'], 'user', 1, 'email', 'status')


@pytest.mark.asyncio
async def test_get_article_1_comments(cli):
    json = await _get(cli, '/articles/1/comments/')
    assert len(json['data']) == 1
    for rec in json['data']:
        _check_object(rec, 'comment', 1, 'body')


@pytest.mark.asyncio
async def test_get_article_1_keywords(cli):
    json = await _get(cli, '/articles/1/keywords/')
    assert len(json['data']) == 4
    for rec in json['data']:
        _check_object(rec, 'keyword', (1, 2, 3, 4), 'name')
