#!/usr/bin/env python

from distutils.core import setup

setup(
    name='pg-jsonapi',
    version='0.1.0.dev0',
    description='PostgreSQL JSONAPI',
    author='Omar Zabaneh',
    author_email='zabano@gmail.com',
    packages=['jsonapi'],
    license='SSPL',
    keywords='jsonapi marshmallow asyncpgsa',
    install_requires=[
        'sqlalchemy',
        'asyncpg',
        'asyncpgsa',
        'marshmallow',
        'uvloop',
        'werkzeug',
        'quart',
        'inflection',
        'pytest',
        'pytest-asyncio',
        'faker',
        'sqlparse'
    ],
    entry_points={
        'console_scripts': [
            'jsonapi_populate_test_db=jsonapi.tests.data:populate_test_db',
        ],
    }
)
