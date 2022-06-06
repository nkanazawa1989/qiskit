# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=invalid-name

"""Symbolic waveform module.

These are pulses which are described by symbolic equations for their envelopes and for their
parameter constraints.
"""

import functools
from typing import Any, Dict, Optional, Union, Callable

import numpy as np

from qiskit.circuit.parameterexpression import ParameterExpression
from qiskit.pulse.exceptions import PulseError
from qiskit.pulse.library.pulse import Pulse
from qiskit.pulse.library.waveform import Waveform
from qiskit.utils import optionals as _optional

if _optional.HAS_SYMENGINE:
    import symengine as sym
else:
    import sympy as sym


def _lifted_gaussian(
    t: sym.Symbol,
    center: Union[sym.Symbol, sym.Expr, complex],
    t_zero: Union[sym.Symbol, sym.Expr, complex],
    sigma: Union[sym.Symbol, sym.Expr, complex],
) -> sym.Expr:
    r"""Helper function that returns a lifted Gaussian symbolic equation.

    For :math:`\sigma=` ``sigma`` the symbolic equation will be

    .. math::

        f(x) = \exp\left(-\frac12 \left(\frac{x - \mu}{\sigma}\right)^2 \right),

    with the center :math:`\mu=` ``duration/2``.
    Then, each output sample :math:`y` is modified according to:

    .. math::

        y \mapsto \frac{y-y^*}{1.0-y^*},

    where :math:`y^*` is the value of the un-normalized Gaussian at the endpoints of the pulse.
    This sets the endpoints to :math:`0` while preserving the amplitude at the center,
    i.e. :math:`y` is set to :math:`1.0`.

    Args:
        t: Symbol object representing time.
        center: Symbol or expression representing the middle point of the samples.
        t_zero: The value of t at which the pulse is lowered to 0.
        sigma: Symbol or expression representing Gaussian sigma.

    Returns:
        Symbolic equation.
    """
    gauss = sym.exp(-(((t - center) / sigma) ** 2) / 2)
    offset = sym.exp(-(((t_zero - center) / sigma) ** 2) / 2)

    return (gauss - offset) / (1 - offset)


@functools.lru_cache(maxsize=None)
def _validate_amplitude_limit(symbolic_pulse: "SymbolicPulse") -> bool:
    """A helper function to validate maximum amplitude limit.

    Result is cached for better performance.

    Args:
        symbolic_pulse: A pulse to validate.

    Returns:
        Return True if any sample point exceeds 1.0 in absolute value.
    """
    return np.any(np.abs(symbolic_pulse.get_waveform().samples) > 1.0)


class LamdifiedExpression:
    """Descriptor to lambdify symbolic expression with cache.

    When new symbolic expression is set for the first time,
    this will internally lambdify the expressions and store the callbacks in the instance cache.
    For the next time it will just return the cached callbacks for speed up.
    """

    def __init__(self, attribute: str):
        """Create new descriptor.

        Args:
            attribute: Name of attribute of :class:`.SymbolicPulse` that returns
                the target expression to evaluate.
        """
        self.attribute = attribute
        self.lambda_funcs = dict()

    def __get__(self, instance, owner) -> Callable:
        expr = getattr(instance, self.attribute, None)
        if expr is None:
            raise PulseError(f"'{self.attribute}' of '{instance.pulse_type}' is not assigned.")
        key = hash(expr)
        if key not in self.lambda_funcs:
            self.__set__(instance, expr)

        return self.lambda_funcs[key]

    def __set__(self, instance, value):
        key = hash(value)
        if key not in self.lambda_funcs:
            if value.free_symbols == instance.parameters.keys():
                raise PulseError(
                    "Symbolic pulse parameter and expression's free symbols don't match. "
                    "Cannot generate samples for this symbolic pulse."
                )
            params = sorted(value.free_symbols, key=lambda s: s.name)

            if _optional.HAS_SYMENGINE:
                # Symengine lambdify requires array-like
                value = [value]
            try:
                func = sym.lambdify(params, value)
            except RuntimeError:
                # If symengine and complex valued function
                func = sym.lambdify(params, value, real=False)

            self.lambda_funcs[key] = func


