# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave.recipe_modules.v8 import builders


# With more than 23 letters, labels are to big for buildbot's popup boxes.
MAX_LABEL_SIZE = 23


TEST_CONFIGS = {
  'benchmarks': {
    'name': 'Benchmarks',
    'tests': 'benchmarks',
  },
  'mjsunit': {
    'name': 'Mjsunit',
    'tests': 'mjsunit',
    'add_flaky_step': True,
  },
  'mozilla': {
    'name': 'Mozilla',
    'tests': 'mozilla',
    'gclient_apply_config': ['mozilla_tests'],
  },
  'optimize_for_size': {
    'name': 'OptimizeForSize',
    'tests': 'cctest mjsunit webkit',
    'add_flaky_step': True,
    'test_args': ['--no-variants', '--shell_flags="--optimize-for-size"'],
  },
  'test262': {
    'name': 'Test262',
    'tests': 'test262',
  },
  'v8testing': {
    'name': 'Check',
    'tests': 'mjsunit fuzz-natives cctest message preparser',
    'add_flaky_step': True,
  },
  'webkit': {
    'name': 'Webkit',
    'tests': 'webkit',
    'add_flaky_step': True,
  },
}


# TODO(machenbach): Clean up api indirection. "Run" needs the v8 api while
# "gclient_apply_config" needs the general injection module.
class V8Test(object):
  def __init__(self, name):
    self.name = name

  def run(self, api, **kwargs):
    return api.runtest(TEST_CONFIGS[self.name], **kwargs)

  def gclient_apply_config(self, api):
    for c in TEST_CONFIGS[self.name].get('gclient_apply_config', []):
      api.gclient.apply_config(c)


class V8Presubmit(object):
  @staticmethod
  def run(api, **kwargs):
    return api.presubmit()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8CheckInitializers(object):
  @staticmethod
  def run(api, **kwargs):
    return api.check_initializers()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8GCMole(object):
  @staticmethod
  def run(api, **kwargs):
    return api.gc_mole()

  @staticmethod
  def gclient_apply_config(_):
    pass


class V8SimpleLeakCheck(object):
  @staticmethod
  def run(api, **kwargs):
    return api.simple_leak_check()

  @staticmethod
  def gclient_apply_config(_):
    pass


V8_NON_STANDARD_TESTS = {
  'gcmole': V8GCMole,
  'presubmit': V8Presubmit,
  'simpleleak': V8SimpleLeakCheck,
  'v8initializers': V8CheckInitializers,
}


# TODO(machenbach): This is copied from gclient's config.py and should be
# unified somehow.
def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


