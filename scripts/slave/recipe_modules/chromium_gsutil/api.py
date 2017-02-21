# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class ChromiumGSUtilApi(recipe_api.RecipeApi):
  def download_with_polling(self, url, destination, poll_interval, timeout,
                            name='Download GS file with polling'):
    """Returns a step that downloads a Google Storage file via polling.

    This step allows waiting for the presence of a file so that it can be
    used as a signal to continue work.

    Args:
      url: The Google Storage URL of the file to download.
      destination: The local path where the file will be stored.
      poll_interval: How often, in seconds, to poll for the file.
      timeout: How long, in seconds, to poll for the file before giving up.
      name: The name of the step.
    """
    gsutil_download_path = self.package_repo_resource(
        'scripts', 'slave', 'gsutil_download.py')
    args = ['--poll',
            '--url', url,
            '--dst', destination,
            '--poll-interval', str(poll_interval),
            '--timeout', str(timeout)]
    with self.m.step.context({'cwd': self.m.path['start_dir']}):
      return self.m.python(name, gsutil_download_path, args)

  def download_latest_file(self, base_url, partial_name, destination,
                           name='Download latest file from GS'):
    """Get the latest archived object with the given base url and partial name.

    Args:
      base_url: Base Google Storage archive URL (gs://...) containing the build.
      partial_name: Partial name of the archive file to download.
      destination: Destination file/directory where the file will be downloaded.
      name: The name of the step.
    """
    gsutil_download_path = self.package_repo_resource(
        'scripts', 'slave', 'gsutil_download.py')
    args = ['--url', base_url,
            '--dst', destination,
            '--partial-name', partial_name]
    with self.m.step.context({'cwd': self.m.path['start_dir']}):
      return self.m.python(name, gsutil_download_path, args)
