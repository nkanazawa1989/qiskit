# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
ScheduleComponent = Common interface for components of schedule (Instruction and Schedule).
"""
from abc import ABCMeta, abstractmethod
from typing import Tuple

from .timeslots import TimeslotOccupancy


class ScheduleComponent(metaclass=ABCMeta):
    """Common interface for components of schedule. """

    @property
    @abstractmethod
    def duration(self) -> int:
        """Duration of this schedule component. """
        pass

    @property
    @abstractmethod
    def occupancy(self) -> TimeslotOccupancy:
        """Occupied time slots by this schedule component. """
        pass

    @abstractmethod
    def shifted(self, shift: int) -> 'ScheduleComponent':
        """Return a new shifted schedule component by `shift`.

        Args:
            shift: time to be shifted

        Returns:
            ScheduleComponent: shifted schedule component
        """
        pass

    @property
    @abstractmethod
    def begin_time(self) -> int:
        """Relative begin time of this schedule component. """
        pass

    @property
    @abstractmethod
    def end_time(self) -> int:
        """Relative end time of this schedule component. """
        pass

    @property
    @abstractmethod
    def children(self) -> Tuple['ScheduleComponent', ...]:
        """Child nodes of this schedule component. """
        pass
