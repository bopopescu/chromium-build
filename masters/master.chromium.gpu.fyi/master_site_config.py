# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumGPUFYI(Master.Master1):
  project_name = 'Chromium GPU FYI'
  master_port = 8017
  slave_port = 8117
  master_port_alt = 8217
  buildbot_url = 'http://build.chromium.org/p/chromium.gpu.fyi/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.gpu.fyi'
