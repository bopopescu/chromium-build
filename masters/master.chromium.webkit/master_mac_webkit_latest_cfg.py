# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# WebKit test builders using the Skia graphics library.
#
# Note that we use the builder vs tester role separation differently
# here than in our other buildbot configurations.
#
# In this configuration, the testers build the tests themselves rather than
# extracting them from the builder.  That's because these testers always
# fetch from webkit HEAD, and by the time the tester runs, webkit HEAD may
# point at a different revision than it did when the builder fetched webkit.
#
# Even though the testers don't extract the build package from the builder,
# the builder is still useful because it can cycle more quickly than the
# builder+tester can, and can alert us more quickly to build breakages.
#
# If you have questions about this, you can ask nsylvain.

from buildbot.process.properties import WithProperties

from master import master_config
from master import master_utils
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

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

defaults['category'] = 'layout'

################################################################################
## Release
################################################################################

#
# Triggerable scheduler for testers
#
T('s5_webkit_rel_trigger')

#
# Mac Rel Builder
#
B('WebKit Mac Builder', 'f_webkit_mac_rel',
  auto_reboot=False, scheduler='global_scheduler',
  builddir='webkit-mac-latest-rel')
F('f_webkit_mac_rel', m_remote_run_chromium_src(
    'chromium', triggers=['s5_webkit_rel_trigger']))

#
# Mac Rel WebKit testers
#

B('WebKit Mac10.9', 'f_webkit_rel_tests_109',
  scheduler='s5_webkit_rel_trigger')
F('f_webkit_rel_tests_109', m_remote_run_chromium_src('chromium'))

B('WebKit Mac10.10', 'f_webkit_rel_tests_1010',
  scheduler='s5_webkit_rel_trigger')
F('f_webkit_rel_tests_1010', m_remote_run_chromium_src('chromium'))

B('WebKit Mac10.11', 'f_webkit_rel_tests_1011',
  scheduler='s5_webkit_rel_trigger')
F('f_webkit_rel_tests_1011', m_remote_run_chromium_src('chromium'))

B('WebKit Mac10.11 (retina)', 'f_webkit_rel_tests_1011_retina',
  scheduler='s5_webkit_rel_trigger')
F('f_webkit_rel_tests_1011_retina', m_remote_run_chromium_src('chromium'))


################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = master_config.GetGSUtilUrl('chromium-build-transfer',
                                         'WebKit Mac Builder (dbg)')

#
# Triggerable scheduler for testers
#
T('s5_webkit_dbg_trigger')

#
# Mac Dbg Builder
#
B('WebKit Mac Builder (dbg)', 'f_webkit_mac_dbg', auto_reboot=False,
  scheduler='global_scheduler', builddir='webkit-mac-latest-dbg')
F('f_webkit_mac_dbg', m_remote_run_chromium_src(
    'chromium', triggers=['s5_webkit_dbg_trigger']))

#
# Mac Dbg WebKit testers
#

B('WebKit Mac10.11 (dbg)', 'f_webkit_dbg_tests',
    scheduler='s5_webkit_dbg_trigger')
F('f_webkit_dbg_tests', m_remote_run_chromium_src('chromium'))


################################################################################
##
################################################################################

def Update(_config, _active_master, c):
  return helper.Update(c)
