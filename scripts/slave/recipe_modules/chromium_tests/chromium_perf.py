# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

from . import steps

import DEPS
CHROMIUM_CONFIG_CTX = DEPS['chromium'].CONFIG_CTX
GCLIENT_CONFIG_CTX = DEPS['gclient'].CONFIG_CTX


builders = collections.defaultdict(dict)


SPEC = {
  'builders': {},
  'settings': {
    'build_gs_bucket': 'chrome-perf',
    # Bucket for storing builds for manual bisect
    'bisect_build_gs_bucket': 'chrome-test-builds',
    'bisect_build_gs_extra': 'official-by-commit',
    'bisect_builders': []
  },
}


@CHROMIUM_CONFIG_CTX(includes=['chromium', 'official', 'mb'])
def chromium_perf(c):
  c.clobber_before_runhooks = False
  pass


def _BaseSpec(bot_type, config_name, platform, target_bits, tests):
  spec = {
    'bot_type': bot_type,
    'chromium_config': config_name,
    'chromium_config_kwargs': {
      'BUILD_CONFIG': 'Release',
      'TARGET_BITS': target_bits,
    },
    'gclient_config': config_name,
    'testing': {
      'platform': 'linux' if platform == 'android' else platform,
    },
    'tests': tests,
  }

  if platform == 'android':
    spec['android_config'] = 'chromium_perf'
    spec['android_apply_config'] = ['use_devil_adb']
    spec['chromium_apply_config'] = ['android']
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['gclient_apply_config'] = ['android']

  return spec


def BuildSpec(
  config_name, perf_id, platform, target_bits, enable_swarming=False,
  extra_compile_targets=None):
  if platform == 'android':
    # TODO: Run sizes on Android.
    tests = []
  else:
    tests = [steps.SizesStep('https://chromeperf.appspot.com', perf_id)]

  spec = _BaseSpec(
      bot_type='builder',
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      tests=tests,
  )

  if enable_swarming:
    spec['enable_swarming'] = True
    spec['use_isolate'] = True
  spec['compile_targets'] = ['chromium_builder_perf']
  if extra_compile_targets:
    spec['compile_targets'] += extra_compile_targets

  return spec


def TestSpec(config_name, perf_id, platform, target_bits,
             parent_buildername=None, tests=None):
  spec = _BaseSpec(
      bot_type='tester',
      config_name=config_name,
      platform=platform,
      target_bits=target_bits,
      tests=tests or [],
  )

  if not parent_buildername:
    parent_buildername = builders[platform][target_bits]
  spec['parent_buildername'] = parent_buildername
  spec['perf-id'] = perf_id
  spec['results-url'] = 'https://chromeperf.appspot.com'

  return spec


def _AddIsolatedTestSpec(name, perf_id, platform, target_bits=64):
  spec = TestSpec('chromium_perf', perf_id, platform, target_bits)
  spec['enable_swarming'] = True
  SPEC['builders'][name] = spec


def _AddBuildSpec(
  name, platform, target_bits=64, add_to_bisect=False, enable_swarming=False,
  extra_compile_targets=None):
  if target_bits == 64:
    perf_id = platform
  else:
    perf_id = '%s-%d' % (platform, target_bits)

  SPEC['builders'][name] = BuildSpec(
      'chromium_perf', perf_id, platform, target_bits, enable_swarming,
      extra_compile_targets=extra_compile_targets)

  # TODO(martiniss): re-enable assertion once android has switched to the
  # chromium recipe
  # assert target_bits not in builders[platform]

  if not builders[platform].get(target_bits, None):
    builders[platform][target_bits] = name
  if add_to_bisect:
    SPEC['settings']['bisect_builders'].append(name)


