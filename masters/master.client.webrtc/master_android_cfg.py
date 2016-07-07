# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_android_scheduler',
                            branch='master',
                            treeStableTimer=30,
                            builderNames=[
          'Android32 Builder',
          'Android32 Builder (dbg)',
          'Android32 Builder x86',
          'Android32 Builder x86 (dbg)',
          'Android32 Builder MIPS (dbg)',
          'Android32 Clang (dbg)',
          'Android64 Builder',
          'Android64 Builder (dbg)',
          'Android64 Builder x64 (dbg)',
          'Android32 GN',
          'Android32 GN (dbg)',
      ]),
  ])

  # 'slavebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple slave machines.
  specs = [
    {'name': 'Android32 Builder'},
    {'name': 'Android32 Builder (dbg)'},
    {'name': 'Android32 Builder x86', 'slavebuilddir': 'android_x86'},
    {'name': 'Android32 Builder x86 (dbg)', 'slavebuilddir': 'android_x86'},
    {'name': 'Android32 Builder MIPS (dbg)', 'slavebuilddir': 'android_mips'},
    {'name': 'Android32 Clang (dbg)', 'slavebuilddir': 'android_clang'},
    {'name': 'Android64 Builder', 'slavebuilddir': 'android_arm64'},
    {'name': 'Android64 Builder (dbg)', 'slavebuilddir': 'android_arm64'},
    {'name': 'Android64 Builder x64 (dbg)', 'slavebuilddir': 'android_x64'},
    {'name': 'Android32 GN', 'slavebuilddir': 'android_gn'},
    {'name': 'Android32 GN (dbg)', 'slavebuilddir': 'android_gn'},
    {'name': 'Android32 Tests (L Nexus5)(dbg)'},
    {'name': 'Android32 Tests (L Nexus7.2)(dbg)'},
    {'name': 'Android64 Tests (L Nexus9)'},
    {'name': 'Android32 Tests (L Nexus5)'},
    {'name': 'Android32 Tests (L Nexus7.2)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'android',
        'slavebuilddir': spec.get('slavebuilddir', 'android'),
      } for spec in specs
  ])
