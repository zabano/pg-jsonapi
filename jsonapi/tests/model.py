from sqlalchemy.sql import func

from jsonapi.datatypes import Integer
from jsonapi.db.table import MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE
from jsonapi.model import Aggregate, Field, Model, Relationship
from jsonapi.tests.auth import current_user
from jsonapi.tests.db import *


class TestModel(Model):
    from_ = test_data_t
    fields = ('test_bool',
              'test_int', 'test_small_int', 'test_big_int',
              'test_float', 'test_double', 'test_numeric',
              'test_char', 'test_varchar', 'test_text', 'test_enum',
              'test_time', 'test_date', 'test_timestamp', 'test_timestamp_tz',
              'test_json', 'test_json_b')


class UserModel(Model):
    from_ = users_t, user_names_t
    fields = ('email', 'first', 'last', 'created_on', 'status',
              Field('name', lambda rec: rec.first + ' ' + rec.last),
              Relationship('bio', 'UserBioModel', ONE_TO_ONE),
              Relationship('articles', 'ArticleModel', ONE_TO_MANY, articles_t.c.author_id),
              Relationship('followers', 'UserModel', MANY_TO_MANY,
                           user_followers_t.c.user_id, user_followers_t.c.follower_id),
              Aggregate('article_count', 'articles', func.count))
    search = users_ts


class UserBioModel(Model):
    from_ = user_bios_t
    fields = ('summary', 'birthday',
              Field('age', lambda rec: func.extract('year', func.age(rec['birthday'])), Integer))


class ArticleModel(Model):
    from_ = articles_t
    fields = ('title', 'body', 'created_on', 'updated_on', 'is_published',
              Relationship('author', 'UserModel', MANY_TO_ONE, articles_t.c.author_id),
              Relationship('publisher', 'UserModel', MANY_TO_ONE, articles_t.c.published_by),
              Relationship('keywords', 'KeywordModel', MANY_TO_MANY,
                           article_keywords_t.c.article_id, article_keywords_t.c.keyword_id),
              Relationship('comments', 'CommentModel', ONE_TO_MANY, comments_t.c.article_id),
              Aggregate('keyword_count', 'keywords', func.count),
              Aggregate('comment_count', 'comments', func.count),
              Aggregate('author_count', 'author', func.count))

    @staticmethod
    def filter_custom(rec, val, compare):
        return compare(func.char_length(rec.title), int(val))

    search = articles_ts
    access = func.check_article_read_access
    user = current_user


class KeywordModel(Model):
    from_ = keywords_t
    fields = 'name'

    Relationship('articles', 'ArticleModel', MANY_TO_MANY,
                 article_keywords_t.c.keyword_id, article_keywords_t.c.article_id),


class CommentModel(Model):
    from_ = comments_t
    fields = ('body', 'created_on', 'updated_on',
              Relationship('article', 'ArticleModel', MANY_TO_ONE, comments_t.c.article_id),
              Relationship('user', 'UserModel', MANY_TO_ONE, comments_t.c.user_id),
              Relationship('replies', 'ReplyModel', ONE_TO_MANY, replies_t.c.comment_id),
              Aggregate('reply_count', 'replies', func.count))


class ReplyModel(Model):
    from_ = replies_t
    fields = 'body', 'created_on', 'updated_on'
