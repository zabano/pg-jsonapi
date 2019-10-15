import operator

import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_int(articles, article_count, superuser_id):
    for val, limit in ((4, 10), (5, 20)):
        length_by_op = {'': 1, 'eq': 1, 'lt': val - 1, 'le': val,
                        'gt': min(limit, article_count - val),
                        'ge': min(limit, article_count - val + 1)}
        for op in length_by_op.keys():
            filter_name = '{}:{}'.format('id', op) if op else 'id'
            compare = getattr(operator, op if op else 'eq')
            async with get_collection(articles,
                                      {'fields[article]': 'id',
                                       'filter[{}]'.format(filter_name): str(val),
                                       'page[size]': limit},
                                      login=superuser_id) as json:
                for article in assert_collection(json, 'article',
                                                 lambda size: size == length_by_op[op]):
                    assert_object(article, 'article', lambda v: compare(int(v), val))


@pytest.mark.asyncio
async def test_int_multiple(articles, article_count, superuser_id):
    for length in (5, 12, 32):
        id_list = sample_integers(1, article_count, length)
        async with get_collection(articles,
                                  {'fields[article]': 'id',
                                   'filter[id]': ','.join(str(x) for x in id_list)},
                                  login=superuser_id) as json:
            for article in assert_collection(json, 'article', lambda size: size == length):
                assert_object(article, 'article', lambda v: int(v) in id_list)


@pytest.mark.asyncio
async def test_int_range(articles, article_count, superuser_id):
    for (filter_spec, id_list) in (
            ('<4,6,>=9,<12', (1, 2, 3, 6, 9, 10, 11)),
            ('<4,6,>=9,<12,none', (1, 2, 3, 6, 9, 10, 11)),
            ('<10,>=20,30', list(range(1, 10)) + list(range(20, 31))),
            ('>2000,<1000', list(range(1, 1000)) + list(range(2001, article_count + 1))),
            ('3,<8,10,>=15,<20', (3, 4, 5, 6, 7, 10, 15, 16, 17, 18, 19))):
        async with get_collection(articles,
                                  {'fields[article]': 'id',
                                   'filter[id]': filter_spec},
                                  login=superuser_id) as json:
            for article in assert_collection(json, 'article', lambda size: size == len(id_list)):
                assert_object(article, 'article', lambda v: int(v) in id_list)


@pytest.mark.asyncio
async def test_bool(articles, superuser_id, true_values, false_values):
    for val in true_values:
        async with get_collection(articles,
                                  {'fields[article]': 'is-published',
                                   'filter[is-published]': val,
                                   'page[size]': 10},
                                  login=superuser_id) as json:
            for article in assert_collection(json, 'article'):
                assert_attribute(article, 'is-published', lambda v: v is True)
    for val in false_values:
        async with get_collection(articles,
                                  {'fields[article]': 'is-published',
                                   'filter[is-published]': val,
                                   'page[size]': 10},
                                  login=superuser_id) as json:
            for article in assert_collection(json, 'article'):
                assert_attribute(article, 'is-published', lambda v: v is False)


@pytest.mark.asyncio
async def test_enum(users, user_count):
    for val in ('active', 'pending', 'active,pending'):
        async with get_collection(users, {'filter[status]': val}) as json:
            assert_meta(json, 'total', lambda v: int(v) == user_count)
            total_filtered = assert_meta(json, 'totalFiltered')
            assert total_filtered > 0
            for user in assert_collection(json, 'user', lambda size: size == total_filtered):
                assert_attribute(user, 'status',
                                 lambda v: v in val.split(',') if ',' in val else v == val)


@pytest.mark.asyncio
async def test_datetime(users, user_count):
    for val in ('2019-10-01T00:00:00Z', '2019-10-01T00:00:00',
                '2019-10-01T00:00', '2019-10-01', '2019-10'):
        async with get_collection(users,
                                  {'filter[created-on:gt]': val,
                                   'sort': 'created-on'}) as json:
            assert_meta(json, 'total', lambda v: int(v) == user_count)
            total_filtered = assert_meta(json, 'totalFiltered')
            assert total_filtered > 0
            for user in assert_collection(json, 'user', lambda size: size == total_filtered):
                assert_attribute(user, 'created-on',
                                 lambda v: parse_datetime(v) > dt.datetime(2019, 10, 1))

    async with get_collection(users,
                              {'filter[created-on]': '>2018-08,<2018-09,'
                                                     '>2019-08,<2019-09'}) as json:
        assert_meta(json, 'total', lambda v: int(v) == user_count)
        total_filtered = assert_meta(json, 'totalFiltered')
        assert total_filtered > 0
        for user in assert_collection(json, 'user', lambda size: size == total_filtered):
            assert_attribute(
                user, 'created-on',
                lambda v: (dt.datetime(2018, 8, 1) < parse_datetime(v)
                           < dt.datetime(2018, 9, 1)) or
                          (dt.datetime(2019, 8, 1) < parse_datetime(v)
                           < dt.datetime(2019, 9, 1)))


