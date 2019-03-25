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
from .timeslots import TimeslotOccupancy

logger = logging.getLogger(__name__)


class ScheduleNode(metaclass=ABCMeta):
    """Common interface for nodes of a schedule tree. """

    def __init__(self,
                 t0: int,
                 parent: 'ScheduleNode' = None,
                 children: List['ScheduleNode'] = None):
        self._t0 = t0
        self._parent = parent
        self._children = children

    @property
    def t0(self) -> int:
        """Relative begin time of this pulse. """
        return self._t0

    @property
    def parent(self) -> Optional['ScheduleNode']:
        """Parent node of this schedule node. """
        return self._parent

    @property
    def children(self) -> Optional[List['ScheduleNode']]:
        """Child nodes of this schedule node. """
        return self._children

    @abstractmethod
    def begin_time(self) -> int:
        """Absolute begin time of this schedule node. """
        pass

    @abstractmethod
    def end_time(self) -> int:
        """Absolute end time of this schedule node. """
        pass

    @abstractmethod
    def duration(self) -> int:
        """Duration of this schedule node. """
        pass


class TimedPulse(ScheduleNode):
    """A `Pulse` with begin time relative to its parent,
    which is a leaf in a schedule tree."""

    def __init__(self, t0: int, pulse: Pulse, parent: ScheduleNode):
        super().__init__(t0, parent)
        self._pulse = pulse
        self._parent = parent

    @property
    def pulse(self) -> Pulse:
        return self._pulse

    def begin_time(self) -> int:
        """Absolute begin time of this pulse. """
        t0 = self._t0
        point = self._parent
        while point:
            t0 += point.t0
            point = point.parent
        return t0

    def end_time(self) -> int:
        """Absolute end time of this pulse. """
        return self.begin_time() + self.duration()

    def duration(self) -> int:
        """Duration of this pulse. """
        return self._pulse.duration()

    def __str__(self):
        return "(%s, %d)" % (self._pulse, self._t0)


class Schedule(ScheduleNode, Pulse):
    """Schedule of pulses with timing. The root of a schedule tree."""

    def __init__(self,
                 device: DeviceSpecification,
                 schedules: List[Tuple[int, Pulse]] = None,
                 name: str = None
                 ):
        """Create schedule.

        Args:
            device:
            schedules:
            name:
        """
        super().__init__(0)
        self._device = device
        self._name = name
        self._occupancy = TimeslotOccupancy(timeslots=[])
        self._children = []
        if schedules:
            for t0, pulse in schedules:
                if isinstance(pulse, Schedule):
                    raise NotImplementedError("This version doesn't support schedule of schedules.")
                elif isinstance(pulse, Pulse):
                    self.insert(t0, pulse)
                else:
                    raise ScheduleError("Invalid to be scheduled: %s", pulse.__class__.__name__)

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
        # self._check_channels(pulse)
        if isinstance(pulse, Schedule):
            raise NotImplementedError("This version doesn't support schedule of schedules.")
        elif isinstance(pulse, Pulse):
            shifted = pulse.occupancy.shifted(t0)
            if self._occupancy.is_mergeable_with(shifted):
                self._occupancy = self._occupancy.merged(shifted)
                self._children.append(TimedPulse(t0, pulse, parent=self))
            else:
                logger.warning("Fail to insert %s at %s due to timing overlap", pulse, t0)
                raise ScheduleError("Fail to insert %s at %s due to overlap" % (str(pulse), t0))
        else:
            raise ScheduleError("Invalid to be inserted: %s", pulse.__class__.__name__)

    def append(self, pulse: Pulse):
        """Append a new pulse on a channel at the timing
        just after the last pulse finishes.

        Args:
            pulse (Pulse):
        """
        # self._check_channels(pulse)
        if isinstance(pulse, Schedule):
            raise NotImplementedError("This version doesn't support schedule of schedules.")
        elif isinstance(pulse, Pulse):
            t0 = self.end_time()
            try:
                self.insert(t0, pulse)
            except ScheduleError:
                logger.warning("Fail to append %s due to timing overlap", pulse)
                raise ScheduleError("Fail to append %s due to overlap" % str(pulse))
        else:
            raise ScheduleError("Invalid to be appended: %s", pulse.__class__.__name__)

    def begin_time(self) -> int:
        return 0

    def end_time(self) -> int:
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version doesn't support schedule of schedules.")
        # This implementation only works for flat schedule
        return max([child.end_time() for child in self._children], default=0)

    def duration(self) -> int:
        return self.end_time()

    def _check_channels(self, pulse: Pulse):
        if isinstance(pulse, Schedule):
            # if pulse._device != self._device:
            #     raise ScheduleError("Additional schedule must have same device as self")
            raise NotImplementedError("This version doesn't support schedule of schedules.")
        else:
            # check if all the channels of pulse are defined in the device
            for ch in pulse.channelset:
                if not self._device.has_channel(ch):
                    raise ScheduleError("%s has no channel %s", self._device, ch)

    def __str__(self):
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version doesn't support schedule of schedules.")
        dic = defaultdict(list)
        for c in self._children:
            dic[c.channel.name].append(str(c))
        return pprint.pformat(dic)

    def get_sample_pulses(self) -> List[PulseCommand]:
        # TODO: Handle schedule of schedules
        for child in self._children:
            if not isinstance(child, TimedPulse):
                raise NotImplementedError("This version doesn't support schedule of schedules.")
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
                raise NotImplementedError("This version doesn't support schedule of schedules.")
        return self._children
