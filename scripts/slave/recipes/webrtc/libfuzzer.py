# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze


DEPS = [
  'archive',
  'depot_tools/bot_update',
  'chromium',
  'file',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'webrtc',
]


BUILDERS = freeze({
  'client.webrtc': {
    'builders': {
      'Linux64 Release (Libfuzzer)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_libfuzzer'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'linux_libfuzzer_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_libfuzzer'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
})


def RunSteps(api):
  webrtc = api.webrtc
  webrtc.apply_bot_config(BUILDERS, webrtc.RECIPE_CONFIGS)

  api.webrtc.checkout()
  api.chromium.ensure_goma()
  api.chromium.runhooks()

  api.chromium.run_gn(use_goma=False)

  step_result = api.python('calculate targets',
          api.path['depot_tools'].join('gn.py'),
          ['--root=%s' % str(api.path['checkout']),
           'refs',
           str(api.chromium.output_dir),
           '--all',
           '--type=executable',
           '--as=output',
           '//webrtc/test/fuzzers:webrtc_fuzzer_main',
          ],
          stdout=api.raw_io.output())

  targets = step_result.stdout.split()
  api.step.active_result.presentation.logs['targets'] = targets
  api.chromium.compile(targets=targets)


def GenTests(api):
  for test in api.chromium.gen_tests_for_builders(BUILDERS):
    yield (test +
           api.step_data('calculate targets',
               stdout=api.raw_io.output('target1 target2 target3'))
           )

