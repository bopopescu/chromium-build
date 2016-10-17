# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='libyuv_mac_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
          'Mac64 Debug',
          'Mac64 Release',
          'Mac64 Debug (GYP)',
          'Mac64 Release (GYP)',
          'Mac Asan',
          'iOS Debug',
          'iOS Release',
          'iOS ARM64 Debug',
          'iOS ARM64 Release',
      ]),
  ])

  specs = [
    {'name': 'Mac64 Debug', 'slavebuilddir': 'mac64'},
    {'name': 'Mac64 Release', 'slavebuilddir': 'mac64'},
    {'name': 'Mac64 Debug (GYP)', 'slavebuilddir': 'mac64_gyp'},
    {'name': 'Mac64 Release (GYP)', 'slavebuilddir': 'mac64_gyp'},
    {'name': 'Mac Asan', 'slavebuilddir': 'mac_asan'},
    {'name': 'iOS Debug', 'slavebuilddir': 'mac32'},
    {'name': 'iOS Release', 'slavebuilddir': 'mac32'},
    {'name': 'iOS ARM64 Debug', 'slavebuilddir': 'mac64'},
    {'name': 'iOS ARM64 Release', 'slavebuilddir': 'mac64'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('libyuv/libyuv'),
        'notify_on_missing': True,
        'category': 'mac',
        'slavebuilddir': spec['slavebuilddir'],
      } for spec in specs
  ])
