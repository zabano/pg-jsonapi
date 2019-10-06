import pytest

from jsonapi.tests.util import *


#
# single attribute sort (collection)
#

@pytest.mark.asyncio
async def test_single_1(users, user_count):
    async with get_collection(users, {'sort': 'id'}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == user_count
        for user_id, user in enumerate(json['data'], start=1):
            assert_object(user, 'user')
            assert user['id'] == str(user_id)


@pytest.mark.asyncio
async def test_single_2(users, user_count):
    async with get_collection(users, {'sort': '+id'}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == user_count
        for user_id, user in enumerate(json['data'], start=1):
            assert_object(user, 'user')
            assert user['id'] == str(user_id)


@pytest.mark.asyncio
async def test_single_3(users, user_count):
    async with get_collection(users, {'sort': '-id'}) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) == user_count
        for user_id, user in enumerate(reversed(json['data']), start=1):
            assert_object(user, 'user')
            assert user['id'] == str(user_id)


#
# single attribute sort (related)
#

@pytest.mark.asyncio
async def test_single_4(users, user_1_id, superuser_id):
    async with get_related(users, user_1_id, 'articles',
                           {'sort': 'id'},
                           login=superuser_id) as json:
        assert len(json['data']) > 0
        id_list = [int(article['id']) for article in json['data']]
        assert id_list == sorted(id_list)


@pytest.mark.asyncio
async def test_single_5(users, user_1_id, superuser_id):
    async with get_related(users, user_1_id, 'articles',
                           {'sort': '+id'},
                           login=superuser_id) as json:
        assert len(json['data']) > 0
        id_list = [int(article['id']) for article in json['data']]
        assert id_list == sorted(id_list)


@pytest.mark.asyncio
async def test_single_6(users, user_1_id, superuser_id):
    async with get_related(users, user_1_id, 'articles',
                           {'sort': '-id'},
                           login=superuser_id) as json:
        assert len(json['data']) > 0
        id_list = [int(article['id']) for article in json['data']]
        assert id_list == sorted(id_list, reverse=True)


#
# aggregate sort (collection)
#

@pytest.mark.asyncio
async def test_aggregate_1(users, user_count):
    async with get_collection(users, {'sort': 'article-count'}) as json:
        assert len(json['data']) == user_count
        for user in json['data']:
            check_user(user)
            assert_attribute_does_not_exist(user, 'articleCount')


@pytest.mark.asyncio
async def test_aggregate_2(users, user_count):
    async with get_collection(users, {'fields[user]': 'email',
                                      'sort': 'article-count'}) as json:
        assert len(json['data']) == user_count
        for user in json['data']:
            assert_object(user, 'user')
            assert_attribute(user, 'email')
            assert_attribute_does_not_exist(user, 'first')
            assert_attribute_does_not_exist(user, 'createdOn')
            assert_attribute_does_not_exist(user, 'articleCount')


@pytest.mark.asyncio
async def test_aggregate_3(users, user_count):
    async with get_collection(users, {'fields[user]': 'email,article-count',
                                      'sort': 'article-count'}) as json:
        assert len(json['data']) == user_count
        for user in json['data']:
            assert_object(user, 'user')
            assert_attribute(user, 'email')
            assert_attribute(user, 'articleCount', lambda v: is_size(v))
            assert_attribute_does_not_exist(user, 'created_on')
            assert_attribute_does_not_exist(user, 'first')
            assert_attribute_does_not_exist(user, 'last')


@pytest.mark.asyncio
async def test_aggregate_4(users, user_count):
    async with get_collection(users, {'fields[user]': 'article-count',
                                      'sort': 'article-count'}) as json:
        assert len(json['data']) == user_count
        for user in json['data']:
            assert_object(user, 'user')
            assert_attribute(user, 'articleCount', lambda v: is_size(v))
            assert_attribute_does_not_exist(user, 'email')
            assert_attribute_does_not_exist(user, 'createdOn')
            assert_attribute_does_not_exist(user, 'first')
            assert_attribute_does_not_exist(user, 'last')


#
# aggregate sort (related)
#

@pytest.mark.asyncio
async def test_aggregate_5(users, user_1_id):
    async with get_related(users, user_1_id, 'articles',
                           {'sort': 'keyword-count'},
                           login=user_1_id) as json:
        assert isinstance(json['data'], list)
        assert len(json['data']) > 0
        for article in json['data']:
            check_article(article)
            assert_attribute_does_not_exist(article, 'keywordCount')


@pytest.mark.asyncio
async def test_aggregate_6(users, user_1_id):
    async with get_related(users, user_1_id, 'articles',
                           {'fields[article]': 'title',
                            'sort': 'keyword-count'},
                           login=user_1_id) as json:
        assert len(json['data']) > 0
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'title')
            assert_attribute_does_not_exist(article, 'body')
            assert_attribute_does_not_exist(article, 'createdOn')
            assert_attribute_does_not_exist(article, 'keywordCount')


@pytest.mark.asyncio
async def test_aggregate_7(users, user_1_id):
    async with get_related(users, user_1_id, 'articles',
                           {'fields[article]': 'title,keyword-count',
                            'sort': 'keyword-count'},
                           login=user_1_id) as json:
        assert len(json['data']) > 0
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'title')
            assert_attribute(article, 'keywordCount', lambda v: is_size(v))
            assert_attribute_does_not_exist(article, 'createdOn')
            assert_attribute_does_not_exist(article, 'body')


@pytest.mark.asyncio
async def test_aggregate_8(users, user_1_id):
    async with get_related(users, user_1_id, 'articles',
                           {'fields[article]': 'keyword-count',
                            'sort': 'keyword-count'},
                           login=user_1_id) as json:
        assert len(json['data']) > 0
        for article in json['data']:
            assert_object(article, 'article')
            assert_attribute(article, 'keywordCount', lambda v: is_size(v))
            assert_attribute_does_not_exist(article, 'title')
            assert_attribute_does_not_exist(article, 'createdOn')
            assert_attribute_does_not_exist(article, 'body')

#
# multi attribute sort
#
