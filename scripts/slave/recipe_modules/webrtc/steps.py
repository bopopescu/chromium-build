# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

def generate_tests(api, test_suite, revision, enable_swarming=False):
  tests = []

  GTestTest = api.m.chromium_tests.steps.GTestTest

  if test_suite == 'webrtc':
    for test, extra_args in sorted(api.NORMAL_TESTS.items()):
      tests.append(WebRTCTest(test, enable_swarming=enable_swarming,
                              revision=revision, **extra_args))
  elif test_suite == 'desktop_swarming':
    for test, extra_args in sorted(api.NORMAL_TESTS.items()):
      if api.mastername == 'client.webrtc.fyi':
        tests.append(GTestTest(test, enable_swarming=enable_swarming,
                               **extra_args))
      else:
        tests.append(WebRTCTest(test, enable_swarming=enable_swarming,
                                revision=revision, **extra_args))
  elif test_suite == 'webrtc_baremetal':
    api.virtual_webcam_check()  # Needed for video_capture_tests below.

    # This test currently fails on Trusty Linux due to pulseaudio issues. See
    # http://crbug.com/589101
    if api.m.platform.is_mac or api.m.platform.is_win:
      tests.append(BaremetalTest('audio_device_tests', revision))

    tests.extend([
        BaremetalTest('voe_auto_test', revision, args=['--automated']),
        BaremetalTest('video_capture_tests', revision),
    ])
  elif test_suite == 'desktop_perf':
    assert api.c.PERF_ID
    if api.m.platform.is_linux:
      f = api.m.path['checkout'].join
      tests.append(
          BaremetalTest('isac_fix_test',
                        revision,
                        args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                              'isac_speech_and_misc_wb.pcm'],
                        perf_test=True),
      )
    tests.append(BaremetalTest('webrtc_perf_tests', revision, perf_test=True))
  elif test_suite == 'android_perf' and api.c.PERF_ID:
    # TODO(kjellander): Fix the Android ASan bot so we can have an assert here.
    tests.append(AndroidPerfTest('webrtc_perf_tests', revision))
  elif test_suite == 'android_swarming':
    for test in (api.ANDROID_DEVICE_TESTS +
                 api.ANDROID_INSTRUMENTATION_TESTS):
      tests.append(GTestTest(test, enable_swarming=enable_swarming,
                             override_isolate_target=test))
    for test in api.ANDROID_JUNIT_TESTS:
      tests.append(AndroidJunitTest(test))

  return tests


# TODO(kjellander): Continue refactoring an integrate the classes in the
# chromium_tests recipe module instead (if possible).
class Test(object):
  def __init__(self, name, enable_swarming=False, swarming_shards=1):
    self._name = name
    self._enable_swarming = enable_swarming
    self._swarming_task = None
    self._swarming_shards = swarming_shards

  def run_nonswarming(self, api, suffix): # pragma: no cover:
    raise NotImplementedError()

  def pre_run(self, api, suffix):
    return []

  def run(self, api, suffix):
    if self._enable_swarming:
      isolated_hash = api.m.isolate.isolated_tests[self._name]
      self._swarming_task = api.m.swarming.task(self._name, isolated_hash,
                                                shards=self._swarming_shards)
      api.m.swarming.trigger_task(self._swarming_task)
    else:
      self.run_nonswarming(api, suffix)

  def post_run(self, api, suffix):
    if self._enable_swarming:
      api.swarming.collect_task(self._swarming_task)
    else:
      return []

class WebRTCTest(Test):
  """A normal WebRTC desktop test."""
  def __init__(self, name, revision=None, enable_swarming=False,
               swarming_shards=1, parallel=True, perf_test=False,
               **runtest_kwargs):
    super(WebRTCTest, self).__init__(name, enable_swarming, swarming_shards)
    self._revision = revision
    self._parallel = parallel
    self._perf_test = perf_test
    self._runtest_kwargs = runtest_kwargs

  def run_nonswarming(self, api, suffix):
    self._runtest_kwargs['test'] = self._name
    api.add_test(name=self._name, revision=self._revision,
                 parallel=self._parallel, perf_test=self._perf_test,
                 **self._runtest_kwargs)

class BaremetalTest(WebRTCTest):
  """A WebRTC desktop test that uses audio and/or video devices."""
  def __init__(self, name, revision, perf_test=False, **runtest_kwargs):
    # Tests accessing hardware devices shouldn't be run in parallel.
    super(BaremetalTest, self).__init__(name, revision, parallel=False,
                                        perf_test=perf_test, **runtest_kwargs)

class AndroidJunitTest(Test):
  """Runs an Android Junit test."""

  def run_nonswarming(self, api, suffix):
    api.m.chromium_android.run_java_unit_test_suite(self._name)

class AndroidPerfTest(Test):
  """A performance test to run on Android devices.

    Basically just wrap what happens in chromium_android.run_test_suite to run
    inside runtest.py so we can scrape perf data. This way we can get perf data
    from the gtest binaries since the way of running perf tests with telemetry
    is entirely different.
  """

  def __init__(self, name, revision):
    super(AndroidPerfTest, self).__init__(name)
    self._revision = revision

  def run_nonswarming(self, api, suffix):
    wrapper_script = api.m.chromium.output_dir.join('bin',
                                                    'run_%s' % self._name)
    args = ['--verbose']
    api.add_test(name=self._name,
                 test=wrapper_script,
                 args=args,
                 revision=self._revision,
                 python_mode=True,
                 perf_test=True,
                 perf_dashboard_id=self._name)

