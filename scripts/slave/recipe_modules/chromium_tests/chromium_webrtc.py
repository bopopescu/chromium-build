# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
from . import steps


_builders = collections.defaultdict(dict)


RESULTS_URL = 'https://chromeperf.appspot.com'
SPEC = {
  'settings': {
    'build_gs_bucket': 'chromium-webrtc',
  },
  'builders': {},
}

BROWSER_TESTS_FILTER = [
  # Benefits from non-default device configurations (but could be implemented
  # on a VM using the fake device flags in different combinations)..
  'MediaStreamDevicesControllerTest.*',
  'MediaStreamDevicesControllerBrowserTestInstance*',

  # Runs hardware-exercising test and/or video calling tests.
  'WebRtcApprtcBrowserTest.*',
  'WebrtcAudioPrivateTest.*',
  'WebRtcAudioQualityBrowserTest.*',
  'WebRtcBrowserTest.*',
  'WebRtcDisableEncryptionFlagBrowserTest.*',
  'WebRtcGetMediaDevicesBrowserTests*',
  'WebRtcInternalsPerfBrowserTest.*',
  'WebRtcMediaRecorderTest.*',
  'WebRtcSimulcastBrowserTest.*',
  'WebRtcStatsPerfBrowserTest.*',
  'WebRtcVideoQualityBrowserTests*',
  'WebRtcWebcamBrowserTests*',
]


def BaseSpec(bot_type, chromium_apply_config, gclient_config, platform,
             target_bits, build_config='Release'):
  spec = {
    'bot_type': bot_type,
    'chromium_apply_config' : chromium_apply_config,
    'chromium_config': 'chromium',
    'chromium_config_kwargs': {
      'BUILD_CONFIG': build_config,
      'TARGET_BITS': target_bits,
    },
    'gclient_config': gclient_config,
    'gclient_apply_config': [],
    'testing': {
      'platform': 'linux' if platform == 'android' else platform,
    },
  }
  spec['chromium_apply_config'].append('chrome_with_codecs')
  if platform == 'android':
    spec['android_config'] = 'base_config'
    spec['chromium_config_kwargs']['TARGET_ARCH'] = 'arm'
    spec['chromium_config_kwargs']['TARGET_PLATFORM'] = 'android'
    spec['chromium_apply_config'].append('android')
    spec['gclient_apply_config'].append('android')
  return spec


def BuildSpec(platform, target_bits, build_config='Release',
              gclient_config='chromium_webrtc'):
  spec = BaseSpec(
      bot_type='builder',
      chromium_apply_config=['dcheck', 'blink_logging_on', 'mb'],
      gclient_config=gclient_config,
      platform=platform,
      target_bits=target_bits,
      build_config=build_config)
  return spec


class WebRTCPerfTest(steps.LocalGTestTest):
  """A LocalGTestTest reporting perf metrics.

  WebRTC is the only project that runs correctness tests with perf reporting
  enabled at the same time, which differs from the chromium.perf bots.
  """
  def __init__(self, name, args, perf_id, **runtest_kwargs):
    assert perf_id
    # TODO(kjellander): See if it's possible to rely on the build spec
    # properties 'perf-id' and 'results-url' as set in the
    # chromium_tests/chromium_perf.py. For now, set these to get an exact
    # match of our current expectations.
    runtest_kwargs['perf_id'] = perf_id
    runtest_kwargs['results_url'] = RESULTS_URL

    # TODO(kjellander): See if perf_dashboard_id is still needed.
    runtest_kwargs['perf_dashboard_id'] = name
    runtest_kwargs['annotate'] = 'graphing'
    super(WebRTCPerfTest, self).__init__(name, args, **runtest_kwargs)

  def run(self, api, suffix):
    webrtc_subtree_git_hash = api.bot_update.last_returned_properties.get(
        'got_webrtc_revision', 'deadbeef')
    self._runtest_kwargs['perf_config'] = {
        # TODO(kjellander: Change to r_webrtc_git after crbug.com/611808.
        'r_webrtc_subtree_git': webrtc_subtree_git_hash,
        'a_default_rev': 'r_webrtc_subtree_git',
    }
    steps.LocalGTestTest.run(self, api, suffix)


def TestSpec(parent_builder, perf_id, platform, target_bits,
             build_config='Release', gclient_config='chromium_webrtc',
             test_spec_file='chromium.webrtc.json'):
  spec = BaseSpec(
      bot_type='tester',
      chromium_apply_config=[],
      gclient_config=gclient_config,
      platform=platform,
      target_bits=target_bits,
      build_config=build_config)

  spec['parent_buildername'] = parent_builder

  if platform == 'android':
    spec['root_devices'] = True
    spec['tests'] = [
      steps.GTestTest(
          'content_browsertests',
          args=['--gtest_filter=WebRtc*']),
    ]
  else:
    spec['gclient_apply_config'].append('webrtc_test_resources')
    spec['tests'] = [
      WebRTCPerfTest('content_browsertests',
                     args=['--gtest_filter=WebRtc*', '--run-manual',
                           '--test-launcher-print-test-stdio=always',
                           '--test-launcher-bot-mode'],
                     perf_id=perf_id),
      WebRTCPerfTest('browser_tests',
          # These tests needs --test-launcher-jobs=1 since some of them are
          # not able to run in parallel (due to the usage of the
          # peerconnection server).
          args=['--gtest_filter=%s' % ':'.join(BROWSER_TESTS_FILTER),
                '--run-manual', '--ui-test-action-max-timeout=350000',
                '--test-launcher-jobs=1',
                '--test-launcher-bot-mode',
                '--test-launcher-print-test-stdio=always'],
          perf_id=perf_id),

      # Run capture unittests as well since our bots have real webcams.
      steps.GTestTest('capture_unittests',
                 args=['--enable-logging',
                       '--v=1',
                       '--test-launcher-jobs=1',
                       '--test-launcher-print-test-stdio=always']),
      steps.GTestTest('content_unittests'),
      steps.GTestTest('jingle_unittests'),
      steps.GTestTest('remoting_unittests', args=['--gtest_filter=Webrtc*']),
    ]
  return spec


def AddBuildSpec(name, platform, target_bits=64):
  SPEC['builders'][name] = BuildSpec(platform, target_bits)
  assert target_bits not in _builders[platform]
  _builders[platform][target_bits] = name


def AddTestSpec(name, perf_id, platform, target_bits=64):
  parent_builder = _builders[platform][target_bits]
  SPEC['builders'][name] = TestSpec(parent_builder, perf_id, platform,
                                    target_bits)


AddBuildSpec('Win Builder', 'win', target_bits=32)
AddBuildSpec('Mac Builder', 'mac')
AddBuildSpec('Linux Builder', 'linux')

AddTestSpec('Win7 Tester', 'chromium-webrtc-rel-7', 'win', target_bits=32)
AddTestSpec('Win8 Tester', 'chromium-webrtc-rel-win8', 'win', target_bits=32)
AddTestSpec('Win10 Tester', 'chromium-webrtc-rel-win10', 'win', target_bits=32)
AddTestSpec('Mac Tester', 'chromium-webrtc-rel-mac', 'mac')
AddTestSpec('Linux Tester', 'chromium-webrtc-rel-linux', 'linux')