class V8Api(recipe_api.RecipeApi):
  BUILDERS = builders.BUILDERS

  # Map of GS archive names to urls.
  GS_ARCHIVES = {
    'linux_rel_archive': 'gs://chromium-v8/v8-linux-rel',
    'linux_dbg_archive': 'gs://chromium-v8/v8-linux-dbg',
    'linux_nosnap_rel_archive': 'gs://chromium-v8/v8-linux-nosnap-rel',
    'linux_nosnap_dbg_archive': 'gs://chromium-v8/v8-linux-nosnap-dbg',
    'linux64_rel_archive': 'gs://chromium-v8/v8-linux64-rel',
    'linux64_dbg_archive': 'gs://chromium-v8/v8-linux64-dbg',
    'win32_rel_archive': 'gs://chromium-v8/v8-win32-rel',
    'win32_dbg_archive': 'gs://chromium-v8/v8-win32-dbg',
  }

  def apply_bot_config(self):
    """Entry method for using the v8 api.

    Requires the presence of a bot_config dict for any master/builder pair.
    This bot_config will be used to refine other api methods.
    """

    self.m.step.auto_resolve_conflicts = True
    mastername = self.m.properties.get('mastername')
    buildername = self.m.properties.get('buildername')
    master_dict = self.BUILDERS.get(mastername, {})
    self.bot_config = master_dict.get('builders', {}).get(buildername)
    assert self.bot_config, (
        'Unrecognized builder name %r for master %r.' % (
            buildername, mastername))
    
    self.set_config('v8',
                    optional=True,
                    **self.bot_config.get('v8_config_kwargs', {}))
    for c in self.bot_config.get('gclient_apply_config', []):
      self.m.gclient.apply_config(c)
    for c in self.bot_config.get('chromium_apply_config', []):
      self.m.chromium.apply_config(c)
    for c in self.bot_config.get('v8_apply_config', []):
      self.apply_config(c)
    # Test-specific configurations.
    for t in self.bot_config.get('tests', []):
      self.create_test(t).gclient_apply_config(self.m)

  def init_tryserver(self):
    self.m.chromium.apply_config('trybot_flavor')
    self.m.chromium.apply_config('optimized_debug')
    self.apply_config('trybot_flavor')

  # TODO(machenbach): Make this a step_history helper.
  def has_failed_steps(self):
    return any(s.retcode != 0 for s in self.m.step_history.values())

  def tryserver_checkout(self):
    yield self.m.gclient.checkout(
        revert=True, can_fail_build=False, abort_on_failure=False)
    if self.has_failed_steps():
      # TODO(phajdan.jr): Remove the workaround, http://crbug.com/357767 .
      yield (
          self.m.path.rmcontents('slave build directory',
                                 self.m.path['slave_build']),
          self.m.gclient.checkout(),
        )

  def runhooks(self, **kwargs):
    return self.m.chromium.runhooks(**kwargs)

  @property
  def needs_clang(self):
    return 'clang' in self.bot_config.get('gclient_apply_config', [])

  def update_clang(self):
    # TODO(machenbach): Implement this for windows or unify with chromium's
    # update clang step as soon as it exists.
    yield self.m.step(
        'update clang',
        [self.m.path['checkout'].join('tools', 'clang',
                                      'scripts', 'update.sh')],
        env={'LLVM_URL': ChromiumSvnSubURL(self.m.gclient.c,
                                           'llvm-project')})

  def tryserver_lkgr_fallback(self):
    self.m.gclient.apply_config('v8_lkgr')
    yield (
      self.tryserver_checkout(),
      self.m.tryserver.maybe_apply_issue(),
      self.runhooks(),
    )

  @property
  def bot_type(self):
    return self.bot_config.get('bot_type', 'builder_tester')

  @property
  def should_build(self):
    return self.bot_type in ['builder', 'builder_tester']

  @property
  def should_test(self):
    return self.bot_type in ['tester', 'builder_tester']

  @property
  def should_upload_build(self):
    return self.bot_type == 'builder'

  @property
  def should_download_build(self):
    return self.bot_type == 'tester'

  def compile(self, **kwargs):
    yield self.m.chromium.compile(**kwargs)

  def tryserver_compile(self, fallback_fn, **kwargs):
    yield self.compile(name='compile (with patch)',
                       abort_on_failure=False,
                       can_fail_build=False)
    if self.m.step_history['compile (with patch)'].retcode != 0:
      yield fallback_fn()
      yield self.compile(name='compile (with patch, lkgr, clobber)',
                         force_clobber=True)

  def upload_build(self):
    yield(self.m.archive.zip_and_upload_build(
          'package build',
          self.m.chromium.c.build_config_fs,
          self.GS_ARCHIVES[self.bot_config['build_gs_archive']],
          src_dir='v8'))

  def download_build(self):
    yield(self.m.path.rmtree(
          'build directory',
          self.m.chromium.c.build_dir.join(self.m.chromium.c.build_config_fs)))

    yield(self.m.archive.download_and_unzip_build(
          'extract build',
          self.m.chromium.c.build_config_fs,
          self.GS_ARCHIVES[self.bot_config['build_gs_archive']],
          abort_on_failure=True,
          src_dir='v8'))


  # TODO(machenbach): Pass api already in constructor to avoid redundant api
  # parameter passing later.
  def create_test(self, test):
    """Wrapper that allows to shortcut common tests with their names.
    Returns a runnable test instance.
    """
    if test in V8_NON_STANDARD_TESTS:
      return V8_NON_STANDARD_TESTS[test]()
    else:
      return V8Test(test)

  def runtests(self):
    yield [self.create_test(t).run(self)
           for t in self.bot_config.get('tests', [])]

  def presubmit(self):
    return self.m.python(
      'Presubmit',
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      ['--testname', 'presubmit'],
      cwd=self.m.path['checkout'],
    )

  def check_initializers(self):
    return self.m.step(
      'Static-Initializers',
      ['bash',
       self.m.path['checkout'].join('tools', 'check-static-initializers.sh'),
       self.m.path.join(self.m.path.basename(self.m.chromium.c.build_dir),
                        self.m.chromium.c.build_config_fs,
                        'd8')],
      cwd=self.m.path['checkout'],
    )

  def gc_mole(self):
    # TODO(machenbach): Make gcmole work with absolute paths. Currently, a
    # particular clang version is installed on one slave in '/b'.
    env = {
      'CLANG_BIN': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole', 'bin')
      ),
      'CLANG_PLUGINS': (
        self.m.path.join('..', '..', '..', '..', '..', 'gcmole')
      ),
    }
    return self.m.step(
      'GCMole',
      ['lua', self.m.path.join('tools', 'gcmole', 'gcmole.lua')],
      cwd=self.m.path['checkout'],
      env=env,
    )

  def simple_leak_check(self):
    # TODO(machenbach): Add task kill step for windows.
    relative_d8_path = self.m.path.join(
        self.m.path.basename(self.m.chromium.c.build_dir),
        self.m.chromium.c.build_config_fs,
        'd8')
    return self.m.step(
      'Simple Leak Check',
      ['valgrind', '--leak-check=full', '--show-reachable=yes',
       '--num-callers=20', relative_d8_path, '-e', '"print(1+2)"'],
      cwd=self.m.path['checkout'],
    )

  def _update_test_presentation(self, results, presentation):
    if not results:
      return

    unique_results = {}
    for result in results:
      # Use test base name as UI label (without suite and directory names).
      label = result['name'].split('/')[-1]
      # Truncate the label if it is still too long.
      if len(label) > MAX_LABEL_SIZE:
        label = label[:MAX_LABEL_SIZE - 2] + '..'
      # Group tests with the same label (usually the same test that ran under
      # different configurations).
      unique_results.setdefault(label, []).append(result)

    for label in sorted(unique_results):
      lines = []
      for result in unique_results[label]:
        lines.append('Test: %s' % result['name'])
        lines.append('Flags: %s' % " ".join(result['flags']))
        lines.append('Exit code: %s' % result['exit_code'])
        lines.append('Result: %s' % result['result'])
        lines.append('Command: %s' % result['command'])
        lines.append('')
        if result['stdout']:
          lines.append('Stdout:')
          lines.extend(result['stdout'].splitlines())
          lines.append('')
        if result['stderr']:
          lines.append('Stderr:')
          lines.extend(result['stderr'].splitlines())
          lines.append('')
      presentation.logs[label] = lines

  def _runtest(self, name, test, flaky_tests=None, **kwargs):
    env = {}
    full_args = [
      '--target', self.m.chromium.c.build_config_fs,
      '--arch', self.m.chromium.c.gyp_env.GYP_DEFINES['v8_target_arch'],
      '--testname', test['tests'],
    ]

    # Add test-specific test arguments.
    full_args += test.get('test_args', [])

    # Add builder-specific test arguments.
    full_args += self.c.testing.test_args

    if self.c.testing.SHARD_COUNT > 1:
      full_args += [
        '--shard_count=%d' % self.c.testing.SHARD_COUNT,
        '--shard_run=%d' % self.c.testing.SHARD_RUN,
      ]

    if flaky_tests:
      full_args += ['--flaky-tests', flaky_tests]

    # Arguments and environment for asan builds:
    if self.m.chromium.c.gyp_env.GYP_DEFINES.get('asan') == 1:
      full_args.append('--asan')
      env['ASAN_SYMBOLIZER_PATH'] = self.m.path['checkout'].join(
          'third_party', 'llvm-build', 'Release+Asserts', 'bin',
          'llvm-symbolizer')

    if self.c.testing.show_test_results:
      full_args += ['--json-test-results',
                    self.m.json.output(add_json_log=False)]
      def followup_fn(step_result):
        r = step_result.json.output
        # The output is expected to be a list of architecture dicts that
        # each contain a results list. On buildbot, there is only one
        # architecture.
        if (r and isinstance(r, list) and isinstance(r[0], dict)):
          self._update_test_presentation(r[0]['results'],
                                         step_result.presentation)

    step_test_data = lambda: self.test_api.output_json(
        self._test_data.get('test_failures', False),
        self._test_data.get('wrong_results', False))

    yield self.m.python(
      name,
      self.m.path['build'].join('scripts', 'slave', 'v8', 'v8testing.py'),
      full_args,
      cwd=self.m.path['checkout'],
      env=env,
      followup_fn=followup_fn,
      step_test_data=step_test_data,
      always_run=True,
      **kwargs
    )

    if self.c.testing.show_test_results:
      # Check integrity of the last output. The json list is expected to
      # contain only one element for one (architecture, build config type)
      # pair on the buildbot.
      result = self.m.step_history.last_step().json.output
      if result and len(result) > 1:
        yield self.m.python.inline(
            name,
            r"""
            import sys
            print 'Unexpected results set present.'
            sys.exit(1)
            """,
            always_run=True)

  def runtest(self, test, **kwargs):
    # Get the flaky-step configuration default per test.
    add_flaky_step = test.get('add_flaky_step', False)

    # Overwrite the flaky-step configuration on a per builder basis as some
    # types of builders (e.g. branch, try) don't have any flaky steps.
    if self.c.testing.add_flaky_step is not None:
      add_flaky_step = self.c.testing.add_flaky_step
    if add_flaky_step:
      return [
        self._runtest(test['name'], test, flaky_tests='skip', **kwargs),
        self._runtest(test['name'] + ' - flaky', test, flaky_tests='run',
                      can_fail_build=False, **kwargs),
      ]
    else:
      return self._runtest(test['name'], test, **kwargs)
