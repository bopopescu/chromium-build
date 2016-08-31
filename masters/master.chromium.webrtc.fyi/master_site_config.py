# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumWebRTCFYI(Master.Master1):
  project_name = 'Chromium WebRTC FYI'
  master_port = 8056
  slave_port = 8156
  master_port_alt = 8256
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'chromium-webrtc-cb-fyi-watchlist@google.com'
  master_domain = 'webrtc.org'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
  base_app_url = 'https://webrtc-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
  buildbot_url = 'http://build.chromium.org/p/chromium.webrtc.fyi/'
  service_account_file = 'service-account-webrtc.json'
  buildbucket_bucket = 'master.chromium.webrtc.fyi'
  pubsub_service_account_file = 'service-account-luci-milo.json'
  pubsub_topic = 'projects/luci-milo/topics/public-buildbot'
  name = 'chromium.webrtc.fyi'