def _AddTestSpec(name, perf_id, platform, target_bits=64,
                 num_host_shards=1, num_device_shards=1,
                 parent_buildername=None):
  for shard_index in xrange(num_host_shards):
    builder_name = '%s (%d)' % (name, shard_index + 1)
    tests = [steps.DynamicPerfTests(
        perf_id, platform, target_bits, num_device_shards=num_device_shards,
        num_host_shards=num_host_shards, shard_index=shard_index)]
    SPEC['builders'][builder_name] = TestSpec(
        'chromium_perf', perf_id, platform, target_bits, tests=tests,
        parent_buildername=parent_buildername)


_AddBuildSpec('Android Builder', 'android', target_bits=32)
_AddBuildSpec('Android Compile', 'android', target_bits=32,
              extra_compile_targets=['android_tools',
                                     'cc_perftests',
                                     'chrome_public_apk',
                                     'gpu_perftests',
                                     'push_apps_to_background_apk',
                                     'system_webview_apk',
                                     'system_webview_shell_apk',])
_AddBuildSpec('Android arm64 Builder', 'android')
_AddBuildSpec('Win Builder', 'win', target_bits=32, enable_swarming=True)
_AddBuildSpec( \
  'Win x64 Builder', 'win', add_to_bisect=True, enable_swarming=True)
_AddBuildSpec('Mac Builder', 'mac', add_to_bisect=True, enable_swarming=True)
_AddBuildSpec( \
  'Linux Builder', 'linux', add_to_bisect=True, enable_swarming=True)


_AddTestSpec('Android Nexus5 Perf', 'android-nexus5', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus5X Perf', 'android-nexus5X', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3,
             parent_buildername='Android Compile')
_AddTestSpec('Android Nexus6 Perf', 'android-nexus6', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus7v2 Perf', 'android-nexus7v2', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android Nexus9 Perf', 'android-nexus9', 'android',
             num_device_shards=7, num_host_shards=3)
_AddTestSpec('Android One Perf', 'android-one', 'android',
             target_bits=32, num_device_shards=7, num_host_shards=3)


_AddTestSpec('Win Zenbook Perf', 'win-zenbook', 'win',
             num_host_shards=5)
_AddTestSpec('Win 10 High-DPI Perf', 'win-high-dpi', 'win',
             num_host_shards=5)
_AddTestSpec('Win 10 Perf', 'chromium-rel-win10', 'win',
             num_host_shards=5)
_AddTestSpec('Win 8 Perf', 'chromium-rel-win8-dual', 'win',
             num_host_shards=5)
_AddIsolatedTestSpec('Win 7 Perf', 'chromium-rel-win7-dual', 'win',
                     target_bits=32)
_AddIsolatedTestSpec('Win 7 x64 Perf', 'chromium-rel-win7-x64-dual', 'win')
_AddIsolatedTestSpec('Win 7 ATI GPU Perf', 'chromium-rel-win7-gpu-ati', 'win')
_AddIsolatedTestSpec('Win 7 Intel GPU Perf', 'chromium-rel-win7-gpu-intel',
                     'win')
_AddIsolatedTestSpec('Win 7 Nvidia GPU Perf', 'chromium-rel-win7-gpu-nvidia',
                     'win')


_AddTestSpec('Mac 10.11 Perf', 'chromium-rel-mac11', 'mac',
             num_host_shards=5)
_AddIsolatedTestSpec('Mac 10.10 Perf', 'chromium-rel-mac10', 'mac')
_AddTestSpec('Mac Retina Perf', 'chromium-rel-mac-retina', 'mac',
             num_host_shards=5)
_AddTestSpec('Mac HDD Perf', 'chromium-rel-mac-hdd', 'mac',
             num_host_shards=5)
_AddIsolatedTestSpec('Mac Pro 10.11 Perf', 'chromium-rel-mac11-pro', 'mac')
_AddIsolatedTestSpec('Mac Air 10.11 Perf', 'chromium-rel-mac11-air', 'mac')


_AddIsolatedTestSpec('Linux Perf', 'linux-release', 'linux')
