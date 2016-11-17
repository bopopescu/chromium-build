# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import copy

from recipe_engine import recipe_api


class iOSApi(recipe_api.RecipeApi):

  # Mapping of common names of supported iOS devices to product types
  # exposed by the Swarming server.
  PRODUCT_TYPES = {
    'iPad Air': 'iPad4,1',
    'iPhone 5s': 'iPhone6,1',
    'iPhone 6s': 'iPhone8,1',
  }

  def __init__(self, *args, **kwargs):
    super(iOSApi, self).__init__(*args, **kwargs)
    self.__config = None

  def host_info(self):
    """Emits information about the current host and available tools."""
    step_result = self.m.step('host and tools info', [
      self.package_repo_resource(
        'scripts', 'slave', 'ios', 'host_info.py'),
      '--json-file', self.m.json.output(),
    ], infra_step=True, step_test_data=self.test_api.host_info)

    if step_result.json.output:
      step_result.presentation.step_text = '<br />OS X %s, Xcode %s (%s)' % (
        step_result.json.output['Mac OS X Version'],
        step_result.json.output['Xcode Version'],
        step_result.json.output['Xcode Build Version'],
      )
    return step_result

  def checkout(self, **kwargs):
    """Checks out Chromium."""
    self.m.gclient.set_config('ios')

    checkout_dir = self.m.chromium_checkout.get_checkout_dir({})
    if checkout_dir:
      kwargs.setdefault('cwd', checkout_dir)

    return self.m.bot_update.ensure_checkout(**kwargs)

  @property
  def bucket(self):
    assert self.__config is not None
    return self.__config.get('bucket')

  @property
  def configuration(self):
    assert self.__config is not None
    return self.__config['configuration']

  @property
  def platform(self):
    assert self.__config is not None
    if self.__config['sdk'].startswith('iphoneos'):
      return 'device'
    elif self.__config['sdk'].startswith('iphonesimulator'):
      return 'simulator'

  def read_build_config(
    self,
    master_name=None,
    build_config_base_dir=None,
    buildername=None,
  ):
    """Reads the iOS build config for this bot.

    Args:
      master_name: Name of a master to read the build config from, or None
        to read from buildbot properties at run-time.
      build_config_base_dir: Directory to search for build config master and
        test include directories.
    """
    buildername = buildername or self.m.properties['buildername']
    master_name = master_name or self.m.properties['mastername']
    build_config_base_dir = build_config_base_dir or (
        self.m.path['checkout'].join('ios', 'build', 'bots'))
    build_config_dir = build_config_base_dir.join(master_name)
    include_dir = build_config_base_dir.join('tests')

    self.__config = self.m.json.read(
      'read build config',
      build_config_dir.join('%s.json' % buildername),
      step_test_data=lambda: self.m.json.test_api.output(
        self._test_data['build_config']
      ),
    ).json.output

    # If this bot is triggered by another bot, then the build configuration
    # has to be read from the parent's build config. A triggered bot only
    # specifies the tests.
    parent = str(self.__config.get('triggered by', ''))

    if parent:
      parent_config = self.m.json.read(
        'read parent build config (%s)' % parent,
        build_config_dir.join('%s.json' % parent),
        step_test_data=lambda: self.m.json.test_api.output(
          self._test_data['parent_build_config'],
        ),
      ).json.output

      for key in (
        'additional_compile_targets',
        'bucket',
        'configuration',
        'gn_args',
        'gn_args_file',
        'mb_type',
        'sdk',
        'xcode version',
      ):
        if key in parent_config:
          self.__config[key] = parent_config[key]

    # TODO(crbug.com/552146): Once 'all' works, the default should be ['all'].
    self.__config.setdefault('additional_compile_targets', ['All'])

    # In order to simplify the code that uses the values of self.__config, here
    # we default to empty values of their respective types, so in other places
    # we can iterate over them without having to check if they are in the dict
    # at all.
    self.__config.setdefault('triggered bots', {})
    self.__config.setdefault('tests', [])
    self.__config.setdefault('env', {})
    self.__config.setdefault('mb_type', None)
    self.__config.setdefault('gn_args', [])
    self.__config.setdefault('use_analyze', True)

    self.__config['mastername'] = master_name

    # Elements of the "tests" list are dicts. There are two types of elements,
    # determined by the presence of one of these mutually exclusive keys:
    #   "app": This says to run a particular app.
    #   "include": This says to include a common set of tests from include_dir.
    # So now we go through the "tests" list replacing any "include" keys.
    # The value of an "include" key is the name of a set of tests to include,
    # which can be found as a .json file in include_dir. Read the contents
    # lazily as needed into includes.
    def read_include(includes):
      """Reads the contents of the given include.

      Args:
        include: Name of the include.
      """
      return self.m.json.read(
        'include %s' % include,
        include_dir.join(include),
        step_test_data=lambda: self.m.json.test_api.output({
          'tests': [
            {
              'app': 'fake included test 1',
            },
            {
              'app': 'fake included test 2',
            },
          ],
        }),
      ).json.output

    includes = {}
    expanded_tests_list = []

    # expanded_tests_list will be the list of test dicts, with
    # any "include" replaced with the tests from that include.
    for element in self.__config['tests']:
      if element.get('include'):
        # This is an include dict.
        include = str(element.pop('include'))

        # Lazily read the include if we haven't already.
        if include not in includes:
          includes[include] = read_include(include)

        # Now take each test dict from the include, update it with the
        # extra keys (e.g. device, OS), and append to the list of tests.
        for included_test in includes[include]['tests']:
          expanded_tests_list.append(copy.deepcopy(included_test))
          expanded_tests_list[-1].update(element)
      else:
        # This is a test dict.
        expanded_tests_list.append(element)

    self.__config['tests'] = expanded_tests_list

    # Generate a unique ID we can use to refer to each test, since the config
    # may specify to run the exact same test multiple times.
    i = 0
    for test in self.__config['tests']:
      test['id'] = str(i)
      i += 1

    self.m.step('finalize build config', [
      'echo',
      '-e',
      self.m.json.dumps(self.__config, indent=2),
    ])

    cfg = self.m.chromium.make_config()

    self.m.chromium.c = cfg
    self.m.chromium.apply_config('force_mac_toolchain_off')

    use_goma = 'use_goma=true' in self.__config['gn_args']
    if use_goma:
      # Make sure these chromium configs are applied consistently for the
      # rest of the recipe; they are needed in order for m.chromium.compile()
      # to work correctly.
      self.m.chromium.apply_config('ninja')
      self.m.chromium.apply_config('default_compiler')
      self.m.chromium.apply_config('goma')

      # apply_config('goma') sets the old (wrong) directory for goma in
      # chromium.c.compile_py.goma_dir, but calling ensure_goma() after
      # that fixes things, and makes sure that goma is actually
      # available as well.
      self.m.chromium.ensure_goma(canary=self.__config.get('use_goma_canary'))

    return copy.deepcopy(self.__config)

  def build(self, mb_config_path=None, suffix=None):
    """Builds from this bot's build config."""
    assert self.__config is not None

    suffix = ' (%s)' % suffix if suffix else ''

    self.m.step(
      'find xcode', [
      self.package_repo_resource(
        'scripts', 'slave', 'ios', 'find_xcode.py'),
      '--json-file', self.m.json.output(),
      '--version', self.__config['xcode version'],
    ], step_test_data=lambda: self.m.json.test_api.output({}))

    self.m.chromium.c.project_generator.tool = 'mb'

    mb_type = self.__config['mb_type']
    gn_args = self.__config['gn_args']

    env = {
      'LANDMINES_VERBOSE': '1',
    }

    # Add extra env variables.
    env.update(self.__config['env'])

    build_sub_path = ''

    build_sub_path = '%s-%s' % (self.configuration, {
        'simulator': 'iphonesimulator',
        'device': 'iphoneos',
      }[self.platform])

    cwd = self.m.path['checkout'].join('out', build_sub_path)
    compile_targets = self.__config['additional_compile_targets']
    cmd = ['ninja', '-C', cwd]

    step_result = self.m.gclient.runhooks(name='runhooks' + suffix, env=env)

    self.m.chromium.run_mb(self.__config['mastername'],
                           self.m.properties['buildername'],
                           name='generate_build_files' + suffix,
                           mb_config_path=mb_config_path,
                           build_dir='//out/' + build_sub_path)

    use_analyze = self.__config['use_analyze']
    if (use_analyze and
        self.m.tryserver.is_tryserver and
        'without patch' not in suffix):
      affected_files = self.m.chromium_checkout.get_files_affected_by_patch(
          cwd=self.m.path['checkout'])
      # The same test may be configured to run on multiple simulators.
      # Only specify each test once for the analyzer.
      tests = list(set(test['app'] for test in self.__config['tests']))

      test_targets, compile_targets = (
        self.m.filter.analyze(
          affected_files,
          tests,
          self.__config['additional_compile_targets'] + tests,
          'trybot_analyze_config.json',
          additional_names=['chromium', 'ios'],
          mb_mastername=self.__config['mastername'],
        )
      )

      test_targets = set(test_targets)

      for test in self.__config['tests']:
        if test['app'] not in test_targets:
          test['skip'] = True

      if compile_targets: # pragma: no cover
        cmd.extend(compile_targets)
      else:
        return

    use_goma = 'use_goma=true' in gn_args
    if use_goma:
      self.m.chromium.compile(targets=compile_targets,
                              target=build_sub_path,
                              cwd=cwd, use_goma_module=True)
    else:
      self.m.step('compile' + suffix, cmd, cwd=cwd)

  def test(self, *args):
    """Runs tests as instructed by this bot's build config.

    Args:
      *args: Any additional arguments to pass to the test harness.
    """
    assert self.__config is not None
    test_failures = []
    infrastructure_failures = []

    for test in self.__config['tests']:
      cmd = [
        self.package_repo_resource(
          'scripts', 'slave', 'ios', 'run.py'),
        '--app', self.m.path['start_dir'].join(
          self.most_recent_app_dir,
          '%s.app' % test['app'],
        ),
        '--json_file', self.m.json.output(),
      ]
      if test.get('xctest'): # pragma: no cover
        cmd.extend([
          '--test-host', test['app'],
          '--dummyproj', self.package_repo_resource(
            'scripts', 'slave', 'ios', 'TestProject', 'TestProject.xcodeproj'),
        ])

      step_name = test['app']

      if self.platform == 'simulator':
        cmd.extend([
          '--iossim', self.m.path['start_dir'].join(self.most_recent_iossim),
          '--platform', test['device type'],
          '--version', test['os'],
        ])

        # Since we may be running simulator tests on multiple platforms,
        # include the platform and OS in the name of the step.
        step_name = '%s (%s iOS %s)' % (
          test['app'],
          test['device type'],
          test['os'],
        )

      cmd.extend(args)

      if test.get('skip'): # pragma: no cover
        step_result = self.m.step('[skipped] %s' % str(step_name), [])
        step_result.presentation.step_text = (
          'This test was skipped because it was not affected.'
        )
        continue

      try:
        step_result = self.m.step(
          str(step_name),
          cmd,
          step_test_data=self.test_api.test_results,
        )
      except self.m.step.StepFailure as f:
        step_result = f.result

        # The test scripts use a return code of 2 to indicate
        # an infrastructure failure.
        if step_result.retcode == 2:
          step_result.presentation.status = self.m.step.EXCEPTION
          infrastructure_failures.append(step_name)
        else:
          test_failures.append(step_name)

      if step_result.json.output:
        step_result.presentation.logs.update(
          step_result.json.output.get('logs', {})
        )
        step_result.presentation.links.update(
          step_result.json.output.get('links', {})
        )
        step_result.presentation.step_text = (
          step_result.json.output.get('step_text', '')
        )

    # Here we turn the build red if there were any test failures, or purple if
    # there were any infrastructure failures. If there were both, turn the build
    # red to call sheriff attention to the legitimate failures.
    if test_failures:
      raise self.m.step.StepFailure(
        'Failed %s.' % ', '.join(test_failures + infrastructure_failures)
      )
    elif infrastructure_failures:
      raise self.m.step.InfraFailure(
        'Failed %s.' % ', '.join(infrastructure_failures)
      )

  def bootstrap_swarming(self):
    """Bootstraps Swarming."""
    self.m.swarming.show_isolated_out_in_collect_step = False
    self.m.swarming.show_shards_in_collect_step = True
    self.m.swarming_client.checkout('stable')
    self.m.swarming_client.query_script_version('swarming.py')

  def isolate(self):
    """Isolates the tests specified in this bot's build config."""
    assert self.__config

    class Task(object):
      def __init__(self, isolate_gen_file, step_name, test):
        self.isolate_gen_file = isolate_gen_file
        self.isolated_hash = None
        self.step_name = step_name
        self.task = None
        self.test = copy.deepcopy(test)
        self.tmp_dir = None

    tasks = []
    failures = []
    skipped = []

    cmd = [
      'src/ios/build/bots/scripts/run.py',
      '--app', '<(app_path)',
      '--args-json', '{"test_args": <(test_args), "xctest": <(xctest)}',
      '--out-dir', '${ISOLATED_OUTDIR}',
      '--xcode-version', '<(xcode_version)',
    ]
    files = [
      # .apps are directories. Need the trailing slash to isolate the
      # contents of a directory.
      '<(app_path)/',
      'src/ios/build/bots/scripts/',
    ]
    if self.platform == 'simulator':
      iossim = self.m.path.join(self.most_recent_iossim)
      cmd.extend([
        '--iossim', iossim,
        '--platform', '<(platform)',
        '--version', '<(version)',
      ])
      files.append(iossim)
    isolate_template_contents = {
      'conditions': [
        ['OS == "ios"', {
          'variables': {
            'command': cmd,
            'files': files,
          },
        }],
      ],
    }
    if self.platform == 'simulator':
      isolate_template_contents['conditions'][0][1]
    isolate_template_contents = self.m.json.dumps(
      isolate_template_contents, indent=2)

    isolate_template = self.m.path['start_dir'].join('template.isolate')
    step_result = self.m.file.write(
      'generate template.isolate',
      isolate_template,
      isolate_template_contents,
    )
    step_result.presentation.logs['template.isolate'] = (
      isolate_template_contents.splitlines())

    tmp_dir = self.m.path.mkdtemp('isolate')

    for test in self.__config['tests']:
      step_name = str('%s (%s iOS %s)' % (
        test['app'], test['device type'], test['os']))

      if test.get('skip'):
        skipped.append(step_name)
        continue

      app_path = self.m.path.join(
        self.most_recent_app_dir,
        '%s.app' % test['app'],
      )
      isolate_gen_file = tmp_dir.join('%s.isolate.gen.json' % test['id'])

      try:
        args = [
          '--config-variable', 'OS', 'ios',
          '--config-variable', 'app_path', app_path,
          '--config-variable', 'test_args', self.m.json.dumps(
              test.get('test args') or []),
          '--config-variable', 'xcode_version', test.get(
            'xcode version', self.__config['xcode version']),
          '--config-variable', 'xctest', (
            'true' if test.get('xctest') else 'false'),
          '--isolate', isolate_template,
          '--isolated', tmp_dir.join('%s.isolated' % test['id']),
          '--path-variable', 'app_path', app_path,
        ]
        if self.platform == 'simulator':
          args.extend([
            '--config-variable', 'platform', test['device type'],
            '--config-variable', 'version', test['os'],
          ])
        isolate_gen_file_contents = self.m.json.dumps({
          'args': args,
          'dir': self.m.path['start_dir'],
          'version': 1,
        }, indent=2)
        step_result = self.m.file.write(
          'generate %s.isolate.gen.json' % test['id'],
          isolate_gen_file,
          isolate_gen_file_contents,
        )
        step_result.presentation.logs['%s.isolate.gen.json' % test['id']] = (
          isolate_gen_file_contents.splitlines())
        step_result.presentation.step_text = step_name

        tasks.append(Task(isolate_gen_file, step_name, test))
      except self.m.step.StepFailure as f:
        f.result.presentation.status = self.m.step.EXCEPTION
        failures.append(step_name)

    if not tasks:
      return tasks, failures, skipped

    cmd = [
      self.m.swarming_client.path.join('isolate.py'),
      'batcharchive',
      '--dump-json', self.m.json.output(),
      '--isolate-server', self.m.isolate.isolate_server,
    ]
    for task in tasks:
      cmd.append(task.isolate_gen_file)
    step_result = self.m.step(
      'archive',
      cmd,
      infra_step=True,
      step_test_data=lambda: self.m.json.test_api.output({
        task.test['id']: 'fake-hash-%s' % task.test['id']
        for task in tasks
      }),
    )
    for task in tasks:
      if task.test['id'] in step_result.json.output:
        task.isolated_hash = step_result.json.output[task.test['id']]

    return tasks, failures, skipped

  def trigger(self, tasks):
    """Triggers the given Swarming tasks."""
    failures = []

    for task in tasks:
      if not task.isolated_hash: # pragma: no cover
        continue

      task.tmp_dir = self.m.path.mkdtemp(task.test['id'])
      swarming_task = self.m.swarming.task(
        task.step_name, task.isolated_hash, task_output_dir=task.tmp_dir)

      swarming_task.dimensions = {
        'pool': 'Chrome',
        'xcode_version': task.test.get(
          'xcode version', self.__config['xcode version'])
      }
      if self.platform == 'simulator':
        swarming_task.dimensions['os'] = 'Mac'
      elif self.platform == 'device':
        swarming_task.dimensions['os'] = 'iOS-%s' % str(task.test['os'])
        swarming_task.dimensions['device_status'] = 'available'
        swarming_task.dimensions['device'] = self.PRODUCT_TYPES.get(
          task.test['device type'])
        if not swarming_task.dimensions['device']:
          failures.append(task.step_name)
          # Create a dummy step so we can annotate it to explain what
          # went wrong.
          step_result = self.m.step('[trigger] %s' % task.step_name, [])
          step_result.presentation.status = self.m.step.EXCEPTION
          step_result.presentation.logs['supported devices'] = sorted(
            self.PRODUCT_TYPES.keys())
          step_result.presentation.step_text = (
            'Requested unsupported device type.')
          continue

      spec = [
        self.m.properties['mastername'],
        self.m.properties['buildername'],
        task.test['app'],
        self.platform,
        task.test['device type'],
        task.test['os'],
        swarming_task.dimensions['xcode_version'],
      ]
      # e.g.
      # chromium.mac:ios-simulator:base_unittests:simulator:iPad Air:10.0:8.0
      swarming_task.tags.add('spec_name:%s' % str(':'.join(spec)))

      swarming_task.tags.add('device_type:%s' % str(task.test['device type']))
      swarming_task.tags.add('ios_version:%s' % str(task.test['os']))
      swarming_task.tags.add('platform:%s' % self.platform)
      swarming_task.tags.add('test:%s' % str(task.test['app']))

      try:
        self.m.swarming.trigger_task(swarming_task)
        task.task = swarming_task
      except self.m.step.StepFailure as f:
        f.result.presentation.status = self.m.step.EXCEPTION
        failures.append(task.step_name)

    return failures

  def test_swarming(self):
    """Runs tests on Swarming as instructed by this bot's build config."""
    assert self.__config

    test_failures = []
    infra_failures = []

    with self.m.step.nest('bootstrap swarming'):
      self.bootstrap_swarming()

    with self.m.step.nest('isolate'):
      tasks, failures, skipped = self.isolate()
      infra_failures.extend(failures)

    if skipped:
      with self.m.step.nest('skipped'):
        for step_name in skipped:
          # Create a dummy step to indicate we skipped this test.
          step_result = self.m.step('[skipped] %s' % step_name, [])
          step_result.presentation.step_text = (
            'This test was skipped because it was not affected.'
          )

    with self.m.step.nest('trigger'):
      failures = self.trigger(tasks)
      infra_failures.extend(failures)

    for task in tasks:
      if not task.task:
        # We failed to isolate or trigger this test.
        # Create a dummy step for it and mark it as failed.
        step_result = self.m.step(task.step_name, [])
        step_result.presentation.status = self.m.step.EXCEPTION
        step_result.presentation.step_text = 'Failed to trigger the test.'
        infra_failures.append(task.step_name)
        continue

      try:
        step_result = self.m.swarming.collect_task(task.task)
      except self.m.step.StepFailure as f:
        step_result = f.result

      # We only run one shard, so the results we're interested in will
      # always be shard 0.
      swarming_summary = step_result.json.output['shards'][0]
      state = swarming_summary['state']
      exit_code = (swarming_summary.get('exit_codes') or [None])[0]

      # Interpret the result and set the display appropriately.
      if state == self.m.swarming.State.COMPLETED and exit_code is not None:
        # Task completed and we got an exit code from the iOS test runner.
        if exit_code == 1:
          step_result.presentation.status = self.m.step.FAILURE
          test_failures.append(task.step_name)
        elif exit_code == 2:
          # The iOS test runner exits 2 to indicate an infrastructure failure.
          step_result.presentation.status = self.m.step.EXCEPTION
          infra_failures.append(task.step_name)
      elif state == self.m.swarming.State.TIMED_OUT:
        # The task was killed for taking too long. This is a test failure
        # because the test itself hung.
        step_result.presentation.status = self.m.step.FAILURE
        step_result.presentation.step_text = 'Test timed out.'
        test_failures.append(task.step_name)
      elif state == self.m.swarming.State.EXPIRED:
        # No Swarming bot accepted the task in time.
        step_result.presentation.status = self.m.step.EXCEPTION
        step_result.presentation.step_text = (
          'No suitable Swarming bot found in time.'
        )
        infra_failures.append(task.step_name)
      else:
        step_result.presentation.status = self.m.step.EXCEPTION
        step_result.presentation.step_text = (
          'Unexpected infrastructure failure.'
        )
        infra_failures.append(task.step_name)

      # Add any iOS test runner results to the display.
      test_summary = self.m.path.join(
        task.task.task_output_dir, '0', 'summary.json')
      if self.m.path.exists(test_summary): # pragma: no cover
        with open(test_summary) as f:
          test_summary_json = self.m.json.loads(f.read())
        step_result.presentation.logs['test_summary.json'] = self.m.json.dumps(
          test_summary_json, indent=2).splitlines()
        step_result.presentation.logs.update(test_summary_json.get('logs', {}))
        step_result.presentation.links.update(
          test_summary_json.get('links', {}))
        if test_summary_json.get('step_text'):
          step_result.presentation.step_text = '%s<br />%s' % (
            step_result.presentation.step_text, test_summary_json['step_text'])

      # Upload any test data.
      task_output = self.m.path.join(task.task.task_output_dir, '0')
      if self.bucket and self.m.path.exists(task_output):
        with self.m.step.nest('archive %s' % task.step_name):
          local_archive = self.m.path.join(
              task.task.task_output_dir, 'test_data.tar.gz')
          self.m.step('tar', [
            'tar',
            '--create',
            '--directory', task_output,
            '--file', local_archive,
            '--gzip',
            '--verbose',
            '.',
          ])
          self.m.gsutil.upload(
            local_archive,
            self.bucket,
            self.m.path.join(
                self.archive_path, task.step_name, 'test_data.tar.gz'),
            link_name='test_data.tar.gz',
            name='upload test_data.tar.gz',
          )

    if test_failures:
      raise self.m.step.StepFailure(
        'Failed %s.' % ', '.join(sorted(set(test_failures + infra_failures))))
    elif infra_failures:
      raise self.m.step.InfraFailure(
        'Failed %s.' % ', '.join(sorted(set(infra_failures))))

  @property
  def archive_path(self):
    """Returns the path on Google Storage to archive artifacts to."""
    return '%s/%s/%s' % (
        self.m.properties['mastername'],
        self.m.properties['buildername'],
        str(self.m.properties['buildnumber'] or 0),
    )

  @property
  def most_recent_app_dir(self):
    """Returns the path to the directory of the most recently compiled apps."""
    platform = {
      'device': 'iphoneos',
      'simulator': 'iphonesimulator',
    }[self.platform]

    return self.m.path.join(
      'src',
      'out',
      '%s-%s' % (self.configuration, platform),
    )

  @property
  def most_recent_iossim(self):
    """Returns the path to the most recently compiled iossim."""
    platform = {
      'device': 'iphoneos',
      'simulator': 'iphonesimulator',
    }[self.platform]

    return self.m.path.join(
      'src', 'out', '%s-%s' % (self.configuration, platform), 'iossim')
