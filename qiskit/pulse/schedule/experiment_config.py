# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Configurations for pulse experiments.
"""
import copy
from typing import Dict, List
from qiskit.pulse.channels import OutputChannel


class ScheduleConfig:
    """Configurations for user LO frequencies."""

    def __init__(self, user_lo_dic: Dict[OutputChannel, float] = None):
        self._user_lo_dic = {}
        if user_lo_dic:
            for channel, user_lo in user_lo_dic.items():
                # TODO: lo_range check
                self._user_lo_dic[channel] = user_lo

    @property
    def user_lo_dic(self):
        return self._user_lo_dic

    def replaced_with_user_los(self, default_los: List[float]):
        """Return user LO frequencies replaced from `default_los`.

        Args:
            default_los: default LO frequencies to be replaced

        Returns:
            List: user LO frequencies
        """
        res = copy.copy(default_los)
        for channel, user_lo in self._user_lo_dic.items():
            res[channel.index] = user_lo
        return res