class SymbolicPulse(Pulse):
    r"""The pulse representation model with parameters and symbolic expressions.

    A symbolic pulse instance can be defined with an envelope and parameter constraints.
    Envelope and parameter constraints should be provided as symbolic expressions.
    Rather than creating a subclass, different pulse shapes can be distinguished by
    the instance attributes :attr:`SymbolicPulse.envelope` and :attr:`SymbolicPulse.constraints`,
    together with the ``pulse_type`` argument of the :class:`SymbolicPulse` constructor.


    .. _symbolic_pulse_envelope:

    .. rubric:: Envelope function

    This is defined with an instance attribute :attr:`SymbolicPulse.envelope`
    which can be provided through the symbolic pulse constructor.
    The envelope function at time :math:`t` must be defined in the form

    .. math::

        F(t, \Theta) = {\rm amp} \times F'(t, {\rm duration}, \overline{\rm params})

    where :math:`\Theta` is the full pulse parameter in :attr:`SymbolicPulse.parameters`
    dictionary which must include the :math:`\rm amp` and :math:`\rm duration`.
    The :math:`\rm amp` is a complex value representing a scale factor and phase applied to
    the envelope function :math:`F'` which is defined with :attr:`SymbolicPulse.envelope`.
    This indicates that by convention the Qiskit Pulse conforms to the IQ format rather
    than the phasor representation. When a real value is assigned to the amplitude,
    it is internally typecasted to the complex. The real and imaginary part may be
    directly supplied to two quadratures of the IQ mixer in the control electronics.
    The time :math:`t` and :math:`\rm duration` are in units of dt, i.e. sample time resolution,
    and this function is sampled with a discrete time vector in :math:`[0, {\rm duration}]`
    sampling the pulse envelope at every 0.5 dt (middle sampling strategy) when
    :meth:`SymbolicPulse.get_waveform` method is called.
    The sample data is not generated until this method is called
    thus a symbolic pulse instance only stores parameter values and waveform shape,
    which greatly reduces memory footprint during the program generation.


    .. _symbolic_pulse_constraints:

    .. rubric:: Constraint functions

    Constraints on the parameters are defined with an instance attribute
    :attr:`SymbolicPulse.constraints` which can be provided through the constructor.
    The constraints value must be a symbolic expression, which is a
    function of parameters to be validated and must return a boolean value
    being ``True`` when parameters are valid.
    If there are multiple conditions to be evaluated, these conditions can be
    concatenated with logical expressions such as ``And`` and ``Or`` in SymPy or Symengine.
    The symbolic pulse instance can be played only when the constraint function returns ``True``.
    The constraint is evaluated when :meth:`SymbolicPulse.validate_parameters` is called.
    Note that the maximum pulse amplitude limit is separately evaluated when
    the :attr:`.limit_amplitude` is set.
    Since this is evaluated with actual waveform samples by calling :meth:`.get_waveform`,
    it is not necessary to define any explicit constraint for the amplitude limitation.

    .. rubric:: Examples

    This is how a user can instantiate a symbolic pulse instance.
    In this example, we instantiate a custom `Sawtooth` envelope.

    .. jupyter-execute::

        from qiskit.pulse.library import SymbolicPulse

        my_pulse = SymbolicPulse(
            pulse_type="Sawtooth",
            duration=100,
            amp=0.1,
            parameters={"freq": 0.05},
            name="pulse1",
        )

    Note that :class:`SymbolicPulse` can be instantiated without providing
    the envelope and constraints. However, this instance cannot generate waveforms
    without knowing the envelope definition. Now you need to provide the envelope.

    .. jupyter-execute::

        import sympy

        t, freq = sympy.symbols("t, freq")
        envelope = 2 * (freq * t - sympy.floor(1 / 2 + freq * t))
        my_pulse.envelope = envelope

        my_pulse.draw()

    Likewise, you can define :attr:`SymbolicPulse.constraints` for ``my_pulse``.
    After providing the envelope definition, you can generate the waveform data.
    Note that it would be convenient to define a factory function that automatically
    accomplishes this procedure.

    .. code-block:: python

        def Sawtooth(duration, amp, freq, name):
            instance = SymbolicPulse(
                pulse_type="Sawtooth",
                duration=duration,
                amp=amp,
                parameters={"freq": freq},
                name=name,
            )

            t, amp, freq = sympy.symbols("t, amp, freq")
            instance.envelope = amp * 2 * (freq * t - sympy.floor(1 / 2 + freq * t))

            return instance

    You can also provide a :class:`Parameter` object in the ``parameters`` dictionary,
    or define ``duration`` and ``amp`` with parameters when you instantiate
    the symbolic pulse instance.
    Waveform cannot be generated until you assign all unbounded parameters.
    Note that parameters will be assigned through the schedule playing the pulse.


    .. _symbolic_pulse_serialize:

    .. rubric:: Serialization

    The :class:`~SymbolicPulse` subclass is QPY serialized with symbolic expressions.
    A user can therefore create a custom pulse subclass with a novel envelope and constraints,
    and then one can instantiate the class with certain parameters to run on a backend.
    This pulse instance can be saved in the QPY binary, which can be loaded afterwards
    even within the environment not having original class definition loaded.
    This mechanism also allows us to easily share a pulse program including
    custom pulse instructions with collaborators.

    .. note::

        Currently QPY serialization of :class:`SymbolicPulse` is not available.
        This feature will be implemented shortly.
    """

    __slots__ = (
        "amp",
        "_pulse_type",
        "_param_names",
        "_param_vals",
        "envelope",
        "constraints",
    )

    # Lambdify caches keyed on sympy expressions. Returns the corresponding callable.
    _envelope_lambdify = LamdifiedExpression("envelope")
    _constraints_lambdify = LamdifiedExpression("constraints")

    def __init__(
        self,
        pulse_type: str,
        duration: Union[ParameterExpression, int],
        amp: Optional[Union[ParameterExpression, complex]] = 1.0 + 0j,
        parameters: Optional[Dict[str, Union[ParameterExpression, complex]]] = None,
        name: Optional[str] = None,
        limit_amplitude: Optional[bool] = None,
        envelope: Optional["Expr"] = None,
        constraints: Optional["Expr"] = None,
    ):
        """Create a parametric pulse and validate the input parameters.

        Args:
            pulse_type: Display name of this pulse shape.
            duration: Duration of pulse.
            amp: Scale factor of the pulse envelope, which is represented by a complex value
                including a phase information.
            parameters: Dictionary of pulse parameters that defines the pulse envelope.
            name: Display name for this particular pulse envelope.
            limit_amplitude: If ``True``, then limit the absolute value of the amplitude of the
                waveform to 1. The default is ``True`` and the amplitude is constrained to 1.
            envelope: Pulse envelope expression.
            constraints: Pulse parameter constraint expression.

        Raises:
            PulseError: When not all parameters are listed in the attribute :attr:`PARAM_DEF`.
        """
        super().__init__(
            duration=duration,
            name=name,
            limit_amplitude=limit_amplitude,
        )
        if not isinstance(amp, ParameterExpression):
            amp = complex(amp)
        self.amp = amp

        self._pulse_type = pulse_type

        if parameters is None:
            parameters = {}
        self._param_names = tuple(parameters.keys())
        self._param_vals = tuple(parameters.values())

        self.envelope = envelope
        self.constraints = constraints

    def __getattr__(self, item):
        # Get pulse parameters with attribute-like access.
        param_names = object.__getattribute__(self, "_param_names")
        param_vals = object.__getattribute__(self, "_param_vals")
        if item not in param_names:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")
        return param_vals[param_names.index(item)]

    @property
    def pulse_type(self) -> str:
        """Return display name of the pulse shape."""
        return self._pulse_type

    def get_waveform(self) -> Waveform:
        r"""Return a Waveform with samples filled according to the formula that the pulse
        represents and the parameter values it contains.

        Since the returned array is a discretized time series of the continuous function,
        this method uses a midpoint sampler. For ``duration``, return:

        .. math::

            \{f(t+0.5) \in \mathbb{C} | t \in \mathbb{Z} \wedge  0<=t<\texttt{duration}\}

        Returns:
            A waveform representation of this pulse.

        Raises:
            PulseError: When parameters are not assigned.
            PulseError: When expression for pulse envelope is not assigned.
        """
        if self.is_parameterized():
            raise PulseError("Unassigned parameter exists. All parameters must be assigned.")

        if self.envelope is None:
            raise PulseError("Pulse envelope expression is not assigned.")

        times = np.arange(0, self.duration) + 1 / 2
        params = self.parameters

        func = self._envelope_lambdify
        if _optional.HAS_SYMENGINE:
            func = np.vectorize(func)

        func_args = []
        for name in sorted(map(lambda s: s.name, self.envelope.free_symbols)):
            if name == "t":
                value = times
            else:
                value = params[name]
            func_args.append(value)

        return Waveform(samples=self.amp * func(*func_args), name=self.name)

    def validate_parameters(self) -> None:
        """Validate parameters.

        Raises:
            PulseError: If the parameters passed are not valid.
        """
        if self.is_parameterized():
            return

        if any(p.imag != 0 for p in self._param_vals):
            raise PulseError("Pulse parameters must be real numbers except for 'amp'.")

        if self.constraints is not None:
            func_args = []
            params = self.parameters
            for name in sorted(map(lambda s: s.name, self.constraints.free_symbols)):
                func_args.append(params[name])

            if not bool(self._constraints_lambdify(*func_args)):
                param_repr = ", ".join(f"{p}={v}" for p, v in self.parameters.items())
                const_repr = str(self.constraints)
                raise PulseError(
                    f"Assigned parameters {param_repr} violate following constraint: {const_repr}."
                )

        if self.limit_amplitude and (np.abs(self.amp) > 1.0 or _validate_amplitude_limit(self)):
            # Check max amplitude limit by generating waveform.
            # We can avoid calling _validate_amplitude_limit when |amp| > 1.0
            # which obviously violates the amplitude constraint by definition.
            param_repr = ", ".join(f"{p}={v}" for p, v in self.parameters.items())
            raise PulseError(
                f"Maximum pulse amplitude norm exceeds 1.0 with assigned parameters {param_repr}."
                "This can be overruled by setting Pulse.limit_amplitude."
            )

    def is_parameterized(self) -> bool:
        """Return True iff the instruction is parameterized."""
        args = (self.duration, self.amp, *self._param_vals)
        return any(isinstance(val, ParameterExpression) for val in args)

    @property
    def parameters(self) -> Dict[str, Any]:
        params = {"duration": self.duration, "amp": self.amp}
        params.update(dict(zip(self._param_names, self._param_vals)))
        return params

    def __eq__(self, other: "SymbolicPulse") -> bool:

        # Not aware of expressions.
        if type(self) is not type(other):
            return False
        if self.parameters != other.parameters:
            return False
        return True

    def __hash__(self) -> int:
        return hash(
            (self._pulse_type, self.duration, self.amp, *self._param_names, *self._param_vals)
        )

    def __repr__(self) -> str:
        param_repr = ", ".join(f"{p}={v}" for p, v in self.parameters.items())
        return "{}({}{})".format(
            self._pulse_type,
            param_repr,
            f", name='{self.name}'" if self.name is not None else "",
        )


