# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class Libyuv(Master.Master3):
  project_name = 'Libyuv'
  master_port = 8062
  slave_port = 8162
  master_port_alt = 8262
  buildbot_url = 'http://build.chromium.org/p/client.libyuv/'
  server_url = 'https://chromium.googlesource.com/libyuv/libyuv'
  project_url = 'https://code.google.com/p/libyuv/'
  from_address = 'libyuv-cb-watchlist@google.com'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.libyuv'
