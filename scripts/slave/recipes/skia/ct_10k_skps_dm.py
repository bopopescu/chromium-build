# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common.skia import global_constants


DEPS = [
  'ct_swarming',
  'file',
  'gclient',
  'path',
  'properties',
  'step',
  'swarming',
  'swarming_client',
]


CT_PAGE_TYPE = '10k'
CT_DM_ISOLATE = 'ct_dm.isolate'

# Number of slaves to shard CT runs to.
DEFAULT_CT_NUM_SLAVES = 100

# The SKP repository to use.
DEFAULT_SKPS_CHROMIUM_BUILD = '310ea93-42bd6bf'


def RunSteps(api):
  # Checkout Skia and Chromium.
  gclient_cfg = api.gclient.make_config()
  src = gclient_cfg.solutions.add()
  src.name = 'src'
  src.url = 'https://chromium.googlesource.com/chromium/src.git'
  src.revision = 'origin/master'  # Always checkout Chromium at ToT.

  skia = gclient_cfg.solutions.add()
  skia.name = 'skia'
  skia.url = global_constants.SKIA_REPO
  skia.revision = (api.properties.get('parent_got_revision') or
                   api.properties.get('orig_revision') or
                   api.properties.get('revision') or
                   'origin/master')
  gclient_cfg.got_revision_mapping['skia'] = 'got_revision'

  api.gclient.checkout(gclient_config=gclient_cfg)

  # Checkout Swarming scripts.
  # Explicitly set revision to empty string to checkout swarming ToT. If this is
  # not done then it crashes due to missing
  # api.properties['parent_got_swarming_client_revision'] which seems to be
  # set only for Chromium bots.
  api.swarming_client.checkout(revision='')
  # Ensure swarming_client is compatible with what recipes expect.
  api.swarming.check_client_version()

  chromium_checkout = api.path['checkout']

  # Build DM in Debug mode.
  api.step('build dm', ['make', 'dm'], cwd=api.path['slave_build'].join('skia'))

  skps_chromium_build = api.properties.get(
      'skps_chromium_build', DEFAULT_SKPS_CHROMIUM_BUILD)
  ct_num_slaves = api.properties.get('ct_num_slaves', DEFAULT_CT_NUM_SLAVES)

  for slave_num in range(1, ct_num_slaves + 1):
    # Download SKPs.
    api.ct_swarming.download_skps(CT_PAGE_TYPE, slave_num, skps_chromium_build)

    # Create this slave's isolated.gen.json file to use for batcharchiving.
    isolate_dir = chromium_checkout.join('chrome')
    isolate_path = isolate_dir.join(CT_DM_ISOLATE)
    extra_variables = {
        'SLAVE_NUM': str(slave_num),
    }
    api.ct_swarming.create_isolated_gen_json(
        isolate_path, isolate_dir, 'linux', slave_num, extra_variables)

  # Batcharchive everything on the isolate server for efficiency.
  api.ct_swarming.batcharchive(ct_num_slaves)
  swarm_hashes = (
      api.step.active_result.presentation.properties['swarm_hashes']).values()

  # Trigger all swarming tasks.
  tasks = api.ct_swarming.trigger_swarming_tasks(
      swarm_hashes, task_name_prefix='ct-10k-dm',
      dimensions={'os': 'Ubuntu', 'gpu': '10de'})

  # Now collect all tasks.
  failed_tasks = []
  for task in tasks:
    try:
      api.ct_swarming.collect_swarming_task(task)
    except api.step.StepFailure as e:
      failed_tasks.append(e)
  if failed_tasks:
    raise api.step.StepFailure(
        'Failed steps: %s' % ', '.join([f.name for f in failed_tasks]))


def GenTests(api):
  ct_num_slaves = 5
  skia_revision = 'abc123'

  yield(
    api.test('CT_DM_10k_SKPs') +
    api.properties(
        buildername='CT-DM-10k-SKPs',
        ct_num_slaves=ct_num_slaves,
        revision=skia_revision,
    )
  )

  yield(
    api.test('CT_DM_10k_SKPs_slave3_failure') +
    api.step_data('ct-10k-dm-3 on Ubuntu', retcode=1) +
    api.properties(
        buildername='CT-DM-10k-SKPs',
        ct_num_slaves=ct_num_slaves,
        revision=skia_revision,
    )
  )

  yield(
    api.test('CT_DM_10k_SKPs_2slaves_failure') +
    api.step_data('ct-10k-dm-1 on Ubuntu', retcode=1) +
    api.step_data('ct-10k-dm-3 on Ubuntu', retcode=1) +
    api.properties(
        buildername='CT-DM-10k-SKPs',
        ct_num_slaves=ct_num_slaves,
        revision=skia_revision,
    )
  )
