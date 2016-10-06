# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO: remove redundant DEPS.
DEPS = [
  'file',
  'recipe_engine/path',
  'recipe_engine/properties',
  'repo',
  'recipe_engine/step',
]

_TARGET_DEVICE_MAP = {
    'volantis': {
      'bitness': 64,
      'make_jobs': 2,
      'product': 'armv8',
      },
    'hammerhead': {
      'bitness': 32,
      'make_jobs': 4,
      'product': 'arm_krait',
      },
    'fugu': {
      'bitness': 32,
      'make_jobs': 4,
      'product': 'silvermont',
      },
    'mips64_emulator': {
      'bitness': 64,
      'make_jobs': 1,
      'product': 'mips64r6',
      },
    'mips32': {
      'bitness': 32,
      'make_jobs': 2,
      'product': 'mips32r2_fp_xburst',
      },
    'angler': {
      'bitness': 64,
      'make_jobs': 4,
      'product': 'armv8',
      },
    }

_ANDROID_CLEAN_DIRS = ['/data/local/tmp', '/data/art-test',
                       '/data/nativetest']

def checkout(api):
  api.repo.init('https://android.googlesource.com/platform/manifest',
      '-b', 'master-art')
  api.repo.sync()

def full_checkout(api):
  api.repo.init('https://android.googlesource.com/platform/manifest',
      '-b', 'master')
  api.repo.sync()

