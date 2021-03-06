# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Defines variables necessary to make lightweight linux perf builds.

Declares required files and whitelisted files to run manual bisect
script on perf builds. Binary files that should be
stripped to reduce zip file size are declared. The file list was
gotten from the local chrome executable path. (This can be retrieved by
typing 'chrome://version' in chrome and following the executable path.
The list needs to be updated if future chrome versions require additional files.
"""
CHROME_REQUIRED_FILES = {
  'linux': [
    'chrome',
    'chrome_100_percent.pak',
    'chrome_200_percent.pak',
    'default_apps',
    'icudtl.dat',
    'libclearkeycdm.so',
    'libclearkeycdmadapter.so',
    'libwidevinecdm.so',
    'libwidevinecdmadapter.so',
    'locales',
    'nacl_helper',
    'nacl_helper_bootstrap',
    'nacl_helper_nonsfi',
    'nacl_irt_x86_64.nexe',
    'natives_blob.bin',
    'PepperFlash',
    'pnacl',
    'product_logo_48.png',
    'resources',
    'resources.pak',
    'snapshot_blob.bin',
    'xdg-mime',
    'xdg-settings'
  ],
  'win': [
    'chrome.dll',
    'chrome.exe',
    'chrome_100_percent.pak',
    'chrome_200_percent.pak',
    'chrome_child.dll',
    'chrome_elf.dll',
    'chrome_watcher.dll',
    'default_apps',
    'd3dcompiler_47.dll',
    'icudtl.dat',
    'libEGL.dll',
    'libGLESv2.dll',
    'locales',
    'nacl_irt_x86_64.nexe',
    'natives_blob.bin',
    'PepperFlash',
    'resources.pak',
    'SecondaryTile.png',
    'snapshot_blob.bin'
  ],
  'mac': [
    'Google Chrome.app'
  ]
}

CHROME_WHITELIST_FILES = {
  'linux': '',
  'win': '^\d+\.\d+\.\d+\.\d+\.manifest$',
  'mac': ''
}

CHROME_STRIP_LIST = {
  'linux': [
    'chrome',
    'nacl_helper'
  ],
  'win': [
    # No stripping symbols from win64 archives.

  ],
  'mac': [
    # No stripping symbols from Mac archives.
  ]
}
