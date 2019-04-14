# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Configurations for pulse experiments.
"""
from typing import List


class UserLoDict:
    """Dictionary of user LO frequency by channel"""

    def __init__(self, qubit_lo_freq: List[float], meas_lo_freq: List[float]):
        self._qubit_lo_freq = tuple(qubit_lo_freq)
        self._meas_lo_freq = tuple(meas_lo_freq)

    @property
    def qubit_lo_freq(self):
        """ Qubit LO frequency."""
        return self._qubit_lo_freq

    @property
    def meas_lo_freq(self):
        """ Measurement LO frequency."""
        return self._meas_lo_freq
