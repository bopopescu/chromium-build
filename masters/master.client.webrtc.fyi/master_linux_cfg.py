# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Nightly
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_linux_scheduler',
                            branch='master',
                            treeStableTimer=0,
                            builderNames=[
                                'Linux64 GCC',
                                'Linux64 Release (swarming)',
      ]),
      # Run WebRTC DEPS roller at CET hours: 4am, 12pm and 8pm.
      Nightly(
          name='webrtc_deps',
          branch=None,
          builderNames=['Auto-roll - WebRTC DEPS'],
          hour=[19,3,11],  # Pacific timezone.
      ),
  ])

  specs = [
    {
      'name': 'Linux64 GCC',
      'slavebuilddir': 'linux_gcc',
    },
    {
      'name': 'Linux64 Release (swarming)',
      'slavebuilddir': 'linux_swarming',
    },
    {
      'name': 'Auto-roll - WebRTC DEPS',
      'recipe': 'webrtc/auto_roll_webrtc_deps',
      'slavebuilddir': 'linux_autoroll',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec.get('recipe',
                                                    'webrtc/standalone')),
        'notify_on_missing': True,
        'category': 'linux',
        'slavebuilddir': spec['slavebuilddir'],
        'auto_reboot': False,
      } for spec in specs
  ])
