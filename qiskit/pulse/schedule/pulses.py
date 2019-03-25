# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Pulse = Command with its operands (Channels).
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import List, Union, Set

from qiskit.pulse import Qubit
from qiskit.pulse.channels import (PulseChannel, OutputChannel, MemorySlot, RegisterSlot,
                                   SnapshotChannel)
from qiskit.pulse.commands import (SamplePulse, Acquire, Kernel, Discriminator,
                                   FrameChange, PersistentValue, Snapshot)
from qiskit.pulse.exceptions import PulseError
from .timeslots import Interval, Timeslot, TimeslotOccupancy

logger = logging.getLogger(__name__)


class Pulse(metaclass=ABCMeta):
    """Common interface for `Command with its operands (Channels)`. """

    def __init__(self, occupancy: TimeslotOccupancy):
        self._occupancy = occupancy

    @property
    def occupancy(self):
        return self._occupancy

    @abstractmethod
    def duration(self) -> int:
        pass

    @property
    def channelset(self) -> Set[PulseChannel]:
        return self._occupancy.channelset


class DrivePulse(Pulse):
    """Pulse to drive a pulse shape to a `OutputChannel`. """

    def __init__(self, pulse: SamplePulse, channel: OutputChannel):
        slots = [Timeslot(Interval(0, pulse.duration), channel)]
        super().__init__(TimeslotOccupancy(slots))
        self._command = pulse
        self._channel = channel

    def duration(self):
        return self._command.duration

    @property
    def channelset(self) -> Set[PulseChannel]:
        return {self._channel}


class AcquirePulse(Pulse):
    """Pulse to acquire measurement result. """

    def __init__(self,
                 duration: int,
                 qubits: Union[Qubit, List[Qubit]],
                 mem_slots: Union[MemorySlot, List[MemorySlot]],
                 discriminator: Discriminator = None,
                 kernel: Kernel = None,
                 reg_slots: Union[RegisterSlot, List[RegisterSlot]] = None):
        if isinstance(qubits, Qubit):
            qubits = [qubits]
        if isinstance(mem_slots, MemorySlot):
            mem_slots = [mem_slots]
        if reg_slots:
            if isinstance(reg_slots, RegisterSlot):
                reg_slots = [reg_slots]
            if len(qubits) != len(reg_slots):
                raise PulseError("#reg_slots must be equals to #qubits")
        else:
            reg_slots = []
        # TODO: more precise time-slots
        slots = [Timeslot(Interval(0, duration), q.acquire) for q in qubits]
        slots.extend([Timeslot(Interval(0, duration), mem) for mem in mem_slots])
        super().__init__(TimeslotOccupancy(slots))
        self._command = Acquire(duration, discriminator, kernel)
        self._acquire_channels = [q.acquire for q in qubits]
        self._mem_slots = mem_slots
        self._reg_slots = reg_slots

    def duration(self):
        return self._command.duration

    @property
    def channelset(self) -> Set[PulseChannel]:
        channels = []
        channels.extend(self._acquire_channels)
        channels.extend(self._mem_slots)
        channels.extend(self._reg_slots)
        return {channels}


class FrameChangePulse(Pulse):
    """Pulse to acquire measurement result. """

    def __init__(self, phase: float, channel: OutputChannel):
        slots = [Timeslot(Interval(0, 0), channel)]
        super().__init__(TimeslotOccupancy(slots))
        self._command = FrameChange(phase)
        self._channel = channel

    def duration(self):
        return self._command.duration

    @property
    def channelset(self) -> Set[PulseChannel]:
        return {self._channel}


class PersistentValuePulse(Pulse):
    """Pulse to keep persistent value. """

    def __init__(self, value: complex, channel: OutputChannel):
        slots = [Timeslot(Interval(0, 0), channel)]
        super().__init__(TimeslotOccupancy(slots))
        self._command = PersistentValue(value)
        self._channel = channel

    def duration(self):
        return self._command.duration

    @property
    def channelset(self) -> Set[PulseChannel]:
        return {self._channel}


class SnapshotPulse(Pulse):
    """Pulse to keep persistent value. """

    def __init__(self, label: str, snap_type: str):
        slots = [Timeslot(Interval(0, 0), SnapshotChannel())]
        super().__init__(TimeslotOccupancy(slots))
        self._command = Snapshot(label, snap_type)

    def duration(self):
        return self._command.duration

    @property
    def channelset(self) -> Set[PulseChannel]:
        return {self._channel}


class MeasurementPulse(Pulse):
    """Pulse to drive a measurement pulse shape and acquire the results to a `Qubit`. """

    def __init__(self,
                 shapes: Union[SamplePulse, List[SamplePulse]],
                 qubits: Union[Qubit, List[Qubit]],
                 mem_slots: Union[MemorySlot, List[MemorySlot]],
                 discriminator: Discriminator = None,
                 kernel: Kernel = None,
                 reg_slots: Union[RegisterSlot, List[RegisterSlot]] = None):
        if isinstance(shapes, SamplePulse):
            shapes = [shapes]
        if len(shapes) != len(qubits):
            raise PulseError("#pulses must be equals to #qubits")
        if reg_slots:
            if len(qubits) != len(reg_slots):
                raise PulseError("#reg_slots must be equals to #qubits")
        self._drive_pulses = []
        for shape, q in zip(shapes, qubits):
            self._drive_pulses.append(DrivePulse(shape, q.measure))
        # TODO: check if all of the meas_pulse duration is the same
        self._acquire_pulse = AcquirePulse(shapes[0].duration,
                                           qubits,
                                           discriminator,
                                           kernel,
                                           reg_slots)

        durations = [shape.duration for shape in shapes]
        # TODO: more precise time-slots
        slots = [Timeslot(Interval(0, dur), q.measure) for dur, q in zip(durations, qubits)]
        slots.extend([Timeslot(Interval(0, dur), q.acquire) for dur, q in zip(durations, qubits)])
        slots.extend([Timeslot(Interval(0, dur), mem) for dur, mem in zip(durations, mem_slots)])
        super().__init__(TimeslotOccupancy(slots))

    def duration(self):
        return self._acquire_pulse.duration

    @property
    def channelset(self) -> Set[PulseChannel]:
        channels = []
        for pulse in self._drive_pulses:
            channels.extend(pulse.channelset)
        channels.extend(self._acquire_pulse.channelset)
        return {channels}