class Gaussian(SymbolicPulse):
    r"""A lifted and truncated pulse envelope shaped according to the Gaussian function whose
    mean is centered at the center of the pulse (duration / 2):

    .. math::

        f'(x) &= \exp\Bigl( -\frac12 \frac{{(x - \text{duration}/2)}^2}{\text{sigma}^2} \Bigr)\\
        f(x) &= \text{amp} \times \frac{f'(x) - f'(-1)}{1-f'(-1)}, \quad 0 \le x < \text{duration}

    where :math:`f'(x)` is the gaussian waveform without lifting or amplitude scaling.
    """

    def __init__(
        self,
        duration: Union[int, ParameterExpression],
        amp: Union[complex, ParameterExpression],
        sigma: Union[float, ParameterExpression],
        name: Optional[str] = None,
        limit_amplitude: Optional[bool] = None,
    ):
        """Create new pulse instance.

        Args:
            duration: Pulse length in terms of the sampling period `dt`.
            amp: The amplitude of the Gaussian envelope.
            sigma: A measure of how wide or narrow the Gaussian peak is; described mathematically
                   in the class docstring.
            name: Display name for this pulse envelope.
            limit_amplitude: If ``True``, then limit the amplitude of the
                waveform to 1. The default is ``True`` and the amplitude is constrained to 1.

        """
        parameters = {"sigma": sigma}

        # Prepare symbolic expressions
        _t, _duration, _sigma = sym.symbols("t, duration, sigma", real=True)
        _center = _duration / 2

        envelope_expr = _lifted_gaussian(_t, _center, _duration + 1, _sigma)
        consts_expr = _sigma > 0

        super().__init__(
            pulse_type=self.__class__.__name__,
            duration=duration,
            amp=amp,
            parameters=parameters,
            name=name,
            limit_amplitude=limit_amplitude,
            envelope=envelope_expr,
            constraints=consts_expr,
        )
        self.validate_parameters()


