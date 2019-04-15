# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
Configurations for pulse experiments.
"""
from typing import Dict
from .channels.output_channel import OutputChannel


class UserLoDict:
    """Dictionary of user LO frequency by channel"""

    def __init__(self,
                 qubit_lo_freq: Dict[OutputChannel, float],
                 meas_lo_freq: Dict[OutputChannel, float]
                 ):
        self._qubit_lo_freq = qubit_lo_freq
        self._meas_lo_freq = meas_lo_freq

    @property
    def qubit_lo_freq(self):
        """ Qubit LO frequency."""
        qubit_lo_freq = tuple(val for val in self._qubit_lo_freq.values())

        return qubit_lo_freq

    @property
    def meas_lo_freq(self):
        """ Measurement LO frequency."""
        meas_lo_freq = tuple(val for val in self._meas_lo_freq.values())

        return meas_lo_freq
