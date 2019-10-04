from jsonapi.db.table import MANY_TO_MANY, MANY_TO_ONE, ONE_TO_MANY, ONE_TO_ONE
from jsonapi.model import Aggregate, Derived, MixedModel, Model, Relationship
from jsonapi.tests.auth import current_user
from jsonapi.tests.db import *


class TestModel(Model):
    from_ = test_data_t
    fields = ('test_bool',
              'test_smallint', 'test_int', 'test_bigint',
              'test_float', 'test_double', 'test_numeric',
              'test_char', 'test_varchar', 'test_text', 'test_enum',
              'test_time', 'test_date', 'test_timestamp', 'test_timestamp_tz',
              'test_json', 'test_jsonb')


class UserModel(Model):
    from_ = users_t, user_names_t
    fields = ('email', 'first', 'last', 'created_on', 'status',
              Derived('name', lambda rec: '{first} {last}'.format(**rec)),
              Relationship('bio', 'UserBioModel',
                           ONE_TO_ONE, 'user_bios_id_fkey'),
              Relationship('articles', 'ArticleModel',
                           ONE_TO_MANY, 'articles_author_id_fkey'),
              Aggregate('article_count', 'articles', sa.func.count))
    search = users_ts


class UserBioModel(Model):
    from_ = user_bios_t
    fields = 'birthday', 'summary'


class ArticleModel(Model):
    from_ = articles_t
    fields = ('title', 'body', 'created_on', 'updated_on', 'is_published',
              Relationship('author', 'UserModel',
                           MANY_TO_ONE, 'articles_author_id_fkey'),
              Relationship('published_by', 'UserModel',
                           MANY_TO_ONE, 'articles_published_by_fkey'),
              Relationship('keywords', 'KeywordModel',
                           MANY_TO_MANY, 'article_keywords_article_id_fkey'),
              Relationship('comments', 'CommentModel',
                           ONE_TO_MANY, 'articles_article_id_fkey'),
              Aggregate('keyword_count', 'keywords', sa.func.count),
              Aggregate('comment_count', 'comments', sa.func.count),
              Aggregate('author_count', 'author', sa.func.count))

    @staticmethod
    def filter_custom(v):
        return sa.func.char_length(articles_t.c.title) == int(v)

    search = articles_ts
    access = sa.func.check_article_read_access
    user = current_user


class KeywordModel(Model):
    from_ = keywords_t
    fields = 'name'


class CommentModel(Model):
    from_ = comments_t
    fields = ('body', 'created_on', 'updated_on',
              Relationship('author', 'UserModel', MANY_TO_ONE, 'articles_user_id_fkey'),
              Relationship('replies', 'ReplyModel', ONE_TO_MANY, 'replies_comment_id_fkey'),
              Aggregate('reply_count', 'replies', sa.func.count))


class ReplyModel(Model):
    from_ = replies_t
    fields = 'body', 'created_on', 'updated_on'


class SearchModel(MixedModel):
    models = UserModel, ArticleModel
