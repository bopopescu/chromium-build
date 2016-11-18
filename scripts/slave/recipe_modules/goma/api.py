# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from contextlib import contextmanager

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  def __init__(self, **kwargs):
    super(GomaApi, self).__init__(**kwargs)
    self._goma_dir = None
    self._goma_started = False

    self._goma_ctl_env = {}
    self._goma_jobs = None

  @property
  def service_account_json_path(self):
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts\\service-account-goma-client.json'
    return '/creds/service_accounts/service-account-goma-client.json'

  @property
  def cloudtail_path(self):  # pragma: nocover
    assert self._goma_dir
    return self.m.path.join(self._goma_dir, 'cloudtail')

  @property
  def cloudtail_pid_file(self):  # pragma: nocover
    return self.m.path['tmp_base'].join('cloudtail.pid')

  @property
  def json_path(self):
    assert self._goma_dir
    return self.m.path.join(self._goma_dir, 'jsonstatus')

  @property
  def default_cache_path(self):
    try:
      # Legacy Buildbot cache path:
      return self.m.path['goma_cache']
    except KeyError:  # pragma: no cover | TODO(nodir): cover
      # New more generic cache path
      return self.m.path['cache'].join('goma')

  @property
  def recommended_goma_jobs(self):
    """
    Return the recommended number of jobs for parallel build using Goma.

    This function caches the _goma_jobs.
    """
    if self._goma_jobs:
      return self._goma_jobs

    # In presubmit, a buildbot generates recipe json file and
    # another buildbot checks generated recipe,
    # so we need to use python.inline not to change
    # behavior of recipes.
    step_result = self.m.python.inline(
      'calculate the number of recommended jobs',
      """
import multiprocessing
import sys

job_limit = 200
if sys.platform.startswith('linux'):
  # Use 80 for linux not to load goma backend.
  job_limit = 80

try:
  jobs = min(job_limit, multiprocessing.cpu_count() * 10)
except NotImplementedError:
  jobs = 50

print jobs
      """,
      stdout=self.m.raw_io.output(),
      step_test_data=(
          lambda: self.m.raw_io.test_api.stream_output('50\n'))
    )
    self._goma_jobs = int(step_result.stdout)

    return self._goma_jobs

  def remove_j_flag(self, command):
    """Remove -j flag from command.
    This function elimitnates -j flag from command for
    '-j', '80' style and '-j80' style.

    Args:
      command: List of command line arg.
    """
    parallel_flag_regexp = re.compile('-j\d*')
    for i in range(len(command)):
      if (isinstance(command[i], str) and
          parallel_flag_regexp.match(command[i])):
        if command[i] == '-j':
          command.pop(i + 1)
        command.pop(i)
        return

  def ensure_goma(self, canary=False):
    with self.m.step.nest('ensure_goma'):
      with self.m.step.context({'infra_step': True}):
        try:
          self.m.cipd.set_service_account_credentials(
              self.service_account_json_path)

          self.m.cipd.install_client()
          goma_package = ('infra_internal/goma/client/%s' %
              self.m.cipd.platform_suffix())
          # For Windows there's only 64-bit goma client.
          if self.m.platform.is_win:
            goma_package = goma_package.replace('386', 'amd64')
          ref='release'
          if canary:
            ref='candidate'
          self._goma_dir = self.m.path['cache'].join('cipd', 'goma')

          # To update:
          # ./cipd set-ref infra/tools/cloudtail/ \
          #     -ref goma_recipe_module \
          #     -version git_revision:c6b17d5aa4fa6396c5f971248120e0e624c21fb3
          #
          # To see tags (e.g. git_revision:*):
          # ./cipd describe infra/tools/cloudtail/linux-amd64 \
          #     -version goma_recipe_module
          cloudtail_package = (
              'infra/tools/cloudtail/%s' % self.m.cipd.platform_suffix())
          cloudtail_version = 'goma_recipe_module'

          self.m.cipd.ensure(self._goma_dir,
                             {goma_package: ref,
                              cloudtail_package: cloudtail_version})

          return self._goma_dir
        except self.m.step.StepFailure:
          # TODO(phajdan.jr): make failures fatal after experiment.
          return None

  @property
  def goma_ctl(self):
    return self.m.path.join(self._goma_dir, 'goma_ctl.py')

  @property
  def goma_dir(self):
    assert self._goma_dir
    return self._goma_dir

  @property
  def build_data_dir(self):
    return self.m.properties.get('build_data_dir')

  def _start_cloudtail(self):  # pragma: nocover
    """Start cloudtail to upload compiler_proxy.INFO

    Raises:
      InfraFailure if it fails to start cloudtail
    """

    # TODO(vadimsh): crbug/642299
    return

    self.m.python(
      name='start cloudtail',
      script=self.resource('cloudtail_utils.py'),
      args=['start',
            '--cloudtail-path', self.cloudtail_path,
            '--pid-file', self.m.raw_io.output(
                leak_to=self.cloudtail_pid_file)],
      env=self._goma_ctl_env,
      step_test_data=(
          lambda: self.m.raw_io.test_api.output('12345')),
      infra_step=True)

  def _stop_cloudtail(self):  # pragma: nocover
    """Stop cloudtail started by _start_cloudtail

    Raises:
      InfraFailure if it fails to stop cloudtail
    """

    # TODO(vadimsh): crbug/642299
    return

    self.m.python(
        name='stop cloudtail',
        script=self.resource('cloudtail_utils.py'),
        args=['stop',
              '--killed-pid-file', self.cloudtail_pid_file],
        infra_step=True)

  def start(self, env=None, **kwargs):
    """Start goma compiler_proxy.

    A user MUST execute ensure_goma beforehand.
    It is user's responsibility to handle failure of starting compiler_proxy.
    """
    assert self._goma_dir
    assert not self._goma_started

    with self.m.step.nest('preprocess_for_goma'):
      if self.build_data_dir:
        self._goma_ctl_env['GOMA_DUMP_STATS_FILE'] = (
            self.m.path.join(self.build_data_dir, 'goma_stats_proto'))
        self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'] = (
            self.m.path.join(self.build_data_dir, 'crash_report_id_file'))

      self._goma_ctl_env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = (
          self.service_account_json_path)

      # GLOG_log_dir should not be set.
      assert env is None or 'GLOG_log_dir' not in env

      goma_ctl_start_env = self._goma_ctl_env.copy()

      if env is not None:
        goma_ctl_start_env.update(env)

      try:
        self.m.python(
            name='start_goma',
            script=self.goma_ctl,
            args=['restart'], env=goma_ctl_start_env, infra_step=True, **kwargs)
        self._goma_started = True

        self._start_cloudtail()

      except self.m.step.InfraFailure as e: # pragma: no cover
        try:
          with self.m.step.defer_results():
            self.m.python(
                name='stop_goma (start failure)',
                script=self.goma_ctl,
                args=['stop'], env=self._goma_ctl_env, **kwargs)
            self._upload_logs(name='upload_goma_start_failed_logs',
                              skip_sendgomatsmon=True)
        except self.m.step.StepFailure:
          pass

        raise e

  def stop(self, ninja_log_outdir=None, ninja_log_compiler=None,
           ninja_log_command=None, ninja_log_exit_status=None, **kwargs):
    """Stop goma compiler_proxy.

    A user MUST execute start beforehand.
    It is user's responsibility to handle failure of stopping compiler_proxy.

    Raises:
      StepFailure if it fails to stop goma or upload logs.
    """

    assert self._goma_dir
    assert self._goma_started

    with self.m.step.nest('postprocess_for_goma'):
      with self.m.step.defer_results():
        self.m.python(name='goma_jsonstatus', script=self.goma_ctl,
                      args=['jsonstatus', self.json_path],
                      env=self._goma_ctl_env, **kwargs)
        self.m.python(name='goma_stat', script=self.goma_ctl,
                      args=['stat'],
                      env=self._goma_ctl_env, **kwargs)
        self.m.python(name='stop_goma', script=self.goma_ctl,
                      args=['stop'], env=self._goma_ctl_env, **kwargs)
        self._upload_logs(ninja_log_outdir, ninja_log_compiler,
                         ninja_log_command, ninja_log_exit_status)
        self._stop_cloudtail()

      self._goma_started = False
      self._goma_ctl_env = {}

  def _upload_logs(self, ninja_log_outdir=None, ninja_log_compiler=None,
                   ninja_log_command=None, ninja_log_exit_status=None,
                   name=None, skip_sendgomatsmon=False):
    args = [
        '--upload-compiler-proxy-info',
    ]

    if skip_sendgomatsmon: # pragma: no cover
      args.append('--skip-sendgomatsmon')

    if self.json_path:
      args.extend(['--json-status', self.json_path])

    if ninja_log_outdir:
      assert ninja_log_compiler is not None
      assert ninja_log_command is not None
      assert ninja_log_exit_status is not None

      args.extend([
        '--ninja-log-outdir', ninja_log_outdir,
        '--ninja-log-compiler', ninja_log_compiler,
        '--ninja-log-command', str(ninja_log_command),
        '--ninja-log-exit-status', ninja_log_exit_status,
      ])
    else:
      args.extend(['--ninja-log-exit-status', '-1'])

    if self.build_data_dir:
      args.extend([
          '--goma-stats-file', self._goma_ctl_env['GOMA_DUMP_STATS_FILE'],
          '--goma-crash-report-id-file',
          self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'],
          '--build-data-dir', self.build_data_dir,
      ])

    # Set some buildbot info used in goma_utils.SendGomaTsMon.
    for key in ['buildername', 'mastername', 'slavename', 'clobber']:
      if key in self.m.properties:
        args.extend([
            '--buildbot-%s' % key, self.m.properties[key]
        ])


    self.m.python(
      name=name or 'upload_log',
      script=self.package_repo_resource(
          'scripts', 'slave', 'upload_goma_logs.py'),
      args=args,
      env=self._goma_ctl_env
    )

  @contextmanager
  def build_with_goma(self, ninja_log_outdir=None, ninja_log_compiler=None,
                      ninja_log_command=None, env=None,
                      allow_build_without_goma=False):
    """Make context wrapping goma start/stop.

    Args ninja_log_* are NOT used to run actual build in this context.
    These args are only used to collect log and upload them.

    Args:
      ninja_log_outdir: Directory of ninja log. (e.g. "out/Release")
      ninja_log_compiler: Compiler used in ninja. (e.g. "clang")
      ninja_log_command: Command used for build.
                         This is used only to be sent as part of log,
                         NOT used to run actual build.
                         (e.g. ['ninja', '-C', 'out/Release', '-j', '100'])
      env: Environment controlling goma behavior.
           This should be used for ninja if allow_build_without_goma is True.
           Otherwise, only used for goma behavior control.
      allow_build_without_goma (bool):
        If this is not True, goma starting failure is ignored.
        This argument should be used with env.
        If starting goma fails, env and ninja_log_command are modified.

    Raises:
      StepFailure or InfraFailure if it fails to build.
    """
    ninja_log_exit_status = 0

    if allow_build_without_goma:
      assert(env is not None)
      try:
        self.start(env)
      except:
        env['GOMA_DISABLED'] = 'true'
        self.remove_j_flag(ninja_log_command)
        try:
          yield
        except self.m.step.StepFailure as e: # pragma: no cover
          ninja_log_exit_status = e.retcode
          raise e
        except self.m.step.InfraFailure as e: # pragma: no cover
          ninja_log_exit_status = -1
          raise e
        finally:
          self._upload_logs(ninja_log_outdir=ninja_log_outdir,
                            ninja_log_compiler=ninja_log_compiler,
                            ninja_log_command=ninja_log_command,
                            ninja_log_exit_status=ninja_log_exit_status,
                            name='upload log goma start failed')
        return
    else:
      self.start(env)

    try:
      yield
    except self.m.step.StepFailure as e: # pragma: no cover
      ninja_log_exit_status = e.retcode
      raise e
    except self.m.step.InfraFailure as e: # pragma: no cover
      ninja_log_exit_status = -1
      raise e
    finally:
      self.stop(ninja_log_outdir=ninja_log_outdir,
                ninja_log_compiler=ninja_log_compiler,
                ninja_log_command=ninja_log_command,
                ninja_log_exit_status=ninja_log_exit_status)
