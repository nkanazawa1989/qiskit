# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""RunningPassManager class for the transpiler.
This object holds the state of a pass manager during running-time."""
from __future__ import annotations

import inspect
import logging
from functools import wraps
from typing import Callable, Any

from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.passmanager.base_optimization_tasks import OptimizerTask
from qiskit.passmanager.exceptions import PassManagerError
from qiskit.utils.deprecation import deprecate_func

# pylint: disable=unused-import
from qiskit.passmanager.flow_controllers import (
    FlowController,
    FlowControllerLiner,
    # for backward compatibility
    ConditionalController,
    DoWhileController,
)

from .basepasses import BasePass
from .exceptions import TranspilerError
from .layout import TranspileLayout

logger = logging.getLogger(__name__)


class RunningPassManager(FlowControllerLiner):
    """A RunningPassManager is a running pass manager.

    .. warning::

        :class:`.RunningPassManager` will be deprecated in the future release.
        As of Qiskit Terra 0.25 this class becomes a subclass of the flow controller
        with extra methods for backward compatibility.
        Relying on a subclass of the running pass manager might break your code stack.
    """

    @deprecate_func(
        since="0.25",
        additional_msg="Now RunningPassManager is a subclass of flow controller.",
        pending=True,
    )
    def append(
        self,
        passes: OptimizerTask | list[OptimizerTask],
        **flow_controller_conditions,
    ):
        """Append a passes to the schedule of passes.

        Args:
            passes: A set of passes (a pass set) to be added to schedule. A pass set is a list of
                passes that are controlled by the same flow controller. If a single pass is
                provided, the pass set will only have that pass a single element.
                It is also possible to append a :class:`.BaseFlowController` instance and
                the rest of the parameter will be ignored.
            flow_controller_conditions: Dictionary of control flow plugins.
                Following built-in controllers are available by default:

                * do_while: The passes repeat until the callable returns False.
                * condition: The passes run only if the callable returns True.
        """
        # Backward compatibility.
        normalized_controller = FlowController(
            passes=passes,
            options=self._options,
            **flow_controller_conditions,
        )
        self.pipeline.append(normalized_controller)

    # pylint: disable=arguments-differ
    def run(
        self,
        circuit: QuantumCircuit,
        output_name: str = None,
        callback: Callable = None,
    ) -> QuantumCircuit:
        """Run all the passes on a QuantumCircuit

        Args:
            circuit: Circuit to transform via all the registered passes.
            output_name: The output circuit name. If not given, the same as the input circuit.
            callback: A callback function that will be called after each pass execution.

        Returns:
            QuantumCircuit: Transformed circuit.
        """
        self.callback = callback
        passmanager_ir = circuit_to_dag(circuit)
        passmanager_ir = super().execute(passmanager_ir=passmanager_ir)

        out_circuit = dag_to_circuit(passmanager_ir, copy_operations=False)
        out_circuit.name = output_name

        if self.property_set["layout"] is not None:
            circuit._layout = TranspileLayout(
                initial_layout=self.property_set["layout"],
                input_qubit_mapping=self.property_set["original_qubit_indices"],
                final_layout=self.property_set["final_layout"],
            )
        circuit._clbit_write_latency = self.property_set["clbit_write_latency"]
        circuit._conditional_latency = self.property_set["conditional_latency"]

        if self.property_set["node_start_time"]:
            # This is dictionary keyed on the DAGOpNode, which is invalidated once
            # dag is converted into circuit. So this schedule information is
            # also converted into list with the same ordering with circuit.data.
            topological_start_times = []
            start_times = self.property_set["node_start_time"]
            for dag_node in passmanager_ir.topological_op_nodes():
                topological_start_times.append(start_times[dag_node])
            circuit._op_start_times = topological_start_times

        return circuit

    def _finalize(
        self,
        task: BasePass,
        passmanager_ir: Any,
        running_time: float,
    ):
        self.valid_passes.add(task)
        if not task.is_analysis_pass:
            # Analysis passes preserve all
            self.valid_passes.intersection_update(set(task.preserves))

        if self._callback is not None:
            # Use old signature for backward compatibility.
            # Count information is dropped because pass execution management is moved to
            # pass flow controller, and count cannot be accumulated.
            self._callback(
                pass_=task,
                dag=passmanager_ir,
                time=running_time,
                property_set=self.property_set,
                count=None,
            )


# A temporary error handling with slight overhead at class loading.
# This method wraps all class methods to replace PassManagerError with TranspilerError.
# The pass flow controller mechanics raises PassManagerError, as it has been moved to base class.
# PassManagerError is not caught by TranspilerError due to the hierarchy.


def _replace_error(meth):
    @wraps(meth)
    def wrapper(*meth_args, **meth_kwargs):
        try:
            return meth(*meth_args, **meth_kwargs)
        except PassManagerError as ex:
            raise TranspilerError(ex.message) from ex

    return wrapper


for _name, _method in inspect.getmembers(RunningPassManager, predicate=inspect.isfunction):
    if _name.startswith("_"):
        # Ignore protected and private.
        # User usually doesn't directly execute and catch error from these methods.
        continue
    _wrapped = _replace_error(_method)
    setattr(RunningPassManager, _name, _wrapped)
