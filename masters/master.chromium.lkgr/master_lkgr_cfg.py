# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.process.properties import WithProperties

from master import gitiles_poller
from master import master_config
from master import master_utils
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumLKGR

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

revision_getter = master_utils.ConditionalProperty(
    lambda build: build.getProperty('revision'),
    WithProperties('%(revision)s'),
    'master')

def m_remote_run_chromium_src(recipe, **kwargs):
  kwargs.setdefault('revision', revision_getter)
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/src.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      use_gitiles=True,
      **kwargs)

defaults['category'] = '1lkgr'

# Global scheduler
S(name='chromium_lkgr', branch='lkgr')

################################################################################
## Windows
################################################################################

# ASan/Win bot.
B('Win ASan Release', 'win_asan_rel', scheduler='chromium_lkgr')
F('win_asan_rel', m_remote_run_chromium_src('chromium'))

# ASan/Win coverage bot.
B('Win ASan Release Coverage', 'win_asan_rel_cov', scheduler='chromium_lkgr')
F('win_asan_rel_cov', m_remote_run_chromium_src('chromium'))

# ASan/Win media bot.
B('Win ASan Release Media', 'win_asan_rel_media', scheduler='chromium_lkgr')
F('win_asan_rel_media', m_remote_run_chromium_src('chromium'))

# Win SyzyASan bot.
B('Win SyzyASAN LKGR', 'win_syzyasan_lkgr', 'compile', 'chromium_lkgr')
F('win_syzyasan_lkgr', m_remote_run_chromium_src('chromium', timeout=7200))

################################################################################
## Mac
################################################################################

asan_mac_gyp = 'asan=1 v8_enable_verify_heap=1 enable_ipc_fuzzer=1 '

B('Mac ASAN Release', 'mac_asan_rel', 'compile', 'chromium_lkgr')
F('mac_asan_rel', m_remote_run_chromium_src('chromium'))

B('Mac ASAN Release Media', 'mac_asan_rel_media', 'compile', 'chromium_lkgr')
F('mac_asan_rel_media', m_remote_run_chromium_src('chromium'))

B('Mac ASAN Debug', 'mac_asan_dbg', 'compile', 'chromium_lkgr')
F('mac_asan_dbg', m_remote_run_chromium_src('chromium'))

################################################################################
## Linux
################################################################################


B('ASAN Release', 'linux_asan_rel', 'compile', 'chromium_lkgr')
F('linux_asan_rel', m_remote_run_chromium_src('chromium',
    # We started seeing 29 minute links, bug 360158
    timeout=2400))

B('ASAN Release Media', 'linux_asan_rel_media',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_media', m_remote_run_chromium_src('chromium',
    # We started seeing 29 minute links, bug 360158
    timeout=2400))

B('ASAN Debug', 'linux_asan_dbg', 'compile', 'chromium_lkgr')
F('linux_asan_dbg', m_remote_run_chromium_src('chromium'))

B('ChromiumOS ASAN Release', 'linux_chromiumos_asan_rel', 'compile',
  'chromium_lkgr')
F('linux_chromiumos_asan_rel', m_remote_run_chromium_src('chromium',
    # We started seeing 29 minute links, bug 360158
    timeout=2400))

# The build process is described at
# https://sites.google.com/a/chromium.org/dev/developers/testing/addresssanitizer#TOC-Building-with-v8_target_arch-arm
B('ASan Debug (32-bit x86 with V8-ARM)',
  'linux_asan_dbg_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_dbg_ia32_v8_arm', m_remote_run_chromium_src('chromium'))

B('ASan Release (32-bit x86 with V8-ARM)',
  'linux_asan_rel_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_ia32_v8_arm', m_remote_run_chromium_src('chromium'))

B('ASan Release Media (32-bit x86 with V8-ARM)',
  'linux_asan_rel_media_ia32_v8_arm',
  'compile', 'chromium_lkgr')
F('linux_asan_rel_media_ia32_v8_arm', m_remote_run_chromium_src('chromium'))

# TSan bots.
B('TSAN Release', 'linux_tsan_rel', 'compile', 'chromium_lkgr')
F('linux_tsan_rel', m_remote_run_chromium_src('chromium'))

B('TSAN Debug', 'linux_tsan_dbg', 'compile', 'chromium_lkgr')
F('linux_tsan_dbg', m_remote_run_chromium_src('chromium'))

# MSan bots.
B('MSAN Release (no origins)', 'linux_msan_rel_no_origins', 'compile',
  'chromium_lkgr')
F('linux_msan_rel_no_origins', m_remote_run_chromium_src('chromium'))

B('MSAN Release (chained origins)', 'linux_msan_rel_chained_origins', 'compile',
  'chromium_lkgr')
F('linux_msan_rel_chained_origins', m_remote_run_chromium_src('chromium'))

# UBSan bots.
B('UBSan Release', 'linux_ubsan_rel', 'compile', 'chromium_lkgr')
# UBSan builds very slowly with edge level coverage
F('linux_ubsan_rel', m_remote_run_chromium_src('chromium', timeout=5400))

B('UBSan vptr Release', 'linux_ubsan_vptr_rel', 'compile', 'chromium_lkgr')
F('linux_ubsan_vptr_rel', m_remote_run_chromium_src('chromium'))

def Update(_config, active_master, c):
  lkgr_poller = gitiles_poller.GitilesPoller(
      'https://chromium.googlesource.com/chromium/src',
      branches=['lkgr'])
  c['change_source'].append(lkgr_poller)
  return helper.Update(c)
