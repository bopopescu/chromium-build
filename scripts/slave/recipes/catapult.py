# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
  'gitiles',
  'recipe_engine/generator_script',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'platform': Property(default=None, kind=str),
}


def _CheckoutSteps(api):
  """Checks out the catapult repo (and any dependencies) using gclient."""
  api.gclient.set_config('catapult')
  api.bot_update.ensure_checkout()
  api.gclient.runhooks()


def _FetchAppEngineSDKSteps(api):
  """Fetches the App Engine SDK and returns its path.

  This uses a downloader script in the infra repo to download a script
  which is then used to download and unpack the SDK itself.
  """
  script_content = api.gitiles.download_file(
      'https://chromium.googlesource.com/infra/infra',
      'bootstrap/get_appengine.py',
      step_name='Fetch SDK downloader',
      branch='refs/heads/master')
  slave_build_path = api.path['slave_build']
  api.file.write('Create get_appengine.py',
                 path=slave_build_path.join('get_appengine.py'),
                 data=script_content)
  api.python('Run SDK downloader',
             slave_build_path.join('get_appengine.py'), args=['--dest=.'])
  return slave_build_path.join('google_appengine')


def _RemoteSteps(api, app_engine_sdk_path, platform):
  """Runs the build steps specified in catapult_build/build_steps.py.

  Steps are specified in catapult repo in order to avoid multi-sided patches
  when updating tests and adding/moving directories.

  This step uses the generator_script; see documentation at
  github.com/luci/recipes-py/blob/master/recipe_modules/generator_script/api.py

  Use the test_checkout_path property in local tests to run against a local
  copy of catapult_build/build_steps.py.
  """
  base = api.properties.get('test_checkout_path', str(api.path['checkout']))
  script = api.path.join(base, 'catapult_build', 'build_steps.py')
  args = [
      script,
      '--api-path-checkout', api.path['checkout'],
      '--app-engine-sdk-pythonpath', app_engine_sdk_path,
      '--platform', platform or api.platform.name,
  ]
  return api.generator_script(*args)


def RunSteps(api, platform):
  _CheckoutSteps(api)

  # The dashboard unit tests depend on Python modules in the App Engine SDK,
  # and the unit test runner script assumes that the SDK is in PYTHONPATH.
  sdk_path = _FetchAppEngineSDKSteps(api)
  app_engine_sdk_path = api.path.pathsep.join([
      '%(PYTHONPATH)s', str(sdk_path)])
  _RemoteSteps(api, app_engine_sdk_path, platform)


def GenTests(api):
  yield (
    api.test('basic') +
    api.properties(mastername='master.client.catapult',
                   buildername='windows',
                   slavename='windows_slave') +
    api.step_data('Fetch SDK downloader',
                  api.gitiles.make_encoded_file(
                      '"<simulated contents of get_appengine.py>"')) +
    api.generator_script(
      'build_steps.py',
      {'name': 'Dashboard Tests', 'cmd': ['run_py_tests', '--no-hooks']},
    )
  )

  yield (
    api.test('android') +
    api.properties(mastername='master.client.catapult',
                   buildername='android',
                   slavename='android_slave',
                   platform='android') +
    api.step_data('Fetch SDK downloader',
                  api.gitiles.make_encoded_file(
                      '"<simulated contents of get_appengine.py>"')) +
    api.generator_script(
        'build_steps.py',
        {'name': 'Dashboard Tests', 'cmd': ['run_py_tests', '--no-hooks']},
    )
  )
