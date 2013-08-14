#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Checks if a virtual webcam is running and starts it if not.

Returns a non-zero return code if the webcam could not be started.

Prerequisites:
* The Python interpreter must have the psutil package installed.
* Windows: a scheduled task named 'ManyCam' must exist and be configured to
  launch ManyCam preconfigured to auto-play the test clip.
* Mac: ManyCam must be installed in the default location and be preconfigured
  to auto-play the test clip.
* Linux: The v4l2loopback kernel module must be compiled and loaded to the
  kernel already (with the devices=2 argument) and the v4l2_file_player
  application must be compiled and put in the location specified below.

NOTICE: When running this script as a buildbot step, make sure to set
usePTY=False for the build step when adding it, or the subprocess will die as
soon the step has executed.
"""

import os
# psutil is not installed on non-Linux machines by default.
import psutil  # pylint: disable=F0401
import subprocess
import sys


WEBCAM_WIN = ['schtasks', '/run', '/tn', 'ManyCam']
WEBCAM_MAC = ['open', '/Applications/ManyCam/ManyCam.app']
E = os.path.expandvars
WEBCAM_LINUX = [
    E('$HOME/fake-webcam-driver/linux/v4l2_file_player/v4l2_file_player'),
    E('$HOME/webrtc_video_quality/reference_video.yuv'),
    '640', '480', '/dev/video1']


def IsWebCamRunning():
  if sys.platform == 'win32':
    process_name = 'ManyCam.exe'
  elif sys.platform.startswith('darwin'):
    process_name = 'ManyCam'
  elif sys.platform.startswith('linux'):
    process_name = 'v4l2_file_player'
  else:
    raise Exception('Unsupported platform: %s' % sys.platform)
  for p in psutil.process_iter():
    if process_name == p.name:
      print 'Found a running virtual webcam (%s with PID %s)' % (p.name, p.pid)
      return True
  return False


def Main():
  if IsWebCamRunning():
    return 0

  try:
    if sys.platform == 'win32':
      subprocess.check_call(WEBCAM_WIN)
      print 'Successfully launched virtual webcam.'
    elif sys.platform.startswith('darwin'):
      subprocess.check_call(WEBCAM_MAC)
      print 'Successfully launched virtual webcam.'
    elif sys.platform.startswith('linux'):

      # Must redirect stdout/stderr/stdin to avoid having the subprocess
      # being killed when the parent shell dies (happens on the bots).
      process = subprocess.Popen(WEBCAM_LINUX, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
      print 'Successfully launched virtual webcam with PID %s' % process.pid

    return 0

  except Exception as e:
    print 'Failed to launch virtual webcam: %s' % e


if __name__ == '__main__':
  sys.exit(Main())