@pytest.mark.asyncio
async def test_aggregate(articles, article_count, superuser_id):
    async with get_collection(articles,
                              {'filter[comment-count:gt]': '30',
                               'filter[keyword-count]': '3',
                               'fields[article]': 'comment-count,keyword-count'},
                              login=superuser_id) as json:
        assert_meta(json, 'total', lambda v: int(v) == article_count)
        total_filtered = assert_meta(json, 'totalFiltered')
        assert total_filtered > 0
        for article in assert_collection(json, 'article', lambda size: size == total_filtered):
            assert_object(article, 'article')
            assert_attribute(article, 'comment-count', lambda v: v > 30)
            assert_attribute(article, 'keyword-count', lambda v: v == 3)


@pytest.mark.asyncio
async def test_mixed(users, user_count, superuser_id):
    async with get_collection(users,
                              {'filter[created-on:lt]': '2019-10-15',
                               'filter[status]': 'pending',
                               'filter[id:gt]': '100',
                               'filter[article-count]:le': '2',
                               'fields[user]': 'created-on,status,article-count'},
                              login=superuser_id) as json:
        assert_meta(json, 'total', lambda v: int(v) == user_count)
        total_filtered = assert_meta(json, 'totalFiltered')
        assert total_filtered > 0
        for user in assert_collection(json, 'user', lambda size: size == total_filtered):
            assert_object(user, 'user', lambda v: int(v) > 100)
            assert_attribute(user, 'status', lambda v: v == 'pending')
            assert_attribute(user, 'article-count', lambda v: v <= 2)
            assert_attribute(user, 'created-on',
                             lambda v: parse_datetime(v) < dt.datetime(2019, 10, 1))


@pytest.mark.asyncio
async def test_custom(articles, article_count, superuser_id):
    async with get_collection(articles,
                              {'filter[custom]': '15',
                               'filter[is-published]': 't',
                               'fields[article]': 'title,is-published'},
                              login=superuser_id) as json:
        assert_meta(json, 'total', lambda v: int(v) == article_count)
        total_filtered = assert_meta(json, 'totalFiltered')
        assert total_filtered > 0
        for article in assert_collection(json, 'article', lambda size: size == total_filtered):
            assert_object(article, 'article')
            assert_attribute(article, 'title', lambda v: len(v) == 15)
            assert_attribute(article, 'isPublished', lambda v: v is True)


@pytest.mark.asyncio
async def test_relationship(articles, article_count, superuser_id):
    for args in [{'filter[publisher]': 'none'},
                 {'filter[publisher:eq]': 'none'},
                 {'filter[publisher.id]': 'none'},
                 {'filter[publisher.id:eq]': 'none'}]:
        async with get_collection(articles, args, login=superuser_id) as json:
            assert_meta(json, 'total', lambda v: int(v) == article_count)
            total_filtered = assert_meta(json, 'totalFiltered')
            assert total_filtered > 0
            for article in assert_collection(json, 'article', lambda size: size == total_filtered):
                assert_object(article, 'article')
                assert_attribute(article, 'is-published', lambda v: v is False)

    async with get_collection(articles,
                              {'include': 'author',
                               'fields[user]': 'article-count',
                               'filter[author.article-count:eq]': '3',
                               'filter[publisher:ne]': 'none'},
                              login=superuser_id) as json:

        for article in assert_collection(json, 'article', lambda size: size > 0):
            assert_attribute(article, 'is-published', lambda v: v is True)
            author = assert_included(json, assert_relationship(article, 'author'))
            assert_attribute(author, 'article-count', lambda v: v == 3)


@pytest.mark.asyncio
async def test_derived(users, user_count):
    async with get_collection(users,
                              {'include': 'bio',
                               'filter[bio.age:gt]': '18',
                               'fields[user]': 'id',
                               'fields[user-bio]': 'age'}) as json:
        assert_meta(json, 'total', lambda v: int(v) == user_count)
        total_filtered = assert_meta(json, 'totalFiltered')
        assert total_filtered > 0
        for user in assert_collection(json, 'user', lambda size: size == total_filtered):
            assert_object(user, 'user')
            bio = assert_included(json, assert_relationship(user, 'bio'))
            assert_attribute(bio, 'age', lambda v: int(v) > 18)
