def convert_trie_to_flat_paths(trie, prefix, sep):
  # Cloned from webkitpy.layout_tests.layout_package.json_results_generator
  # so that this code can stand alone.
  result = {}
  for name, data in trie.iteritems():
    if prefix:
      name = prefix + sep + name

    if len(data) and not "actual" in data and not "expected" in data:
      result.update(convert_trie_to_flat_paths(data, name, sep))
    else:
      result[name] = data

  return result


class TestResults(object):
  def __init__(self, jsonish=None):
    self.raw = jsonish or {'version': 3}
    self.valid = (jsonish is not None)
    self.interrupted = False
    self.version = self.raw.get('version', 'simplified')

    tests = self.raw.get('tests', {})
    sep = self.raw.get('path_delimiter', '/')
    self.tests = convert_trie_to_flat_paths(tests, prefix=None, sep=sep)

    self.passes = {}
    self.unexpected_passes = {}
    self.failures = {}
    self.unexpected_failures = {}
    self.flakes = {}
    self.unexpected_flakes = {}
    self.skipped = {}
    self.unknown = {}

    # TODO(dpranke): https://crbug.com/357866 - we should simplify the handling
    # of both the return code and parsing the actual results.

    if self.version == 'simplified':
      self._simplified_json_results()
    else:
      self._json_results()

  @property
  def total_test_runs(self):
    # Number of tests actually run, hence exclude skipped tests.
    return sum([
        len(self.passes), len(self.unexpected_passes),
        len(self.failures), len(self.unexpected_failures),
        len(self.flakes), len(self.unexpected_flakes),
    ])

  # TODO(tansell): https://crbug.com/704066 - Kill simplified JSON format.
  def _simplified_json_results(self):
    self.valid = self.raw.get('valid', False)
    self.passes = {x: {} for x in self.raw.get('successes', [])}
    self.unexpected_failures = {x: {} for x in self.raw.get('failures', [])}
    self.tests = {}
    self.tests.update(self.passes)
    self.tests.update(self.unexpected_failures)

  def _json_results(self):
    self.valid = self.raw.get('version', 0) == 3
    self.interrupted = self.raw.get('interrupted', False)

    # Test result types are described on the follow page.
    # https://www.chromium.org/developers/the-json-test-results-format#TOC-Test-result-types

    passing_statuses = (
        # PASS - The test ran as expected.
        'PASS',
        # SLOW - Layout test specific. The test is expected to take longer than
        # normal to run.
        'SLOW',
        # REBASELINE, NEEDSREBASELINE, NEEDSMANUALREBASELINE - Layout test
        # specific. The expected test result is out of date and will be ignored
        # (any result other than a crash or timeout will be considered as
        # passing).
        'REBASELINE', 'NEEDSREBASELINE', 'NEEDSMANUALREBASELINE',
        # WONTFIX - **Undocumented** - Test is failing and won't be fixed?
        'WONTFIX',
    )

    failing_statuses = (
        # FAIL - The test did not run as expected.
        'FAIL',
        # CRASH - The test runner crashed during the test.
        'CRASH',
        # TIMEOUT - The test hung (did not complete) and was aborted.
        'TIMEOUT',
        # MISSING - Layout test specific. The test completed but we could not
        # find an expected baseline to compare against.
        'MISSING',
        # LEAK - Layout test specific. Memory leaks were detected during the
        # test execution.
        'LEAK',
        # TEXT, AUDIO, IMAGE, IMAGE+TEXT - Layout test specific, deprecated.
        # The test is expected to produce a failure for only some parts.
        # Normally you will see "FAIL" instead.
        'TEXT', 'AUDIO', 'IMAGE', 'IMAGE+TEXT',
    )

    skipping_statuses = (
        # SKIP - The test was not run.
        'SKIP',
    )

    for (test, result) in self.tests.iteritems():
      key = 'unexpected_' if result.get('is_unexpected') else ''
      data = result['actual']
      actual_results = data.split()
      last_result = actual_results[-1]
      expected_results = result['expected'].split()

      if (len(actual_results) > 1 and
          (last_result in expected_results or last_result in passing_statuses)):
        key += 'flakes'
      elif last_result in passing_statuses:
        key += 'passes'
        # TODO(dpranke): https://crbug.com/357867 ...  Why are we assigning
        # result instead of actual_result here. Do we even need these things to
        # be hashes, or just lists?
        data = result
      elif last_result in failing_statuses:
        key += 'failures'
      elif last_result in skipping_statuses:
        key = 'skipped'
      else:
        # Unknown test state was found.
        key = 'unknown'
      getattr(self, key)[test] = data

  def add_result(self, name, expected, actual=None):
    """Adds a test result to a 'json test results' compatible object.
    Args:
      name - A full test name delimited by '/'. ex. 'some/category/test.html'
      expected - The string value for the 'expected' result of this test.
      actual (optional) - If not None, this is the actual result of the test.
                          Otherwise this will be set equal to expected.

    The test will also get an 'is_unexpected' key if actual != expected.
    """
    actual = actual or expected
    entry = self.tests
    for token in name.split('/'):
      entry = entry.setdefault(token, {})
    entry['expected'] = expected
    entry['actual'] = actual
    if expected != actual:  # pragma: no cover
      entry['is_unexpected'] = True
      # TODO(dpranke): crbug.com/357866 - this test logic is overly-simplified
      # and is counting unexpected passes and flakes as regressions when it
      # shouldn't be.
      self.raw['num_regressions'] += 1

  def as_jsonish(self):
    ret = self.raw.copy()
    ret.setdefault('tests', {}).update(self.tests)
    return ret


