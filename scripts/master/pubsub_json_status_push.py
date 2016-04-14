# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import collections
import datetime
import functools
import json
import os

from buildbot.status.base import StatusReceiverMultiService
from master import auth
from master.deferred_resource import DeferredResource
from twisted.internet import defer, reactor
from twisted.python import log


PUBSUB_SCOPES = ['https://www.googleapis.com/auth/pubsub']


class PubSubClient(object):
  """A client residing in a separate process to send data to PubSub.

  This is separated from the main twistd reactor in order to shield the
  main reactor from the increased load.
  """

  def __init__(self, topic, service_account_file):
    self.topic = topic
    self.service_account_file = '/' + os.path.join(
        'creds', 'service_accounts', service_account_file)
    try:
      self.credentials = auth.create_service_account_credentials(
          self.service_account_file, scope=PUBSUB_SCOPES)
    except auth.Error as e:
      log.err(
          'PubSub: Could not load credentials %s: %s.' % (
              self.service_account_file, e))
      raise e
    self.resource = None
    log.msg('PubSub client for topic %s created' % self.topic)

  @defer.inlineCallbacks
  def start(self):
    self.resource = yield DeferredResource.build(
        'pubsub', 'v1', credentials=self.credentials)
    self.resource.start()
    # Check to see if the topic exists.  Anything that's not a 200 means it
    # doesn't exist or is inaccessable.
    res = yield self.resource.api.projects.topics.get(topic=self.topic)
    log.msg('PubSub client for topic %s started: %s' % (self.topic, res))

  def close(self):
    self.resource.stop()

  @defer.inlineCallbacks
  def send(self, data):
    # TODO(hinoka): Sign messages so that they can be verified to originate
    # from buildbot.
    assert self.resource

    encoded_data = base64.b64encode(data)
    body = { 'messages': [{'data': encoded_data}] }

    log.msg('PubSub: Sending %d bytes' % len(encoded_data))
    try:
      res = yield self.resource.api.projects.topics.publish(
          topic=self.topic, body=body)
      log.msg('PubSub: Send successful %s' % res)
    except Exception as e:
      log.msg('PubSub: Send failed: %s' % e)

# Annotation that wraps an event handler.
def event_handler(func):
  """Annotation to simplify 'StatusReceiver' event callback methods.

  This annotation uses the wrapped function's name as the event name and
  logs the event if the 'StatusPush' is configured to be verbose.
  """
  status = func.__name__
  @functools.wraps(func)
  def wrapper(self, *args, **kwargs):
    if self.verbose:
      log.msg('Status update (%s): %s %s' % (
          status, args, ' '.join(['%s=%s' % (k, kwargs[k])
                                  for k in sorted(kwargs.keys())])))
    return func(self, *args, **kwargs)
  return wrapper


class ConfigError(ValueError):
  pass
class NotEnabled(Exception):
  """Raised when PubSub is purposely not enabled."""


_BuildBase = collections.namedtuple(
    '_BuildBase', ('builder_name', 'build_number'))
class _Build(_BuildBase):
  # Disable "no __init__ method" warning | pylint: disable=W0232
  def __repr__(self):
    return '%s/%s' % (self.builder_name, self.build_number)


