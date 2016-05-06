# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'file',
  'gsutil',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
  'zip',
]

BUCKET_NAME = 'flutter_infra'

def GetCloudPath(api, path):
  # TODO(eseidel): api.bot_update.last_returned_properties is supposedly a known
  # api wart. iannucci says it will be improved at some point.
  git_hash = api.bot_update.last_returned_properties['got_engine_revision']
  return 'flutter/%s/%s' % (git_hash, path)


def Build(api, config, *targets):
  checkout = api.path['checkout']
  build_dir = checkout.join('out/%s' % config)
  ninja_args = ['ninja', '-C', build_dir]
  ninja_args.extend(targets)
  api.step('build %s' % ' '.join([config] + list(targets)), ninja_args)


def RunGN(api, *args):
  checkout = api.path['checkout']
  gn_cmd = [checkout.join('sky/tools/gn')]
  gn_cmd.extend(args)
  api.step('gn %s' % ' '.join(args), gn_cmd)


def AddFiles(api, pkg, relative_paths):
  for path in relative_paths:
    pkg.add_file(pkg.root.join(path), archive_name=api.path.basename(path))


def UploadArtifacts(api, platform, file_paths, archive_name='artifacts.zip'):
  with MakeTempDir(api) as temp_dir:
    local_zip = temp_dir.join('artifacts.zip')
    remote_name = '%s/%s' % (platform, archive_name)
    remote_zip = GetCloudPath(api, remote_name)
    pkg = api.zip.make_package(api.path['checkout'], local_zip)
    AddFiles(api, pkg, file_paths)

    pkg.zip('Zip %s Artifacts' % platform)
    api.gsutil.upload(local_zip, BUCKET_NAME, remote_zip,
        name='upload "%s"' % remote_name)


def UploadDartPackage(api, package_name):
  with MakeTempDir(api) as temp_dir:
    local_zip = temp_dir.join('%s.zip' % package_name)
    remote_name = '%s.zip' % package_name
    remote_zip = GetCloudPath(api, remote_name)
    parent_dir = api.path['checkout'].join(
        'out/android_Release/dist/packages')
    pkg = api.zip.make_package(parent_dir, local_zip)
    pkg.add_directory(parent_dir.join(package_name))
    pkg.zip('Zip %s Package' % package_name)
    api.gsutil.upload(local_zip, BUCKET_NAME, remote_zip,
        name='upload %s' % remote_name)


# TODO(eseidel): Would be nice to have this on api.path or api.file.
@contextlib.contextmanager
def MakeTempDir(api):
  try:
    temp_dir = api.path.mkdtemp('tmp')
    yield temp_dir
  finally:
    api.file.rmtree('temp dir', temp_dir)


def AnalyzeDartUI(api):
  RunGN(api, '--debug')
  Build(api, 'Debug', 'generate_dart_ui')

  checkout = api.path['checkout']
  api.step('analyze dart_ui', ['/bin/sh', 'travis/analyze.sh'], cwd=checkout)


def BuildLinuxAndroidx86(api):
  for x86_variant, abi in [('x64', 'x86_64'), ('x86', 'x86')]:
    RunGN(api, '--release', '--android', '--android-cpu=' + x86_variant)
    out_dir = 'android_Release_' + x86_variant
    Build(api, out_dir)
    UploadArtifacts(api, 'android-' + x86_variant, [
      'build/android/ant/chromium-debug.keystore',
      'out/%s/apks/SkyShell.apk' % out_dir,
      ('out/%s/gen/sky/shell/shell/shell/libs/%s/libsky_shell.so' %
       (out_dir, abi)),
      'out/%s/icudtl.dat' % out_dir,
      'out/%s/gen/sky/shell/shell/classes.dex.jar' % out_dir,
    ])


def AddPathPrefix(api, prefix, paths):
  return map(lambda path: api.path.join(prefix, path), paths)


def BuildLinuxAndroidArm(api):
  out_paths = [
    'apks/SkyShell.apk',
    'flutter.jar',
    'flutter.mojo',
    'gen/sky/shell/shell/shell/libs/armeabi-v7a/libsky_shell.so',
    'icudtl.dat',
    'gen/sky/shell/shell/classes.dex.jar',
  ]
  RunGN(api, '--release', '--android', '--enable-gcm', '--enable-firebase')
  Build(api, 'android_Release', ':dist', 'gcm', 'sky/services/firebase')
  UploadArtifacts(api, 'android-arm', [
    'build/android/ant/chromium-debug.keystore',
  ] + AddPathPrefix(api, 'out/android_Release', out_paths))

  # Build and upload a deploy mode configuration that uses AOT compilation.
  def MakeDeployBuild(gn_flag, build_output_dir, upload_dir):
    RunGN(api, gn_flag, '--android', '--deploy')
    Build(api, build_output_dir)

    UploadArtifacts(api, upload_dir, [
      'build/android/ant/chromium-debug.keystore',
      'sky/engine/bindings/dart_vm_entry_points.txt',
      'sky/engine/bindings/dart_vm_entry_points_android.txt',
    ] + AddPathPrefix(api, 'out/%s' % build_output_dir, out_paths))

    # Upload artifacts used for AOT compilation on Linux hosts.
    UploadArtifacts(api, upload_dir, [
      'out/%s/clang_x86/gen_snapshot' % build_output_dir,
    ], archive_name='linux-x64.zip')

  MakeDeployBuild('--debug', 'android_Debug_Deploy', 'android-arm-profile')
  MakeDeployBuild('--release', 'android_Release_Deploy', 'android-arm-release')

  UploadDartPackage(api, 'sky_engine')
  UploadDartPackage(api, 'sky_services')

  def UploadService(name, out_dir):
    def Upload(from_path, to_path):
      api.gsutil.upload(from_path, BUCKET_NAME, GetCloudPath(api, to_path),
          name='upload %s' % api.path.basename(to_path))

    def ServicesOut(path):
      checkout = api.path['checkout']
      return checkout.join('%s/%s' % (out_dir, path))

    dex_jar = '%s/%s_lib.dex.jar' % (name, name)
    interfaces_jar = '%s/interfaces_java.dex.jar' % (name)
    Upload(ServicesOut(dex_jar), dex_jar)
    Upload(ServicesOut(interfaces_jar), interfaces_jar)

  UploadService('firebase', 'out/android_Release/gen/sky/services')
  UploadService('gcm', 'out/android_Release/gen/third_party')


