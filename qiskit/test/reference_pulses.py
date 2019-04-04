# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Reference schedules used by the tests."""
import numpy as np

import qiskit.pulse as pulse


class ReferenceSchedules:
    """Container for reference schedules used by the tests."""

    @staticmethod
    def nonsense():
        """Return a nonsense schedule just for tests."""
        @pulse.functional_pulse
        def gaussian(duration, amp, t0, sig):
            x = np.linspace(0, duration - 1, duration)
            return amp * np.exp(-(x - t0) ** 2 / sig ** 2)

        gp0 = gaussian(duration=20, name='pulse0', amp=0.7, t0=9.5, sig=3)
        gp1 = gaussian(duration=20, name='pulse1', amp=0.5, t0=9.5, sig=3)

        qubits = [
            pulse.channels.Qubit(0,
                                 drive_channels=[pulse.channels.DriveChannel(0, 1.2)],
                                 control_channels=[pulse.channels.ControlChannel(0)]),
            pulse.channels.Qubit(1,
                                 drive_channels=[pulse.channels.DriveChannel(1, 3.4)],
                                 acquire_channels=[pulse.channels.AcquireChannel(1)])
        ]
        registers = [pulse.channels.RegisterSlot(i) for i in range(2)]
        device = pulse.DeviceSpecification(qubits, registers)

        fc_pi_2 = pulse.FrameChange(phase=1.57)
        acquire = pulse.Acquire(10)
        sched = pulse.Schedule()
        sched.insert(0, gp0(device.q[0].drive))
        sched.insert(0, pulse.PersistentValue(value=0.2+0.4j)(device.q[0].control))
        sched.insert(30, gp1(device.q[1].drive))
        sched.insert(60, pulse.FrameChange(phase=-1.57)(device.q[0].drive))
        sched.insert(60, gp0(device.q[0].control))
        sched.insert(80, pulse.Snapshot("label", "snap_type"))
        sched.insert(90, fc_pi_2(device.q[0].drive))
        sched.insert(90, acquire(device.q[1], device.mem[1], device.c[1]))
        return sched
