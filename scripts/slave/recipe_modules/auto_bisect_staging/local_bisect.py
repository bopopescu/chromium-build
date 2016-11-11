# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import collections
import json

from . import bisect_exceptions

def perform_bisect(api, **flags):
  # Try catch all the exceptions thrown in bisection so that recipe can
  # post the failed job result to dashboard
  try:
    bisect_attempts = []
    if api.m.chromium.c.TARGET_PLATFORM != 'android':
      _perform_single_bisect(api, bisect_attempts, **flags)
    else:
      # pick an available device if targe platform is android
      connected_devices = _get_connected_devices(api)
      if not connected_devices:
        raise api.m.step.StepFailure(
            'No Android test devices are available')
      for device in connected_devices:
        api.m.bisect_tester_staging.device_to_test = device
        try:
          _perform_single_bisect(api, bisect_attempts, **flags)
          break
        except api.m.step.StepFailure:
          # Redo the bisect job if target platform is android and bisect
          # failed because the test device disconnected
          current_connected_devices = _get_connected_devices(api)
          if (api.m.bisect_tester_staging.device_to_test not in
              current_connected_devices):
            continue
          else:
            raise
  except bisect_exceptions.InconclusiveBisectException as e:
    if bisect_attempts:
      bisect_attempts[-1].print_result_debug_info()
      bisect_attempts[-1].post_result()
    raise api.m.step.StepFailure('Bisect cannot identify a culprit: ' +
                                 e.message)
  except Exception: # pylint: disable=bare-except
    if bisect_attempts:
      bisect_attempts[-1].post_result()
    raise

def _perform_single_bisect(api, bisect_attempts, **flags):
      bisect_config = dict(api.m.properties.get('bisect_config'))
      if bisect_attempts:
        bisect_config['good_revision'] = bisect_attempts[-1].lkgr.commit_hash
        bisect_config['bad_revision'] = bisect_attempts[-1].fkbr.commit_hash
      bisector = api.create_bisector(bisect_config, **flags)
      bisect_attempts.append(bisector)
      with api.m.step.nest('Gathering reference values'):
        _gather_reference_range(bisector)
      if (not bisector.failed and bisector.check_improvement_direction() and
          bisector.check_initial_confidence()):
        bisector.compute_relative_change()
        if bisector.check_reach_adjacent_revision(
            bisector.good_rev): # pragma: no cover
          # Only show this step if bisect has reached adjacent revisions.
          with api.m.step.nest(str('Check bisect finished on revision ' +
                                   bisector.good_rev.revision_string())):
            if bisector.check_bisect_finished(bisector.good_rev):
              bisector.bisect_over = True
        if not bisector.bisect_over:
          _bisect_main_loop(bisector)
      bisector.print_result_debug_info()
      bisector.post_result(halt_on_failure=True)

def _get_connected_devices(api):
  api.m.chromium_android.device_status()
  return api.m.chromium_android.devices

def _gather_reference_range(bisector):  # pragma: no cover
  bisector.good_rev.start_job()
  bisector.bad_rev.start_job()
  if bisector.good_rev.failed:
    bisector.surface_result('REF_RANGE_FAIL')
    bisector.failed = True
    raise bisect_exceptions.InconclusiveBisectException(
        'Testing the "good" revision failed: ' +
        bisector.good_rev.failure_reason)
  elif bisector.bad_rev.failed:
    bisector.surface_result('REF_RANGE_FAIL')
    bisector.failed = True
    raise bisect_exceptions.InconclusiveBisectException(
        'Testing the "bad" revision failed: ' +
        bisector.bad_rev.failure_reason)

def _bisect_main_loop(bisector):  # pragma: no cover
  """This is the main bisect loop.

  It gets an evenly distributed number of revisions in the candidate range,
  then it starts them in parallel and waits for them to finish.
  """
  while not bisector.bisect_over:
    revision_to_check = bisector.get_revision_to_eval()
    if not revision_to_check:
      bisector.bisect_over = True
      break

    with bisector.api.m.step.nest(str('Working on revision ' +
                                      revision_to_check.revision_string())):
      bisector.post_result(halt_on_failure=False)
      revision_to_check.start_job()

    if bisector.check_reach_adjacent_revision(revision_to_check):
      # Only show this step if bisect has reached adjacent revisions.
      with bisector.api.m.step.nest(
          str('Check bisect finished on revision ' +
              revision_to_check.revision_string())):
        if bisector.check_bisect_finished(revision_to_check):
            bisector.bisect_over = True
