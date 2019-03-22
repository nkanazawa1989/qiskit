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
from typing import List, Union

from qiskit.pulse import Qubit
from qiskit.pulse.channels import PulseChannel, OutputChannel, MemorySlot, RegisterSlot
from qiskit.pulse.commands import (PulseCommand, SamplePulse, Acquire, Kernel, Discriminator,
                                   FrameChange, PersistentValue, Snapshot)
from qiskit.pulse.exceptions import PulseError

logger = logging.getLogger(__name__)


class Pulse(metaclass=ABCMeta):
    """Common interface for `Command with its operands (Channels)`. """

    @abstractmethod
    def __init__(self, command: PulseCommand, channels: List[PulseChannel]):
        self._command = command
        self._channels = channels
        # TODO: is this (Channel.supported) really needed?
        for channel in channels:
            if not isinstance(command, channel.__class__.supported):
                raise PulseError("%s (%s) is not supported on %s (%s)" % (
                    command.__class__.__name__, command.name,
                    channel.__class__.__name__, channel.name))

    @property
    def duration(self):
        return self._command.duration

    @property
    def channels(self):
        return self._channels


class DrivePulse(Pulse):
    """Pulse to drive a pulse shape to a `OutputChannel`. """

    def __init__(self, pulse: SamplePulse, channel: OutputChannel):
        super().__init__(pulse, [channel])


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
        if isinstance(reg_slots, RegisterSlot):
            reg_slots = [reg_slots]
        if reg_slots:
            if len(qubits) != len(reg_slots):
                raise PulseError("#reg_slots must be equals to #qubits")
        command = Acquire(duration, discriminator, kernel)
        channels = [q.acquire for q in qubits]
        channels.extend(mem_slots)
        channels.extend(reg_slots)
        super().__init__(command, channels)


class FrameChangePulse(Pulse):
    """Pulse to acquire measurement result. """

    def __init__(self, phase: float, channel: OutputChannel):
        super().__init__(FrameChange(phase), [channel])


class PersistentValuePulse(Pulse):
    """Pulse to keep persistent value. """

    def __init__(self, value: complex, channel: OutputChannel):
        super().__init__(PersistentValue(value), [channel])


class SnapshotPulse(Pulse):
    """Pulse to keep persistent value. """

    def __init__(self, label: str, snap_type: str):
        super().__init__(Snapshot(label, snap_type), [])
