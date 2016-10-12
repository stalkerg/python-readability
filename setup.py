#!/usr/bin/env python
from setuptools import setup, find_packages
import sys

setup(
    name="readability-lxml",
    version="0.4.0.5",
    author="Yuri Zhuravlev aka (stalkerg), Yuri Baburov",
    author_email="stalkerg@gmail.com, burchik@gmail.com",
    description="python3 port of python-readability tool",
    test_suite="tests.test_article_only",
    long_description=open("README.md").read(),
    license="Apache License 2.0",
    url="http://github.com/stalkerg/python-readability",
    packages=['readability'],
    install_requires=[
        "chardet",
        "lxml",
        "cssselect"
    ],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
)
