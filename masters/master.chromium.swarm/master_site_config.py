# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumSwarm(Master.Master1):
  project_name = 'Chromium Swarm'
  master_port = 8023
  slave_port = 8123
  master_port_alt = 8223
  buildbot_url = 'http://build.chromium.org/p/chromium.swarm/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.swarm'
