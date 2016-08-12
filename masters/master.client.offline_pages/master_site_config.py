# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file was generated from
# scripts/tools/buildbot_tool_templates/master_site_config.py
# by "../../build/scripts/tools/buildbot-tool gen .".
# DO NOT EDIT BY HAND!


"""ActiveMaster definition."""

from config_bootstrap import Master

class ClientOffline_pages(Master.Master3a):
  project_name = 'ClientOffline_pages'
  master_port = 20313
  slave_port = 30313
  master_port_alt = 25313
  buildbot_url = 'https://build.chromium.org/p/client.offline_pages/'
  buildbucket_bucket = None
  service_account_file = None
  # To enable outbound pubsub event streaming.
  pubsub_service_account_file = None
  pubsub_topic = None
  name = 'client.offline_pages'
