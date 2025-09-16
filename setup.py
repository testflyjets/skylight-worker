#!/usr/bin/env python

"""
distutils/setuptools install script.
"""

import os
import re

from setuptools import find_packages, setup

ROOT = os.path.dirname(__file__)
VERSION_RE = re.compile(r'''__version__ = ['"]([0-9.]+)['"]''')

requires = [
    'common@git+ssh://git@gitlab.com/dmv_check/common.git@dev',
    'requests',
    'SpeechRecognition',
    'pydub',
    'webdriver-manager',
    'boto3',
    'fake-useragent',
    'pocketsphinx',
    'flask',
    'python-dotenv',
    'blinker==1.7.0',
    'waitress',
    'redis',
    'celery',
    'pyvirtualdisplay',
    'beautifulsoup4',
    'schedule',
    'rq',
    'xdo',
    'nopecha',
    'undetected-chromedriver==3.5.5',
    'undetected-geckodriver',
    'sentry-sdk',
    'seleniumbase',
    'fakeit',
    'humancursor',
    'keyboard'
]


def get_version():
    init = open(os.path.join(ROOT, 'selenium_worker', '__init__.py')).read()
    return VERSION_RE.search(init).group(1)


setup(
    name='selenium_worker',
    version=get_version(),
    description='A Selenium-based worker for Vyyer DMV API',
    long_description=open('README.md').read(),
    author='Daniel Protopopov',
    url='https://gitlab.com/dmv_check/selenium_worker.git',
    scripts=[],
    packages=find_packages(exclude=['supervisor*']),
    include_package_data=True,
    install_requires=requires,
    license="Apache License 2.0",
    python_requires=">= 3.12",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    project_urls={
        'Documentation': 'https://gitlab.com/dmv_check/selenium_worker/README.md',
        'Source': 'https://gitlab.com/dmv_check/selenium_worker.git',
    },
)
