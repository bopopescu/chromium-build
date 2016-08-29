# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['gclient'].CONFIG_CTX
from recipe_engine.config import BadConf


# TODO(machenbach): Remove this.
def ChromiumSvnTrunkURL(c, *pieces):
  BASES = ('https://src.chromium.org/svn/trunk',
           'svn://svn-mirror.golo.chromium.org/chrome/trunk')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


@CONFIG_CTX()
def v8(c):
  soln = c.solutions.add()
  soln.name = 'v8'
  soln.url = 'https://chromium.googlesource.com/v8/v8'
  soln.custom_vars = {'chromium_trunk': ChromiumSvnTrunkURL(c)}
  c.got_revision_mapping['v8'] = 'got_revision'
  # Needed to get the testers to properly sync the right revision.
  # TODO(infra): Upload full buildspecs for every build to isolate and then use
  # them instead of this gclient garbage.
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'

  p = c.patch_projects
  p['icu'] = ('v8/third_party/icu', 'HEAD')


@CONFIG_CTX(includes=['v8'])
def dynamorio(c):
  soln = c.solutions.add()
  soln.name = 'dynamorio'
  soln.url = 'https://chromium.googlesource.com/external/dynamorio'


@CONFIG_CTX(includes=['v8'])
def llvm_compiler_rt(c):
  c.solutions[0].custom_deps['v8/third_party/llvm/projects/compiler-rt'] = (
    'https://chromium.googlesource.com/external/llvm.org/compiler-rt.git')


@CONFIG_CTX()
def node_js(c):
  soln = c.solutions.add()
  soln.name = 'node.js'
  soln.url = 'https://chromium.googlesource.com/external/github.com/v8/node'
  soln.revision = 'vee-eight-lkgr:HEAD'
  c.got_revision_mapping[soln.name] = 'got_node_js_revision'


@CONFIG_CTX(includes=['v8'])
def v8_valgrind(c):
  c.solutions[0].custom_deps['v8/third_party/valgrind'] = (
    'https://chromium.googlesource.com/chromium/deps/valgrind/binaries.git')
