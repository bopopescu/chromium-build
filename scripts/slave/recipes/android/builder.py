# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager
from recipe_engine import recipe_api
from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'chromium_android',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'trigger',
  'depot_tools/tryserver',
]

@contextmanager
def FYIStep():
  try:
    yield
  except recipe_api.StepFailure:
    pass

BUILDERS = freeze({
  'chromium.android': {
    'Android x64 Builder (dbg)': {
      'recipe_config': 'x64_builder_mb',
      'check_licenses': FYIStep,
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
    'Android x86 Builder (dbg)' : {
      'recipe_config': 'x86_builder_mb',
      'check_licenses': FYIStep,
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
    'Android MIPS Builder (dbg)': {
      'recipe_config': 'mipsel_builder_mb',
      'check_licenses': FYIStep,
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
  },
  'chromium.perf': {
    'Android Builder': {
      'recipe_config': 'main_builder_rel_mb',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'chrome-perf',
        'path': lambda api: ('Android Builder/full-build-linux_%s.zip'
                             % api.properties['revision']),
      },
      'run_mb': True,
      'targets': [
        'android_tools',
        'cc_perftests',
        'chrome_public_apk',
        'gpu_perftests',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
      ],
      'triggers': [
        {
          'buildername': 'Android Galaxy S5 Perf (1)',
          'mastername': 'chromium.perf.fyi',
        },
        {
          'buildername': 'Android Power Nexus 5X Perf (1)',
          'mastername': 'chromium.perf.fyi',
        },
      ],
    },
    'Android arm64 Builder': {
      'recipe_config': 'arm64_builder_rel_mb',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'chrome-perf',
        'path': lambda api: (
            'Android arm64 Builder/full-build-linux_%s.zip'
            % api.properties['revision']),
      },
      'run_mb': True,
      'targets': [
        'android_tools',
        'cc_perftests',
        'chrome_public_apk',
        'gpu_perftests',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
      ],
    }
  },
  'tryserver.chromium.perf': {
    'android_perf_bisect_builder': {
      'recipe_config': 'main_builder_rel_mb',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      # Perf bisect builders uses custom file names for binaries with
      # DEPS changes, and the logic for this is in zip_build.py.
      'zip_and_upload': {
        'bucket': 'chrome-perf',
      },
      'run_mb': True,
    },
    'android_arm64_perf_bisect_builder': {
      'recipe_config': 'arm64_builder_rel_mb',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      # Perf bisect builders uses custom file names for binaries with
      # DEPS changes, and the logic for this is in zip_build.py.
      'zip_and_upload': {
        'bucket': 'chrome-perf',
      },
      'run_mb': True,
    },
  },
  'client.v8.fyi': {
    'Android Builder': {
      'recipe_config': 'main_builder_rel_mb',
      'gclient_apply_config': [
        'android',
        'perf',
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'v8-android',
        'path': lambda api: ('v8_android_perf_rel/full-build-linux_%s.zip'
                             % api.properties['revision']),
      },
      'run_mb': True,
      'targets': [
        'android_tools',
        'cc_perftests',
        'chrome_public_apk',
        'gpu_perftests',
        'push_apps_to_background_apk',
        'system_webview_apk',
        'system_webview_shell_apk',
      ],
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
    }
  },
})

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'mastername': Property(),
  'buildername': Property(),
  'revision': Property(default='HEAD'),
}

def _RunStepsInternal(api, mastername, buildername, revision):
  bot_config = BUILDERS[mastername][buildername]
  droid = api.chromium_android

  default_kwargs = {
    'REPO_URL': 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
    'INTERNAL': False,
    'REPO_NAME': 'src',
    'BUILD_CONFIG': bot_config.get('target', 'Debug'),
  }
  default_kwargs.update(bot_config.get('kwargs', {}))
  droid.configure_from_properties(bot_config['recipe_config'], **default_kwargs)
  api.chromium.set_config(bot_config['recipe_config'], **default_kwargs)
  droid.c.set_val({'deps_file': 'DEPS'})

  api.gclient.set_config('chromium')
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if bot_config.get('set_component_rev'):
    # If this is a component build and the main revision is e.g. blink,
    # webrtc, or v8, the custom deps revision of this component must be
    # dynamically set to either:
    # (1) 'revision' from the waterfall, or
    # (2) 'HEAD' for forced builds with unspecified 'revision'.
    component_rev = revision
    dep = bot_config.get('set_component_rev')
    api.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

  api.chromium.ensure_goma()
  api.bot_update.ensure_checkout()
  api.chromium_android.clean_local_files()

  api.chromium.runhooks()

  if bot_config.get('run_mb'):
    api.chromium.run_mb(mastername, buildername, use_goma=True)

  if bot_config.get('check_licenses'):
    with bot_config['check_licenses']():
      droid.check_webview_licenses()
  api.chromium.compile(bot_config.get('targets'))

  upload_config = bot_config.get('upload')
  if upload_config:
    droid.upload_build(upload_config['bucket'],
                       upload_config['path'](api))

  upload_config = bot_config.get('zip_and_upload')
  if upload_config:
    droid.zip_and_upload_build(upload_config['bucket'])

  if 'triggers' in bot_config:
    api.trigger(*[{'bucket': 'master.' + b['mastername'],
                   'builder_name': b['buildername'],
                   'properties': {
                      'revision': api.properties['revision'],
                      'parent_revision': api.properties['revision']}
                   } for b in bot_config['triggers']])


def RunSteps(api, mastername, buildername, revision):
  with api.tryserver.set_failure_hash():
    return _RunStepsInternal(api, mastername, buildername, revision)


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  # tests bots in BUILDERS
  for mastername, builders in BUILDERS.iteritems():
    for buildername in builders:
      yield (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(buildername=buildername,
            repository='svn://svn.chromium.org/chrome/trunk/src',
            buildnumber=257,
            mastername=mastername,
            issue='8675309',
            patchset='1',
            revision='267739',
            got_revision='267739'))

  def step_failure(mastername, buildername, steps, tryserver=False):
    props = api.properties.tryserver if tryserver else api.properties.generic
    return (
      api.test('%s_%s_fail_%s' % (
        _sanitize_nonalpha(mastername),
        _sanitize_nonalpha(buildername),
        '_'.join(_sanitize_nonalpha(step) for step in steps))) +
      props(mastername=mastername, buildername=buildername) +
      reduce(lambda a, b: a + b,
             (api.step_data(step, retcode=1) for step in steps))
    )

  yield step_failure(mastername='chromium.android',
                     buildername='Android x64 Builder (dbg)',
                     steps=['check licenses'])

