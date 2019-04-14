# -*- coding: utf-8 -*-

# Copyright 2019, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Test cases for the experimental conditions for pulse."""
import unittest

from qiskit.pulse import DeviceSpecification
from qiskit.pulse.exceptions import PulseError
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeOpenPulse2Q


class TestUserLoDict(QiskitTestCase):
    """UserLoDict tests."""

    def setUp(self):
        self.device = DeviceSpecification.create_from(FakeOpenPulse2Q())

    def test_can_create_empty_user_lo_dict(self):
        """Test if a UserLoDict can be created without no arguments.
        """
        user_lo_dict = self.device.create_lo_config({})
        self.assertEqual((), user_lo_dict.qubit_lo_freq)
        self.assertEqual((), user_lo_dict.meas_lo_freq)

    def test_can_create_valid_user_lo_dict(self):
        """Test if a UserLoDict can be created with valid user_los.
        """
        user_lo_dict = self.device.create_lo_config({
            self.device.q[0].drive: 5.2,
            self.device.q[0].measure: 7.1
        })
        self.assertEqual(5.2, user_lo_dict.qubit_lo_freq[0])
        self.assertEqual(7.1, user_lo_dict.meas_lo_freq[0])

    def test_fail_to_create_with_out_of_range_user_lo(self):
        """Test if a UserLoDict cannot be created with invalid user_los.
        """
        with self.assertRaises(PulseError):
            _ = self.device.create_lo_config({self.device.q[0].drive: 7.2})

    def test_keep_dict_unchanged_after_updating_the_dict_used_in_construction(self):
        """Test if a UserLoDict keeps its dictionary unchanged even after
        the dictionary used in construction is updated.
        """
        channel = self.device.q[0].drive
        original = {channel: 5.2}

        user_lo_dict = self.device.create_lo_config(original)
        self.assertEqual(5.2, user_lo_dict.qubit_lo_freq[0])

        original[channel] = 5.4
        self.assertEqual(5.2, user_lo_dict.qubit_lo_freq[0])


if __name__ == '__main__':
    unittest.main()