class GaussianSquare(SymbolicPulse):
    """A square pulse with a Gaussian shaped risefall on both sides lifted such that
    its first sample is zero.

    Exactly one of the ``risefall_sigma_ratio`` and ``width`` parameters has to be specified.

    If ``risefall_sigma_ratio`` is not None and ``width`` is None:

    .. math::

        \\text{risefall} &= \\text{risefall_sigma_ratio} \\times \\text{sigma}\\\\
        \\text{width} &= \\text{duration} - 2 \\times \\text{risefall}

    If ``width`` is not None and ``risefall_sigma_ratio`` is None:

    .. math:: \\text{risefall} = \\frac{\\text{duration} - \\text{width}}{2}

    In both cases, the lifted gaussian square pulse :math:`f'(x)` is defined as:

    .. math::

        f'(x) &= \\begin{cases}\
            \\exp\\biggl(-\\frac12 \\frac{(x - \\text{risefall})^2}{\\text{sigma}^2}\\biggr)\
                & x < \\text{risefall}\\\\
            1\
                & \\text{risefall} \\le x < \\text{risefall} + \\text{width}\\\\
            \\exp\\biggl(-\\frac12\
                    \\frac{{\\bigl(x - (\\text{risefall} + \\text{width})\\bigr)}^2}\
                          {\\text{sigma}^2}\
                    \\biggr)\
                & \\text{risefall} + \\text{width} \\le x\
        \\end{cases}\\\\
        f(x) &= \\text{amp} \\times \\frac{f'(x) - f'(-1)}{1-f'(-1)},\
            \\quad 0 \\le x < \\text{duration}

    where :math:`f'(x)` is the gaussian square waveform without lifting or amplitude scaling.
    """

    def __init__(
        self,
        duration: Union[int, ParameterExpression],
        amp: Union[complex, ParameterExpression],
        sigma: Union[float, ParameterExpression],
        width: Optional[Union[float, ParameterExpression]] = None,
        risefall_sigma_ratio: Optional[Union[float, ParameterExpression]] = None,
        name: Optional[str] = None,
        limit_amplitude: Optional[bool] = None,
    ):
        """Create new pulse instance.

        Args:
            duration: Pulse length in terms of the sampling period `dt`.
            amp: The amplitude of the Gaussian and of the square pulse.
            sigma: A measure of how wide or narrow the Gaussian risefall is; see the class
                   docstring for more details.
            width: The duration of the embedded square pulse.
            risefall_sigma_ratio: The ratio of each risefall duration to sigma.
            name: Display name for this pulse envelope.
            limit_amplitude: If ``True``, then limit the amplitude of the
                waveform to 1. The default is ``True`` and the amplitude is constrained to 1.

        Raises:
            PulseError: When width and risefall_sigma_ratio are both empty or both non-empty.
        """
        # Convert risefall_sigma_ratio into width which is defined in OpenPulse spec
        if width is None and risefall_sigma_ratio is None:
            raise PulseError(
                "Either the pulse width or the risefall_sigma_ratio parameter must be specified."
            )
        if width is not None and risefall_sigma_ratio is not None:
            raise PulseError(
                "Either the pulse width or the risefall_sigma_ratio parameter can be specified"
                " but not both."
            )
        if width is None and risefall_sigma_ratio is not None:
            width = duration - 2.0 * risefall_sigma_ratio * sigma

        parameters = {"sigma": sigma, "width": width}

        # Prepare symbolic expressions
        _t, _duration, _sigma, _width = sym.symbols("t, duration, sigma, width", real=True)
        _center = _duration / 2

        _sq_t0 = _center - _width / 2
        _sq_t1 = _center + _width / 2

        _gaussian_ledge = _lifted_gaussian(_t, _sq_t0, -1, _sigma)
        _gaussian_redge = _lifted_gaussian(_t, _sq_t1, _duration + 1, _sigma)

        envelope_expr = sym.Piecewise(
            (_gaussian_ledge, _t <= _sq_t0), (_gaussian_redge, _t >= _sq_t1), (1, True)
        )
        consts_expr = sym.And(_sigma > 0, _width >= 0, _duration >= _width)

        super().__init__(
            pulse_type=self.__class__.__name__,
            duration=duration,
            amp=amp,
            parameters=parameters,
            name=name,
            limit_amplitude=limit_amplitude,
            envelope=envelope_expr,
            constraints=consts_expr,
        )
        self.validate_parameters()

    @property
    def risefall_sigma_ratio(self):
        """Return risefall_sigma_ratio. This is auxiliary parameter to define width."""
        return (self.duration - self.width) / (2.0 * self.sigma)


