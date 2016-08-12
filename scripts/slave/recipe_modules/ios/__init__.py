# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'chromium_checkout',
  'depot_tools/gclient',
  'build/file',
  'filter',
  'isolate',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/step',
  'swarming',
  'swarming_client',
  'depot_tools/tryserver',
]
