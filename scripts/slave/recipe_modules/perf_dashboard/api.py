# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import urllib

from recipe_engine import recipe_api


_BASE_URL = 'https://chromeperf.appspot.com'
_PINPOINT_BASE_URL = 'https://pinpoint-dot-chromeperf.appspot.com'


class PerfDashboardApi(recipe_api.RecipeApi):
  """Provides steps to take a list of perf points and post them to the
  Chromium Perf Dashboard.  Can also use the test url for testing purposes."""

  def get_skeleton_point(self, test, revision, value, bot=None):
    # TODO: masterid is really mastername
    assert (test != '')
    assert (revision != '')
    assert (value != '')
    return {
        'master': self.m.properties['mastername'],
        'bot': bot or self.m.properties['buildername'],
        'test': test,
        'revision': revision,
        'value': value,
        'masterid': self.m.properties['mastername'],
        'buildername': self.m.properties['buildername'],
        'buildnumber': self.m.properties['buildnumber']
    }

  def add_dashboard_link(self, presentation, test, revision, bot=None):
    """Adds a results-dashboard link to the step presentation.

    Must be called from a follow-up function of the step, to which the link
    should be added. For a working link, the parameters test, revision and bot
    must match to the parameters used to upload points to the dashboard.

    Args:
      presentation: A step presentation object. Can be obtained by
                    step_result.presentation from a followup_fn of a step.
      test: Slash-separated test path.
      revision: The build revision, e.g. got_revision from the update step.
      bot: The bot name used for the data on the perf dashboard.
    """
    assert presentation
    assert test
    assert revision
    params = urllib.urlencode({
        'masters': self.m.properties['mastername'],
        'bots': bot or self.m.properties['buildername'],
        'tests': test,
        'rev': revision,
    })
    presentation.links['Results Dashboard'] = (
        '%s/report?%s' % (_BASE_URL, params))

  def set_default_config(self):
    # TODO: Remove.
    pass

  def add_point(self, data, halt_on_failure=False):
    return self.post('perf dashboard post',
                     '%s/add_point' % _BASE_URL,
                     {'data': data}, halt_on_failure)

  def post_bisect_results(self, data, halt_on_failure=False):
    """Posts bisect results to Perf Dashboard."""
    return self.post('Post bisect results',
                     '%s/post_bisect_results' % _BASE_URL,
                     {'data': data}, halt_on_failure)

  def upload_isolated(self, builder_name, git_hash, isolate_map,
                      halt_on_failure=False):
    data = {
        'builder_name': builder_name,
        'git_hash': git_hash,
        'isolate_map': isolate_map,
    }
    return self.post('pinpoint isolate upload',
                     '%s/isolated' % _PINPOINT_BASE_URL, data, halt_on_failure)

  def post(self, name, url, data, halt_on_failure):
    """Takes a data object which can be jsonified and posts it to url."""
    step_result = self.m.python(
        name=name, script=self.resource('post_json.py'), args=[url],
        stdin=self.m.json.input(data), stdout=self.m.json.output())

    response = step_result.stdout
    if not response or response['status_code'] != 200:  # pragma: no cover
      error = response['status_code'] if response else 'None'
      reason = ('Failed to post to Perf Dashboard. '
                'Error response: %s' % error)
      if halt_on_failure:
        self.halt(step_result, reason)
      else:
        self.warning(step_result, reason)

    return step_result

  def halt(self, step_result, reason):  # pragma: no cover
    step_result.presentation.step_text = reason
    step_result.presentation.status = self.m.step.FAILURE
    raise self.m.step.StepFailure(reason)

  def warning(self, step_result, reason):  # pragma: no cover
    step_result.presentation.step_text = reason
    step_result.presentation.status = self.m.step.WARNING
