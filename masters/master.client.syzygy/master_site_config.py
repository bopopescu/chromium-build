# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Syzygy(Master.Master3):
  project_name = 'Syzygy'
  project_url = 'http://www.github.com/google/syzygy'
  master_port = 8042
  slave_port = 8142
  master_port_alt = 8242
  buildbot_url = 'https://build.chromium.org/p/client.syzygy/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.syzygy'