class StatusPush(StatusReceiverMultiService):
  """
  Periodically push builder status updates to pubsub.
  """

  DEFAULT_PUSH_INTERVAL_SEC = 30

  # Perform verbose logging.
  verbose = True

  @classmethod
  def CreateStatusPush(cls, activeMaster, pushInterval=None):
    assert activeMaster, 'An active master must be supplied.'
    if not (
          activeMaster.is_production_host or os.environ.get('TESTING_MASTER')):
      log.msg(
          'Not a production host or testing, not loading the PubSub '
          'status listener.')
      return None

    topic = getattr(activeMaster, 'pubsub_topic', None)
    if not topic:
      log.msg('PubSub: Missing pubsub_topic, not enabling.')
      return None

    # Set the master name, for indexing purposes.
    name = getattr(activeMaster, 'name', None)
    if not name:
      raise ConfigError(
          'A master name must be supplied for pubsub push support.')

    service_account_file = getattr(
        activeMaster, 'pubsub_service_account_file', None)
    if not service_account_file:
      raise ConfigError('A service account file must be specified.')

    return cls(topic, service_account_file, name, pushInterval)


  def __init__(self, topic, service_account_file, name, pushInterval=None):
    """Instantiates a new StatusPush service.

    Args:
      topic: Pubsub topic to push updates to.
      service_account_file: Credentials to use to push to pubsub.
      pushInterval: (number/timedelta) The data push interval. If a number is
          supplied, it is the number of seconds.
    """
    StatusReceiverMultiService.__init__(self)

    # Parameters.
    self.pushInterval = self._getTimeDelta(pushInterval or
                                           self.DEFAULT_PUSH_INTERVAL_SEC)

    self.name = name  # Master name, since builds don't include this info.
    self.topic = topic
    self._client = PubSubClient(self.topic, service_account_file)
    self._status = None
    self._res = None
    self._updated_builds = set()
    self._pushTimer = None

  @staticmethod
  def _getTimeDelta(value):
    """Returns: A 'datetime.timedelta' representation of 'value'."""
    if isinstance(value, datetime.timedelta):
      return value
    elif isinstance(value, (int, long)):
      return datetime.timedelta(seconds=value)
    raise TypeError('Unknown time delta type; must be timedelta or number.')

  @defer.inlineCallbacks
  def startService(self):
    """Twisted service is starting up."""
    StatusReceiverMultiService.startService(self)

    # Subscribe to get status updates.
    self._status = self.parent.getStatus()
    self._status.subscribe(self)

    # Init the client.
    yield self._client.start()

    # Schedule our first push.
    self._schedulePush()

  @defer.inlineCallbacks
  def stopService(self):
    """Twisted service is shutting down."""
    self._clearPushTimer()

    # Do one last status push.
    yield self._doStatusPush(self._updated_builds)

    # Stop our resource.
    self._client.close()

  @defer.inlineCallbacks
  def _doStatusPush(self, updated_builds):
    """Pushes the current state of the builds in 'updated_builds'.

    Args:
      updated_builds: (collection) A collection of _Build instances to push.
    """
    # Load all build information for builds that we're pushing.
    builds = sorted(updated_builds)
    if self.verbose:
      log.msg('PusSub: Pushing status for builds: %s' % (builds,))
    loaded_builds = yield defer.DeferredList([self._loadBuild(b)
                                              for b in builds])

    send_builds = []
    for i, build in enumerate(builds):
      success, result = loaded_builds[i]
      if not success:
        log.err('Failed to load build for [%s]: %s' % (build, result))
        continue

      # result is a (build, build_dict) tuple.
      _, send_build = result
      send_build['master'] = self.name
      send_builds.append(send_build)

    # Add in master builder state into the message.
    master_data = self._getMasterData()

    # Send off the builds.
    self._client.send(json.dumps({
        'builds': send_builds,
        'master': master_data,
    }))

  def _pushTimerExpired(self):
    """Callback invoked when the push timer has expired.

    This function takes a snapshot of updated builds and begins a push.
    """
    self._clearPushTimer()

    # Collect this round of updated builds. We clear our updated builds in case
    # more accumulate during the send interval. If the send fails, we will
    # re-add them back in the errback.
    updates = self._updated_builds.copy()
    self._updated_builds.clear()

    if self.verbose:
      log.msg('PubSub: Status push timer expired. Pushing updates for: %s' % (
              sorted(updates)))

    # Upload them. Reschedule our send timer after this push completes. If it
    # fails, add the builds back to the 'updated_builds' list so we don't lose
    # them.
    d = self._doStatusPush(updates)

    def eb_status_push(failure, updates):
      # Re-add these builds to our 'updated_builds' list.
      log.err('Failed to do status push for %s: %s' % (
          sorted(updates), failure))
      self._updated_builds.update(updates)
    d.addErrback(eb_status_push, updates)

    def cb_schedule_next_push(ignored):
      self._schedulePush()
    d.addBoth(cb_schedule_next_push)

  def _schedulePush(self):
    """Schedules the push timer to perform a push."""
    if self._pushTimer:
      return
    if self.verbose:
      log.msg('PubSub: Scheduling push timer in: %s' % (self.pushInterval,))
    self._pushTimer = reactor.callLater(self.pushInterval.total_seconds(),
        self._pushTimerExpired)

  def _clearPushTimer(self):
    """Cancels any current push timer and clears its state."""
    if self._pushTimer:
      if self._pushTimer.active():
        self._pushTimer.cancel()
      self._pushTimer = None

  def _loadBuild(self, b):
    """Loads the build dictionary associated with a '_Build' object.

    Returns: (build, build_data), via Deferred.
      build: (_Build) The build object that was loaded.
      build_data: (dict) The build data for 'build'.
    """
    builder = self._status.getBuilder(b.builder_name)
    build = builder.getBuild(b.build_number)
    return defer.succeed((b, build.asDict()))

  def _getMasterData(self):
    """Loads and returns a subset of the master data as a JSON.

    This includes:
    * builders: List of builders (builbot.status.builder.Builder).
    * slaves: List of slaves (buildbot.status.slave).
    """
    builders = {builder_name: self._status.getBuilder(builder_name)
                for builder_name in self._status.getBuilderNames()}
    builder_infos = {}
    for name, builder in builders.iteritems():
      # Not included: basedir, category, cachedBuilds, state, pendingBuilds.
      # cachedBuilds isn't useful and takes a ton of resources to compute.
      # pendingBuilds requires a deferred call.
      builder_info = {
        'slaves': builder.slavenames,
        'current_builds': sorted(b.getNumber() for b in builder.currentBuilds),
      }
      builder_infos[name] = builder_info

    slaves = {slave_name: self._status.getSlave(slave_name).asDict()
              for slave_name in self._status.getSlaveNames()}
    return {'builders': builder_infos, 'slaves': slaves, 'name': self.name}


  def _recordBuild(self, build):
    """Records an update to a 'buildbot.status.build.Build' object.

    Args:
      build: (Build) The BuildBot Build object that was updated.
    """
    build = _Build(
        builder_name=build.builder.name,
        build_number=build.number,
    )
    self._updated_builds.add(build)

  #### Events

  @event_handler
  def builderAdded(self, _builderName, _builder):
    return self

  @event_handler
  def buildStarted(self, _builderName, build):
    # This info is included in the master json.
    return self

  @event_handler
  def stepStarted(self, build, _step):
    # This info is included in the master json.
    return self

  @event_handler
  def buildFinished(self, _builderName, build, _results):
    self._recordBuild(build)
