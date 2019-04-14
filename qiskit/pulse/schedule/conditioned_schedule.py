# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Configured Schedule.
"""
from qiskit.pulse.configurations import UserLoDict
from .pulse_schedule import Schedule


class ConditionedSchedule:
    """ConditionedSchedule = Schedule + Conditions for experiment."""

    def __init__(self,
                 schedule: Schedule,
                 user_lo_dict: UserLoDict = None,
                 experiment_name: str = None):
        self._schedule = schedule
        self._user_lo_dict = user_lo_dict
        self._name = experiment_name or schedule.name

    @property
    def schedule(self):
        """Schedule."""
        return self._schedule

    @property
    def user_lo_dict(self):
        """Dictionary of local oscillator."""
        return self._user_lo_dict

    @property
    def name(self):
        """Name of experiment."""
        return self._name
