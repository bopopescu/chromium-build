#!/usr/bin/env python
# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""upload goma related logs."""

import argparse
import os
import sys

from slave import goma_utils


def main():
  parser = argparse.ArgumentParser(description='Upload goma related logs')
  parser.add_argument('--upload-compiler-proxy-info',
                      action='store_true',
                      help='If set, the script will upload the latest '
                      'compiler_proxy.INFO.')
  parser.add_argument('--ninja-log-outdir',
                      metavar='DIR',
                      help='Directory that has .ninja_log file.')
  parser.add_argument('--ninja-log-compiler',
                      metavar='COMPILER',
                      help='compiler name used for the build.')
  parser.add_argument('--ninja-log-command',
                      metavar='COMMAND',
                      help='command line options of the build.')
  parser.add_argument('--ninja-log-exit-status',
                      type=int,
                      metavar='EXIT_STATUS',
                      help='ninja exit status.')
  parser.add_argument('--goma-stats-file',
                      metavar='FILENAME',
                      help='Filename of a GomaStats binary protobuf. '
                      'If empty or non-existing file, it will report error '
                      'to chrome infra monitoring system.')
  parser.add_argument('--goma-crash-report-id-file',
                      metavar='FILENAME',
                      help='Filename that has a crash report id.')
  parser.add_argument('--build-data-dir',
                      metavar='DIR',
                      help='Directory that has build data used by event_mon.')

  parser.add_argument('--json-status',
                      metavar='JSON',
                      help='path of json file generated from'
                      ' ./goma_ctl.py jsonstatus')
  parser.add_argument('--skip-sendgomatsmon', action='store_true',
                      help='Represent whether send jsonstatus'
                      ' and exit_status log to TsMon.'
                      ' This option is only allowed to used when'
                      ' start() of recipe_modules/goma failes.')

  # Arguments set to os.environ
  parser.add_argument('--buildbot-buildername',
                      help='buildbot buildername')
  parser.add_argument('--buildbot-mastername',
                      help='buildbot mastername')
  parser.add_argument('--buildbot-slavename',
                      help='buildbot slavename')
  parser.add_argument('--buildbot-clobber',
                      help='buildbot clobber')

  args = parser.parse_args()

  # TODO(tikuta): Pass these variables explicitly.
  if args.buildbot_buildername:
    os.environ['BUILDBOT_BUILDERNAME'] = args.buildbot_buildername
  if args.buildbot_mastername:
    os.environ['BUILDBOT_MASTERNAME'] = args.buildbot_mastername
  if args.buildbot_slavename:
    os.environ['BUILDBOT_SLAVENAME'] = args.buildbot_slavename
  if args.buildbot_clobber:
    os.environ['BUILDBOT_CLOBBER'] = args.buildbot_clobber

  if args.upload_compiler_proxy_info:
    goma_utils.UploadGomaCompilerProxyInfo()
  if args.ninja_log_outdir:
    goma_utils.UploadNinjaLog(args.ninja_log_outdir,
                              args.ninja_log_compiler,
                              args.ninja_log_command,
                              args.ninja_log_exit_status)
  if args.goma_stats_file:
    goma_utils.SendGomaStats(args.goma_stats_file,
                             args.goma_crash_report_id_file,
                             args.build_data_dir)

  if not args.skip_sendgomatsmon:
    # In the case of goma_start is failed,
    # we want log to investigate failed reason.
    # So, let me send some logs instead of
    # error in parse_args() using required option.
    assert args.json_status is not None and os.path.exists(args.json_status)
    assert args.ninja_log_exit_status is not None
    goma_utils.SendGomaTsMon(args.json_status, args.ninja_log_exit_status)

  return 0


if '__main__' == __name__:
  sys.exit(main())
