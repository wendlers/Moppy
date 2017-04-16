#!/bin/env python3

from distutils.core import setup

setup(
    name='moppy',
    version='0.0.1',
    description='Moppy Python',
    author='Stefan Wendler',
    author_email='sw@kaltpost.de',
    url='https://www.kaltpost.de/',
    requires=[
      "Flask (>=0.12)",
      "pyserial (>=3.0.0)"
    ],
    packages=['moppy'],
    package_data={'moppy': ['templates/*']},
    scripts=['moppy-player', 'moppy-server', 'moppy-proxy']
)
