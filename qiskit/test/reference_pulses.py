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
        def linear(duration: int):
            x = np.arange(0, duration)
            return 0.2 * x + 0.1

        lp0 = linear(duration=3, name='pulse0')

        qubits = [
            pulse.channels.Qubit(0,
                                 drive_channels=[pulse.channels.DriveChannel(0)],
                                 acquire_channels=[pulse.channels.AcquireChannel(0)]),
        ]
        registers = [pulse.channels.RegisterSlot(i) for i in range(1)]
        device = pulse.DeviceSpecification(qubits, registers)

        sched = pulse.Schedule()
        sched.insert(0, lp0(device.q[0].drive))
        sched.insert(3, pulse.Acquire(10)(device.q[0], device.mem[0]))
        return sched