def BuildLinux(api):
  RunGN(api, '--release')
  Build(api, 'Release')
  UploadArtifacts(api, 'linux-x64', [
    'out/Release/flutter.mojo',
    'out/Release/icudtl.dat',
    'out/Release/sky_shell',
    'out/Release/sky_snapshot',
  ])


def TestObservatory(api):
  checkout = api.path['checkout']
  sky_shell_path = checkout.join('out/Release/sky_shell')
  empty_main_path = \
      checkout.join('sky/shell/testing/observatory/empty_main.dart')
  test_path = checkout.join('sky/shell/testing/observatory/test.dart')
  test_cmd = ['dart', test_path, sky_shell_path, empty_main_path]
  api.step('test observatory and service protocol', test_cmd, cwd=checkout)


def BuildMac(api):
  RunGN(api, '--release')
  Build(api, 'Release')
  UploadArtifacts(api, 'darwin-x64', [
    'out/Release/sky_snapshot'
  ])


def GenerateXcodeProject(api):
  checkout = api.path['checkout']
  out_dir = checkout.join('out')

  RunGN(api, '--release', '--ios', '--simulator')
  Build(api, 'ios_sim_Release')

  RunGN(api, '--release', '--ios')
  Build(api, 'ios_Release')

  RunGN(api, '--release', '--ios', '--ios-force-armv7')
  Build(api, 'ios_Release_armv7')

  # Copy device 'Flutter' directory to a deploy dir:
  deploy_dir = out_dir.join('FlutterXcode')

  create_ios_sdk_cmd = [
    checkout.join('sky/tools/create_ios_sdk.py'),
    '--dst',
    deploy_dir
  ]
  api.step('Create iOS SDK', create_ios_sdk_cmd, cwd=checkout)

  # Zip the whole thing and upload it to cloud storage:
  flutter_zip = out_dir.join('FlutterXcode.zip')
  api.zip.directory('make FlutterXcode.zip', deploy_dir, flutter_zip)

  UploadArtifacts(api, 'ios', [
    'out/FlutterXcode.zip'
  ])


def GetCheckout(api):
  src_cfg = api.gclient.make_config(GIT_MODE=True)
  soln = src_cfg.solutions.add()
  soln.name = 'src'
  soln.url = \
      'https://chromium.googlesource.com/external/github.com/flutter/engine'
  # TODO(eseidel): What does parent_got_revision_mapping do?  Do I care?
  src_cfg.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'
  src_cfg.target_os = set(['android'])
  api.gclient.c = src_cfg
  api.gclient.c.got_revision_mapping['src'] = 'got_engine_revision'
  # TODO(eseidel): According to iannucci force=True is required.
  # See https://codereview.chromium.org/1690713003#msg6
  api.bot_update.ensure_checkout(force=True)
  api.gclient.runhooks()


def RunSteps(api):
  # buildbot sets 'clobber' to the empty string which is falsey, check with 'in'
  if 'clobber' in api.properties:
    api.file.rmcontents('everything', api.path['slave_build'])

  GetCheckout(api)

  checkout = api.path['checkout']
  dart_bin = checkout.join('third_party', 'dart-sdk', 'dart-sdk', 'bin')
  env = { 'PATH': api.path.pathsep.join((str(dart_bin), '%(PATH)s')) }

  # The context adds dart to the path, only needed for the analyze step for now.
  with api.step.context({'env': env}):
    AnalyzeDartUI(api)

    if api.platform.is_linux:
      api.step('download android tools',
        [checkout.join('tools/android/download_android_tools.py')])
      BuildLinux(api)
      TestObservatory(api)
      BuildLinuxAndroidArm(api)
      BuildLinuxAndroidx86(api)

    if api.platform.is_mac:
      BuildMac(api)
      GenerateXcodeProject(api)


def GenTests(api):
  # A valid commit to flutter/engine, to make the gsutil urls look real.
  for platform in ('mac', 'linux'):
    yield (api.test(platform) + api.platform(platform, 64)
        + api.properties(mastername='client.flutter',
              buildername='%s Engine' % platform.capitalize(),
              slavename='fake-m1', clobber=''))
