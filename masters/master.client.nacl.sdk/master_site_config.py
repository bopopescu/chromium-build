# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class NativeClientSDK(Master.NaClBase):
  project_name = 'NativeClientSDK'
  master_port = 8034
  slave_port = 8134
  master_port_alt = 8234
  buildbot_url = 'http://build.chromium.org/p/client.nacl.sdk/'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.nacl.sdk'
