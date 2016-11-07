# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Swarming staging recipe: runs tests for HEAD of chromium using HEAD of
swarming_client toolset on Swarming staging server instances
(*-dev.appspot.com).

Intended to catch bugs in swarming_client and Swarming servers early on, before
full roll out.

Waterfall page: https://build.chromium.org/p/chromium.swarm/waterfall
"""

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'commit_position',
  'file',
  'depot_tools/gclient',
  'isolate',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
  'swarming',
  'swarming_client',
  'test_results',
  'test_utils',
]


def RunSteps(api):
  # Configure isolate & swarming modules to use staging instances.
  api.isolate.isolate_server = 'https://isolateserver-dev.appspot.com'
  api.swarming.swarming_server = 'https://chromium-swarm-dev.appspot.com'
  api.swarming.verbose = True

  # Run tests from chromium.swarm buildbot with a relatively high priority
  # so that they take precedence over manually triggered tasks.
  api.swarming.default_priority = 20

  # Do not care about the OS specific version on Canary.
  api.swarming.set_default_dimension(
      'os',
      api.swarming.prefered_os_dimension(api.platform.name).split('-', 1)[0])
  api.swarming.set_default_dimension('pool', 'Chrome')
  api.swarming.add_default_tag('project:chromium')
  api.swarming.add_default_tag('purpose:staging')
  api.swarming.default_idempotent = True

  # We are building simplest Chromium flavor possible.
  if api.properties.get('platform') == 'android':
    api.chromium.set_config(
        'android', BUILD_CONFIG=api.properties.get('configuration', 'Release'),
        TARGET_ARCH='arm', TARGET_BITS=32)

    # Only one android bot, bump the expiration higher.
    # TODO(stip/maruel): add default_expiration property to api.swarming? Add
    # expiration to api.swarming.task()?
    api.swarming._default_expiration = 5*60*60
  else:
    api.chromium.set_config(
        'chromium', BUILD_CONFIG=api.properties.get('configuration', 'Release'))

  # We are checking out Chromium with swarming_client dep unpinned and pointing
  # to ToT of swarming_client repo, see recipe_modules/gclient/config.py.
  api.gclient.set_config('chromium')
  if api.properties.get('platform') == 'android':
    api.gclient.apply_config('android')
  api.gclient.c.solutions[0].custom_vars['swarming_revision'] = ''
  api.gclient.c.revisions['src/tools/swarming_client'] = 'HEAD'

  # Enable test isolation. Modifies GYP_DEFINES used in 'runhooks' below.
  api.isolate.set_isolate_environment(api.chromium.c)

  api.chromium.cleanup_temp()
  # Checkout chromium + deps (including 'master' of swarming_client).
  api.gclient.checkout()

  # Ensure swarming_client version is fresh enough.
  api.swarming.check_client_version()

  targets = ['chromium_swarm_tests']
  if api.properties.get('platform') == 'android':
    targets = [
        'android_webview_test_apk_run',
        'android_webview_unittests_apk_run',
        'base_unittests_apk_run',
        'breakpad_unittests_apk_run',
        'chrome_public_test_apk_run',
        'chrome_sync_shell_test_apk_run',
        'components_browsertests_apk_run',
        'components_unittests_apk_run',
        'content_browsertests_apk_run',
        'content_shell_test_apk_run',
        'content_unittests_apk_run',
        'device_unittests_apk_run',
        'events_unittests_apk_run',
        'gl_tests_apk_run',
        'gl_unittests_apk_run',
        'gpu_unittests_apk_run',
        'ipc_tests_apk_run',
        'media_unittests_apk_run',
        'net_unittests_apk_run',
        'sandbox_linux_unittests_android_run',
        'sql_unittests_apk_run',
        'ui_android_unittests_apk_run',
        'ui_base_unittests_apk_run',
        'ui_touch_selection_unittests_apk_run',
        'unit_tests_apk_run',
    ]

  # Build all supported tests.
  api.chromium.ensure_goma()
  api.chromium.runhooks()
  api.isolate.clean_isolated_files(api.chromium.output_dir)
  api.chromium.compile(targets=targets, use_goma_module=True)
  api.isolate.remove_build_metadata()

  # Will search for *.isolated.gen.json files in the build directory and isolate
  # corresponding targets.
  api.isolate.isolate_tests(
      api.chromium.output_dir,
      verbose=True,
      env={'SWARMING_PROFILE': '1'})

  if api.properties.get('platform') == 'android':
    tasks = [
      api.swarming.task(
          test,
          isolated_hash)
      for test, isolated_hash in sorted(api.isolate.isolated_tests.iteritems())
    ]
    for task in tasks:
      task.dimensions['os'] = 'Android'
      slow_tests = [
        'android_webview_test_apk_run',
        'chrome_public_test_apk',
        'chrome_sync_shell_test_apk',
        'content_browsertests_apk',
        'content_shell_test_apk_run',
        'gl_tests_apk',
        'net_unittests_apk',
        'unit_tests_apk',
      ]
      if task.title in slow_tests:
        # TODO(stip): Eventually scale based on size of test.
        task.dimensions['android_devices'] = '6'
      del task.dimensions['cpu']
      del task.dimensions['gpu']
  else:
    # Make swarming tasks that run isolated tests.
    tasks = [
      api.swarming.gtest_task(
          test,
          isolated_hash,
          shards=2,
          test_launcher_summary_output=api.test_utils.gtest_results(
              add_json_log=False))
      for test, isolated_hash in sorted(api.isolate.isolated_tests.iteritems())
    ]

  for task in tasks:
    api.swarming.trigger_task(task)

  # And wait for ALL them to finish.
  with api.step.defer_results():
    for task in tasks:
      api.swarming.collect_task(task)

      if not api.properties.get('platform') == 'android':
        # TODO(estaab): Move this into the swarming recipe_module behind a flag
        # after testing on staging.
        step_result = api.step.active_result
        gtest_results = getattr(step_result.test_utils, 'gtest_results', None)
        if gtest_results and gtest_results.raw:
          # This is a potentially large json file (on the order of 10s of MiB)
          # but swarming/api.py is already parsing it to get failed shards so we
          # reuse it here.
          parsed_gtest_data = gtest_results.raw
          chrome_revision_cp = api.bot_update.last_returned_properties.get(
              'got_revision_cp', 'x@{#0}')
          chrome_revision = str(api.commit_position.parse_revision(
              chrome_revision_cp))
          api.test_results.upload(
              api.json.input(parsed_gtest_data),
              chrome_revision=chrome_revision,
              test_type=task.title,
              test_results_server='test-results-test.appspot.com')


def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    for configuration in ('Debug', 'Release'):
      yield (
        api.test('%s_%s' % (platform, configuration)) +
        api.platform.name(platform) +
        api.properties.scheduled() +
        api.properties(configuration=configuration)
      )

  # One 'collect' fails due to a missing shard and failing test, should not
  # prevent the second 'collect' from running.
  yield (
    api.test('one_fails') +
    api.platform.name('linux') +
    api.properties.scheduled() +
    api.properties(configuration='Debug') +
    api.override_step_data(
        'dummy_target_1 on Ubuntu',
        api.test_utils.canned_gtest_output(
            passing=False,
            minimal=True,
            extra_json={'missing_shards': [1]}),
    )
  )
  yield (
    api.test('android') +
    api.platform.name('linux') +
    api.properties.scheduled() +
    api.properties(configuration='Release', platform='android') +
    api.override_step_data(
        'isolate tests',
        api.isolate.output_json(targets=[
            'dummy_target_1', 'dummy_target_2', 'chrome_public_test_apk'])
    )
  )
