# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

# pylint: disable=invalid-name,unexpected-keyword-arg

"""Test cases for the pulse schedule."""

import numpy as np

from qiskit.pulse import DeviceSpecification, Qubit
from qiskit.pulse.channels import DriveChannel, AcquireChannel
from qiskit.pulse.commands import function
from qiskit.pulse.schedule import Schedule, DrivePulse, FrameChangePulse, AcquirePulse
from qiskit.test import QiskitTestCase


class TestSchedule(QiskitTestCase):
    """Schedule tests."""

    def test_can_create_valid_schedule(self):
        """Test valid schedule creation without error.
        """

        @function
        def gaussian(duration, amp, t0, sig):
            x = np.linspace(0, duration - 1, duration)
            return amp * np.exp(-(x - t0) ** 2 / sig ** 2)

        gp0 = gaussian(duration=20, name='pulse0', amp=0.7, t0=9.5, sig=3)
        gp1 = gaussian(duration=20, name='pulse1', amp=0.5, t0=9.5, sig=3)

        qubits = [
            Qubit(0, drive_channels=[DriveChannel(0, 1.2)], acquire_channels=[AcquireChannel(0)]),
            Qubit(1, drive_channels=[DriveChannel(1, 3.4)], acquire_channels=[AcquireChannel(1)])
        ]
        device = DeviceSpecification(qubits)

        schedule = Schedule(device, [
            (0, DrivePulse(gp0, device.q[0].drive)),
            (30, DrivePulse(gp1, device.q[1].drive)),
            (60, FrameChangePulse(phase=-1.57, channel=device.q[0].drive)),
            (60, DrivePulse(gp0, device.q[0].drive)),
            (90, FrameChangePulse(phase=1.57, channel=device.q[0].drive)),
            (90, AcquirePulse(10, device.q[0], device.mem[0], reg_slots=device.c[0])),
            (90, AcquirePulse(10, device.q[1], device.mem[1], reg_slots=device.c[1]))
        ])

        self.assertTrue(True)
