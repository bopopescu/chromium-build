# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class WebRTCFYI(Master.Master3):
  project_name = 'WebRTC FYI'
  master_port = 8072
  slave_port = 8172
  master_port_alt = 8272
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-fyi-watchlist@google.com'
  buildbot_url = 'http://build.chromium.org/p/client.webrtc.fyi/'
  service_account_file = 'service-account-webrtc.json'
  buildbucket_bucket = 'master.client.webrtc.fyi'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'client.webrtc.fyi'
