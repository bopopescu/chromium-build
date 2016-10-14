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
import optparse
import os
import re
import socket
import sys

from common import archive_utils
from common import chromium_utils
from slave import slave_utils

# Directory name, above the build directory, in which test results can be
# found if no --results-dir option is given.
RESULT_DIR = 'layout-test-results'


def _CollectArchiveFiles(output_dir):
  """Returns a pair of lists of file paths to archive.

  The first list is all the actual results from the test run;
  the second list is the diffs from the expected results.
  """
  actual_file_list = []
  diff_file_list = []

  for path, _, files in os.walk(output_dir):
    rel_path = path[len(output_dir + '\\'):]
    for name in files:
      if _IsActualResultFile(name):
        actual_file_list.append(os.path.join(rel_path, name))
      if _IsDiffFile(name):
        diff_file_list.append(os.path.join(rel_path, name))
      elif name.endswith('.json'):
        actual_file_list.append(os.path.join(rel_path, name))

  if os.path.exists(os.path.join(output_dir, 'results.html')):
    actual_file_list.append('results.html')

  if sys.platform == 'win32':
    if os.path.exists(os.path.join(output_dir, 'access_log.txt')):
      actual_file_list.append('access_log.txt')
    if os.path.exists(os.path.join(output_dir, 'error_log.txt')):
      actual_file_list.append('error_log.txt')

  return (actual_file_list, diff_file_list)


def _IsActualResultFile(name):
  if '-stack.' in name or '-crash-log.' in name:
    return True
  extension = os.path.splitext(name)[1]
  return ('-actual.' in name and extension in
          ('.txt', '.png', '.checksum', '.wav'))


def _IsDiffFile(name):
  return ('-wdiff.' in name or
          '-expected.' in name or
          name.endswith('-diff.txt') or
          name.endswith('-diff.png'))


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
    chromium_utils.SshExtractZip(archive_utils.Config.archive_host,
                                 remote_zip_file, extract_dir)


