# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for running AndroidWebViewShell instrumentation layout tests using
system WebView.
"""

from infra.libs.infra_types import freeze

DEPS = [
  'adb',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'json',
  'path',
  'properties',
  'python',
  'step',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

WEBVIEW_APK = 'SystemWebView.apk'
WEBVIEW_PACKAGE = 'com.android.webview'

WEBVIEW_SHELL_APK = 'AndroidWebViewShell.apk'
WEBVIEW_SHELL_PACKAGE = 'org.chromium.webview_shell'

INSTRUMENTATION_TESTS = freeze([
  {
    'test': 'AndroidWebViewShell',
    'gyp_target': 'android_webview_shell_apk',
    'kwargs': {
      'install_apk': {
        'package': 'org.chromium.webview_shell',
        'apk': 'AndroidWebViewShell.apk'
      },
      'isolate_file_path':
        'android_webview/android_webview_shell_test_apk.isolate',
    },
  },
])


def RunSteps(api):
  api.chromium_android.configure_from_properties('webview_perf',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')

  # Sync code.
  api.gclient.set_config('perf')
  api.gclient.apply_config('android')
  api.bot_update.ensure_checkout(force=True)
  api.chromium_android.clean_local_files()

  # Gyp the chromium checkout.
  api.chromium.runhooks()

  # Build the WebView apk, WebView shell and Android testing tools.
  api.chromium.compile(targets=['system_webview_apk',
                                'android_webview_shell_apk',
                                'android_tools'])

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.device_status_check()
  api.chromium_android.provision_devices(
      min_battery_level=95, disable_network=True, disable_java_debug=True,
      reboot_timeout=180)

  # Install system WebView.
  api.chromium_android.adb_install_apk(WEBVIEW_APK, WEBVIEW_PACKAGE)

  # Install the WebViewShell.
  api.chromium_android.adb_install_apk(WEBVIEW_SHELL_APK, WEBVIEW_SHELL_PACKAGE)

  api.adb.list_devices()

  # Run the instrumentation tests from the package.
  run_tests(api)

  api.chromium_android.logcat_dump()
  api.chromium_android.stack_tool_steps()
  api.chromium_android.test_report()

def run_tests(api):
  droid = api.chromium_android
  for suite in INSTRUMENTATION_TESTS:
    droid.run_instrumentation_suite(suite['test'], verbose=True,
                                    **suite.get('kwargs', {}))

def GenTests(api):
  yield api.test('basic') + api.properties.scheduled()
