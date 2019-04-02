# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Configurations for experiments.
"""
import copy
from typing import Dict, List
from qiskit.pulse.channels import OutputChannel


class LoConfig:
    """Configurations for user LO frequencies."""

    def __init__(self, user_lo_dic: Dict[OutputChannel, float]):
        self._replace_dic = {}
        for channel, user_lo in user_lo_dic.items():
            # TODO: lo_range check
            self._replace_dic[channel] = user_lo

    def replaced(self, default_los: List[float]):
        res = copy.copy(default_los)
        for channel, user_lo in self._replace_dic.items():
            res[channel.index] = user_lo
        return res
