#!/usr/bin/python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to archive layout test results generated by buildbots.

Actual result files (*-actual.txt), but not results from simplified diff
tests (*-simp-actual.txt) or JS-filtered diff tests (*-jsfilt.txt), will
be included in the archive.

When this is run, the current directory (cwd) should be the outer build
directory (e.g., chrome-release/build/).

For a list of command-line options, call this script with '--help'.
"""

import logging
import optparse
import os
import re
import socket
import sys

from common import chromium_utils
from slave import slave_utils
import config

# Directory name, above the build directory, in which test results can be
# found if no --results-dir option is given.
RESULT_DIR = 'layout-test-results'


def _CollectArchiveFiles(output_dir):
  """Returns a tuple containing two lists list of file paths to archive,
  relative to the output_dir. The first list is all the actual results from the
  test run. The second list is the diffs from the expected results.

  Files in the output_dir or one of its subdirectories, whose names end with
  '-actual.txt' but not '-simp-actual.txt' or '-jsfilt-actual.txt',
  will be included in the list.
  """
  actual_file_list = []
  diff_file_list = []
  for path, _, files in os.walk(output_dir):
    rel_path = path[len(output_dir + '\\'):]
    for name in files:
      if ('-stack.' in name or
          '-crash-log.' in name or
          ('-actual.' in name and
           (name.endswith('.txt') or
            name.endswith('.png') or
            name.endswith('.checksum')) and
           '-simp-actual.' not in name and
           '-jsfilt-actual.' not in name)):
        actual_file_list.append(os.path.join(rel_path, name))
      elif ('-wdiff.' in name or
            '-expected.' in name or
            name.endswith('-diff.txt') or
            name.endswith('-diff.png')):
        diff_file_list.append(os.path.join(rel_path, name))
      elif name.endswith('.json'):
        actual_file_list.append(os.path.join(rel_path, name))
  if os.path.exists(os.path.join(output_dir, 'results.html')):
    actual_file_list.append('results.html')
  return (actual_file_list, diff_file_list)


def _ArchiveFullLayoutTestResults(staging_dir, dest_dir, diff_file_list,
    options):
  # Copy the actual and diff files to the web server.
  # Don't clobber the staging_dir in the MakeZip call so that it keeps the
  # files from the previous MakeZip call on diff_file_list.
  print "archiving results + diffs"
  full_zip_file = chromium_utils.MakeZip(staging_dir,
      'layout-test-results', diff_file_list, options.results_dir,
      remove_archive_directory=False)[1]
  slave_utils.CopyFileToArchiveHost(full_zip_file, dest_dir)

  # Extract the files on the web server.
  extract_dir = os.path.join(dest_dir, 'results')
  print 'extracting zip file to %s' % extract_dir

  if chromium_utils.IsWindows():
    chromium_utils.ExtractZip(full_zip_file, extract_dir)
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    remote_zip_file = os.path.join(dest_dir, os.path.basename(full_zip_file))
    chromium_utils.SshExtractZip(config.Archive.archive_host, remote_zip_file,
                                 extract_dir)


def archive_layout(options, args):
  logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')
  chrome_dir = os.path.abspath(options.build_dir)
  results_dir_basename = os.path.basename(options.results_dir)
  if options.results_dir is not None:
    options.results_dir = os.path.abspath(os.path.join(options.build_dir,
                                                       options.results_dir))
  else:
    options.results_dir = chromium_utils.FindUpward(chrome_dir, RESULT_DIR)
  print 'Archiving results from %s' % options.results_dir
  staging_dir = slave_utils.GetStagingDir(chrome_dir)
  print 'Staging in %s' % staging_dir

  (actual_file_list, diff_file_list) = _CollectArchiveFiles(options.results_dir)
  zip_file = chromium_utils.MakeZip(staging_dir,
                                    results_dir_basename,
                                    actual_file_list,
                                    options.results_dir)[1]

  # Extract the build name of this slave (e.g., 'chrome-release') from its
  # configuration file if not provided as a param.
  build_name = options.builder_name or slave_utils.SlaveBuildName(chrome_dir)
  build_name = re.sub('[ .()]', '_', build_name)

  last_change = str(slave_utils.SubversionRevision(chrome_dir))
  print 'last change: %s' % last_change
  print 'build name: %s' % build_name
  print 'host name: %s' % socket.gethostname()

  # Where to save layout test results.
  dest_parent_dir = os.path.join(config.Archive.www_dir_base,
      results_dir_basename.replace('-','_'), build_name)
  dest_dir = os.path.join(dest_parent_dir, last_change)
  
  gs_bucket = options.factory_properties.get('gs_bucket', None)
  if gs_bucket:
    gs_base = '/'.join([gs_bucket, build_name, last_change])
    slave_utils.GSUtilCopyFile(zip_file, gs_base)
  else:
    slave_utils.MaybeMakeDirectoryOnArchiveHost(dest_dir)
    slave_utils.CopyFileToArchiveHost(zip_file, dest_dir)
    # Not supported on Google Storage yet.
    _ArchiveFullLayoutTestResults(staging_dir, dest_parent_dir, diff_file_list,
                                  options)
  return 0


def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--build-dir', default='webkit',
                           help='path to main build directory (the parent of '
                                'the Release or Debug directory)')
  option_parser.add_option('', '--results-dir',
                           help='path to layout test results, relative to '
                                'the build_dir')
  option_parser.add_option('', '--builder-name',
                           default=None,
                           help='The name of the builder running this script.')
  option_parser.add_option('', '--build-number',
                           default=None,
                           help=('The build number of the builder running'
                                 'this script.'))
  option_parser.add_option('--build-properties', action='callback',
                           callback=chromium_utils.convert_json, type='string',
                           nargs=1, default={},
                           help='build properties in JSON format')
  option_parser.add_option('--factory-properties', action='callback',
                           callback=chromium_utils.convert_json, type='string',
                           nargs=1, default={},
                           help='factory properties in JSON format')
  options, args = option_parser.parse_args()
  return archive_layout(options, args)


if '__main__' == __name__:
  sys.exit(main())
