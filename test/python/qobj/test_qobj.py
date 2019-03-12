# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.


"""Qobj tests."""

import copy
import uuid

import jsonschema

from qiskit import BasicAer
from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
from qiskit.compiler import assemble_circuits, RunConfig
from qiskit.providers.basicaer import basicaerjob
from qiskit.qobj import PulseQobjConfig, PulseQobjExperiment, PulseQobjInstruction, PulseQobjHeader
from qiskit.qobj import QASMQobj, PulseQobj
from qiskit.qobj import QASMQobjConfig, QASMQobjExperiment, QASMQobjInstruction, QASMQobjHeader
from qiskit.qobj import QobjPulseLibrary, QobjMeasurementOption
from qiskit.qobj import validate_qobj_against_schema
from qiskit.qobj.exceptions import SchemaValidationError
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeRueschlikon


class TestQASMQobj(QiskitTestCase):
    """Tests for QASMQobj."""

    def setUp(self):
        self.valid_qobj = QASMQobj(
            qobj_id='12345',
            header=QASMQobjHeader(),
            config=QASMQobjConfig(shots=1024, memory_slots=2, max_credits=10),
            experiments=[
                QASMQobjExperiment(instructions=[
                    QASMQobjInstruction(name='u1', qubits=[1], params=[0.4]),
                    QASMQobjInstruction(name='u2', qubits=[1], params=[0.4, 0.2])
                ])
            ]
        )

        self.valid_dict = {
            'qobj_id': '12345',
            'type': 'QASM',
            'schema_version': '1.1.0',
            'header': {},
            'config': {'max_credits': 10, 'memory_slots': 2, 'shots': 1024},
            'experiments': [
                {'instructions': [
                    {'name': 'u1', 'params': [0.4], 'qubits': [1]},
                    {'name': 'u2', 'params': [0.4, 0.2], 'qubits': [1]}
                ]}
            ],
        }

        self.bad_qobj = copy.deepcopy(self.valid_qobj)
        self.bad_qobj.experiments = None  # set experiments to None to cause the qobj to be invalid

    def test_as_dict_against_schema(self):
        """Test dictionary representation of Qobj against its schema."""
        try:
            validate_qobj_against_schema(self.valid_qobj)
        except jsonschema.ValidationError as validation_error:
            self.fail(str(validation_error))

    def test_from_dict_per_class(self):
        """Test Qobj and its subclass representations given a dictionary."""
        test_parameters = {
            QASMQobj: (
                self.valid_qobj,
                self.valid_dict
            ),
            QASMQobjConfig: (
                QASMQobjConfig(shots=1, memory_slots=2),
                {'shots': 1, 'memory_slots': 2}
            ),
            QASMQobjExperiment: (
                QASMQobjExperiment(
                    instructions=[QASMQobjInstruction(name='u1', qubits=[1], params=[0.4])]),
                {'instructions': [{'name': 'u1', 'qubits': [1], 'params': [0.4]}]}
            ),
            QASMQobjInstruction: (
                QASMQobjInstruction(name='u1', qubits=[1], params=[0.4]),
                {'name': 'u1', 'qubits': [1], 'params': [0.4]}
            )
        }

        for qobj_class, (qobj_item, expected_dict) in test_parameters.items():
            with self.subTest(msg=str(qobj_class)):
                self.assertEqual(qobj_item, qobj_class.from_dict(expected_dict))

    def test_simjob_raises_error_when_sending_bad_qobj(self):
        """Test SimulatorJob is denied resource request access when given an invalid Qobj instance.
        """
        job_id = str(uuid.uuid4())
        backend = FakeRueschlikon()
        self.bad_qobj.header = QASMQobjHeader(backend_name=backend.name())

        with self.assertRaises(SchemaValidationError):
            job = basicaerjob.BasicAerJob(backend, job_id, _nop, self.bad_qobj)
            job.submit()

    def test_change_qobj_after_compile(self):
        """Test modifying Qobj parameters after compile."""
        qr = QuantumRegister(3)
        cr = ClassicalRegister(3)
        qc1 = QuantumCircuit(qr, cr)
        qc2 = QuantumCircuit(qr, cr)
        qc1.h(qr[0])
        qc1.cx(qr[0], qr[1])
        qc1.cx(qr[0], qr[2])
        qc2.h(qr)
        qc1.measure(qr, cr)
        qc2.measure(qr, cr)
        circuits = [qc1, qc2]
        backend = BasicAer.get_backend('qasm_simulator')
        qobj1 = assemble_circuits(circuits, RunConfig(backend=backend, shots=1024, seed=88))
        qobj1.experiments[0].config.shots = 50
        qobj1.experiments[1].config.shots = 1
        self.assertTrue(qobj1.experiments[0].config.shots == 50)
        self.assertTrue(qobj1.experiments[1].config.shots == 1)
        self.assertTrue(qobj1.config.shots == 1024)


