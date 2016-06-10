# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumWin(Master.Master1):
  project_name = 'Chromium Win'
  master_port = 8085
  slave_port = 8185
  master_port_alt = 8285
  buildbot_url = 'http://build.chromium.org/p/chromium.win/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.win'
