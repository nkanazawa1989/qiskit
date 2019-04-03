# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Physical qubit.
"""
from typing import List

from qiskit.pulse.exceptions import PulseError
from .output_channel import DriveChannel, ControlChannel, MeasureChannel
from .pulse_channel import AcquireChannel, MemorySlot


class Qubit:
    """Physical qubit."""

    def __init__(self, index: int,
                 drive_channels: List[DriveChannel] = None,
                 control_channels: List[ControlChannel] = None,
                 measure_channels: List[MeasureChannel] = None,
                 acquire_channel: AcquireChannel = None,
                 memory_slot: MemorySlot = None):
        self._index = index
        self._drives = drive_channels
        self._controls = control_channels
        self._measures = measure_channels
        self._acquire = acquire_channel or AcquireChannel(index)
        self._mem_slot = memory_slot or MemorySlot(index)

    def __eq__(self, other):
        """Two physical qubits are the same if they have the same index and channels.

        Args:
            other (Qubit): other Qubit

        Returns:
            bool: are self and other equal.
        """
        # pylint: disable=too-many-boolean-expressions
        if type(self) is type(other) and \
                self._index == other._index and \
                self._drives == other._drives and \
                self._controls == other._controls and \
                self._measures == other._measures and \
                self._acquire == other._acquire and \
                self._mem_slot == other._mem_slot:
            return True
        return False

    @property
    def drive(self) -> DriveChannel:
        """Return the primary drive channel of this qubit."""
        if self._drives:
            return self._drives[0]
        else:
            raise PulseError("No drive channels in q[%d]" % self._index)

    @property
    def control(self) -> ControlChannel:
        """Return the primary control channel of this qubit."""
        if self._controls:
            return self._controls[0]
        else:
            raise PulseError("No control channels in q[%d]" % self._index)

    @property
    def measure(self) -> MeasureChannel:
        """Return the primary measure channel of this qubit."""
        if self._measures:
            return self._measures[0]
        else:
            raise PulseError("No measurement channels in q[%d]" % self._index)

    @property
    def acquire(self) -> AcquireChannel:
        """Return the acquire channel of this qubit."""
        if self._acquire:
            return self._acquire
        else:
            raise PulseError("No memory slot in q[%d]" % self._index)

    @property
    def mem_slot(self) -> MemorySlot:
        """Return the memory slot of this qubit."""
        if self._mem_slot:
            return self._mem_slot
        else:
            raise PulseError("No memory slot in q[%d]" % self._index)
