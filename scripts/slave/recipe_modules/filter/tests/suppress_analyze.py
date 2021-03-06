# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'filter',
  'recipe_engine/properties',
]


def RunSteps(api):
  api.chromium.set_config('chromium')

  api.filter.analyze(
      ['file1', 'file2'],
      ['test1', 'test2'],
      ['compile1', 'compile2'],
      'config.json')


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
          mastername='test_mastername',
          buildername='test_buildername') +
      api.filter.suppress_analyze()
  )
