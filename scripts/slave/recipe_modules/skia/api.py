# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import json
import os
import re
import sys

from recipe_engine import recipe_api
from recipe_engine import config_types

# TODO(luqui): Make this recipe stop depending on common so we can make it
# independent of build/.
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))))
from common.skia import global_constants

from . import android_flavor
from . import cmake_flavor
from . import coverage_flavor
from . import default_flavor
from . import fake_specs
from . import ios_flavor
from . import pdfium_flavor
from . import valgrind_flavor
from . import xsan_flavor


BOTO_CHROMIUM_SKIA_GM = 'chromium-skia-gm.boto'

GS_SUBDIR_TMPL_SK_IMAGE = 'skimage/v%s'
GS_SUBDIR_TMPL_SKP = 'playback_%s/skps'

MIN_COLORSPACE_SKIMAGE_VERSION = 5

TEST_EXPECTED_SKP_VERSION = '42'
TEST_EXPECTED_SK_IMAGE_VERSION = '42'

VERSION_FILE_SK_IMAGE = 'SK_IMAGE_VERSION'
VERSION_FILE_SKP = 'SKP_VERSION'

VERSION_NONE = -1

BUILD_PRODUCTS_ISOLATE_WHITELIST = [
  'dm',
  'dm.exe',
  'nanobench',
  'nanobench.exe',
  '*.so',
  '*.dll',
  '*.dylib',
  'skia_launcher',
  'lib/*.so',
  'iOSShell.app',
  'iOSShell.ipa',
  'visualbench',
  'visualbench.exe',
]


def is_android(builder_cfg):
  """Determine whether the given builder is an Android builder."""
  return ('Android' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'Android')


def is_cmake(builder_cfg):
  return 'CMake' in builder_cfg.get('extra_config', '')


def is_ios(builder_cfg):
  return ('iOS' in builder_cfg.get('extra_config', '') or
          builder_cfg.get('os') == 'iOS')


def is_pdfium(builder_cfg):
  return 'PDFium' in builder_cfg.get('extra_config', '')


def is_valgrind(builder_cfg):
  return 'Valgrind' in builder_cfg.get('extra_config', '')


def is_xsan(builder_cfg):
  return ('ASAN' in builder_cfg.get('extra_config', '') or
          'MSAN' in builder_cfg.get('extra_config', '') or
          'TSAN' in builder_cfg.get('extra_config', ''))


