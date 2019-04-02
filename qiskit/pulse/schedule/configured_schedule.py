# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Configured Schedule.
"""
from .experiment_config import LoConfig
from .pulse_schedule import Schedule


class ConfiguredSchedule:
    """ConfiguredSchedule = Schedule + Configurations for experiment."""

    def __init__(self, schedule: Schedule, lo_conf: LoConfig = None, name: str = None):
        self._schedule = schedule
        self._lo_conf = lo_conf or LoConfig()
        self._name = name or schedule.name

    @property
    def schedule(self):
        return self._schedule

    @property
    def lo_config(self):
        return self._lo_conf

    @property
    def name(self):
        return self._name
