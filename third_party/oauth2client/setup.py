# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Setup script for oauth2client.

Also installs included versions of third party libraries, if those libraries
are not already installed.
"""
from __future__ import print_function

import sys

if sys.version_info <= (2, 6):
  print('oauth2client requires python version >= 2.6.', file=sys.stderr)
  sys.exit(1)

from setuptools import setup

packages = [
    'oauth2client',
]

install_requires = [
    'httplib2>=0.8',
    'pyasn1==0.1.7',
    'pyasn1_modules==0.0.5',
    'rsa==3.1.4',
]

long_desc = """The oauth2client is a client library for OAuth 2.0."""

import oauth2client
version = oauth2client.__version__

setup(
    name="oauth2client",
    version=version,
    description="OAuth 2.0 client library",
    long_description=long_desc,
    author="Google Inc.",
    url="http://github.com/google/oauth2client/",
    install_requires=install_requires,
    packages=packages,
    license="Apache 2.0",
    keywords="google oauth 2.0 http client",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
