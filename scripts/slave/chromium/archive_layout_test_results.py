#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to archive layout test results.

To archive files on Google Storage, pass a GS bucket name via --gs-bucket.
To control access to archives, pass a value for --gs-acl (e.g. 'public-read',
see https://developers.google.com/storage/docs/accesscontrol#extension
for other supported canned-acl values). If no gs_acl key is given,
then the bucket's default object ACL will be applied (see
https://developers.google.com/storage/docs/accesscontrol#defaultobjects).

When this is run, the current directory (cwd) should be the outer build
directory (e.g., chrome-release/build/).

For a list of command-line options, call this script with '--help'.
"""

import logging
import argparse
import os
import re
import socket
import sys

from common import archive_utils
from common import chromium_utils
from slave import build_directory
from slave import slave_utils


def _CollectZipArchiveFiles(output_dir):
  """Returns a list of layout test result files to archive in a zip file."""
  file_list = []

  for path, _, files in os.walk(output_dir):
    rel_path = path[len(output_dir + '\\'):]
    for name in files:
      if _IsIncludedInZipArchive(name):
        file_list.append(os.path.join(rel_path, name))

  if os.path.exists(os.path.join(output_dir, 'results.html')):
    file_list.append('results.html')

  if sys.platform == 'win32':
    if os.path.exists(os.path.join(output_dir, 'access_log.txt')):
      file_list.append('access_log.txt')
    if os.path.exists(os.path.join(output_dir, 'error_log.txt')):
      file_list.append('error_log.txt')

  return file_list


def _IsIncludedInZipArchive(name):
  """Returns True if a file should be included in the zip, False otherwise."""
  if '-stack.' in name or '-crash-log.' in name:
    return True
  extension = os.path.splitext(name)[1]
  if '-actual.' in name and extension in ('.txt', '.png', '.checksum', '.wav'):
    return True
  if '-expected.' in name:
    return True
  if '-wdiff.' in name:
    return True
  if name.endswith('-diff.txt') or name.endswith('-diff.png'):
    return True
  if name.endswith('.json'):
    return True
  return False


def archive_layout(args):
  chrome_dir = os.path.abspath(args.build_dir)
  results_dir_basename = os.path.basename(args.results_dir)
  args.results_dir = os.path.abspath(args.results_dir)
  print 'Archiving results from %s' % args.results_dir
  staging_dir = args.staging_dir or slave_utils.GetStagingDir(chrome_dir)
  print 'Staging in %s' % staging_dir
  if not os.path.exists(staging_dir):
    os.makedirs(staging_dir)

  file_list = _CollectZipArchiveFiles(args.results_dir)
  zip_file = chromium_utils.MakeZip(staging_dir,
                                    results_dir_basename,
                                    file_list,
                                    args.results_dir)[1]

  wc_dir = os.path.dirname(chrome_dir)
  last_change = slave_utils.GetHashOrRevision(wc_dir)

  builder_name = re.sub('[ .()]', '_', args.builder_name)
  build_number = str(args.build_number)

  print 'last change: %s' % last_change
  print 'build name: %s' % builder_name
  print 'build number: %s' % build_number
  print 'host name: %s' % socket.gethostname()

  # Create a file containing last_change revision. This file will be uploaded
  # after all layout test results are uploaded so the client can check this
  # file to see if the upload for the revision is complete.
  # See crbug.com/574272 for more details.
  last_change_file = os.path.join(staging_dir, 'LAST_CHANGE')
  with open(last_change_file, 'w') as f:
    f.write(last_change)

  # Copy the results to a directory archived by build number.
  gs_base = '/'.join([args.gs_bucket, builder_name, build_number])
  gs_acl = args.gs_acl
  # These files never change, cache for a year.
  cache_control = "public, max-age=31556926"
  slave_utils.GSUtilCopyFile(zip_file, gs_base, gs_acl=gs_acl,
                             cache_control=cache_control,
                             add_quiet_flag=True)
  slave_utils.GSUtilCopyDir(args.results_dir, gs_base, gs_acl=gs_acl,
                            cache_control=cache_control,
                            add_quiet_flag=True)
  slave_utils.GSUtilCopyFile(last_change_file,
                             gs_base + '/' + results_dir_basename,
                             gs_acl=gs_acl,
                             cache_control=cache_control,
                             add_quiet_flag=True)

  # And also to the 'results' directory to provide the 'latest' results
  # and make sure they are not cached at all (Cloud Storage defaults to
  # caching w/ a max-age=3600).
  gs_base = '/'.join([args.gs_bucket, builder_name, 'results'])
  cache_control = 'no-cache'
  slave_utils.GSUtilCopyFile(zip_file, gs_base, gs_acl=gs_acl,
                             cache_control=cache_control,
                             add_quiet_flag=True)
  slave_utils.GSUtilCopyDir(args.results_dir, gs_base, gs_acl=gs_acl,
                            cache_control=cache_control,
                            add_quiet_flag=True)
  slave_utils.GSUtilCopyFile(last_change_file,
                             gs_base + '/' + results_dir_basename,
                             gs_acl=gs_acl,
                             cache_control=cache_control,
                             add_quiet_flag=True)
  return 0


def _ParseArgs():
  parser = argparse.ArgumentParser()
  # TODO(crbug.com/655798): Make --build-dir not ignored.
  parser.add_argument('--build-dir', help='ignored')
  parser.add_argument('--results-dir', required=True,
                      help='path to layout test results')
  parser.add_argument('--builder-name', required=True,
                      help='The name of the builder running this script.')
  parser.add_argument('--build-number', type=int, required=True,
                      help='Build number of the builder running this script.')
  parser.add_argument('--gs-bucket', required=True,
                      help='The Google Storage bucket to upload to.')
  parser.add_argument('--gs-acl',
                      help='The access policy for Google Storage files.')
  parser.add_argument('--staging-dir',
                      help='Directory to use for staging the archives. '
                           'Default behavior is to automatically detect '
                           'slave\'s build directory.')
  slave_utils_callback = slave_utils.AddArgs(parser)

  args = parser.parse_args()
  args.build_dir = build_directory.GetBuildOutputDirectory()
  slave_utils_callback(args)
  return args


def main():
  args = _ParseArgs()
  logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')
  return archive_layout(args)


if '__main__' == __name__:
  sys.exit(main())