class GTestResults(object):

  MAX_LOG_LINES = 5000

  def __init__(self, jsonish=None):
    self.logs = {}
    self.raw = jsonish or {}
    self.pass_fail_counts = {}

    self.passes = set()
    self.failures = set()

    if not jsonish:
      self.valid = False
      return

    self.valid = True

    for cur_iteration_data in self.raw.get('per_iteration_data', []):
      for test_fullname, results in cur_iteration_data.iteritems():
        # Results is a list with one entry per test try. Last one is the final
        # result, the only we care about for the .passes and .failures
        # attributes.
        last_result = results[-1]
        # martiniss: this will go away once aggregate steps lands (I think)
        if last_result['status'] == 'SUCCESS':
          self.passes.add(test_fullname)
        elif last_result['status'] != 'SKIPPED':
          self.failures.add(test_fullname)

        # The pass_fail_counts attribute takes into consideration all runs.

        # TODO (robertocn): Consider a failure in any iteration a failure of
        # the whole test, but allow for an override that makes a test pass if
        # it passes at least once.
        self.pass_fail_counts.setdefault(
            test_fullname, {'pass_count': 0, 'fail_count': 0})
        self.logs.setdefault(test_fullname, [])
        for cur_result in results:
          if cur_result['status'] == 'SUCCESS':
            self.pass_fail_counts[test_fullname]['pass_count'] += 1
          elif cur_result['status'] != 'SKIPPED':
            self.pass_fail_counts[test_fullname]['fail_count'] += 1
          ascii_log = cur_result['output_snippet'].encode('ascii',
                                                          errors='replace')
          self.logs[test_fullname].extend(
              self._compress_list(ascii_log.splitlines()))

    # With multiple iterations a test could have passed in one but failed
    # in another. Remove tests that ever failed from the passing set.
    self.passes -= self.failures

  def _compress_list(self, lines):
    if len(lines) > self.MAX_LOG_LINES: # pragma: no cover
      remove_from_start = self.MAX_LOG_LINES / 2
      return (lines[:remove_from_start] +
              ['<truncated>'] +
              lines[len(lines) - (self.MAX_LOG_LINES - remove_from_start):])
    return lines

  def as_jsonish(self):
    ret = self.raw.copy()
    return ret
