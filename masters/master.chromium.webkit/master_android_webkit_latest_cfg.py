# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from master import master_config
from master.factory import remote_run_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_master=ActiveMaster,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


################################################################################
## Release
################################################################################

defaults['category'] = 'layout'

#
# Triggerable scheduler for the builder
#
T('android_rel_trigger')

#
# Android Rel Builder
#
B('Android Builder', 'f_android_rel', scheduler='global_scheduler')
F('f_android_rel', m_remote_run('chromium', triggers=['android_rel_trigger']))

B('WebKit Android (Nexus4)', 'f_webkit_android_tests', None,
  'android_rel_trigger')
F('f_webkit_android_tests', m_remote_run('chromium'))

def Update(_config, _active_master, c):
  return helper.Update(c)
