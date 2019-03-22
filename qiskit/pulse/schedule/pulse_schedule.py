# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Schedule.
"""
import logging
import pprint
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from typing import List, Optional, Tuple, Union

from qiskit.pulse import DeviceSpecification
from qiskit.pulse.commands import PulseCommand, SamplePulse
from qiskit.pulse.exceptions import ScheduleError
from .pulses import Pulse

logger = logging.getLogger(__name__)


class ScheduleNode(metaclass=ABCMeta):
    """Common interface for nodes of a schedule tree. """

    @abstractmethod
    def begin_time(self) -> int:
        pass

    @abstractmethod
    def end_time(self) -> int:
        pass

    @abstractmethod
    def duration(self) -> int:
        pass

    @abstractmethod
    def parent(self) -> Optional['ScheduleNode']:
        pass

    @abstractmethod
    def children(self) -> List['ScheduleNode']:
        pass


class TimedPulse(ScheduleNode):
    """A `Pulse` with begin time relative to its parent,
    which is a leaf in a schedule tree."""

    def __init__(self, t0: int, pulse: Pulse, parent: ScheduleNode):
        self._t0 = t0
        self._pulse = pulse
        self._parent = parent

    @property
    def pulse(self) -> Pulse:
        return self._pulse

    def begin_time(self) -> int:
        t0 = self._t0
        parent = self._parent
        while parent:
            t0 += parent.t0
            parent = parent.parent()
        return t0

    def end_time(self) -> int:
        return self.begin_time() + self.duration()

    def duration(self) -> int:
        return self._pulse.duration

    def parent(self) -> Optional[ScheduleNode]:
        return self._parent

    def children(self) -> List[ScheduleNode]:
        return []

    def __str__(self):
        return "(%s, %d)" % (self._pulse, self._t0)


class Schedule(ScheduleNode):
    """Schedule of pulses with timing. The root of a schedule tree."""

    def __init__(self,
                 device: DeviceSpecification,
                 schedules: Tuple[int, Union[Pulse, 'Schedule']] = None,
                 name: str = None
                 ):
        """Create schedule.

        Args:
            device:
            schedules:
            name:
        """
        self._device = device
        self._name = name
        self._children = []
        if schedules:
            for t0, pulse in schedules:
                if isinstance(pulse, Pulse):
                    # self._check_channels(pulse)
                    self.insert(t0, pulse)
                elif isinstance(pulse, Schedule):
                    raise NotImplementedError("This version doesn't support schedule of schedules.")
                    # if self._device is not pulse._device:
                    #     raise ScheduleError("Additional schedule must have same device as self")
                else:
                    raise ScheduleError("Non supported class: %s", pulse.__class__.__name__)

    @property
    def name(self) -> str:
        return self._name

    @property
    def device(self) -> DeviceSpecification:
        return self._device

    def insert(self, t0: int, pulse: Pulse):
        """Insert a new pulse at `begin_time`.

        Args:
            t0:
            pulse (Pulse):
        """
        try:
            self._add(TimedPulse(t0, pulse, parent=self))
        except ScheduleError as err:
            logger.warning("Fail to insert %s at %s", pulse, t0)
            raise ScheduleError(err.message)

    def _add(self, child: ScheduleNode):
        """Add a new child schedule node.

        Args:
            child:
        """
        if self._is_occupied_time(child):
            logger.warning("A pulse is not added due to the occupied timing: %s", str(child))
            raise ScheduleError("Cannot add to occupied time slot.")
        else:
            self._children.append(child)

    def begin_time(self) -> int:
        return 0

    def end_time(self) -> int:
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimedPulse.")
        # This implementation only works for flat schedule
        return max([child.end_time() for child in self._children], default=0)

    def duration(self) -> int:
        return self.end_time() - self.begin_time()

    def children(self) -> List[ScheduleNode]:
        return self._children

    def parent(self) -> Optional[ScheduleNode]:
        return None

    def _check_channels(self, pulse: Pulse):
        # check if all the channels of pulse are defined in the device
        for ch in pulse.channels:
            if not self._device._has_channel(ch):
                raise ScheduleError("%s has no channel %s", ch, self._device)

    def _is_occupied_time(self, timed_pulse) -> bool:
        # TODO: Handle schedule of schedules
        if not isinstance(timed_pulse, TimedPulse):
            raise NotImplementedError("This version assumes all children are TimedPulse.")
        # TODO: Improve implementation
        for tp in self.flat_pulse_sequence():
            if tp.pulse.channels == timed_pulse.pulse.channels:
                # interval check
                if tp.begin_time() < timed_pulse.end_time() \
                        and timed_pulse.begin_time() < tp.end_time():
                    return True
        return False

    def __str__(self):
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimedPulse.")
        dic = defaultdict(list)
        for c in self._children:
            dic[c.channel.name].append(str(c))
        return pprint.pformat(dic)

    def get_sample_pulses(self) -> List[PulseCommand]:
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimedPulse.")
        # TODO: Improve implementation (compute at add and remove would be better)
        lib = []
        for tp in self._children:
            if isinstance(tp.command, SamplePulse) and \
                    tp.command not in lib:
                lib.append(tp.command)
        return lib

    def flat_pulse_sequence(self) -> List[TimedPulse]:
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version assumes all children are TimedPulse.")
        return self._children
