# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
import os
import sys
import threading
from unittest import mock

# In case this is run locally from
sys.path.append(os.path.abspath('../../src/jukebox'))

import jukebox.plugs  # noqa: E402
jukebox.plugs.ALLOW_DIRECT_IMPORTS = True
from jukebox.multitimer import GenericMultiTimerClass  # noqa: E402
import components.timers.idle_shutdown_timer as idle  # noqa: E402


def test_idle_shutdown_runs_through_multitimer():
    """The timer passes iterations/iteration to its callee; IdleShutdown must accept them and shut down"""
    called = threading.Event()

    def fake_call(package, plugin, method=None, args=None, **kwargs):
        if (package, plugin) == ("host", "shutdown"):
            called.set()

    timer_cls = mock.patch.object(idle.IdleShutdown, '_has_active_ssh_sessions', return_value=False)
    with timer_cls, mock.patch.object(idle.plugin, 'call_ignore_errors', side_effect=fake_call):
        timer = GenericMultiTimerClass(name='test.idle_shutdown', iterations=1, wait_seconds_per_iteration=0.1,
                                       callee=lambda iterations: idle.IdleShutdown())
        timer.start()
        assert called.wait(timeout=5), "IdleShutdown was not called by the timer"
        timer.cancel()
