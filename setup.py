#!/usr/bin/env python

from setuptools import setup, find_packages


def get_long_description():
    with open('README.md') as f:
        return f.read()
    

setup(
    name="Starlette-WTF",
    python_requires=">=3.6",
    version="0.4.2",
    url="https://github.com/muicss/starlette-wtf",
    license="MIT",
    author="Andres Morey",
    description="Simple integration of Starlette and WTForms.",
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    packages=['starlette_wtf'],
    platforms='any',
    install_requires=[
        'itsdangerous',
        'python-multipart',
        'starlette',
        'WTForms'
    ],
    extras_require={
        'test': ['pytest', 'requests']
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    zip_safe=False
    )
