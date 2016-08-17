# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api

class GomaApi(recipe_api.RecipeApi):
  """GomaApi contains helper functions for using goma."""

  def __init__(self, **kwargs):
    super(GomaApi, self).__init__(**kwargs)
    self._goma_dir = None
    self._goma_started = False

    self._goma_ctl_env = {}

  @property
  def service_account_json_path(self):
    if self.m.platform.is_win:
      return 'C:\\creds\\service_accounts\\service-account-goma-client.json'
    return '/creds/service_accounts/service-account-goma-client.json'

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
          self.m.cipd.ensure(self._goma_dir, {goma_package: ref})
          return self._goma_dir
        except self.m.step.StepFailure:
          # TODO(phajdan.jr): make failures fatal after experiment.
          return None

  @property
  def goma_ctl(self):
    return self.m.path.join(self._goma_dir, 'goma_ctl.py')

  @property
  def build_data_dir(self):
    return self.m.properties.get('build_data_dir')

  def start(self, env=None, **kwargs):
    """Start goma compiler_proxy.

    A user MUST execute ensure_goma beforehand.
    It is user's responsibility to handle failure of starting compiler_proxy.
    """
    assert self._goma_dir
    assert not self._goma_started

    if self.build_data_dir:
      self._goma_ctl_env['GOMA_DUMP_STATS_FILE'] = (
          self.m.path.join(self.build_data_dir, 'goma_stats_proto'))
      self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'] = (
          self.m.path.join(self.build_data_dir, 'crash_report_id_file'))

    self._goma_ctl_env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = (
        self.service_account_json_path)

    goma_ctl_start_env = self._goma_ctl_env.copy()

    if env is not None:
      goma_ctl_start_env.update(env)

    try:
      self.m.python(
          name='start_goma',
          script=self.goma_ctl,
          args=['restart'], env=goma_ctl_start_env, infra_step=True, **kwargs)
      self._goma_started = True
    except self.m.step.InfraFailure as e: # pragma: no cover
      upload_logs_name = 'upload_goma_start_failed_logs'

      try:
        self.m.python(
            name='stop_goma (start failure)',
            script=self.goma_ctl,
            args=['stop'], env=self._goma_ctl_env, **kwargs)
      except self.m.step.StepFailure:
        upload_logs_name = 'upload_goma_start_and_stop_failed_logs'

      self.upload_logs(name=upload_logs_name)
      raise e

  def stop(self, ninja_log_outdir=None, ninja_log_compiler=None,
           ninja_log_command=None, ninja_log_exit_status=None, **kwargs):
    """Stop goma compiler_proxy.

    A user MUST execute start beforehand.
    It is user's responsibility to handle failure of stopping compiler_proxy.
    """
    assert self._goma_dir
    assert self._goma_started
    self.m.python(
        name='stop_goma',
        script=self.goma_ctl,
        args=['stop'], env=self._goma_ctl_env, **kwargs)

    self.upload_logs(ninja_log_outdir, ninja_log_compiler, ninja_log_command,
                     ninja_log_exit_status)

    self._goma_started = False
    self._goma_ctl_env = {}

  def upload_logs(self, ninja_log_outdir=None, ninja_log_compiler=None,
                  ninja_log_command=None, ninja_log_exit_status=None,
                  name=None):
    args = [
        '--upload-compiler-proxy-info'
    ]

    if ninja_log_outdir:
      assert ninja_log_compiler is not None
      assert ninja_log_command is not None
      assert ninja_log_exit_status is not None

      args.extend([
        '--ninja-log-outdir', ninja_log_outdir,
        '--ninja-log-compiler', ninja_log_compiler,
        '--ninja-log-command', ninja_log_command,
        '--ninja-log-exit-status', ninja_log_exit_status,
      ])

    if self.build_data_dir:
      args.extend([
          '--goma-stats-file', self._goma_ctl_env['GOMA_DUMP_STATS_FILE'],
          '--goma-crash-report-id-file',
          self._goma_ctl_env['GOMACTL_CRASH_REPORT_ID_FILE'],
          '--build-data-dir', self.build_data_dir,
      ])

    self.m.python(
      name=name or 'upload_log',
      script=self.package_repo_resource(
          'scripts', 'slave', 'upload_goma_logs.py'),
      args=args
    )
