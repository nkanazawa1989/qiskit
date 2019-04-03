# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Configured Schedule.
"""
from .experiment_config import ScheduleConfig
from .pulse_schedule import Schedule


class ConfiguredSchedule:
    """ConfiguredSchedule = Schedule + Configurations for experiment."""

    def __init__(self, schedule: Schedule, config: ScheduleConfig = None, name: str = None):
        self._schedule = schedule
        self._config = config or ScheduleConfig()
        self._name = name or schedule.name

    @property
    def schedule(self):
        return self._schedule

    @property
    def config(self):
        return self._config

    @property
    def name(self):
        return self._name
