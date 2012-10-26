# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to build the chromium master."""

import os

from buildbot.steps import shell
from buildbot.process.properties import Property, WithProperties

from common import chromium_utils
from master import chromium_step
from master.factory import build_factory
from master.factory import chromeos_build_factory
from master.factory import commands
from master.log_parser import process_log

import config


class CbuildbotFactory(object):
  """
  Create a cbuildbot build factory.

  This is designed mainly to utilize build scripts directly hosted in
  chromite.git.

  Attributes:
      buildroot: --buildroot to pass to cbuild.
      params: string of parameters to pass to the cbuildbot type
      timeout: Timeout in seconds for the main command
          (i.e. the type command). Default 9000 seconds.
      crostools_repo: git repo for crostools toolset.
      chromite_repo: git repo for chromite toolset.
      dry_run: Means cbuildbot --debug, or don't push anything (cbuildbot only)
      factory: a factory with pre-existing steps to extend rather than start
          fresh.  Allows composing.
      pass_revision: to pass the chrome revision desired into the build.
      chromite_patch: a url and ref pair (dict) to patch the checked out
          chromite. Fits well with a single change from a codereview, to use
          on one or more builders for realistic testing, or experiments.
      trybot: Whether this is creating builders for the trybot waterfall.
      sleep_sync: Whether to randomly delay the start of the cbuildbot step.
      show_gclient_output: Set to False to hide the output of 'gclient sync'.
          Used by external masters to prevent leaking sensitive information,
          since both external and internal slaves use internal.DEPS/.
      perf_file: If set, name of the perf file to upload.
  """
  _default_git_base = 'http://git.chromium.org/chromiumos'
  _default_crostools = 'ssh://gerrit-int.chromium.org:29419/chromeos/crostools'
  _default_chromite = _default_git_base + '/chromite.git'

  def __init__(self, params, buildroot='/b/cbuild', timeout=9000,
               branch='master', crostools_repo=_default_crostools,
               chromite_repo=_default_chromite, dry_run=False, chrome_root=None,
               factory=None, pass_revision=False, slave_manager=True,
               chromite_patch=None, trybot=False, sleep_sync=None,
               show_gclient_output=True, perf_file=None):
    self.buildroot = buildroot
    self.crostools_repo = crostools_repo
    self.chromite_repo = chromite_repo
    self.chromite_patch = chromite_patch
    if chromite_patch:
      assert ('url' in chromite_patch and 'ref' in chromite_patch)

    self.timeout = timeout
    self.branch = branch
    self.dry_run = dry_run
    self.chrome_root = chrome_root
    self.slave_manager = slave_manager
    self.trybot = trybot
    self.sleep_sync = sleep_sync
    self.show_gclient_output = show_gclient_output

    if factory:
      self.f_cbuild = factory
    elif pass_revision:
      self.f_cbuild = build_factory.BuildFactory()
    else:
      self.f_cbuild = chromeos_build_factory.BuildFactory()

    self.add_bootstrap_steps()
    self.add_cbuildbot_step(params, pass_revision)
    if perf_file:
      self.add_perf_step(params, perf_file)

  def _git_clear_and_checkout(self, repo, patch=None):
    """rm -rf and clone the basename of the repo passed without .git

    Args:
      repo: ssh: uri for the repo to be checked out
      patch: object with url and ref to patch on top
    """
    git_bin = '/usr/bin/git'
    git_checkout_dir = os.path.basename(repo).replace('.git', '')
    clear_and_clone_cmd = 'rm -rf %s' % git_checkout_dir
    clear_and_clone_cmd += ' && %s clone %s' % (git_bin, repo)
    clear_and_clone_cmd += ' && cd %s' % git_checkout_dir

    # We ignore branches coming from buildbot triggers and rely on those in the
    # config.  This is because buildbot branch names do not match up with
    # cros builds.
    clear_and_clone_cmd += ' && %s checkout %s' % (git_bin, self.branch)
    msg = 'Clear and Clone %s' % git_checkout_dir
    if patch:
      clear_and_clone_cmd += (' && %s pull %s %s' %
                              (git_bin, patch['url'], patch['ref']))
      msg = 'Clear, Clone and Patch %s' % git_checkout_dir

    self.f_cbuild.addStep(shell.ShellCommand,
                          command=clear_and_clone_cmd,
                          name=msg,
                          description=msg,
                          haltOnFailure=True)

  def add_bootstrap_steps(self):
    """Bootstraps Chromium OS Build by syncing pre-requisite repositories.

    * gclient sync of /b
    * clearing of chromite[& crostools]
    * clean checkout of chromite[& crostools]
    """
    if self.slave_manager:
      build_slave_sync = ['gclient', 'sync',
                          '--delete_unversioned_trees']
      self.f_cbuild.addStep(shell.ShellCommand,
                            command=build_slave_sync,
                            name='update_scripts',
                            description='Sync buildbot slave files',
                            workdir='/b',
                            timeout=300,
                            want_stdout=self.show_gclient_output,
                            want_stderr=self.show_gclient_output)

    if self.sleep_sync:
      # We run a script from the script checkout above.
      fuzz_start = ['python', 'scripts/slave/random_delay.py',
                    '--max=%g' % self.sleep_sync]
      self.f_cbuild.addStep(shell.ShellCommand,
                            command=fuzz_start,
                            name='random_delay',
                            description='Delay start of build',
                            workdir='/b/build',
                            timeout=int(self.sleep_sync) + 10)

    self._git_clear_and_checkout(self.chromite_repo, self.chromite_patch)
    if self.crostools_repo:
      self._git_clear_and_checkout(self.crostools_repo)

  def add_cbuildbot_step(self, params, pass_revision=False):
    """Adds cbuildbot step for Chromium OS builds.

    Cbuildbot includes all steps for building any Chromium OS config.

    Args:
      params:  Extra parameters for cbuildbot.
      pass_revision: To pass the chrome revision desired into the build.
    """
    cmd = ['chromite/buildbot/cbuildbot',
           shell.WithProperties('--buildnumber=%(buildnumber)s'),
           '--buildroot=%s' % self.buildroot]

    if self.trybot:
      cmd.append(Property('extra_args'))
    else:
      cmd += ['--buildbot']

    if self.dry_run:
      cmd += ['--debug']

    if self.chrome_root:
      cmd.append('--chrome_root=%s' % self.chrome_root)

    # Add properties from buildbot as necessary.
    cmd.append(WithProperties('%s', 'clobber:+--clobber'))
    if pass_revision:
      cmd.append(shell.WithProperties('--chrome_version=%(revision)s'))

    # Add additional parameters.
    cmd += params.split()

    description = 'cbuildbot'

    self.f_cbuild.addStep(chromium_step.AnnotatedCommand,
                          command=cmd,
                          timeout=self.timeout,
                          name='cbuildbot',
                          description=description,
                          usePTY=False)


  def add_perf_step(self, params, perf_file):
    """Adds step for uploading perf results using the given file.

    Args:
      params: Extra parameters for cbuildbot.
      perf_file: Name of the perf file to upload. Note the name of this file
        will be used as the testname and params[0] will be used as the platform
        name.
    """
    # Name of platform is always taken as the first param.
    platform = params.split()[0]
    # Name of the test is based off the name of the file.
    test = os.path.splitext(perf_file)[0]
    # Assuming all perf files will be stored in the cbuildbot log directory.
    perf_file_path = os.path.join(self.buildroot, 'cbuildbot_logs', perf_file)
    report_link = '/'.join([config.Master.perf_base_url, platform, test,
                            config.Master.perf_report_url_suffix])
    output_dir = chromium_utils.AbsoluteCanonicalPath('/'.join([
        config.Master.perf_output_dir, platform, test]))

    cmd = ['cat', perf_file_path]

    perf_class = commands.CreatePerformanceStepClass(
        process_log.GraphingLogProcessor,
        report_link=report_link, output_dir=output_dir,
        factory_properties={}, perf_name=platform,
        test_name=test)

    self.f_cbuild.addStep(
        perf_class, command=cmd, name='Upload Perf Results',
        description='upload_perf_results')


  def get_factory(self):
    """Returns the produced factory."""
    return self.f_cbuild
