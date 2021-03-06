# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'file',
  'depot_tools/gsutil',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]


BUILDERS = freeze({
  'tryserver.chromium.linux': {
    'builders': {
      'linux_upload_clang': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'linux',
          'TARGET_BITS': 64,
        },

        # We need this to build the Clang toolchain
        # with proper AddressSanitizer prebuilts for
        # Chrome on Android.
        'gclient_apply_config': ['android'],
      },
    },
  },
  'tryserver.chromium.mac': {
    'builders': {
      'mac_upload_clang': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'mac',
          'TARGET_BITS': 64,
        },
      },
    },
  },
  'tryserver.chromium.win': {
    'builders': {
      'win_upload_clang': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'win',
          'TARGET_BITS': 32,
        },
      },
    },
  },
})


def RunSteps(api):
  _, bot_config = api.chromium.configure_bot(BUILDERS)

  api.bot_update.ensure_checkout(
      patch_root=bot_config.get('root_override'))

  api.python('update win toolchain',
      api.path['checkout'].join('build', 'vs_toolchain.py'), ['update'])
  api.python('update mac toolchain',
      api.path['checkout'].join('build', 'mac_toolchain.py'))
  api.python('download binutils',
      api.path['checkout'].join('third_party', 'binutils', 'download.py'))

  api.python(
      'package clang',
      api.path['checkout'].join('tools', 'clang', 'scripts', 'package.py'),
      args=['--upload'])


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield test