class Drag(SymbolicPulse):
    """The Derivative Removal by Adiabatic Gate (DRAG) pulse is a standard Gaussian pulse
    with an additional Gaussian derivative component and lifting applied.

    It can be calibrated either to reduce the phase error due to virtual population of the
    :math:`|2\\rangle` state during the pulse or to reduce the frequency spectrum of a
    standard Gaussian pulse near the :math:`|1\\rangle\\leftrightarrow|2\\rangle` transition,
    reducing the chance of leakage to the :math:`|2\\rangle` state.

    .. math::

        g(x) &= \\exp\\Bigl(-\\frac12 \\frac{(x - \\text{duration}/2)^2}{\\text{sigma}^2}\\Bigr)\\\\
        g'(x) &= \\text{amp}\\times\\frac{g(x)-g(-1)}{1-g(-1)}\\\\
        f(x) &=  g'(x) \\times \\Bigl(1 + 1j \\times \\text{beta} \\times\
            \\Bigl(-\\frac{x - \\text{duration}/2}{\\text{sigma}^2}\\Bigr)  \\Bigr),
            \\quad 0 \\le x < \\text{duration}

    where :math:`g(x)` is a standard unlifted Gaussian waveform and
    :math:`g'(x)` is the lifted :class:`~qiskit.pulse.library.Gaussian` waveform.

    References:
        1. |citation1|_

        .. _citation1: https://link.aps.org/doi/10.1103/PhysRevA.83.012308

        .. |citation1| replace:: *Gambetta, J. M., Motzoi, F., Merkel, S. T. & Wilhelm, F. K.
           Analytic control methods for high-fidelity unitary operations
           in a weakly nonlinear oscillator. Phys. Rev. A 83, 012308 (2011).*

        2. |citation2|_

        .. _citation2: https://link.aps.org/doi/10.1103/PhysRevLett.103.110501

        .. |citation2| replace:: *F. Motzoi, J. M. Gambetta, P. Rebentrost, and F. K. Wilhelm
           Phys. Rev. Lett. 103, 110501 – Published 8 September 2009.*
    """

    def __init__(
        self,
        duration: Union[int, ParameterExpression],
        amp: Union[complex, ParameterExpression],
        sigma: Union[float, ParameterExpression],
        beta: Union[float, ParameterExpression],
        name: Optional[str] = None,
        limit_amplitude: Optional[bool] = None,
    ):
        """Create new pulse instance.

        Args:
            duration: Pulse length in terms of the sampling period `dt`.
            amp: The amplitude of the Drag envelope.
            sigma: A measure of how wide or narrow the Gaussian peak is; described mathematically
                   in the class docstring.
            beta: The correction amplitude.
            name: Display name for this pulse envelope.
            limit_amplitude: If ``True``, then limit the amplitude of the
                waveform to 1. The default is ``True`` and the amplitude is constrained to 1.
        """
        parameters = {"sigma": sigma, "beta": beta}

        # Prepare symbolic expressions
        _t, _duration, _sigma, _beta = sym.symbols("t, duration, sigma, beta", real=True)
        _center = _duration / 2

        _gauss = _lifted_gaussian(_t, _center, _duration + 1, _sigma)
        _deriv = -(_t - _center) / (_sigma**2) * _gauss

        envelope_expr = _gauss + sym.I * _beta * _deriv

        # In IBM quantum backend, im(beta) == 0 is explicitly checked.
        # In Qiskit, we impose real number constraints on all parameters except for 'amp'.
        consts_expr = _sigma > 0

        super().__init__(
            pulse_type=self.__class__.__name__,
            duration=duration,
            amp=amp,
            parameters=parameters,
            name=name,
            limit_amplitude=limit_amplitude,
            envelope=envelope_expr,
            constraints=consts_expr,
        )
        self.validate_parameters()


