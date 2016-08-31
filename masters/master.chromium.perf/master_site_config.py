# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumPerf(Master.Master1):
  project_name = 'Chromium Perf'
  master_port = 8013
  slave_port = 8113
  master_port_alt = 8213
  buildbot_url = 'http://build.chromium.org/p/chromium.perf/'
  service_account_file = 'service-account-chromium.json'
  buildbucket_bucket = 'master.chromium.perf'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.perf'