class SkiaApi(recipe_api.RecipeApi):

  def get_flavor(self, builder_cfg):
    """Return a flavor utils object specific to the given builder."""
    if is_android(builder_cfg):
      return android_flavor.AndroidFlavorUtils(self)
    elif is_cmake(builder_cfg):
      return cmake_flavor.CMakeFlavorUtils(self)
    elif is_ios(builder_cfg):
      return ios_flavor.iOSFlavorUtils(self)
    elif is_pdfium(builder_cfg):
      return pdfium_flavor.PDFiumFlavorUtils(self)
    elif is_valgrind(builder_cfg):
      return valgrind_flavor.ValgrindFlavorUtils(self)
    elif is_xsan(builder_cfg):
      return xsan_flavor.XSanFlavorUtils(self)
    elif builder_cfg.get('configuration') == global_constants.CONFIG_COVERAGE:
      return coverage_flavor.CoverageFlavorUtils(self)
    else:
      return default_flavor.DefaultFlavorUtils(self)

  @property
  def home_dir(self):
    """Find the home directory."""
    home_dir = os.path.expanduser('~')
    if self._test_data.enabled:
      home_dir = '[HOME]'
    return home_dir

  def gsutil_env(self, boto_file):
    """Environment variables for gsutil."""
    boto_path = None
    if boto_file:
      boto_path = self.m.path.join(self.home_dir, boto_file)
    return {'AWS_CREDENTIAL_FILE': boto_path,
            'BOTO_CONFIG': boto_path}

  def gen_steps(self):
    """Generate all build steps."""
    self.setup()
    self.run_steps()

  def get_builder_spec(self, skia_dir, builder_name):
    """Obtain the buildbot spec for the given builder."""
    fake_spec = None
    if self._test_data.enabled:
      fake_spec = fake_specs.FAKE_SPECS[builder_name]
    builder_spec = self.json_from_file(
      skia_dir.join('tools', 'buildbot_spec.py'),
      skia_dir,
      builder_name,
      fake_spec)
    return builder_spec

  def make_path(self, *path):
    """Return a Path object for the given path."""
    key  = 'custom_%s' % '_'.join(path)
    self.m.path.c.base_paths[key] = tuple(path)
    return self.m.path[key]

  def setup(self, running_in_swarming=False):
    """Prepare the bot to run."""
    # Setup
    self.failed = []

    self.builder_name = self.m.properties['buildername']
    self.master_name = self.m.properties['mastername']
    self.slave_name = self.m.properties['slavename']

    self.slave_dir = self.m.path['slave_build']
    self.checkout_root = self.slave_dir
    self.default_env = {}
    self.is_compile_bot = self.builder_name.startswith('Build-')

    if running_in_swarming:
      self.default_env['CHROME_HEADLESS'] = '1'
      # The 'build' and 'depot_tools' directories are provided through isolate
      # and aren't in the expected location, so we need to override them.
      self.m.path.c.base_paths['depot_tools'] = (
          self.m.path.c.base_paths['slave_build'] +
          ('build', 'scripts', 'slave', '.recipe_deps', 'depot_tools'))
      if 'Win' in self.builder_name:
        self.m.path.c.base_paths['depot_tools'] = (
            'c:\\', 'Users', 'chrome-bot', 'depot_tools')
      self.m.path.c.base_paths['build'] = (
          self.m.path.c.base_paths['slave_build'] + ('build',))
      self.default_env['PYTHONPATH'] = self.m.path['build'].join('scripts')

      # Compile bots keep a persistent checkout.
      if self.is_compile_bot:
        if 'Win' in self.builder_name:
          self.checkout_root = self.make_path('C:\\', 'b', 'work')
          self.gclient_cache = self.make_path('C:\\', 'b', 'cache')
        else:
          self.checkout_root = self.make_path('/', 'b', 'work')
          self.gclient_cache = self.make_path('/', 'b', 'cache')

    self.skia_dir = self.checkout_root.join('skia')
    self.infrabots_dir = self.skia_dir.join('infra', 'bots')

    # We run through this recipe in one of two ways:
    # 1. Normal bot: run all of the steps.
    # 2. Running as a Swarming task: perform the given task only, with
    #    adaptations for running within Swarming, eg. copying build results
    #    into the correct output directory.
    self.running_in_swarming = running_in_swarming

    # Some bots also require a checkout of chromium.
    self._need_chromium_checkout = 'CommandBuffer' in self.builder_name
    if (self.running_in_swarming and
        self.is_compile_bot and
        'SAN' in self.builder_name):
      self._need_chromium_checkout = True

    # Some bots also require a checkout of PDFium.
    self._need_pdfium_checkout = 'PDFium' in self.builder_name

    # Check out the Skia code.
    self.checkout_steps()

    # Obtain the spec for this builder from the Skia repo. Use it to set more
    # properties.
    self.builder_spec = self.get_builder_spec(self.skia_dir, self.builder_name)

    self.builder_cfg = self.builder_spec['builder_cfg']
    self.role = self.builder_cfg['role']

    # Set some important variables.
    self.resource_dir = self.skia_dir.join('resources')
    self.images_dir = self.slave_dir.join('images')
    self.skia_out = self.skia_dir.join('out', self.builder_name)
    if self.running_in_swarming:
      self.swarming_out_dir = self.make_path(self.m.properties['swarm_out_dir'])
      self.local_skp_dir = self.slave_dir.join('skps')
      if not self.is_compile_bot:
        self.skia_out = self.slave_dir.join('out')
    else:
      self.local_skp_dir = self.slave_dir.join('playback', 'skps')
    self.tmp_dir = self.m.path['slave_build'].join('tmp')

    self.gsutil_env_chromium_skia_gm = self.gsutil_env(BOTO_CHROMIUM_SKIA_GM)

    self.device_dirs = None
    self._ccache = None
    self._checked_for_ccache = False
    self.configuration = self.builder_spec['configuration']
    self.default_env.update({'SKIA_OUT': self.skia_out,
                             'BUILDTYPE': self.configuration})
    self.default_env.update(self.builder_spec['env'])
    self.build_targets = [str(t) for t in self.builder_spec['build_targets']]
    self.do_compile_steps = self.builder_spec.get('do_compile_steps', True)
    self.do_test_steps = self.builder_spec['do_test_steps']
    self.do_perf_steps = self.builder_spec['do_perf_steps']
    self.is_trybot = self.builder_cfg['is_trybot']
    self.upload_dm_results = self.builder_spec['upload_dm_results']
    self.upload_perf_results = self.builder_spec['upload_perf_results']
    if self.running_in_swarming:
      self.dm_dir = self.m.path.join(
          self.swarming_out_dir, 'dm')
      self.perf_data_dir = self.m.path.join(self.swarming_out_dir,
          'perfdata', self.builder_name, 'data')
    else:
      self.dm_dir = self.slave_dir.join('dm')
      self.perf_data_dir = self.slave_dir.join('perfdata', self.builder_name,
                                               'data')
    self.dm_flags = self.builder_spec['dm_flags']
    self.nanobench_flags = self.builder_spec['nanobench_flags']

    self.flavor = self.get_flavor(self.builder_cfg)

  def run_steps(self):
    """Compile, run tests, perf, etc."""
    if self.do_compile_steps:
      self.compile_steps()
    if self.do_test_steps:
      self.test_steps()
    if self.do_perf_steps:
      self.perf_steps()

    if self.do_test_steps or self.do_perf_steps:
      self.cleanup_steps()

    self.check_failure()

  def check_failure(self):
    """Raise an exception if any step failed."""
    if self.failed:
      raise self.m.step.StepFailure('Failed build steps: %s' %
                                    ', '.join([f.name for f in self.failed]))

  def _run_once(self, fn, *args, **kwargs):
    if not hasattr(self, '_already_ran'):
      self._already_ran = {}
    if not fn.__name__ in self._already_ran:
      self._already_ran[fn.__name__] = fn(*args, **kwargs)
    return self._already_ran[fn.__name__]

  def update_repo(self, parent_dir, repo):
    """Update an existing repo. This is safe to call without gen_steps."""
    repo_path = parent_dir.join(repo.name)
    if self.m.path.exists(repo_path):
      if 'Win' in self.m.properties['buildername']:
        git = 'git.bat'
      else:
        git = 'git'
      self.m.step('git remote set-url',
                  cmd=[git, 'remote', 'set-url', 'origin', repo.url],
                  cwd=repo_path,
                  infra_step=True)
      self.m.step('git fetch',
                  cmd=[git, 'fetch'],
                  cwd=repo_path,
                  infra_step=True)
      self.m.step('git reset',
                  cmd=[git, 'reset', '--hard', repo.revision],
                  cwd=repo_path,
                  infra_step=True)
      self.m.step('git clean',
                  cmd=[git, 'clean', '-d', '-f'],
                  cwd=repo_path,
                  infra_step=True)

  def checkout_steps(self):
    """Run the steps to obtain a checkout of Skia."""
    cfg_kwargs = {}
    if self.running_in_swarming:
      if not self.is_compile_bot:
        # We should've obtained the Skia checkout through isolates, so we don't
        # need to perform the checkout ourselves.
        self.m.path['checkout'] = self.skia_dir
        self.got_revision = self.m.properties['revision']
        return

      # Use a persistent gclient cache for Swarming.
      cfg_kwargs['CACHE_DIR'] = self.gclient_cache

    # Create the checkout path if necessary.
    if not self.m.path.exists(self.checkout_root):
      self.m.file.makedirs('checkout_path', self.checkout_root, infra_step=True)

    # Initial cleanup.
    gclient_cfg = self.m.gclient.make_config(**cfg_kwargs)
    skia = gclient_cfg.solutions.add()
    skia.name = 'skia'
    skia.managed = False
    skia.url = global_constants.SKIA_REPO
    skia.revision = self.m.properties.get('revision') or 'origin/master'
    self.update_repo(self.checkout_root, skia)

    # TODO(rmistry): Remove the below block after there is a solution for
    #                crbug.com/616443
    entries_file = self.checkout_root.join('.gclient_entries')
    if self.m.path.exists(entries_file):
      self.m.file.remove('remove %s' % entries_file,
                         entries_file,
                         infra_step=True)  # pragma: no cover

    if self._need_chromium_checkout:
      chromium = gclient_cfg.solutions.add()
      chromium.name = 'src'
      chromium.managed = False
      chromium.url = 'https://chromium.googlesource.com/chromium/src.git'
      chromium.revision = 'origin/lkgr'
      self.update_repo(self.checkout_root, chromium)

    if self._need_pdfium_checkout:
      pdfium = gclient_cfg.solutions.add()
      pdfium.name = 'pdfium'
      pdfium.managed = False
      pdfium.url = 'https://pdfium.googlesource.com/pdfium.git'
      pdfium.revision = 'origin/master'
      self.update_repo(self.checkout_root, pdfium)

    # Run 'gclient sync'.
    gclient_cfg.got_revision_mapping['skia'] = 'got_revision'
    gclient_cfg.target_os.add('llvm')
    checkout_kwargs = {}
    if self.running_in_swarming:
      checkout_kwargs['env'] = self.default_env
    update_step = self.m.gclient.checkout(gclient_config=gclient_cfg,
                                          cwd=self.checkout_root,
                                          **checkout_kwargs)

    self.got_revision = update_step.presentation.properties['got_revision']
    self.m.tryserver.maybe_apply_issue()

    if self._need_chromium_checkout:
      self.m.gclient.runhooks(cwd=self.checkout_root)

  def copy_build_products(self, src, dst):
    """Copy whitelisted build products from src to dst."""
    self.m.python.inline(
        name='copy build products',
        program='''import errno
import glob
import os
import shutil
import sys

src = sys.argv[1]
dst = sys.argv[2]
build_products_whitelist = %s

try:
  os.makedirs(dst)
except OSError as e:
  if e.errno != errno.EEXIST:
    raise

for pattern in build_products_whitelist:
  path = os.path.join(src, pattern)
  for f in glob.glob(path):
    dst_path = os.path.join(dst, os.path.relpath(f, src))
    if not os.path.isdir(os.path.dirname(dst_path)):
      os.makedirs(os.path.dirname(dst_path))
    print 'Copying build product %%s to %%s' %% (f, dst_path)
    shutil.move(f, dst_path)
''' % str(BUILD_PRODUCTS_ISOLATE_WHITELIST),
        args=[src, dst],
        infra_step=True)

  def compile_steps(self, clobber=False):
    """Run the steps to build Skia."""
    try:
      for target in self.build_targets:
        self.flavor.compile(target)
      if self.running_in_swarming:
        self.copy_build_products(
            self.flavor.out_dir,
            self.swarming_out_dir.join('out', self.configuration))
        self.flavor.copy_extra_build_products(self.swarming_out_dir)
    finally:
      if 'Win' in self.builder_cfg.get('os', ''):
        self.m.python.inline(
            name='cleanup',
            program='''import psutil
for p in psutil.process_iter():
  try:
    if p.name in ('mspdbsrv.exe', 'vctip.exe', 'cl.exe', 'link.exe'):
      p.kill()
  except psutil._error.AccessDenied:
    pass
''',
            infra_step=True)

  def _readfile(self, filename, *args, **kwargs):
    """Convenience function for reading files."""
    name = kwargs.pop('name') or 'read %s' % self.m.path.basename(filename)
    return self.m.file.read(name, filename, infra_step=True, *args, **kwargs)

  def _writefile(self, filename, contents):
    """Convenience function for writing files."""
    return self.m.file.write('write %s' % self.m.path.basename(filename),
                             filename, contents, infra_step=True)

  def rmtree(self, path, running_in_swarming):
    """Wrapper around api.file.rmtree with environment fix."""
    env = {}
    if running_in_swarming:
      env['PYTHONPATH'] = str(self.m.path.join('build', 'scripts'))
    self.m.file.rmtree(self.m.path.basename(path),
                       path,
                       env=env,
                       infra_step=True)

  def run(self, steptype, name, abort_on_failure=True,
          fail_build_on_failure=True, env=None, **kwargs):
    """Run a step. If it fails, keep going but mark the build status failed."""
    env = dict(env or {})
    env.update(self.default_env)
    try:
      return steptype(name=name, env=env, **kwargs)
    except self.m.step.StepFailure as e:
      if abort_on_failure:
        raise  # pragma: no cover
      if fail_build_on_failure:
        self.failed.append(e)

  def download_dir(self, version_file, gs_path_tmpl, tmp_dir, host_path,
                   test_expected_version, test_actual_version,
                   running_in_swarming):
    """Download the given directory from Google Storage if necessary.

    Return the downloaded version.
    """
    actual_version_file = self.m.path.join(tmp_dir, version_file)
    # If we're running as a Swarming task, we should've received the test inputs
    # via the isolate server. Only download if we're not running in Swarming.
    if not running_in_swarming:
      # Ensure that the tmp_dir exists.
      self._run_once(self.m.file.makedirs,
                     'tmp_dir',
                     tmp_dir,
                     infra_step=True)

    # Find the actually-downloaded version.
    try:
      actual_version = self._readfile(actual_version_file,
                                      name='Get downloaded %s' % version_file,
                                      test_data=test_actual_version).rstrip()
    except self.m.step.StepFailure:
      if running_in_swarming:
        raise  # pragma: no cover
      actual_version = VERSION_NONE

    if not running_in_swarming:
      # Find the expected version and download if needed.
      expected_version_file = self.m.path['checkout'].join(version_file)
      expected_version = self._readfile(
          expected_version_file,
          name='Get expected %s' % version_file,
          test_data=test_expected_version).rstrip()

      # If we don't have the desired version, download it.
      if actual_version != expected_version:
        if actual_version != VERSION_NONE:
          self.m.file.remove('remove actual %s' % version_file,
                             actual_version_file,
                             infra_step=True)

        self.rmtree(host_path, running_in_swarming)
        self.m.file.makedirs(self.m.path.basename(host_path), host_path,
                             infra_step=True)
        self.m.gsutil.download(
            global_constants.GS_GM_BUCKET,
            (gs_path_tmpl % expected_version) + '/*',
            host_path,
            name='download %s' % self.m.path.basename(host_path),
            args=['-R'],
            env=self.gsutil_env(BOTO_CHROMIUM_SKIA_GM))
        self._writefile(actual_version_file, expected_version)
        actual_version = expected_version
    return actual_version

  def copy_dir(self, host_version, version_file, tmp_dir,
               host_path, device_path, test_expected_version,
               test_actual_version):
    actual_version_file = self.m.path.join(tmp_dir, version_file)
    # Copy to device.
    device_version_file = self.flavor.device_path_join(
        self.device_dirs.tmp_dir, version_file)
    if str(actual_version_file) != str(device_version_file):
      try:
        device_version = self.flavor.read_file_on_device(device_version_file)
      except self.m.step.StepFailure:
        device_version = VERSION_NONE
      if device_version != host_version:
        self.flavor.remove_file_on_device(device_version_file)
        self.flavor.create_clean_device_dir(device_path)
        self.flavor.copy_directory_contents_to_device(host_path, device_path)

        # Copy the new version file.
        self.flavor.copy_file_to_device(actual_version_file,
                                        device_version_file)

  def download_images(self, tmp_dir, local_images_dir, running_in_swarming):
    """Download test images if needed."""
    return self.download_dir(
        VERSION_FILE_SK_IMAGE,
        GS_SUBDIR_TMPL_SK_IMAGE,
        tmp_dir,
        local_images_dir,
        test_expected_version=TEST_EXPECTED_SK_IMAGE_VERSION,
        test_actual_version=self.m.properties.get(
            'test_downloaded_sk_image_version',
            TEST_EXPECTED_SK_IMAGE_VERSION),
        running_in_swarming=running_in_swarming)

  def _download_and_copy_images(self):
    """Download and copy test images if needed."""
    version = self.download_images(self.tmp_dir, self.images_dir, self.running_in_swarming)
    self.copy_dir(
        version,
        VERSION_FILE_SK_IMAGE,
        self.tmp_dir,
        self.images_dir,
        self.device_dirs.images_dir,
        test_expected_version=TEST_EXPECTED_SK_IMAGE_VERSION,
        test_actual_version=self.m.properties.get(
            'test_downloaded_sk_image_version',
            TEST_EXPECTED_SK_IMAGE_VERSION))
    return version

  def download_skps(self, tmp_dir, local_skp_dir, running_in_swarming):
    """Download SKPs if needed."""
    return self.download_dir(
        VERSION_FILE_SKP,
        GS_SUBDIR_TMPL_SKP,
        tmp_dir,
        local_skp_dir,
        test_expected_version=TEST_EXPECTED_SKP_VERSION,
        test_actual_version=self.m.properties.get(
            'test_downloaded_skp_version', TEST_EXPECTED_SKP_VERSION),
        running_in_swarming=running_in_swarming)

  def _download_and_copy_skps(self):
    """Download and copy the SKPs if needed."""
    version = self.download_skps(self.tmp_dir, self.local_skp_dir, self.running_in_swarming)
    self.copy_dir(
        version,
        VERSION_FILE_SKP,
        self.tmp_dir,
        self.local_skp_dir,
        self.device_dirs.skp_dir,
        test_expected_version=TEST_EXPECTED_SKP_VERSION,
        test_actual_version=self.m.properties.get(
            'test_downloaded_skp_version', TEST_EXPECTED_SKP_VERSION))
    return version

  def install(self):
    """Copy the required executables and files to the device."""
    self.device_dirs = self.flavor.get_device_dirs()

    # Run any device-specific installation.
    self.flavor.install()

    # TODO(borenet): Only copy files which have changed.
    # Resources
    self.flavor.copy_directory_contents_to_device(self.resource_dir,
                                                  self.device_dirs.resource_dir)

  def ccache(self):
    if not self._checked_for_ccache:
      self._checked_for_ccache = True
      if not 'Win' in self.m.properties['buildername']:
        result = self.run(
            self.m.python.inline,
            name='has ccache?',
            program='''import json
import subprocess
import sys

ccache = None
try:
  ccache = subprocess.check_output(['which', 'ccache']).rstrip()
except:
  pass
print json.dumps({'ccache': ccache})
''',
            stdout=self.m.json.output(),
            infra_step=True,
            abort_on_failure=False,
            fail_build_on_failure=False)
        if result and result.stdout and result.stdout.get('ccache'):
          self._ccache = result.stdout['ccache']

    return self._ccache

  def json_from_file(self, filename, cwd, builder_name, test_data):
    """Execute the given script to obtain JSON data."""
    return self.m.python(
        'exec %s' % self.m.path.basename(filename),
        filename,
        args=[self.m.json.output(), builder_name],
        step_test_data=lambda: self.m.json.test_api.output(test_data),
        cwd=cwd,
        infra_step=True).json.output

  def test_steps(self):
    """Run the DM test."""
    self._run_once(self.install)
    self._run_once(self._download_and_copy_skps)
    skimage_version = self._run_once(self._download_and_copy_images)

    use_hash_file = False
    if self.upload_dm_results:
      # This must run before we write anything into self.device_dirs.dm_dir
      # or we may end up deleting our output on machines where they're the same.
      self.flavor.create_clean_host_dir(self.dm_dir)
      if str(self.dm_dir) != str(self.device_dirs.dm_dir):
        self.flavor.create_clean_device_dir(self.device_dirs.dm_dir)

      # Obtain the list of already-generated hashes.
      hash_filename = 'uninteresting_hashes.txt'

      # Ensure that the tmp_dir exists.
      self._run_once(self.m.file.makedirs,
                     'tmp_dir',
                     self.tmp_dir,
                     infra_step=True)

      host_hashes_file = self.tmp_dir.join(hash_filename)
      hashes_file = self.flavor.device_path_join(
          self.device_dirs.tmp_dir, hash_filename)
      self.run(
          self.m.python.inline,
          'get uninteresting hashes',
          program="""
          import contextlib
          import math
          import socket
          import sys
          import time
          import urllib2

          HASHES_URL = 'https://gold.skia.org/_/hashes'
          RETRIES = 5
          TIMEOUT = 60
          WAIT_BASE = 15

          socket.setdefaulttimeout(TIMEOUT)
          for retry in range(RETRIES):
            try:
              with contextlib.closing(
                  urllib2.urlopen(HASHES_URL, timeout=TIMEOUT)) as w:
                hashes = w.read()
                with open(sys.argv[1], 'w') as f:
                  f.write(hashes)
                  break
            except Exception as e:
              print 'Failed to get uninteresting hashes from %s:' % HASHES_URL
              print e
              if retry == RETRIES:
                raise
              waittime = WAIT_BASE * math.pow(2, retry)
              print 'Retry in %d seconds.' % waittime
              time.sleep(waittime)
          """,
          args=[host_hashes_file],
          cwd=self.skia_dir,
          abort_on_failure=False,
          fail_build_on_failure=False,
          infra_step=True)

      if self.m.path.exists(host_hashes_file):
        self.flavor.copy_file_to_device(host_hashes_file, hashes_file)
        use_hash_file = True

    # Run DM.
    properties = [
      'gitHash',      self.got_revision,
      'master',       self.master_name,
      'builder',      self.builder_name,
      'build_number', self.m.properties['buildnumber'],
    ]
    if self.is_trybot:
      properties.extend([
        'issue',    self.m.properties['issue'],
        'patchset', self.m.properties['patchset'],
      ])

    args = [
      'dm',
      '--undefok',   # This helps branches that may not know new flags.
      '--resourcePath', self.device_dirs.resource_dir,
      '--skps', self.device_dirs.skp_dir,
      '--images', self.flavor.device_path_join(
          self.device_dirs.images_dir, 'dm'),
      '--nameByHash',
      '--properties'
    ] + properties

    if int(skimage_version) >= MIN_COLORSPACE_SKIMAGE_VERSION:
      args .extend(['--colorImages',
                    self.flavor.device_path_join(self.device_dirs.images_dir,
                                                 'colorspace')])

    args.append('--key')
    args.extend(self._KeyParams())
    if use_hash_file:
      args.extend(['--uninterestingHashesFile', hashes_file])
    if self.upload_dm_results:
      args.extend(['--writePath', self.device_dirs.dm_dir])

    skip_flag = None
    if self.builder_cfg.get('cpu_or_gpu') == 'CPU':
      skip_flag = '--nogpu'
    elif self.builder_cfg.get('cpu_or_gpu') == 'GPU':
      skip_flag = '--nocpu'
    if skip_flag:
      args.append(skip_flag)
    args.extend(self.dm_flags)

    self.run(self.flavor.step, 'dm', cmd=args, abort_on_failure=False,
             env=self.default_env)

    if self.upload_dm_results:
      # Copy images and JSON to host machine if needed.
      self.flavor.copy_directory_contents_to_host(self.device_dirs.dm_dir,
                                                  self.dm_dir)

      if self.running_in_swarming:
        # If we're running in Swarming, we wrote the output to the swarm out dir
        # so we don't need to upload.
        return

      # Upload them to Google Storage.
      self.run(
          self.m.python,
          'Upload DM Results',
          script=self.resource('upload_dm_results.py'),
          args=[
              self.dm_dir,
              self.got_revision,
              self.builder_name,
              self.m.properties['buildnumber'],
              self.m.properties['issue'] if self.is_trybot else '',
              self.skia_dir.join('common', 'py', 'utils'),
          ],
          cwd=self.m.path['checkout'],
          env=self.gsutil_env_chromium_skia_gm,
          abort_on_failure=False,
          infra_step=True)

    # See skia:2789.
    if ('Valgrind' in self.builder_name and
        self.builder_cfg.get('cpu_or_gpu') == 'GPU'):
      abandonGpuContext = list(args)
      abandonGpuContext.append('--abandonGpuContext')
      self.run(self.flavor.step, 'dm --abandonGpuContext',
               cmd=abandonGpuContext, abort_on_failure=False)
      preAbandonGpuContext = list(args)
      preAbandonGpuContext.append('--preAbandonGpuContext')
      self.run(self.flavor.step, 'dm --preAbandonGpuContext',
               cmd=preAbandonGpuContext, abort_on_failure=False,
               env=self.default_env)

  def perf_steps(self):
    """Run Skia benchmarks."""
    self._run_once(self.install)
    self._run_once(self._download_and_copy_skps)
    self._run_once(self._download_and_copy_images)

    if self.upload_perf_results:
      self.flavor.create_clean_device_dir(self.device_dirs.perf_data_dir)

    # Run nanobench.
    properties = [
      '--properties',
      'gitHash',      self.got_revision,
      'build_number', self.m.properties['buildnumber'],
    ]
    if self.is_trybot:
      properties.extend([
        'issue',    self.m.properties['issue'],
        'patchset', self.m.properties['patchset'],
      ])

    target = 'nanobench'
    if 'VisualBench' in self.builder_name:
      target = 'visualbench'
    args = [
        target,
        '--undefok',   # This helps branches that may not know new flags.
        '-i',       self.device_dirs.resource_dir,
        '--skps',   self.device_dirs.skp_dir,
        '--images', self.flavor.device_path_join(
            self.device_dirs.images_dir, 'nanobench'),
    ]

    skip_flag = None
    if self.builder_cfg.get('cpu_or_gpu') == 'CPU':
      skip_flag = '--nogpu'
    elif self.builder_cfg.get('cpu_or_gpu') == 'GPU':
      skip_flag = '--nocpu'
    if skip_flag:
      args.append(skip_flag)
    args.extend(self.nanobench_flags)

    if self.upload_perf_results:
      if self.running_in_swarming:
        json_path = self.flavor.device_path_join(
            self.device_dirs.perf_data_dir,
            'nanobench_%s.json' % self.got_revision)
      else:  # pragma: nocover
        git_timestamp = self.m.git.get_timestamp(test_data='1408633190',
                                                 infra_step=True)
        json_path = self.flavor.device_path_join(
            self.device_dirs.perf_data_dir,
            'nanobench_%s_%s.json' % (self.got_revision, git_timestamp))
      args.extend(['--outResultsFile', json_path])
      args.extend(properties)

      keys_blacklist = ['configuration', 'role', 'is_trybot']
      args.append('--key')
      for k in sorted(self.builder_cfg.keys()):
        if not k in keys_blacklist:
          args.extend([k, self.builder_cfg[k]])

    self.run(self.flavor.step, target, cmd=args, abort_on_failure=False,
             env=self.default_env)

    # See skia:2789.
    if ('Valgrind' in self.builder_name and
        self.builder_cfg.get('cpu_or_gpu') == 'GPU'):
      abandonGpuContext = list(args)
      abandonGpuContext.extend(['--abandonGpuContext', '--nocpu'])
      self.run(self.flavor.step, '%s --abandonGpuContext' % target,
               cmd=abandonGpuContext, abort_on_failure=False,
               env=self.default_env)

    # Upload results.
    if self.upload_perf_results:
      self.m.file.makedirs('perf_dir', self.perf_data_dir)
      self.flavor.copy_directory_contents_to_host(
          self.device_dirs.perf_data_dir, self.perf_data_dir)

      # If we're running in Swarming, we wrote the results into the Swarming
      # out dir, so we don't need to upload.
      if not self.running_in_swarming:  # pragma: nocover
        gsutil_path = self.m.path['depot_tools'].join(
            'third_party', 'gsutil', 'gsutil')
        upload_args = [self.builder_name, self.m.properties['buildnumber'],
                       self.perf_data_dir, self.got_revision, gsutil_path]
        if self.is_trybot:
          upload_args.append(self.m.properties['issue'])
        self.run(self.m.python,
                 'Upload %s Results' % target,
                 script=self.resource('upload_bench_results.py'),
                 args=upload_args,
                 cwd=self.m.path['checkout'],
                 env=self.gsutil_env_chromium_skia_gm,
                 abort_on_failure=False,
                 infra_step=True)

  def cleanup_steps(self):
    """Run any cleanup steps."""
    self.flavor.cleanup_steps()

  def _KeyParams(self):
    """Build a unique key from the builder name (as a list).

    E.g.  arch x86 gpu GeForce320M mode MacMini4.1 os Mac10.6
    """
    # Don't bother to include role, which is always Test.
    # TryBots are uploaded elsewhere so they can use the same key.
    blacklist = ['role', 'is_trybot']

    flat = []
    for k in sorted(self.builder_cfg.keys()):
      if k not in blacklist:
        flat.append(k)
        flat.append(self.builder_cfg[k])
    return flat
