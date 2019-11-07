#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='pg-jsonapi',
    version='0.1.0.dev0',
    description='PostgreSQL JSONAPI',
    author='Omar Zabaneh',
    author_email='zabano@gmail.com',
    packages=find_packages(),
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
