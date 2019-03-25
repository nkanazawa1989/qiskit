# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Timeslot occupancy for each channels.
"""
import logging
from collections import defaultdict
from typing import List, Optional, Set

from qiskit.pulse.channels import PulseChannel
from qiskit.pulse.exceptions import PulseError

logger = logging.getLogger(__name__)


class Interval:
    """Time interval."""

    def __init__(self, begin: int, duration: int):
        """Create an interval = (begin, end (= begin + duration))

        Args:
            begin: begin time of this interval
            duration: duration of this interval
        """
        self._begin = begin
        self._end = begin + duration

    @property
    def begin(self):
        return self._begin

    @property
    def end(self):
        return self._end

    @property
    def duration(self):
        return self._end - self._begin

    def has_overlap(self, interval: 'Interval'):
        if self.begin < interval.end and interval.begin < self.end:
            return True

    def shifted(self, time: int) -> 'Interval':
        return Interval(self.begin + time, self.duration)


class Timeslot:
    """Namedtuple of (Interval, PulseChannel)."""

    def __init__(self, interval: Interval, channel: PulseChannel):
        """Create a timeslot.

        Args:
            interval:
            channel:
        """
        self._interval = interval
        self._channel = channel

    @property
    def interval(self):
        return self._interval

    @property
    def channel(self):
        return self._channel


class TimeslotOccupancy:
    """Timeslot occupancy for each channels."""

    def __init__(self, timeslots: List[Timeslot]):
        """Create a timeslot occupancy.

        Args:
            timeslot:
        """
        self._timeslots = timeslots
        self._table = defaultdict(list)
        for slot in timeslots:
            for interval in self._table[slot.channel]:
                if slot.interval.has_overlap(interval):
                    raise PulseError("Cannot create TimeslotOccupancy from overlapped timeslots")
            self._table[slot.channel].append(slot.interval)

    @property
    def timeslots(self):
        return self._timeslots

    @property
    def channelset(self) -> Set[PulseChannel]:
        return {key for key in self._table.keys()}

    def is_mergeable_with(self, occupancy: 'TimeslotOccupancy') -> bool:
        """Return if self is mergeable with a specified `occupancy` or not.

        Args:
            occupancy: TimeslotOccupancy to be checked

        Returns:
            True if self is mergeable with `occupancy`, otherwise False.
        """
        for slot in occupancy.timeslots:
            for interval in self._table[slot.channel]:
                if slot.interval.has_overlap(interval):
                    return False
        return True

    def merged(self, occupancy: 'TimeslotOccupancy') -> Optional['TimeslotOccupancy']:
        """Return a new TimeslotOccupancy merged with a specified `occupancy`

        Args:
            occupancy: TimeslotOccupancy to be merged

        Returns:
            A new TimeslotOccupancy object merged with a specified `occupancy`.
        """
        timeslots = [Timeslot(slot.interval, slot.channel) for slot in self.timeslots]
        timeslots.extend([Timeslot(slot.interval, slot.channel) for slot in occupancy.timeslots])
        return TimeslotOccupancy(timeslots)

    def shifted(self, time: int) -> 'TimeslotOccupancy':
        """Return a new TimeslotOccupancy shifted by a non-negative `time`.

        Args:
            time:

        Returns:
            A new TimeslotOccupancy object shifted by a `time`.
        """
        """Return  """
        if time < 0:
            raise PulseError("Cannot shift TimeslotOccupancy by negative time")
        timeslots = []
        for slot in self.timeslots:
            timeslots.append(Timeslot(slot.interval.shifted(time), slot.channel))
        return TimeslotOccupancy(timeslots)
