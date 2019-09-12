#!/usr/bin/env python

from distutils.core import setup

setup(
    name='pg-jsonapi',
    version='0.1.0dev',
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
        'quart',
        'inflection',
        'pytest',
        'pytest-asyncio'
    ]
)
