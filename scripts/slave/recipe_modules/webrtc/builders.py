# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the WebRTC builder configurations so they can be reused
# from multiple recipes.

from recipe_engine.types import freeze

RECIPE_CONFIGS = freeze({
  'webrtc': {
    'chromium_config': 'webrtc_standalone',
    'gclient_config': 'webrtc',
    'test_suite': 'webrtc',
  },
  'webrtc_gcc': {
    'chromium_config': 'webrtc_gcc',
    'gclient_config': 'webrtc',
  },
  'webrtc_baremetal': {
    'chromium_config': 'webrtc_standalone',
    'gclient_config': 'webrtc',
    'test_suite': 'webrtc_baremetal',
  },
  'webrtc_clang': {
    'chromium_config': 'webrtc_clang',
    'gclient_config': 'webrtc',
    'test_suite': 'webrtc',
  },
  'webrtc_android': {
    'chromium_config': 'android',
    'chromium_android_config': 'webrtc',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
    'test_suite': 'android',
  },
  'webrtc_android_clang': {
    'chromium_config': 'android_clang',
    'chromium_android_config': 'webrtc',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
  },
  'webrtc_android_asan': {
    'chromium_config': 'android_asan',
    'chromium_android_config': 'webrtc',
    'gclient_config': 'webrtc',
    'gclient_apply_config': ['android'],
    'test_suite': 'android',
  },
})

WEBRTC_REVISION_PERF_CONFIG = '{\'a_default_rev\': \'r_webrtc_rev\'}'

BUILDERS = freeze({
  'client.webrtc': {
    'settings': {
      'build_gs_bucket': 'chromium-webrtc',
      'PERF_CONFIG': WEBRTC_REVISION_PERF_CONFIG,
    },
    'builders': {
      'Win32 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win32 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win64 Debug': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['static_library'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win64 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win64 Debug (GN)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win64 Release (GN)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win32 Debug (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win32 Release (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win64 Debug (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win64 Release (Clang)': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'Win32 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-win-large-tests',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win DrMemory Full': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_full'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win DrMemory Light': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_light'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Win SyzyASan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['syzyasan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'Mac64 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'Mac64 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'Mac64 Debug (GN)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'Mac64 Release (GN)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'Mac Asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'Mac64 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-mac-large-tests',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'Linux32 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux32 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux64 Debug': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux64 Release': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux64 Debug (GN)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Linux64 Release (GN)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Linux Asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan', 'lsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux Memcheck': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['webrtc_valgrind'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux MSan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['msan', 'msan_full_origin_tracking',
                                  'prebuilt_instrumented_libraries'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux Tsan v2': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['tsan2'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
       'Linux UBSan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['ubsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux UBSan vptr': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['ubsan_vptr'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Linux64 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-linux-large-tests',
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Android32 Builder': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android32 Tests (L Nexus5)',
          'Android32 Tests (L Nexus7.2)',
        ],
      },
      'Android32 Builder (dbg)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android32 Tests (L Nexus5)(dbg)',
          'Android32 Tests (L Nexus7.2)(dbg)',
        ],
      },
      'Android32 Builder x86 (dbg)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Builder MIPS (dbg)': {
        'recipe_config': 'webrtc_android_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'mipsel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android64 Builder': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android64 Tests (L Nexus9)',
        ],
      },
      'Android64 Builder (dbg)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android64 Builder x64 (dbg)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Clang (dbg)': {
        'recipe_config': 'webrtc_android_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 GN (dbg)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 GN': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus5)(dbg)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder (dbg)',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus5)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus5',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus7.2)(dbg)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder (dbg)',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus7.2)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus72',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder Release',
        'testing': {'platform': 'linux'},
      },
      'Android64 Tests (L Nexus9)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus9',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android64 Builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
  'client.webrtc.fyi': {
    'settings': {
      'build_gs_bucket': 'chromium-webrtc',
    },
    'builders':  {
      'Win32 Release (swarming)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
      },
      'Mac64 Release (swarming)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
      },
      'Linux64 Release (swarming)': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
      },
      'Linux32 ARM': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Linux64 GCC': {
        'recipe_config': 'webrtc_gcc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 ASan (L Nexus6)': {
        'recipe_config': 'webrtc_android_asan',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'Android32 Builder': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
        'triggers': [
          'Android32 Tests (J Nexus4)',
          'Android32 Tests (K Nexus5)',
          'Android32 Tests (L Nexus6)',
        ],
      },
      'Android32 Tests (J Nexus4)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus4-jellybean',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (K Nexus5)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus5-kitkat',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
      'Android32 Tests (L Nexus6)': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'PERF_ID': 'webrtc-android-tests-nexus6-lollipop',
        },
        'bot_type': 'tester',
        'parent_buildername': 'Android32 Builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'win_compile_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_compile_x64_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_x64_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_x64_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_x64_gn_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_x64_gn_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_clang_dbg': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_clang_rel': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_x64_clang_dbg': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_x64_clang_rel': {
        'recipe_config': 'webrtc_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'win'},
      },
      'win_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_asan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['syzyasan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_drmemory_light': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_light'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_drmemory_full': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_full'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
      },
      'win_swarming': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'win'},
        'use_isolate': True,
        'enable_swarming': True,
      },
      'mac_compile_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'mac_compile_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'mac_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'mac_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'mac_gn_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'mac_gn_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'mac'},
      },
      'mac_asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'mac_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
      },
      'mac_swarming': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'mac'},
        'use_isolate': True,
        'enable_swarming': True,
      },
      'linux_compile_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'linux_compile_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'linux_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_gn_dbg': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'linux_gn_rel': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'linux_asan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['asan', 'lsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_memcheck': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['webrtc_valgrind'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_msan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['msan', 'msan_full_origin_tracking',
                                  'prebuilt_instrumented_libraries'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_tsan2': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['tsan2'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_ubsan': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['ubsan'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_ubsan_vptr': {
        'recipe_config': 'webrtc_clang',
        'chromium_apply_config': ['ubsan_vptr'],
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'linux_swarming': {
        'recipe_config': 'webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
        'use_isolate': True,
        'enable_swarming': True,
      },
      'android_compile_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_compile_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_compile_arm64_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_compile_arm64_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_compile_x86_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_compile_x64_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'intel',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_compile_mips_dbg': {
        'recipe_config': 'webrtc_android_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'mipsel',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_clang_dbg': {
        'recipe_config': 'webrtc_android_clang',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_arm64_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_n6': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {'platform': 'linux'},
      },
      'android_gn_dbg': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
      'android_gn_rel': {
        'recipe_config': 'webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'chromium_apply_config': ['webrtc_gn'],
        'bot_type': 'builder',
        'testing': {'platform': 'linux'},
      },
    },
  },
})

