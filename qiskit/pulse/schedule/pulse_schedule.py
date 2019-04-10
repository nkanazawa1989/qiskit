# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Schedule.
"""
import logging
from copy import copy
from typing import List, Tuple, Dict, Any

from qiskit.pulse.common.interfaces import ScheduleComponent
from qiskit.pulse.common.timeslots import TimeslotOccupancy
from qiskit.pulse.exceptions import PulseError

logger = logging.getLogger(__name__)


class Schedule(ScheduleComponent):
    """Schedule of instructions. The composite node of a schedule tree."""

    def __init__(self, name: str = None, begin_time: int = 0):
        """Create empty schedule.

        Args:
            name (str, optional): Name of this schedule. Defaults to None.
            begin_time (int, optional): Begin time of this schedule. Defaults to 0.
        """
        self._name = name
        self._begin_time = begin_time
        self._occupancy = TimeslotOccupancy(timeslots=[])
        self._children = ()

    @property
    def name(self) -> str:
        """Name of this schedule."""
        return self._name

    def insert(self, begin_time: int, schedule: ScheduleComponent):
        """Return a new schedule with inserting a `schedule` at `begin_time`.

        Args:
            begin_time (int): time to be inserted
            schedule (ScheduleComponent): schedule to be inserted

        Returns:
            ScheduleComponent: a new schedule inserted a `schedule` at `begin_time`

        Raises:
            PulseError: when an invalid schedule is specified or failed to insert
        """
        if not isinstance(schedule, ScheduleComponent):
            raise PulseError("Invalid to be inserted: %s" % schedule.__class__.__name__)
        news = copy(self)
        try:
            news._insert(begin_time, schedule)
        except PulseError as err:
            raise PulseError(err.message)
        return news

    def _insert(self, begin_time: int, schedule: ScheduleComponent):
        """Insert a new `schedule` at `begin_time`.
        Args:
            begin_time (int): begin time of the schedule
            schedule (ScheduleComponent): schedule to be inserted
        Raises:
            PulseError: when an invalid schedule is specified or failed to insert
        """
        if schedule == self:
            raise PulseError("Cannot insert self to avoid infinite recursion")
        shifted = schedule.occupancy.shifted(begin_time)
        if self._occupancy.is_mergeable_with(shifted):
            self._occupancy = self._occupancy.merged(shifted)
            self._children += (schedule.shifted(begin_time),)
        else:
            logger.warning("Fail to insert %s at %s due to timing overlap", schedule, begin_time)
            raise PulseError("Fail to insert %s at %s due to overlap" % (str(schedule), begin_time))

    def append(self, schedule: ScheduleComponent):
        """Return a new schedule with appending a `schedule` at the timing
        just after the last instruction finishes.

        Args:
            schedule (ScheduleComponent): schedule to be appended

        Returns:
            ScheduleComponent: a new schedule appended a `schedule`

        Raises:
            PulseError: when an invalid schedule is specified or failed to append
        """
        if not isinstance(schedule, ScheduleComponent):
            raise PulseError("Invalid to be appended: %s" % schedule.__class__.__name__)
        news = copy(self)
        try:
            news._insert(self.end_time, schedule)
        except PulseError:
            logger.warning("Fail to append %s due to timing overlap", schedule)
            raise PulseError("Fail to append %s due to overlap" % str(schedule))
        return news

    @property
    def duration(self) -> int:
        return self.end_time - self.begin_time

    @property
    def occupancy(self) -> TimeslotOccupancy:
        return self._occupancy

    def shifted(self, shift: int) -> ScheduleComponent:
        news = copy(self)
        news._begin_time += shift
        news._occupancy = self._occupancy.shifted(shift)
        return news

    @property
    def begin_time(self) -> int:
        return self._begin_time

    @property
    def end_time(self) -> int:
        return max([slot.interval.end for slot in self._occupancy.timeslots],
                   default=self._begin_time)

    @property
    def children(self) -> Tuple[ScheduleComponent, ...]:
        return self._children

    def __add__(self, schedule: ScheduleComponent):
        return self.append(schedule)

    def __or__(self, schedule: ScheduleComponent):
        return self.insert(0, schedule)

    def __lshift__(self, shift: int) -> ScheduleComponent:
        return self.shifted(shift)

    def __str__(self):
        # TODO: Handle schedule of schedules
        for child in self._children:
            if child.children:
                raise NotImplementedError("This version doesn't support schedule of schedules.")
        return '\n'.join([str(child) for child in self._children])

    @property
    def to_dict(self) -> Dict[str, Any]:
        """Schedule is not used to create PulseQobjInstruction."""
        return {}

    def flat_instruction_sequence(self) -> List[ScheduleComponent]:
        """Return instruction sequence of this schedule.
        Each instruction has absolute begin time.
        """
        return [_ for _ in Schedule._flatten_generator(self, self.begin_time)]

    @staticmethod
    def _flatten_generator(node: ScheduleComponent, time: int):
        if node.children:
            for child in node.children:
                yield from Schedule._flatten_generator(child, time + node.begin_time)
        else:
            yield node.shifted(time)
