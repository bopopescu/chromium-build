# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class DynamoRIO(Master.Master3):
  project_name = 'DynamoRIO'
  master_port = 8059
  slave_port = 8159
  master_port_alt = 8259
  buildbot_url = 'http://build.chromium.org/p/client.dynamorio/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.dynamorio'
