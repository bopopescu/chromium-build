# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Mojo(Master.Master3):
  project_name = 'Mojo'
  master_port = 8019
  slave_port = 8119
  master_port_alt = 8219
  buildbot_url = 'http://build.chromium.org/p/client.mojo/'
  service_account_file = 'service-account-chromium-tryserver.json'
  buidlbucket_build = 'master.tryserver.client.mojo'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.mojo'