def clobber(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmtree('clobber', api.path['slave_build'].join('out'))

def setup_host_x86(api, debug, bitness, concurrent_collector=False):
  with api.step.defer_results():
    checkout(api)
    clobber(api)

    build_top_dir = api.path['slave_build']
    art_tools = api.path['slave_build'].join('art', 'tools')
    env = { 'TARGET_PRODUCT': 'sdk',
            'TARGET_BUILD_VARIANT': 'eng',
            'TARGET_BUILD_TYPE': 'release',
            'SOONG_ALLOW_MISSING_DEPENDENCIES': 'true',
            'ANDROID_BUILD_TOP': build_top_dir,
            'JACK_SERVER': 'false',
            'JACK_REPOSITORY': str(build_top_dir.join('prebuilts', 'sdk',
                                                      'tools', 'jacks')),
            'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                        api.path.pathsep +
                        '/usr/lib/jvm/java-8-openjdk-amd64/bin/' +
                        api.path.pathsep + '%(PATH)s',
            'ART_USE_OPTIMIZING_COMPILER' : 'true',
            'ART_TEST_RUN_TEST_2ND_ARCH': 'false',
            'ART_TEST_INTERPRETER': 'true',
            'ART_TEST_JIT': 'true',
            'ART_TEST_OPTIMIZING': 'true',
            'ART_TEST_FULL': 'false',
            'ART_TEST_KEEP_GOING': 'true' }

    if bitness == 32:
      env.update({ 'HOST_PREFER_32_BIT' : 'true' })

    if not debug:
      env.update({ 'ART_TEST_RUN_TEST_NDEBUG' : 'true' })
      env.update({ 'ART_TEST_RUN_TEST_DEBUG' : 'false' })

    if concurrent_collector:
      env.update({ 'ART_USE_READ_BARRIER' : 'true'  })
      env.update({ 'ART_HEAP_POISONING' : 'true'  })

    api.step('build sdk-eng',
             [art_tools.join('buildbot-build.sh'), '-j8', '--host'],
             env=env)

    api.step('test gtest',
        ['make', '-j8', 'test-art-host-gtest%d' % bitness],
        env=env)

    optimizing_env = env.copy()
    optimizing_env.update({ 'ART_TEST_RUN_TEST_DEBUGGABLE': 'true' })
    api.step('test optimizing', ['make', '-j8',
      'test-art-host-run-test-optimizing', 'dist'], env=optimizing_env)
    # Use a lower -j number for interpreter, some tests take a long time
    # to run on it.
    api.step('test interpreter', ['make', '-j5',
      'test-art-host-run-test-interpreter', 'dist'], env=env)

    api.step('test jit', ['make', '-j8', 'test-art-host-run-test-jit',
                          'dist'],
             env=env)

    libcore_command = [art_tools.join('run-libcore-tests.sh'),
                       '--mode=host',
                       '--variant=X%d' % bitness]
    if debug:
      libcore_command.append('--debug')
    api.step('test libcore', libcore_command, env=env)

    jdwp_command = [art_tools.join('run-jdwp-tests.sh'),
                    '--mode=host',
                    '--variant=X%d' % bitness]
    if debug:
      jdwp_command.append('--debug')
    api.step('test jdwp jit', jdwp_command, env=env)

    jdwp_command = [art_tools.join('run-jdwp-tests.sh'),
                    '--mode=host',
                    '--variant=X%d' % bitness,
                    '--no-jit']
    if debug:
      jdwp_command.append('--debug')
    api.step('test jdwp aot', jdwp_command, env=env)

def setup_target(api,
    serial,
    debug,
    device,
    concurrent_collector=False):
  build_top_dir = api.path['slave_build']
  art_tools = api.path['slave_build'].join('art', 'tools')
  android_root = '/data/local/tmp/system'

  env = {'TARGET_BUILD_VARIANT': 'eng',
         'TARGET_BUILD_TYPE': 'release',
         'SOONG_ALLOW_MISSING_DEPENDENCIES': 'true',
         'ANDROID_SERIAL': serial,
         'ANDROID_BUILD_TOP': build_top_dir,
         'PATH': str(build_top_dir.join('out', 'host', 'linux-x86', 'bin')) +
                     api.path.pathsep +
                     '/usr/lib/jvm/java-8-openjdk-amd64/bin/' +
                     api.path.pathsep + '%(PATH)s',
         'JACK_SERVER': 'false',
         'JACK_REPOSITORY': str(build_top_dir.join('prebuilts', 'sdk', 'tools',
                                                   'jacks')),
         'ART_TEST_RUN_TEST_2ND_ARCH': 'false',
         'ART_USE_OPTIMIZING_COMPILER' : 'true',
         'ART_TEST_INTERPRETER': 'true',
         'ART_TEST_JIT': 'true',
         'ART_TEST_OPTIMIZING': 'true',
         'ART_TEST_FULL': 'false',
         'ART_TEST_ANDROID_ROOT': android_root,
         'USE_DEX2OAT_DEBUG': 'false',
         'ART_BUILD_HOST_DEBUG': 'false',
         'ART_TEST_KEEP_GOING': 'true'}

  if not debug:
    env.update({ 'ART_TEST_RUN_TEST_NDEBUG' : 'true' })
    env.update({ 'ART_TEST_RUN_TEST_DEBUG' : 'false' })

  if concurrent_collector:
    env.update({ 'ART_USE_READ_BARRIER' : 'true' })
    env.update({ 'ART_HEAP_POISONING' : 'true' })


  bitness = _TARGET_DEVICE_MAP[device]['bitness']
  make_jobs = _TARGET_DEVICE_MAP[device]['make_jobs']
  env.update(
      {'TARGET_PRODUCT': _TARGET_DEVICE_MAP[device]['product'],
       'ANDROID_PRODUCT_OUT': build_top_dir.join('out','target', 'product',
         _TARGET_DEVICE_MAP[device]['product'])
      })

  if bitness == 32:
    env.update({ 'CUSTOM_TARGET_LINKER': '%s/bin/linker' % android_root  })
  else:
    env.update({ 'CUSTOM_TARGET_LINKER': '%s/bin/linker64' % android_root  })

  checkout(api)
  clobber(api)

  # Decrease the number of parallel tests, as some tests eat lots of memory.
  if debug and device == 'fugu':
    make_jobs = 1

  with api.step.defer_results():
    api.step('build target', [art_tools.join('buildbot-build.sh'),
                              '-j8', '--target'],
             env=env)

    # Mips64 testing is broken.
    if device == 'mips64_emulator':
      return

    api.step('setup device', [art_tools.join('setup-buildbot-device.sh')],
             env=env)

    api.step('device cleanup', ['adb', 'shell', 'rm', '-rf'] +
                               _ANDROID_CLEAN_DIRS,
             env=env)

    api.step('sync target', ['make', 'test-art-target-sync'], env=env)

    def test_logging(api, test_name):
      api.step(test_name + ': adb logcat',
               ['adb', 'logcat', '-d', '-v', 'threadtime'],
               env=env)
      api.step(test_name + ': crashes',
               [art_tools.join('symbolize-buildbot-crashes.sh')],
               env=env)
      api.step(test_name + ': adb clear log', ['adb', 'logcat', '-c'], env=env)

    test_env = env.copy()
    test_env.update({ 'ART_TEST_NO_SYNC': 'true' })
    test_env.update({ 'ANDROID_ROOT': android_root })

    api.step('test gtest', ['make', '-j%d' % (make_jobs),
      'test-art-target-gtest%d' % bitness], env=test_env)
    test_logging(api, 'test gtest')

    optimizing_env = test_env.copy()
    optimizing_env.update({ 'ART_TEST_RUN_TEST_DEBUGGABLE': 'true' })
    api.step('test optimizing', ['make', '-j%d' % (make_jobs),
      'test-art-target-run-test-optimizing', 'dist'], env=optimizing_env)
    test_logging(api, 'test optimizing')

    api.step('test interpreter', ['make', '-j%d' % (make_jobs),
                                  'test-art-target-run-test-interpreter',
                                  'dist'],
             env=test_env)
    test_logging(api, 'test interpreter')

    api.step('test jit', ['make', '-j%d' % (make_jobs),
      'test-art-target-run-test-jit', 'dist'], env=test_env)
    test_logging(api, 'test jit')

    libcore_command = [art_tools.join('run-libcore-tests.sh'),
                       '--mode=device',
                       '--variant=X%d' % bitness]
    if debug:
      libcore_command.append('--debug')
    api.step('test libcore', libcore_command, env=test_env)
    test_logging(api, 'test libcore')

    jdwp_command = [art_tools.join('run-jdwp-tests.sh'),
                    '--mode=device',
                    '--variant=X%d' % bitness]
    if debug:
      jdwp_command.append('--debug')
    api.step('test jdwp jit', jdwp_command, env=test_env)
    test_logging(api, 'test jdwp jit')

    jdwp_command = [art_tools.join('run-jdwp-tests.sh'),
                    '--mode=device',
                    '--variant=X%d' % bitness,
                    '--no-jit']
    if debug:
      jdwp_command.append('--debug')
    api.step('test jdwp aot', jdwp_command, env=test_env)
    test_logging(api, 'test jdwp aot')

def setup_aosp_builder(api):
  full_checkout(api)
  clobber(api)
  # Build the static version of dex2oat
  env = { 'ART_USE_OPTIMIZING_COMPILER': 'true',
          'TARGET_PRODUCT': 'aosp_x86_64',
          'LEGACY_USE_JAVA7': 'true',
          'ART_BUILD_HOST_STATIC': 'true',
          'TARGET_BUILD_VARIANT': 'eng',
          'TARGET_BUILD_TYPE': 'release'}
  api.step('build dex2oats',
           ['make', '-j8', 'out/host/linux-x86/bin/dex2oats'],
           env=env)

  # Re-enable when we have Java8 jdk on the slave
  #builds = ['x86', 'x86_64', 'arm', 'arm64']
  # TODO: adds mips and mips64 once we have enough storage on the bot.
  # ['mips', 'mips64']
  #with api.step.defer_results():
  #  for build in builds:
  #    env = { 'ART_USE_OPTIMIZING_COMPILER': 'true',
  #            'TARGET_PRODUCT': 'aosp_%s' % build,
  #            'LEGACY_USE_JAVA7': 'true',
  #            'TARGET_BUILD_VARIANT': 'eng',
  #            'TARGET_BUILD_TYPE': 'release'}
  #    api.step('Clean oat %s' % build, ['make', '-j8', 'clean-oat-host'],
  #        env=env)
  #    api.step('build %s' % build, ['make', '-j8'], env=env)

_CONFIG_MAP = {
  'client.art': {

    'x86': {
      'host-x86-ndebug': {
        'debug': False,
        'bitness': 32,
      },
      'host-x86-debug': {
        'debug': True,
        'bitness': 32,
      },
      'host-x86_64-ndebug': {
        'debug': False,
        'bitness': 64,
      },
      'host-x86_64-debug': {
        'debug': True,
        'bitness': 64,
      },
      'host-x86-concurrent-collector': {
        'debug': True,
        'bitness': 32,
        'concurrent_collector': True,
      },
      'host-x86_64-concurrent-collector': {
        'debug': True,
        'bitness': 64,
        'concurrent_collector': True,
      },
    },

    'target': {
      'hammerhead-ndebug': {
        'serial': '84B7N15A28014510',
        'device': 'hammerhead',
        'debug': False,
      },
      'hammerhead-debug': {
        'serial': '84B7N15B03000729',
        'device': 'hammerhead',
        'debug': True,
      },
      'volantis-armv8-ndebug': {
        'serial': 'HT4CTJT03670',
        'device': 'volantis',
        'debug': False,
      },
      'volantis-armv8-debug': {
        'serial': 'HT49CJT00070',
        'device': 'volantis',
        'debug': True,
      },
      'fugu-ndebug': {
        'serial': '0BCDB85D',
        'device': 'fugu',
        'debug': False,
      },
      'fugu-debug': {
        'serial': 'E6B27F19',
        'device': 'fugu',
        'debug': True,
      },
      'hammerhead-concurrent-collector': {
        'serial': '84B7N15B03000347',
        'device': 'hammerhead',
        'debug': True,
        'concurrent_collector': True,
      },
      'volantis-armv8-concurrent-collector': {
        'serial': 'HT591JT00517',
        'device': 'volantis',
        'debug': True,
        'concurrent_collector': True,
      },
      'mips64-emulator-debug': {
        'serial': 'emulator-5554',
        'device': 'mips64_emulator',
        'debug': True,
      },
      'angler-armv8-ndebug': {
        'serial': '84B7N15A28014046',
        'device': 'angler',
        'debug': False,
      },
      'angler-armv8-debug': {
        'serial': '84B7N15B03000615',
        'device': 'angler',
        'debug': True,
      },
      'angler-armv8-concurrent-collector': {
        'serial': '84B7N15B03000641',
        'device': 'angler',
        'debug': True,
        'concurrent_collector': True,
      },
    },

    'aosp': {
      'aosp-builder': {},
    },
  },
}

_CONFIG_DISPATCH_MAP = {
  'client.art': {
    'x86': setup_host_x86,
    'target': setup_target,
    'aosp': setup_aosp_builder,
  }
}

def RunSteps(api):
  if api.properties['mastername'] not in _CONFIG_MAP: # pragma: no cover
    error = "Master not found in recipe's local config!"
    raise KeyError(error)

  builder_found = False
  config = _CONFIG_MAP[api.properties['mastername']]
  for builder_type in config:
    if api.properties['buildername'] in config[builder_type]:
      builder_found = True
      builder_dict = config[builder_type][api.properties['buildername']]
      _CONFIG_DISPATCH_MAP[api.properties['mastername']][builder_type](api,
          **builder_dict)
      break

  if not builder_found: # pragma: no cover
    error = "Builder not found in recipe's local config!"
    raise KeyError(error)

def GenTests(api):
  for mastername, config_dict in _CONFIG_MAP.iteritems():
    for builders in config_dict.values():
      for buildername in builders:
        for clb in (None, True):
          yield (
              api.test("%s__ON__%s__%s" % (buildername, mastername,
                ("" if clb else "no") + "clobber")) +
              api.properties(
                mastername=mastername,
                buildername=buildername,
                slavename='TestSlave',
                # Buildbot uses clobber='' to mean clobber, however
                # api.properties(clobber=None) will set clobber=None!
                # so we have to not even mention it to avoid our
                # 'clobber' in api.properties logic triggering above.
              ) + (api.properties(clobber='') if clb else api.properties())
            )
  yield (
      api.test('x86_32_test_failure') +
      api.properties(
        mastername='client.art',
        buildername='host-x86-ndebug',
        slavename='TestSlave',
      ) +
      api.step_data('test jdwp aot', retcode=1))
  yield (
      api.test('target_hammerhead_setup_failure') +
      api.properties(
        mastername='client.art',
        buildername='hammerhead-ndebug',
        slavename='TestSlave',
      )
      + api.step_data('setup device', retcode=1))
  yield (
      api.test('target_hammerhead_test_failure') +
      api.properties(
        mastername='client.art',
        buildername='hammerhead-ndebug',
        slavename='TestSlave',
      ) +
      api.step_data('test jdwp aot', retcode=1))
  yield (
      api.test('target_hammerhead_device_cleanup_failure') +
      api.properties(
        mastername='client.art',
        buildername='hammerhead-ndebug',
        slavename='TestSlave',
      ) +
      api.step_data('device cleanup', retcode=1))
  yield (
      api.test('aosp_x86_build_failure') +
      api.properties(
        mastername='client.art',
        buildername='aosp-builder',
        slavename='TestSlave',
      ) +
      api.step_data('build dex2oats', retcode=1))
#  These tests *should* exist, but can't be included as they cause the recipe
#  simulation to error out, instead of showing that the build should become
#  purple instead. This may need to be fixed in the simulation test script.
#  yield (
#      api.test('invalid mastername') +
#      api.properties(
#        mastername='client.art.does_not_exist',
#        buildername='aosp-builder',
#        slavename='TestSlave',
#      )
#    )
#  yield (
#      api.test('invalid buildername') +
#      api.properties(
#        mastername='client.art',
#        buildername='builder_does_not_exist',
#        slavename='TestSlave',
#      )
#    )