class Constant(SymbolicPulse):
    """A simple constant pulse, with an amplitude value and a duration:

    .. math::

        f(x) = amp    ,  0 <= x < duration
        f(x) = 0      ,  elsewhere
    """

    def __init__(
        self,
        duration: Union[int, ParameterExpression],
        amp: Union[complex, ParameterExpression],
        name: Optional[str] = None,
        limit_amplitude: Optional[bool] = None,
    ):
        """Create new pulse instance.

        Args:
            duration: Pulse length in terms of the sampling period `dt`.
            amp: The amplitude of the constant square pulse.
            name: Display name for this pulse envelope.
            limit_amplitude: If ``True``, then limit the amplitude of the
                waveform to 1. The default is ``True`` and the amplitude is constrained to 1.
        """
        # Prepare symbolic expressions
        _t, _duration = sym.symbols("t, duration", real=True)

        # Note this is implemented using Piecewise instead of just returning amp
        # directly because otherwise the expression has no t dependence and sympy's
        # lambdify will produce a function f that for an array t returns amp
        # instead of amp * np.ones(t.shape). This does not work well with
        # ParametricPulse.get_waveform().
        #
        # See: https://github.com/sympy/sympy/issues/5642
        envelope_expr = sym.Piecewise((1, sym.And(_t >= 0, _t <= _duration)), (0, True))

        super().__init__(
            pulse_type=self.__class__.__name__,
            duration=duration,
            amp=amp,
            name=name,
            limit_amplitude=limit_amplitude,
            envelope=envelope_expr,
        )
        self.validate_parameters()
