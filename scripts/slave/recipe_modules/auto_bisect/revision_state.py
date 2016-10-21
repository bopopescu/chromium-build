# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""An interface for holding state and result of revisions in a bisect job.

When implementing support for tests other than perf, one should extend this
class so that the bisect module and recipe can use it.

See perf_revision_state for an example.
"""

import hashlib
import json
import math
import os
import tempfile
import re
import uuid

from . import depot_config

# These relate to how to increase the number of repetitions during re-test
MINIMUM_SAMPLE_SIZE = 5
INCREASE_FACTOR = 1.5

class RevisionState(object):
  """Abstracts the state of a single revision on a bisect job."""

  # Possible values for the status attribute of RevisionState:
  (
      NEW,  # A revision_state object that has just been initialized.
      BUILDING,  # Requested a build for this revision, waiting for it.
      TESTING,  # A test job for this revision was triggered, waiting for it.
      TESTED,  # The test job completed with non-failing results.
      FAILED,  # Either the build or the test jobs failed or timed out.
      ABORTED,  # The build or test job was aborted. (For use in multi-secting).
      SKIPPED,  # A revision that was not built or tested for a special reason,
                # such as those ranges that we know are broken, or when nudging
                # revisions.
      NEED_MORE_DATA,  # Current number of test values is too small to establish
                       # a statistically significant difference between this
                       # revision and the revisions known to be good and bad.
  ) = xrange(8)

  def __init__(self, bisector, commit_hash, depot_name=None,
               base_revision=None):
    """Creates a new instance to track the state of a revision.

    Args:
      bisector (Bisector): The object performing the bisection.
      commit_hash (str): The hash identifying the revision to represent.
      depot_name (str): The name of the depot as specified in DEPS. Must be a
        key in depot_config.DEPOT_DEPS_NAME .
      base_revision (RevisionState): The revision state to patch with the deps
        change.
    """
    super(RevisionState, self).__init__()
    self.bisector = bisector
    self._good = None
    self.deps = None
    self.test_results_url = None
    self.build_archived = False
    self.status = RevisionState.NEW
    self.next_revision = None
    self.previous_revision = None
    self.job_name = None
    self.patch_file = None
    self.deps_revision = None
    self.depot_name = depot_name or self.bisector.base_depot
    self.depot = depot_config.DEPOT_DEPS_NAME[self.depot_name]
    self.commit_hash = str(commit_hash)
    self._rev_str = None
    self.base_revision = base_revision
    self.top_revision = self
    # The difference between revsion overrides and revsion ladder is that the
    # former is indexed by paths, e.g. 'src/third_party/skia' and the latter is
    # indexed by depot name, e.g. 'skia'.
    self.revision_overrides = {}
    self.revision_ladder = {self.depot_name: self.commit_hash}
    self.build_id = None
    if self.base_revision:
      assert self.base_revision.deps_file_contents
      self.needs_patch = True
      self.revision_overrides[self.depot['src']] = self.commit_hash
      # To allow multiple nested levels, we go to the topmost revision.
      while self.top_revision.base_revision:
        self.top_revision = self.top_revision.base_revision
        # We want to carry over any overrides from the base revision(s) without
        # overwriting any overrides specified at the self level.
        self.revision_ladder[self.top_revision.depot_name] = (
            self.top_revision.commit_hash)
        self.revision_overrides = dict(
            self.top_revision.revision_overrides.items() +
            self.revision_overrides.items())
      self.deps_patch, self.deps_file_contents = self.bisector.make_deps_patch(
          self.base_revision, self.base_revision.deps_file_contents,
          self.depot, self.commit_hash)
      self.deps_sha = hashlib.sha1(self.deps_patch).hexdigest()
      self.deps_sha_patch = self.bisector.make_deps_sha_file(self.deps_sha)
      self.deps = dict(base_revision.deps)
      self.deps[self.depot_name] = self.commit_hash
    else:
      self.needs_patch = False
    self.build_url = self.bisector.get_platform_gs_prefix() + self._gs_suffix()
    self.values = []
    self.mean_value = None
    self.overall_return_code = None
    self.std_dev = None
    self._test_config = None

    if self.bisector.test_type == 'perf':
      self.repeat_count = MINIMUM_SAMPLE_SIZE
    else:
      self.repeat_count = self.bisector.bisect_config.get(
          'repeat_count', MINIMUM_SAMPLE_SIZE)

  @property
  def tested(self):
    return self.status in (RevisionState.TESTED,)

  @property
  def in_progress(self):
    return self.status in (RevisionState.BUILDING, RevisionState.TESTING,
                           RevisionState.NEED_MORE_DATA)

  @property
  def failed(self):
    return self.status == RevisionState.FAILED

  @property
  def aborted(self):
    return self.status == RevisionState.ABORTED

  @property
  def good(self):
    return self._good == True

  @property
  def bad(self):
    return self._good == False

  @good.setter
  def good(self, value):
    self._good = value

  @bad.setter
  def bad(self, value):
    self._good = not value

  def start_job(self):
    """Starts a build, or a test job if the build is available."""
    if self.status == RevisionState.NEW and not self._is_build_archived():
      self._request_build()
      self.status = RevisionState.BUILDING
      return

    if self._is_build_archived() and self.status in (
        RevisionState.NEW, RevisionState.BUILDING,
        RevisionState.NEED_MORE_DATA):
      self._do_test()
      self.status = RevisionState.TESTING

  def deps_change(self):
    """Uses `git show` to see if a given commit contains a DEPS change."""
    # Avoid checking DEPS changes for dependency repo revisions.
    # crbug.com/580681
    if self.needs_patch:  # pragma: no cover
      return False
    api = self.bisector.api
    working_dir = api.working_dir
    cwd = working_dir.join(
        depot_config.DEPOT_DEPS_NAME[self.depot_name]['src'])
    name = 'Checking DEPS for ' + self.commit_hash
    step_result = api.m.git(
        'show', '--name-only', '--pretty=format:',
        self.commit_hash, cwd=cwd, stdout=api.m.raw_io.output(), name=name)
    if self.bisector.dummy_builds and not self.commit_hash.startswith('dcdc'):
      return False
    if 'DEPS' in step_result.stdout.splitlines():  # pragma: no cover
      return True
    return False  # pragma: no cover

  def _gen_deps_local_scope(self):
    """Defines the Var and From functions in a dict for calling exec.

    This is needed for executing the DEPS file.
    """
    deps_data = {
        'Var': lambda _: deps_data['vars'][_],
        'From': lambda *args: None,
    }
    return deps_data

  def _read_content(self, url, file_name, branch):   # pragma: no cover
    """Uses gitiles recipe module to download and read file contents."""
    try:
      return self.bisector.api.m.gitiles.download_file(
          repository_url=url, file_path=file_name, branch=branch)
    except TypeError:
      print 'Could not read content for %s/%s/%s' % (url, file_name, branch)
      return None

  def read_deps(self, recipe_tester_name):
    """Sets the dependencies for this revision from the contents of DEPS."""
    api = self.bisector.api
    if self.deps:
      return
    if self.bisector.internal_bisect:  # pragma: no cover
      self.deps_file_contents = self._read_content(
          depot_config.DEPOT_DEPS_NAME[self.depot_name]['url'],
          depot_config.DEPOT_DEPS_NAME[self.depot_name]['deps_file'],
          self.commit_hash)
      # On April 5th, 2016 .DEPS.git was changed to DEPS on android-chrome repo,
      # we are doing this in order to support both deps files.
      if not self.deps_file_contents:
        self.deps_file_contents = self._read_content(
            depot_config.DEPOT_DEPS_NAME[self.depot_name]['url'],
            depot_config.DEPS_FILENAME,
            self.commit_hash)
    else:
      step_result = api.m.python(
          'fetch file %s:%s' % (self.commit_hash, depot_config.DEPS_FILENAME),
          api.resource('fetch_file.py'),
          [depot_config.DEPS_FILENAME, '--commit', self.commit_hash],
          stdout=api.m.raw_io.output())
      self.deps_file_contents = step_result.stdout
    try:
      deps_data = self._gen_deps_local_scope()
      exec(self.deps_file_contents or 'deps = {}', {}, deps_data)
      deps_data = deps_data['deps']
    except ImportError:  # pragma: no cover
      # TODO(robertocn): Implement manual parsing of DEPS when exec fails.
      raise NotImplementedError('Path not implemented to manually parse DEPS')

    revision_regex = re.compile('.git@(?P<revision>[a-fA-F0-9]+)')
    results = {}
    for depot_name, depot_data in depot_config.DEPOT_DEPS_NAME.iteritems():
      if (depot_data.get('platform') and
          depot_data.get('platform') not in recipe_tester_name.lower()):
        continue

      if (depot_data.get('recurse') and
          self.depot_name in depot_data.get('from')):
        depot_data_src = depot_data.get('src') or depot_data.get('src_old')
        src_dir = deps_data.get(depot_data_src)
        if src_dir:
          re_results = revision_regex.search(src_dir)
          if re_results:
            results[depot_name] = re_results.group('revision')
          else:  # pragma: no cover
            warning_text = ('Could not parse revision for %s while bisecting '
                            '%s' % (depot_name, self.depot))
            if warning_text not in self.bisector.warnings:
              self.bisector.warnings.append(warning_text)
        else:
          results[depot_name] = None
    self.deps = results
    return

  def update_status(self):
    """Checks on the pending jobs and updates status accordingly.

    This method will check for the build to complete and then trigger the test,
    or will wait for the test as appropriate.

    To wait for the test we try to get the buildbot job url from GS, and if
    available, we query the status of such job.
    """
    if self.status == RevisionState.BUILDING:
      if self._is_build_archived():
        self.start_job()
      elif self._is_build_failed():  # pragma: no cover
        self.status = RevisionState.FAILED
    elif (self.status in (RevisionState.TESTING, RevisionState.NEED_MORE_DATA)
          and self._results_available()):
      # If we have already decided whether the revision is good or bad we
      # shouldn't check again
      check_revision_goodness = not(self.good or self.bad)
      self._read_test_results(
          check_revision_goodness=check_revision_goodness)
      # We assume _read_test_results may have changed the status to a broken
      # state such as FAILED or ABORTED.
      if self.status in (RevisionState.TESTING, RevisionState.NEED_MORE_DATA):
        self.status = RevisionState.TESTED

  def _is_build_archived(self):
    """Checks if the revision is already built and archived."""
    if not self.build_archived:
      api = self.bisector.api
      self.build_archived = api.gsutil_file_exists(self.build_url)

    if self.bisector.dummy_builds:
      self.build_archived = self.in_progress

    return self.build_archived

  def _is_build_failed(self):
    api = self.bisector.api
    try:
      result = api.m.buildbucket.get_build(
          self.build_id,
          api.m.service_account.get_json_path(api.SERVICE_ACCOUNT),
          step_test_data=lambda: api.m.json.test_api.output_stream(
              {'build': {'result': 'SUCCESS', 'status': 'COMPLETED'}}
          ))
    except api.m.step.StepFailure:  # pragma: no cover
      # If the check fails, we cannot assume that the build is failed.
      return False
    return (result.stdout['build']['status'] == 'COMPLETED' and
            result.stdout['build'].get('result') != 'SUCCESS')

  def _results_available(self):
    """Checks if the results for the test job have been uploaded."""
    api = self.bisector.api
    result = api.gsutil_file_exists(self.test_results_url)
    if self.bisector.dummy_builds:
      return self.in_progress
    return result  # pragma: no cover

  def _gs_suffix(self):
    """Provides the expected right half of the build filename.

    This takes into account whether the build has a deps patch.
    """
    name_parts = [self.top_revision.commit_hash]
    if self.needs_patch:
      name_parts.append(self.deps_sha)
    return '%s.zip' % '_'.join(name_parts)

  def _read_test_results(self, check_revision_goodness=True):
    """Gets the test results from GS and checks if the rev is good or bad."""
    test_results = self._get_test_results()
    # Results will contain the keys 'results' and 'output' where output is the
    # stdout of the command, and 'results' is itself a dict with the key
    # 'values' unless the test failed, in which case 'results' will contain
    # the 'error' key explaining the type of error.
    results = test_results['results']
    if results.get('errors'):
      self.status = RevisionState.FAILED
      if 'MISSING_METRIC' in results.get('errors'):  # pragma: no cover
        self.bisector.surface_result('MISSING_METRIC')
      return
    self.values += results['values']
    api = self.bisector.api
    if test_results.get('retcodes') and test_results['retcodes'][-1] != 0 and (
        api.m.chromium.c.TARGET_PLATFORM == 'android'): #pragma: no cover
      api.m.chromium_android.device_status()
      current_connected_devices = api.m.chromium_android.devices
      current_device = api.m.bisect_tester.device_to_test
      if current_device not in current_connected_devices:
        # We need to manually raise step failure here because we are catching
        # them further down the line to enable return_code bisects and bisecting
        # on benchmarks that are a little flaky.
        raise api.m.step.StepFailure('Test device disconnected.')
    if self.bisector.is_return_code_mode():
      retcodes = test_results['retcodes']
      self.overall_return_code = 0 if all(v == 0 for v in retcodes) else 1
      # Keeping mean_value for compatibility with dashboard.
      # TODO(robertocn): refactor mean_value, specially when uploading results
      # to dashboard.
      self.mean_value = self.overall_return_code
    elif self.values:
      api = self.bisector.api
      self.mean_value = api.m.math_utils.mean(self.values)
      self.std_dev = api.m.math_utils.standard_deviation(self.values)
    # Values were not found, but the test did not otherwise fail.
    else:
      self.status = RevisionState.FAILED
      self.bisector.surface_result('MISSING_METRIC')
      return
    # If we have already decided on the goodness of this revision, we shouldn't
    # recheck it.
    if self.good or self.bad:
      check_revision_goodness = False
    # We cannot test the goodness of the initial rev range.
    if (self.bisector.good_rev != self and self.bisector.bad_rev != self and
        check_revision_goodness):
      if self._check_revision_good():
        self.good = True
      else:
        self.bad = True

  def _request_build(self):
    """Posts a request to buildbot to build this revision and archive it."""
    api = self.bisector.api
    bot_name = self.bisector.get_builder_bot_for_this_platform()
    operation_id = 'dummy' if self.bisector.dummy_tests else uuid.uuid4().hex
    build_details = {
        'bucket': 'master.' + api.m.properties['mastername'],
        'parameters': {
            'builder_name': bot_name,
            'properties': {
                'parent_got_revision': self.top_revision.commit_hash,
                'clobber': True,
                'build_archive_url': self.build_url,
            },
        },
        'client_operation_id': operation_id
    }
    if self.revision_overrides:
      build_details['parameters']['properties']['deps_revision_overrides'] = \
          self.revision_overrides

    try:
      result = api.m.buildbucket.put(
          [build_details],
          api.m.service_account.get_json_path(api.SERVICE_ACCOUNT),
          step_test_data=lambda: api.m.json.test_api.output_stream(
              {'results':[{'build':{'id':'1201331270'}}]}))
    except api.m.step.StepFailure:  # pragma: no cover
      self.bisector.surface_result('BUILD_FAILURE')
      raise
    self.build_id = result.stdout['results'][0]['build']['id']


  def _get_bisect_config_for_tester(self):
    """Copies the key-value pairs required by a tester bot to a new dict."""
    result = {}
    required_test_properties = {
        'truncate_percent',
        'metric',
        'command',
        'test_type'
    }
    for k, v in self.bisector.bisect_config.iteritems():
      if k in required_test_properties:
        result[k] = v
    result['repeat_count'] = self.repeat_count
    self._test_config = result
    return result

  def _do_test(self):
    """Triggers tests for a revision, either locally or via try job.

    If local testing is enabled (i.e. director/tester merged) then
    the test will be run on the same machine. Otherwise, this posts
    a request to buildbot to download and perf-test this build.
    """
    if self.bisector.bisect_config.get('dummy_job_names'):
      self.job_name = self.commit_hash + '-test'
    else:  # pragma: no cover
      self.job_name = uuid.uuid4().hex
    api = self.bisector.api
    perf_test_properties = {
        'builder_name': self.bisector.get_perf_tester_name(),
        'properties': {
            'revision': self.top_revision.commit_hash,
            'parent_got_revision': self.top_revision.commit_hash,
            'parent_build_archive_url': self.build_url,
            'bisect_config': self._get_bisect_config_for_tester(),
            'job_name': self.job_name,
            'revision_ladder': self.revision_ladder,
            'deps_revision_overrides': self.revision_overrides,
        },
    }
    self.test_results_url = (self.bisector.api.GS_RESULTS_URL +
                             self.job_name + '.results')
    if (api.m.bisect_tester.local_test_enabled() or
        self.bisector.internal_bisect):  # pragma: no cover
      skip_download = self.bisector.last_tested_revision == self
      self.bisector.last_tested_revision = self
      overrides = perf_test_properties['properties']
      api.run_local_test_run(overrides, skip_download=skip_download)
    else:
      step_name = 'Triggering test job for ' + self.commit_hash
      api.m.trigger(perf_test_properties, name=step_name)

  def retest(self):  # pragma: no cover
    # We need at least 5 samples for applying Mann-Whitney U test
    # with P < 0.01, two-tailed .
    target_sample_size =  max(5, math.ceil(len(self.values) * 1.5))
    self.status = RevisionState.NEED_MORE_DATA
    self.repeat_count = target_sample_size - len(self.values)
    self.start_job()
    self.bisector.wait_for(self)

  def _get_test_results(self):
    """Tries to get the results of a test job from cloud storage."""
    api = self.bisector.api
    try:
      stdout = api.m.raw_io.output()
      name = 'Get test results for build ' + self.commit_hash
      step_result = api.m.gsutil.cat(self.test_results_url, stdout=stdout,
                                     name=name)
      if not step_result.stdout:
        raise api.m.step.StepFailure('Test for build %s failed' %
                                     self.revision_string())
    except api.m.step.StepFailure as sf:  # pragma: no cover
      self.bisector.surface_result('TEST_FAILURE')
      return {'results': {'errors': str(sf)}}
    else:
      return json.loads(step_result.stdout)

  def _check_revision_good(self):
    """Determines if a revision is good or bad.

    Iteratively increment the sample size of the revision being tested, the last
    known good revision, and the first known bad revision until a relationship
    of significant difference can be established betweeb the results of the
    revision being tested and one of the other two.

    If the results do not converge towards finding a significant difference in
    either direction, this is expected to timeout eventually. This scenario
    should be rather rare, since it is expected that the fkbr and lkgr are
    significantly different as a precondition.

    Returns:
      True if the results of testing this revision are significantly different
      from those of testing the earliest known bad revision.
      False if they are instead significantly different form those of testing
      the latest knwon good revision.
    """
    lkgr = self.bisector.lkgr
    fkbr = self.bisector.fkbr

    if self.bisector.is_return_code_mode():
      return self.overall_return_code == lkgr.overall_return_code

    while True:
      diff_from_good = self.bisector.significantly_different(
          lkgr.values[:len(fkbr.values)], self.values)
      diff_from_bad = self.bisector.significantly_different(
          fkbr.values[:len(lkgr.values)], self.values)

      if diff_from_good and diff_from_bad:
        # Multiple regressions.
        # For now, proceed bisecting the biggest difference of the means.
        dist_from_good = abs(self.mean_value - lkgr.mean_value)
        dist_from_bad = abs(self.mean_value - fkbr.mean_value)
        if dist_from_good > dist_from_bad:
          # TODO(robertocn): Add way to handle the secondary regression
          #self.bisector.handle_secondary_regression(self, fkbr)
          return False
        else:
          #self.bisector.handle_secondary_regression(lkgr, self)
          return True

      if diff_from_good or diff_from_bad:  # pragma: no cover
        return diff_from_bad

      self._next_retest()  # pragma: no cover

  def revision_string(self):
    if self._rev_str:
      return self._rev_str
    result = ''
    if self.base_revision:  # pragma: no cover
      result += self.base_revision.revision_string() + ','
    commit = self.commit_hash[:10]
    if self.depot_name == 'chromium':
      try:
        commit = str(self.bisector.api.m.commit_position
                     .chromium_commit_position_from_hash(self.commit_hash))
      except self.bisector.api.m.step.StepFailure:
        pass # Failure to resolve a commit position is no reason to break.
    result += '%s@%s' % (self.depot_name, commit)
    self._rev_str = result
    return self._rev_str

  def _next_retest(self):  # pragma: no cover
    """Chooses one of current, lkgr, fkbr to retest.

    Look for the smallest sample and retest that. If the last tested revision
    is tied for the smallest sample, use that to take advantage of the fact
    that it is already downloaded and unzipped.
    """
    next_revision_to_test = min(self.bisector.lkgr, self, self.bisector.fkbr,
        key=lambda x: len(x.values))
    if (len(self.bisector.last_tested_revision.values) ==
        next_revision_to_test.values):
      self.bisector.last_tested_revision.retest()
    else:
      next_revision_to_test.retest()

  def __repr__(self):
    if self.overall_return_code is not None:
      return ('RevisionState(rev=%s, values=%r, overall_return_code=%r, '
              'std_dev=%r)') % (self.revision_string(), self.values,
                                self.overall_return_code, self.std_dev)
    return ('RevisionState(rev=%s, values=%r, mean_value=%r, std_dev=%r)' % (
        self.revision_string(), self.values, self.mean_value, self.std_dev))
