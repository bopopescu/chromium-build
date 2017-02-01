#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import copy
import json
import logging
import os
import subprocess
import sys
import tempfile


# Install Infra build environment.
BUILD_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
                             os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BUILD_ROOT, 'scripts'))

from common import annotator
from common import chromium_utils
from common import env
from slave import cipd
from slave import logdog_bootstrap
from slave import monitoring_utils
from slave import robust_tempdir
from slave import update_scripts


LOGGER = logging.getLogger('remote_run')


# CIPD_PINS is a mapping of master name to pinned recipe engine CIPD package
# version. If no pin is found, the CIPD pin for "None" will be used.
_CIPD_PINS = {
  # None is the default CIPD pin, and is used if nothing else matches. It MUST
  # be defined.
  None: 'latest',
}

def _get_cipd_pin(mastername):
  return _CIPD_PINS.get(mastername, _CIPD_PINS[None])

# ENGINE_FLAGS is a mapping of master name to a engine flags. This can be used
# to test new recipe engine flags on a select few masters.
_ENGINE_FLAGS = {
  # None is the default set of engine flags, and is used if nothing else
  # matches. It MUST be defined.
  None: {
    'engine_flags': {
      'use_result_proto': True,
    }
  },

  'chromium.fyi': {
    'engine_flags': {
      'use_result_proto': True,
    }
  },
  'tryserver.chromium.linux': {
    'engine_flags': {
      'use_result_proto': True,
    }
  },
}

def _get_engine_flags(mastername):
  return  _ENGINE_FLAGS.get(mastername, _ENGINE_FLAGS[None])


def _call(cmd, **kwargs):
  LOGGER.info('Executing command: %s', cmd)
  exit_code = subprocess.call(cmd, **kwargs)
  LOGGER.info('Command %s finished with exit code %d.', cmd, exit_code)
  return exit_code


def _install_cipd_packages(path, *packages):
  """Bootstraps CIPD in |path| and installs requested |packages|.

  Args:
    path (str): The CIPD installation root.
    packages (list of CipdPackage): The set of CIPD packages to install.
  """
  cmd = [
      sys.executable,
      os.path.join(env.Build, 'scripts', 'slave', 'cipd.py'),
      '--dest-directory', path,
      '-vv' if logging.getLogger().level == logging.DEBUG else '-v',
  ]
  for p in packages:
    cmd += ['-P', '%s@%s' % (p.name, p.version)]

  exit_code = _call(cmd)
  if exit_code != 0:
    raise Exception('Failed to install CIPD packages.')


