# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/gclient',
  'depot_tools/bot_update',
  'goma',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

from recipe_engine.recipe_api import Property

PROPERTIES = {
  'skia': Property(default=False, kind=bool),
  'xfa': Property(default=False, kind=bool),
  'memory_tool': Property(default=None, kind=str),
  'v8': Property(default=True, kind=bool),
  'target_cpu': Property(default=None, kind=str),
  'clang': Property(default=False, kind=bool),
  'rel': Property(default=False, kind=bool),
  'skip_test': Property(default=False, kind=bool),
  'target_os': Property(default=None, kind=str),
}

def _CheckoutSteps(api, memory_tool, skia, xfa, v8, target_cpu, clang,
                   target_os):
  # Checkout pdfium and its dependencies (specified in DEPS) using gclient.
  api.gclient.set_config('pdfium')
  if target_os:
    api.gclient.c.target_os = {target_os}
  api.bot_update.ensure_checkout()

  api.gclient.runhooks()


def _OutPath(api, memory_tool, skia, xfa, v8, clang, rel):
  out_dir = 'release' if rel else 'debug'
  if skia:
    out_dir += "_skia"
  if xfa:
    out_dir += "_xfa"
  if v8:
    out_dir += "_v8"
  if clang:
    out_dir += "_clang"
  if memory_tool == 'asan':
    out_dir += "_asan"
  return out_dir


def _GNGenBuilds(api, memory_tool, skia, xfa, v8, target_cpu, clang, rel,
                 target_os, out_dir):
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.path['depot_tools'].join('gn.py')

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[not rel],
      'is_component_build=false',
      'pdf_enable_v8=%s' % gn_bool[v8],
      'pdf_enable_xfa=%s' % gn_bool[xfa],
      'pdf_use_skia=%s' % gn_bool[skia],
      'pdf_is_standalone=true',
      'use_goma=true',
  ]
  if api.platform.is_win and not memory_tool:
    args.append('symbol_level=1')
  if api.platform.is_linux:
    args.append('use_sysroot=false')
  if clang:
    args.append('is_clang=true')
  if memory_tool == 'asan':
    args.append('is_asan=true')
  if target_os:
    args.append('target_os="%s"' % target_os)
  if target_cpu == 'x86':
    args.append('target_cpu="x86"')

  api.python('gn gen', gn_cmd,
             ['--root=' + str(checkout), 'gen', '//out/' + out_dir,
              '--args=' + ' '.join(args)],
             cwd=checkout)

def _BuildSteps(api, clang, out_dir):
  api.goma.ensure_goma()

  # Build sample file using Ninja
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = ['ninja', '-C', debug_path,
               '-j', api.goma.recommended_goma_jobs]

  with api.goma.build_with_goma(
      ninja_log_outdir=debug_path,
      ninja_log_compiler='clang' if clang else 'unknown',
      ninja_log_command=ninja_cmd):
    api.step('compile with ninja', ninja_cmd)


def _RunDrMemoryTests(api, v8):
  pdfium_tests_py = str(api.path['checkout'].join('tools',
                                                  'drmemory',
                                                  'scripts',
                                                  'pdfium_tests.py'))
  api.python('unittests', pdfium_tests_py,
             args=['--test', 'pdfium_unittests'],
             cwd=api.path['checkout'])
  api.python('embeddertests', pdfium_tests_py,
             args=['--test', 'pdfium_embeddertests'],
             cwd=api.path['checkout'])
  if v8:
    api.python('javascript tests', pdfium_tests_py,
               args=['--test', 'pdfium_javascript'],
               cwd=api.path['checkout'])
  api.python('pixel tests', pdfium_tests_py,
             args=['--test', 'pdfium_pixel'],
             cwd=api.path['checkout'])
  api.python('corpus tests', pdfium_tests_py,
             args=['--test', 'pdfium_corpus'],
             cwd=api.path['checkout'])


def _RunTests(api, memory_tool, v8, out_dir):
  if memory_tool == 'drmemory':
    _RunDrMemoryTests(api, v8)
    return

  env = {}
  if memory_tool == 'asan':
    # TODO(ochang): Once PDFium is less leaky, remove the detect_leaks flag.
    env.update({
        'ASAN_OPTIONS': 'detect_leaks=0:allocator_may_return_null=1'})

  unittests_path = str(api.path['checkout'].join('out', out_dir,
                                                 'pdfium_unittests'))
  if api.platform.is_win:
    unittests_path += '.exe'
  api.step('unittests', [unittests_path], cwd=api.path['checkout'], env=env)

  embeddertests_path = str(api.path['checkout'].join('out', out_dir,
                                                     'pdfium_embeddertests'))
  if api.platform.is_win:
    embeddertests_path += '.exe'
  api.step('embeddertests', [embeddertests_path],
           cwd=api.path['checkout'],
           env=env)

  script_args = ['--build-dir', api.path.join('out', out_dir)]

  if v8:
    javascript_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_javascript_tests.py'))
    api.python('javascript tests', javascript_path, script_args,
               cwd=api.path['checkout'], env=env)

  pixel_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                   'run_pixel_tests.py'))
  api.python('pixel tests', pixel_tests_path, script_args,
             cwd=api.path['checkout'], env=env)

  corpus_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_corpus_tests.py'))
  api.python('corpus tests', corpus_tests_path, script_args,
             cwd=api.path['checkout'], env=env)


