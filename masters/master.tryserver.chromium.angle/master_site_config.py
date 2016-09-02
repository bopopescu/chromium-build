# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class TryServerANGLE(Master.Master4a):
  project_name = 'ANGLE Try Server'
  master_port = 21403
  slave_port = 31403
  master_port_alt = 26403
  buildbot_url = 'http://build.chromium.org/p/tryserver.chromium.angle/'
  gerrit_host = 'https://chromium-review.googlesource.com'
  service_account_file = 'service-account-chromium-tryserver.json'
  buildbucket_bucket = 'master.tryserver.chromium.angle'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'tryserver.chromium.angle'
