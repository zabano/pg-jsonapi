import pytest

from jsonapi.datatypes import Bool, String
from jsonapi.exc import ModelError
from jsonapi.model import Field, Model
from jsonapi.tests.db import test_data_t, users_t


class NoFromModel(Model):
    pass


class IllegalFieldNameModel(Model):
    from_ = users_t
    fields = 'id'


class FieldNotFoundModel(Model):
    from_ = test_data_t
    fields = 'does_not_exist'


class InvalidFieldModel(Model):
    from_ = test_data_t
    fields = test_data_t.c.test_int


class FooModel(Model):
    from_ = test_data_t


class Bar(Model):
    from_ = test_data_t


class FooBar(Model):
    from_ = test_data_t


class FooBarModel(Model):
    type_ = 'test'
    from_ = test_data_t
    fields = ('test_int', 'test_float',
              Field('test_float', String),
              Field('test_bool'))


def test_1_from():
    with pytest.raises(ModelError):
        NoFromModel()


def test_1_type():
    assert FooModel().type_ == 'foo'
    assert Bar().type_ == 'bar'
    assert FooBar().type_ == 'foo-bar'
    assert FooBarModel().type_ == 'test'


def test_1_fields():
    for cls in (FooModel, Bar, FooBar, FooBarModel):
        model = cls()
        assert 'id' in model.fields.keys()

        model.init_schema(model.parse_arguments({}))

        if cls is FooBarModel:
            assert len(model.fields.keys()) == 4
            assert 'test_int' in model.fields.keys()
            assert 'test_float' in model.fields.keys()
            assert model.fields['test_float'].data_type is String
            assert 'test_bool' in model.fields.keys()
            assert model.fields['test_bool'].data_type is Bool

    with pytest.raises(ModelError, match='illegal field name'):
        IllegalFieldNameModel()

    with pytest.raises(ModelError, match='invalid field'):
        InvalidFieldModel()

    model = FieldNotFoundModel()
    with pytest.raises(ModelError, match='not found'):
        model.init_schema(model.parse_arguments({}))
