#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name = "flask-restle",
    version = "0.0.1",
    author = "Ben Hagen",
    author_email = "benhagen@gmail.com",
    description = "In order to facilitate dumb, RESTful-like, API's.",
    license = "BSD",
    keywords = "flask rest api",
    url = "https://github.com/benhagen/flask-restle",
    packages=find_packages(),
    requires=['flask','arrow']
)