def main(argv, stream):
  parser = argparse.ArgumentParser()
  parser.add_argument('--repository', required=True,
      help='URL of a git repository to fetch.')
  parser.add_argument('--revision',
      help='Git commit hash to check out.')
  parser.add_argument('--recipe', required=True,
      help='Name of the recipe to run')
  parser.add_argument('--build-properties-gz', dest='build_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='Build properties in b64 gz JSON format')
  parser.add_argument('--factory-properties-gz', dest='factory_properties',
      type=chromium_utils.convert_gz_json_type, default={},
      help='factory properties in b64 gz JSON format')
  parser.add_argument('--leak', action='store_true',
      help='Refrain from cleaning up generated artifacts.')
  parser.add_argument('--verbose', action='store_true')
  parser.add_argument(
      '--use-gitiles', action='store_true',
      help='Use Gitiles-specific way to fetch repo (faster for large repos)')

  group = parser.add_argument_group('LogDog Bootstrap')
  logdog_bootstrap.add_arguments(group)

  args = parser.parse_args(argv[1:])

  with robust_tempdir.RobustTempdir(
      prefix='rr', leak=args.leak) as rt:
    try:
      basedir = chromium_utils.FindUpward(os.getcwd(), 'b')
    except chromium_utils.PathNotFound as e:
      LOGGER.warn(e)
      # Use base directory inside system temporary directory - if we use slave
      # one (cwd), the paths get too long. Recipes which need different paths
      # or persistent directories should do so explicitly.
      basedir = tempfile.gettempdir()

    # Explicitly clean up possibly leaked temporary directories
    # from previous runs.
    rt.cleanup(basedir)

    tempdir = rt.tempdir(basedir)
    LOGGER.info('Using temporary directory: [%s].', tempdir)

    build_data_dir = rt.tempdir(basedir)
    LOGGER.info('Using build data directory: [%s].', build_data_dir)

    properties = copy.copy(args.factory_properties)
    properties.update(args.build_properties)
    properties['build_data_dir'] = build_data_dir
    # path_config property defines what paths a build uses for checkout, git
    # cache, goma cache, etc.
    # Unless it is explicitly specified by a builder, use paths for buildbot
    # environment.
    properties['path_config'] = properties.get('path_config', 'buildbot')
    LOGGER.info('Using properties: %r', properties)
    properties_file = os.path.join(tempdir, 'remote_run_properties.json')
    with open(properties_file, 'w') as f:
      json.dump(properties, f)

    monitoring_utils.write_build_monitoring_event(build_data_dir, properties)

    # Make switching to remote_run easier: we do not use buildbot workdir,
    # and it takes disk space leading to out of disk errors.
    buildbot_workdir = properties.get('workdir')
    if buildbot_workdir:
      try:
        if os.path.exists(buildbot_workdir):
          buildbot_workdir = os.path.realpath(buildbot_workdir)
          cwd = os.path.realpath(os.getcwd())
          if cwd.startswith(buildbot_workdir):
            buildbot_workdir = cwd

          LOGGER.info('Cleaning up buildbot workdir %r', buildbot_workdir)

          # Buildbot workdir is usually used as current working directory,
          # so do not remove it, but delete all of the contents. Deleting
          # current working directory of a running process may cause
          # confusing errors.
          for p in (os.path.join(buildbot_workdir, x)
                    for x in os.listdir(buildbot_workdir)):
            LOGGER.info('Deleting %r', p)
            chromium_utils.RemovePath(p)
      except Exception as e:
        # It's preferred that we keep going rather than fail the build
        # on optional cleanup.
        LOGGER.exception('Buildbot workdir cleanup failed: %s', e)

    mastername = properties.get('mastername')

    cipd_pin = _get_cipd_pin(mastername)
    cipd_path = os.path.join(basedir, '.remote_run_cipd')
    _install_cipd_packages(
        cipd_path, cipd.CipdPackage('infra/recipes-py', cipd_pin))

    engine_flags = _get_engine_flags(mastername)

    engine_args = []
    if engine_flags:
      engine_flags_path = os.path.join(tempdir, 'engine_flags.json')
      with open(engine_flags_path, 'w') as f:
        json.dump(engine_flags, f)

      engine_args = ['--operational-args-path', engine_flags_path]

    recipe_result_path = os.path.join(tempdir, 'recipe_result.json')
    recipe_cmd = [
        sys.executable,
        os.path.join(cipd_path, 'recipes.py'),] + engine_args + [
        '--verbose',
        'remote',
        '--repository', args.repository,
        '--revision', args.revision,
        '--workdir', os.path.join(tempdir, 'rw'),
    ]
    if args.use_gitiles:
      recipe_cmd.append('--use-gitiles')
    recipe_cmd.extend([
        '--',] + (
        engine_args) + [
        '--verbose',
        'run',
        '--properties-file', properties_file,
        '--workdir', os.path.join(tempdir, 'w'),
        '--output-result-json', recipe_result_path,
        properties.get('recipe') or args.recipe,
    ])
    # If we bootstrap through logdog, the recipe command line gets written
    # to a temporary file and does not appear in the log.
    LOGGER.info('Recipe command line: %r', recipe_cmd)

    # Default to return code != 0 is for the benefit of buildbot, which uses
    # return code to decide if a step failed or not.
    recipe_return_code = 1
    try:
      bs = logdog_bootstrap.bootstrap(rt, args, basedir, tempdir, properties,
                                      recipe_cmd)

      LOGGER.info('Bootstrapping through LogDog: %s', bs.cmd)
      bs.annotate(stream)
      _ = _call(bs.cmd)
      recipe_return_code = bs.get_result()
    except logdog_bootstrap.NotBootstrapped as e:
      LOGGER.info('Not using LogDog. Invoking `recipes.py` directly.')
      recipe_return_code = _call(recipe_cmd)

    # Try to open recipe result JSON. Any failure will result in an exception
    # and an infra failure.
    with open(recipe_result_path) as f:
      return_value = json.load(f)

    if engine_flags.get('use_result_proto'):
      # If we failed, but aren't a step failure, we assume it was an
      # exception.
      f = return_value.get('failure')
      if f is not None and not f.get('step_failure'):
        # The recipe engine used to return -1, which got interpreted as 255
        # by os.exit in python, since process exit codes are a single byte.
        recipe_return_code = 255

    return recipe_return_code


def shell_main(argv):
  logging.basicConfig(
      level=(logging.DEBUG if '--verbose' in argv else logging.INFO))

  if update_scripts.update_scripts():
    # Re-execute with the updated remote_run.py.
    return _call([sys.executable] + argv)

  stream = annotator.StructuredAnnotationStream()
  exc_info = None
  try:
    return main(argv, stream)
  except Exception:
    exc_info = sys.exc_info()

  # Report on the "remote_run" execution. If an exception (infra failure)
  # occurred, raise it so that the build and the step turn purple.
  with stream.step('remote_run_result'):
    if exc_info is not None:
      raise exc_info[0], exc_info[1], exc_info[2]


if __name__ == '__main__':
  sys.exit(shell_main(sys.argv))