class TestPulseQobj(QiskitTestCase):
    """Tests for PulseQobj."""

    def setUp(self):
        self.valid_qobj = PulseQobj(
            qobj_id='12345',
            header=PulseQobjHeader(),
            config=PulseQobjConfig(shots=1024, memory_slots=2, max_credits=10,
                                   meas_level=1,
                                   memory_slot_size=8192,
                                   meas_return='avg',
                                   pulse_library=[
                                       QobjPulseLibrary(name='pulse0',
                                                        samples=[0.0 + 0.0j,
                                                                 0.5 + 0.0j,
                                                                 0.0 + 0.0j])
                                   ],
                                   qubit_lo_freq=[4.9],
                                   meas_lo_freq=[6.9],
                                   rep_time=1000),
            experiments=[
                PulseQobjExperiment(instructions=[
                    PulseQobjInstruction(name='pulse0', t0=0, ch='d0'),
                    PulseQobjInstruction(name='fc', t0=5, ch='d0', phase=1.57),
                    PulseQobjInstruction(name='pv', t0=10, ch='d0', val=0.1 + 0.0j),
                    PulseQobjInstruction(name='acquire', t0=15, duration=5,
                                         qubits=[0], memory_slot=[0],
                                         kernels=[
                                             QobjMeasurementOption(name='boxcar',
                                                                   params={"start_window": 0,
                                                                           "stop_window": 5})
                                         ])
                    ])
            ]
        )
        self.valid_dict = {
            'qobj_id': '12345',
            'type': 'PULSE',
            'schema_version': '1.1.0',
            'header': {},
            'config': {'max_credits': 10, 'memory_slots': 2, 'shots': 1024,
                       'meas_level': 1,
                       'memory_slot_size': 8192,
                       'meas_return': 'avg',
                       'pulse_library': [{'name': 'pulse0',
                                          'samples': [[0.0, 0.0],
                                                      [0.5, 0.0],
                                                      [0.0, 0.0]]}
                                         ],
                       'qubit_lo_freq': [4.9],
                       'meas_lo_freq': [6.9],
                       'rep_time': 1000,
                       'meas_return': 'avg'
                       },
            'experiments': [
                {'instructions': [
                    {'name': 'pulse0', 't0': 0, 'ch': 'd0'},
                    {'name': 'fc', 't0': 5, 'ch': 'd0', 'phase': 1.57},
                    {'name': 'pv', 't0': 10, 'ch': 'd0', 'val': [0.1, 0.0]},
                    {'name': 'acquire', 't0': 15, 'duration': 5,
                     'qubits': [0], 'memory_slot': [0],
                     'kernels': [{'name': 'boxcar',
                                  'params': {'start_window': 0,
                                             'stop_window': 5}}
                                 ]
                     }
                ]}
            ]
        }

    def test_as_dict_against_schema(self):
        """Test dictionary representation of Qobj against its schema."""
        try:
            validate_qobj_against_schema(self.valid_qobj)
        except jsonschema.ValidationError as validation_error:
            self.fail(str(validation_error))

    def test_from_dict_per_class(self):
        """Test Qobj and its subclass representations given a dictionary."""
        test_parameters = {
            PulseQobj: (
                self.valid_qobj,
                self.valid_dict
            ),
            PulseQobjConfig: (
                PulseQobjConfig(meas_level=1,
                                memory_slot_size=8192,
                                meas_return='avg',
                                pulse_library=[
                                    QobjPulseLibrary(name='pulse0', samples=[0.1 + 0.0j])
                                ],
                                qubit_lo_freq=[4.9], meas_lo_freq=[6.9],
                                rep_time=1000),
                {'meas_level': 1,
                 'memory_slot_size': 8192,
                 'meas_return': 'avg',
                 'pulse_library': [{'name': 'pulse0', 'samples': [[0.1, 0.0]]}],
                 'qubit_lo_freq': [4.9],
                 'meas_lo_freq': [6.9],
                 'rep_time': 1000}
            ),
            QobjPulseLibrary: (
                QobjPulseLibrary(name='pulse0', samples=[0.1 + 0.0j]),
                {'name': 'pulse0', 'samples': [[0.1, 0.0]]}
            ),
            PulseQobjExperiment: (
                PulseQobjExperiment(
                    instructions=[PulseQobjInstruction(name='pulse0', t0=0, ch='d0')]),
                {'instructions': [{'name': 'pulse0', 't0': 0, 'ch': 'd0'}]}
            ),
            PulseQobjInstruction: (
                PulseQobjInstruction(name='pulse0', t0=0, ch='d0'),
                {'name': 'pulse0', 't0': 0, 'ch': 'd0'}
            )
        }

        for qobj_class, (qobj_item, expected_dict) in test_parameters.items():
            with self.subTest(msg=str(qobj_class)):
                self.assertEqual(qobj_item, qobj_class.from_dict(expected_dict))


def _nop():
    pass
