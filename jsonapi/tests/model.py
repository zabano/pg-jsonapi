from sqlalchemy.sql import func

from jsonapi.db.table import MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE
from jsonapi.model import Aggregate, Derived, MixedModel, Model, Relationship
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
              Derived('name', lambda rec: rec.first + ' ' + rec.last),
              Relationship('bio', 'UserBioModel', ONE_TO_ONE),
              Relationship('articles', 'ArticleModel', ONE_TO_MANY, 'author_id'),
              Relationship('followers', 'UserModel', MANY_TO_MANY, ('user_id', 'follower_id')),
              Aggregate('article_count', 'articles', func.count))
    search = users_ts


class UserBioModel(Model):
    from_ = user_bios_t
    fields = 'birthday', 'summary'


class ArticleModel(Model):
    from_ = articles_t
    fields = ('title', 'body', 'created_on', 'updated_on', 'is_published',
              Relationship('author', 'UserModel', MANY_TO_ONE, 'author_id'),
              Relationship('publisher', 'UserModel', MANY_TO_ONE, 'published_by'),
              Relationship('keywords', 'KeywordModel', MANY_TO_MANY, ('article_id', 'keyword_id')),
              Relationship('comments', 'CommentModel', ONE_TO_MANY, 'article_id'),
              Aggregate('keyword_count', 'keywords', func.count),
              Aggregate('comment_count', 'comments', func.count),
              Aggregate('author_count', 'author', func.count))

    @staticmethod
    def filter_custom(rec, val):
        return func.char_length(rec.title) == int(val)

    search = articles_ts
    access = func.check_article_read_access
    user = current_user


class KeywordModel(Model):
    from_ = keywords_t
    fields = 'name'


class CommentModel(Model):
    from_ = comments_t
    fields = ('body', 'created_on', 'updated_on',
              Relationship('author', 'UserModel', MANY_TO_ONE, 'user_id'),
              Relationship('replies', 'ReplyModel', ONE_TO_MANY, 'comment_id'),
              Aggregate('reply_count', 'replies', func.count))


class ReplyModel(Model):
    from_ = replies_t
    fields = 'body', 'created_on', 'updated_on'


class SearchModel(MixedModel):
    models = UserModel, ArticleModel