def RunSteps(api, memory_tool, skia, xfa, v8, target_cpu, clang, rel, skip_test,
             target_os):
  _CheckoutSteps(api, memory_tool, skia, xfa, v8, target_cpu, clang, target_os)

  out_dir = _OutPath(api, memory_tool, skia, xfa, v8, clang, rel)

  _GNGenBuilds(api, memory_tool, skia, xfa, v8, target_cpu, clang, rel,
               target_os, out_dir)

  _BuildSteps(api, clang, out_dir)

  if skip_test:
    return

  with api.step.defer_results():
    _RunTests(api, memory_tool, v8, out_dir)


def GenTests(api):
  yield (
      api.test('win') +
      api.platform('win', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='windows',
                     slavename="test_slave")
  )
  yield (
      api.test('linux') +
      api.platform('linux', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='linux',
                     slavename="test_slave")
  )
  yield (
      api.test('mac') +
      api.platform('mac', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='mac',
                     slavename="test_slave")
  )

  yield (
      api.test('win_no_v8') +
      api.platform('win', 64) +
      api.properties(v8=False,
                     mastername="client.pdfium",
                     buildername='windows_no_v8',
                     slavename="test_slave")
  )
  yield (
      api.test('linux_no_v8') +
      api.platform('linux', 64) +
      api.properties(v8=False,
                     mastername="client.pdfium",
                     buildername='linux_no_v8',
                     slavename="test_slave")
  )
  yield (
      api.test('mac_no_v8') +
      api.platform('mac', 64) +
      api.properties(v8=False,
                     mastername="client.pdfium",
                     buildername='mac_no_v8',
                     slavename="test_slave")
  )

  yield (
      api.test('win_skia') +
      api.platform('win', 64) +
      api.properties(skia=True,
                     xfa=True,
                     skip_test=True,
                     mastername="client.pdfium",
                     buildername='windows_skia',
                     slavename="test_slave")
  )

  yield (
      api.test('win_xfa_32') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     target_cpu='x86',
                     mastername="client.pdfium",
                     buildername='windows_xfa_32',
                     slavename="test_slave")
  )

  yield (
      api.test('win_xfa') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     mastername="client.pdfium",
                     buildername='windows_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('win_xfa_rel') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     rel=True,
                     mastername="client.pdfium",
                     buildername='windows_xfa_rel',
                     slavename="test_slave")
  )

  yield (
      api.test('win_xfa_clang_32') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     clang=True,
                     target_cpu='x86',
                     mastername="client.pdfium",
                     buildername='windows_xfa_clang_32',
                     slavename="test_slave")
  )

  yield (
      api.test('win_xfa_clang') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     clang=True,
                     mastername="client.pdfium",
                     buildername='windows_xfa_clang',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_skia') +
      api.platform('linux', 64) +
      api.properties(skia=True,
                     xfa=True,
                     skip_test=True,
                     mastername="client.pdfium",
                     buildername='linux_skia',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_xfa') +
      api.platform('linux', 64) +
      api.properties(xfa=True,
                     mastername="client.pdfium",
                     buildername='linux_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_xfa_rel') +
      api.platform('linux', 64) +
      api.properties(xfa=True,
                     rel=True,
                     mastername="client.pdfium",
                     buildername='linux_xfa_rel',
                     slavename="test_slave")
  )

  yield (
      api.test('mac_skia') +
      api.platform('mac', 64) +
      api.properties(skia=True,
                     xfa=True,
                     skip_test=True,
                     mastername="client.pdfium",
                     buildername='mac_skia',
                     slavename="test_slave")
  )

  yield (
      api.test('mac_xfa') +
      api.platform('mac', 64) +
      api.properties(xfa=True,
                     mastername="client.pdfium",
                     buildername='mac_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('mac_xfa_rel') +
      api.platform('mac', 64) +
      api.properties(xfa=True,
                     rel=True,
                     mastername="client.pdfium",
                     buildername='mac_xfa_rel',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_asan') +
      api.platform('linux', 64) +
      api.properties(memory_tool='asan',
                     mastername="client.pdfium",
                     buildername='linux_asan',
                     slavename="test_slave")
  )

  yield (
      api.test('drm_win_xfa') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     memory_tool='drmemory',
                     target_cpu='x86',
                     mastername="client.pdfium",
                     buildername='drm_win_xfa',
                     slavename="test_slave")
  )

  yield (
      api.test('linux_xfa_asan') +
      api.platform('linux', 64) +
      api.properties(xfa=True,
                     memory_tool='asan',
                     mastername="client.pdfium",
                     buildername='linux_xfa_asan',
                     slavename="test_slave")
  )

  yield (
       api.test('try-linux_xfa_asan') +
       api.platform('linux', 64) +
       api.properties.tryserver(xfa=True,
                                memory_tool='asan',
                                mastername='tryserver.client.pdfium',
                                buildername='linux_xfa_asan')
  )

  yield (
      api.test('android') +
      api.platform('linux', 64) +
      api.properties(mastername='client.pdfium',
                     buildername='android',
                     slavename='test_slave',
                     target_os='android',
                     skip_test=True)
  )
