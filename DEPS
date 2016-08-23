deps = {
  'build/scripts/gsd_generate_index':
    'https://chromium.googlesource.com/chromium/tools/gsd_generate_index.git',
  'build/scripts/private/data/reliability':
    'https://chromium.googlesource.com/chromium/src/chrome/test/data/reliability.git',
  'build/scripts/tools/deps2git':
    'https://chromium.googlesource.com/chromium/tools/deps2git.git',
  'build/third_party/gsutil':
    'https://chromium.googlesource.com/external/gsutil/src.git'
    '@5cba434b828da428a906c8197a23c9ae120d2636',
  'build/third_party/gsutil/boto':
    'https://chromium.googlesource.com/external/boto.git'
    '@98fc59a5896f4ea990a4d527548204fed8f06c64',
  'build/third_party/infra_libs':
    'https://chromium.googlesource.com/infra/infra/packages/infra_libs.git'
    '@15ea0920b5f83d0aff4bd042e95bc388d069d51c',
  'build/third_party/lighttpd':
    'https://chromium.googlesource.com/chromium/deps/lighttpd.git'
    '@9dfa55d15937a688a92cbf2b7a8621b0927d06eb',
  'build/third_party/pyasn1':
    'https://chromium.googlesource.com/external/github.com/etingof/pyasn1.git'
    '@4181b2379eeae3d6fd9f4f76d0e6ae3789ed56e7',
  'build/third_party/pyasn1-modules':
    'https://chromium.googlesource.com/external/github.com/etingof/pyasn1-modules.git'
    '@956fee4f8e5fd3b1c500360dc4aa12dc5a766cb2',
  'build/third_party/python-rsa':
    'https://chromium.googlesource.com/external/github.com/sybrenstuvel/python-rsa.git'
    '@version-3.1.4',
  'depot_tools':
    'https://chromium.googlesource.com/chromium/tools/depot_tools.git',
}

deps_os = {
  'unix': {
    'build/third_party/xvfb':
      'https://chromium.googlesource.com/chromium/tools/third_party/xvfb.git',
  },
}

hooks = [
  {
    "pattern": ".",
    "action": [
      "python", "-u", "build/scripts/common/remove_orphaned_pycs.py",
    ],
  },
  {
    "name": "cros_chromite",
    "pattern": r".*/cros_chromite_pins\.json",
    "action": [
      "python", "build/scripts/tools/runit.py", "python",
      "build/scripts/common/cros_chromite.py", "-v",
    ],
  },
]