def _CopyFileToArchiveHost(src, dest_dir):
  """A wrapper method to copy files to the archive host.

  It calls CopyFileToDir on Windows and SshCopyFiles on Linux/Mac.

  TODO: we will eventually want to change the code to upload the
  data to appengine.

  Args:
      src: full path to the src file.
      dest_dir: destination directory on the host.
  """
  host = archive_utils.Config.archive_host
  if not os.path.exists(src):
    raise chromium_utils.ExternalError('Source path "%s" does not exist' % src)
  chromium_utils.MakeWorldReadable(src)
  if chromium_utils.IsWindows():
    chromium_utils.CopyFileToDir(src, dest_dir)
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    chromium_utils.SshCopyFiles(src, host, dest_dir)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def _MaybeMakeDirectoryOnArchiveHost(dest_dir):
  """A wrapper method to create a directory on the archive host.

  It calls MaybeMakeDirectory on Windows and SshMakeDirectory on Linux/Mac.

  Args:
      dest_dir: destination directory on the host.
  """
  host = archive_utils.Config.archive_host
  if chromium_utils.IsWindows():
    chromium_utils.MaybeMakeDirectory(dest_dir)
    print 'saving results to %s' % dest_dir
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    chromium_utils.SshMakeDirectory(host, dest_dir)
    print 'saving results to "%s" on "%s"' % (dest_dir, host)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def archive_layout(options):
  chrome_dir = os.path.abspath(options.build_dir)
  results_dir_basename = os.path.basename(options.results_dir)
  if options.results_dir is not None:
    options.results_dir = os.path.abspath(os.path.join(options.build_dir,
                                                       options.results_dir))
  else:
    options.results_dir = chromium_utils.FindUpward(chrome_dir, RESULT_DIR)
  print 'Archiving results from %s' % options.results_dir
  staging_dir = options.staging_dir or slave_utils.GetStagingDir(chrome_dir)
  print 'Staging in %s' % staging_dir
  if not os.path.exists(staging_dir):
    os.makedirs(staging_dir)

  (actual_file_list, diff_file_list) = _CollectArchiveFiles(options.results_dir)
  zip_file = chromium_utils.MakeZip(staging_dir,
                                    results_dir_basename,
                                    actual_file_list,
                                    options.results_dir)[1]
  # TODO(crbug.com/655202): Stop separately uploading failing_results.json.
  full_results_json = os.path.join(options.results_dir, 'full_results.json')
  failing_results_json = os.path.join(options.results_dir,
      'failing_results.json')

  # Extract the build name of this slave (e.g., 'chrome-release') from its
  # configuration file if not provided as a param.
  build_name = options.builder_name or slave_utils.SlaveBuildName(chrome_dir)
  build_name = re.sub('[ .()]', '_', build_name)

  wc_dir = os.path.dirname(chrome_dir)
  last_change = slave_utils.GetHashOrRevision(wc_dir)

  # TODO(dpranke): Is it safe to assume build_number is not blank? Should we
  # assert() this ?
  build_number = str(options.build_number)
  print 'last change: %s' % last_change
  print 'build name: %s' % build_name
  print 'build number: %s' % build_number
  print 'host name: %s' % socket.gethostname()

  if options.gs_bucket:
    # Create a file containing last_change revision. This file will be uploaded
    # after all layout test results are uploaded so the client can check this
    # file to see if the upload for the revision is complete.
    # See crbug.com/574272 for more details.
    last_change_file = os.path.join(staging_dir, 'LAST_CHANGE')
    with open(last_change_file, 'w') as f:
      f.write(last_change)

    # Copy the results to a directory archived by build number.
    gs_base = '/'.join([options.gs_bucket, build_name, build_number])
    gs_acl = options.gs_acl
    # These files never change, cache for a year.
    cache_control = "public, max-age=31556926"
    slave_utils.GSUtilCopyFile(zip_file, gs_base, gs_acl=gs_acl,
      cache_control=cache_control)
    slave_utils.GSUtilCopyDir(options.results_dir, gs_base, gs_acl=gs_acl,
      cache_control=cache_control)

    # TODO(dpranke): Remove these two lines once clients are fetching the
    # files from the layout-test-results dir.
    slave_utils.GSUtilCopyFile(full_results_json, gs_base, gs_acl=gs_acl,
      cache_control=cache_control)
    slave_utils.GSUtilCopyFile(failing_results_json, gs_base, gs_acl=gs_acl,
      cache_control=cache_control)

    slave_utils.GSUtilCopyFile(last_change_file,
      gs_base + '/' + results_dir_basename, gs_acl=gs_acl,
      cache_control=cache_control)

    # And also to the 'results' directory to provide the 'latest' results
    # and make sure they are not cached at all (Cloud Storage defaults to
    # caching w/ a max-age=3600).
    gs_base = '/'.join([options.gs_bucket, build_name, 'results'])
    cache_control = 'no-cache'
    slave_utils.GSUtilCopyFile(zip_file, gs_base, gs_acl=gs_acl,
        cache_control=cache_control)
    slave_utils.GSUtilCopyDir(options.results_dir, gs_base, gs_acl=gs_acl,
        cache_control=cache_control)

    slave_utils.GSUtilCopyFile(last_change_file,
        gs_base + '/' + results_dir_basename, gs_acl=gs_acl,
        cache_control=cache_control)

  else:
    # Where to save layout test results.
    dest_parent_dir = os.path.join(archive_utils.Config.www_dir_base,
        results_dir_basename.replace('-', '_'), build_name)
    dest_dir = os.path.join(dest_parent_dir, last_change)

    _MaybeMakeDirectoryOnArchiveHost(dest_dir)
    _CopyFileToArchiveHost(zip_file, dest_dir)
    _CopyFileToArchiveHost(full_results_json, dest_dir)
    _CopyFileToArchiveHost(failing_results_json, dest_dir)
    # Not supported on Google Storage yet.
    _ArchiveFullLayoutTestResults(staging_dir, dest_parent_dir, diff_file_list,
                                  options)
  return 0


def _ParseOptions():
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--build-dir',
                           help='Build dir path, relative to checkout root.')
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
  option_parser.add_option('', '--gs-bucket',
                           default=None,
                           help=('The google storage bucket to upload to. '
                                 'If provided, this script will upload to gs '
                                 'instead of the master.'))
  option_parser.add_option('', '--gs-acl',
                           default=None,
                           help=('The ACL of the google storage files.'))
  option_parser.add_option('--staging-dir',
                           help='Directory to use for staging the archives. '
                                'Default behavior is to automatically detect '
                                'slave\'s build directory.')
  chromium_utils.AddPropertiesOptions(option_parser)
  options, _ = option_parser.parse_args()
  return options


def main():
  options = _ParseOptions()
  logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s %(filename)s:%(lineno)-3d'
                             ' %(levelname)s %(message)s',
                      datefmt='%y%m%d %H:%M:%S')
  return archive_layout(options)


if '__main__' == __name__:
  sys.exit(main())
