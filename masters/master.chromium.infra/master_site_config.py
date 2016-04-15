# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Infra(Master.Master1):
  project_name = 'Infra'
  master_port_id = 11
  buildbot_url = 'https://build.chromium.org/p/chromium.infra/'
  service_account_file = 'service-account-infra.json'
  buildbucket_bucket = 'master.chromium.infra'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.infra'
