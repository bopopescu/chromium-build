# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'chromium',
    'chromium_gsutil',
    'file',
    'depot_tools/gsutil',
    'zip',
    'recipe_engine/json',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/python',
    'recipe_engine/raw_io',
    'recipe_engine/shutil',
    'recipe_engine/step',
    'recipe_engine/tempfile',
]


# TODO(phajdan.jr): provide coverage (http://crbug.com/693058).
DISABLE_STRICT_COVERAGE = True
