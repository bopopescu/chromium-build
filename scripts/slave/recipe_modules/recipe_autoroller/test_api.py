# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from recipe_engine import recipe_test_api


class RecipeAutorollerTestApi(recipe_test_api.RecipeTestApi):
  def roll_data(self, project, success=True, trivial=True, empty=False):
    """Returns mock roll data for |project|."""
    if empty:
      success = False

    ret = self.empty_test_data()

    picked_roll_details = {
      'commit_infos': {
        'recipe_engine': [
          {
            'author': 'foo@chromium.org',
            'message': '\n'.join([
              'some commit message',
              'R=bar@chromium.org,baz@chromium.org,invalid1,invalid2@chromium',
              'BUG=123,456',
            ]),
            'revision': '123abc',
          },
        ],
      },
      'spec': 'api_version: 1\netc: "etc"\n',
    }

    roll_result = {
      'success': success,
      'trivial': trivial if success else None,
      'picked_roll_details': picked_roll_details if success else None,
      'rejected_candidates_details': [],
    }
    if empty:
      roll_result['roll_details'] = []
    else:
      roll_result['roll_details'] = [picked_roll_details]
      if not success:
        roll_result['rejected_candidates_details'].append({
          'spec': 'some_spec',
          'commit_infos': {
          },
        })

    ret += self.step_data('%s.roll' % project, self.m.json.output(roll_result))
    return ret

  def new_upload(self, project):
    return self.step_data('%s.gsutil cat' % project,
          self.m.raw_io.stream_output('', stream='stdout'),
          self.m.raw_io.stream_output('Error: No URLs matched ...',
                                   stream='stderr'),
          retcode=1)

  def previously_uploaded(self, project):
    return self.step_data('%s.gsutil cat' % project,
          self.m.raw_io.stream_output(json.dumps(
              {
                'issue': '123456789',
                'issue_url': 'https://codereview.chromium.org/123456789',
                'diff_digest': 'afe53a0e969fd0b2a6b5c5f89724d0c6'
              }),
              stream='stdout'),
          self.m.raw_io.stream_output('', stream='stderr'))
