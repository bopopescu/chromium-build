# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'ios',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/raw_io',
]

def RunSteps(api):
  swarm = False
  if api.properties['mastername'] == 'chromium.fyi':
    if api.properties['buildername'] == 'ios-simulator':
      swarm = True

  api.ios.host_info()
  api.ios.checkout()
  api.ios.read_build_config()
  api.ios.build()

  if swarm:
    api.ios.test_swarming()
  else:
    api.ios.test()

def GenTests(api):
  yield (
    api.test('basic')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'env': {
        'fake env var 1': 'fake env value 1',
        'fake env var 2': 'fake env value 2',
      },
      'compiler': 'xcodebuild',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests 1',
          'device type': 'fake device',
          'os': '8.0',
        },
        {
          'app': 'fake tests 2',
          'device type': 'fake device',
          'os': '7.1',
        },
        {
          'app': 'fake_eg_test_host',
          'device type': 'fake device 3',
          'os': '9.3',
          'xctest': True,
        },
      ],
    })
  )

  yield (
    api.test('swarming')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios-simulator',
      buildnumber='0',
      mastername='chromium.fyi',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
      },
      'compiler': 'xcodebuild',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests',
          'device type': 'fake device',
          'os': '7.1',
        },
      ],
    })
    + api.step_data(
        'bootstrap swarming.swarming.py --version',
        stdout=api.raw_io.output('1.2.3'),
    )
  )

  yield (
    api.test('no_tests')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'compiler': 'ninja',
      'configuration': 'Release',
      'sdk': 'iphoneos8.0',
      'tests': [
      ],
    })
  )

  yield (
    api.test('goma')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
        'use_goma': '1',
      },
      'compiler': 'ninja',
      'configuration': 'Release',
      'sdk': 'iphoneos8.0',
      'tests': [
      ],
    })
  )

  yield (
    api.test('test_failure')
    + api.platform('mac', 64)
    + api.properties(patch_url='patch url')
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'compiler': 'xcodebuild',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests 1',
          'device type': 'fake device',
          'os': '8.0',
        },
        {
          'app': 'fake tests 2',
          'device type': 'fake device',
          'os': '7.1',
        },
      ],
    })
    + api.step_data(
      'fake tests 1 (fake device iOS 8.0)',
      retcode=1
    )
  )

  yield (
    api.test('infrastructure_failure')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'compiler': 'ninja',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator8.0',
      'tests': [
        {
          'app': 'fake tests 1',
          'device type': 'fake device',
          'os': '8.0',
        },
        {
          'app': 'fake tests 2',
          'device type': 'fake device',
          'os': '7.1',
        },
      ],
    })
    + api.step_data(
      'fake tests 1 (fake device iOS 8.0)',
      retcode=2,
    )
  )

  yield (
    api.test('multiple_failures')
    + api.platform('mac', 64)
    + api.properties(
      buildername='ios',
      buildnumber='0',
      mastername='chromium.fake',
      slavename='fake-vm',
    )
    + api.ios.make_test_build_config({
      'xcode version': 'fake xcode version',
      'GYP_DEFINES': {
        'fake gyp define 1': 'fake value 1',
        'fake gyp define 2': 'fake value 2',
      },
      'compiler': 'xcodebuild',
      'configuration': 'Debug',
      'sdk': 'iphonesimulator7.1',
      'tests': [
        {
          'app': 'fake tests 1',
          'device type': 'fake device',
          'os': '8.1',
        },
        {
          'app': 'fake tests 2',
          'device type': 'fake device',
          'os': '8.1',
        },
        {
          'app': 'fake tests 3',
          'device type': 'fake device',
          'os': '8.1',
        },
        {
          'app': 'fake tests 4',
          'device type': 'fake device',
          'os': '8.1',
        },
        {
          'app': 'fake tests 5',
          'device type': 'fake device',
          'os': '8.1',
        },
        {
          'app': 'fake tests 6',
          'device type': 'fake device',
          'os': '8.1',
        },
      ],
    })
    + api.step_data(
      'fake tests 2 (fake device iOS 8.1)',
      retcode=1
    )
    + api.step_data(
      'fake tests 3 (fake device iOS 8.1)',
      retcode=1
    )
    + api.step_data(
      'fake tests 5 (fake device iOS 8.1)',
      retcode=2
    )
  )
