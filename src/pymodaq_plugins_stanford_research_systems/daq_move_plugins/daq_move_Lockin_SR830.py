from typing import Tuple

from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    DataActuator,
    DataActuatorType,
    comon_parameters_fun,
    main
)
from pymodaq.utils.parameter import Parameter

from pymeasure.adapters import VISAAdapter, PrologixAdapter

import pyvisa

from pymodaq_plugins_stanford_research_systems.hardware.sr_830_thread_safe import SR830ThreadSafe

def build_dict_from_float_list(
        time_constants: list[float],
        unit: str = "") -> dict:
    d = {}
    for tc in time_constants:
        d[f"{tc:.2e} {unit}"] = tc
    return d


rm = pyvisa.ResourceManager()
VISA_RESOURCES = rm.list_resources()
ADAPTERS = dict(VISA=VISAAdapter, Prologix=PrologixAdapter)
SHIELD = {"Grounded": 0, "Floating": 1}
COUPLING = {"AC": 0, "DC": 1}
TIME_CONSTANTS = build_dict_from_float_list(SR830ThreadSafe.TIME_CONSTANTS, "s")
SENSITIVITIES = build_dict_from_float_list(SR830ThreadSafe.SENSITIVITIES, "V")
FILTER_SLOPES = build_dict_from_float_list(SR830ThreadSafe.FILTER_SLOPES, "")
#print(SR830ThreadSafe.INPUT_COUPLINGS)

class DAQ_Move_Lockin_SR830(DAQ_Move_base):
    """Plugin for the Signal Recovery DSP 7265 Instrument

    Does not currently support differential measurement.
    """
    _controller_units = ['Hz','V']
    is_multiaxes = True
    _axis_names = ['Freq','Amp']
    _epsilon = 0.01
    data_actuator_type = DataActuatorType.DataActuator

    params = [
                 {'title': 'Adapter', 'name': 'adapter', 'type': 'list',
                  'limits': list(ADAPTERS.keys())},
                 {'title': 'VISA Address:', 'name': 'address', 'type': 'list',
                  'limits': VISA_RESOURCES},
                 {'title': 'Filter time constant', 'name': 'time_constant',
                  'type': 'list', 'limits': list(TIME_CONSTANTS.keys())},
                 {'title': 'Full-scale sensitivity', 'name': 'sensitivity',
                  'type': 'list', 'limits': list(SENSITIVITIES.keys())},
                 {'title': 'Filter slope', 'name': 'filter_slope',
                  'type': 'list', 'limits': list(FILTER_SLOPES.keys())},
             ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)

    def ini_attributes(self) -> None:
        self.controller: SR830ThreadSafe = None

    def get_actuator_value(self) -> DataActuator:
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The frequency obtained after scaling conversion.
        """
        if self.axis_value == 'Amp':  # Amp axis
            val = DataActuator(data=self.controller.sine_voltage)
        elif self.axis_value == 'Freq':  # Frequency axis
            val = DataActuator(data=self.controller.frequency)
        val = self.get_position_with_scaling(val)
        return val

    def close(self) -> None:
        """Terminate the communication protocol"""
        self.controller.shutdown()

    def commit_settings(self, param: Parameter) -> None:
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been
            changed by the user
        """
        if param.name() == "time_constant":
            self.controller.time_constant = TIME_CONSTANTS[param.value()]
        elif param.name() == "sensitivity":
            self.controller.sensitivity= SENSITIVITIES[param.value()]
        elif param.name() == "filter_slope":
            self.controller.filter_slope= FILTER_SLOPES[param.value()]
        else:
            pass

    def ini_stage(self, controller: object = None) -> Tuple[str, bool]:
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one
            actuator by controller (Master case)

        Returns
        -------
        info: str
            Id of the lockin
        initialized: bool
            False if initialization failed otherwise True
        controller: object
            Controller of the daq_move
        """
        self.ini_stage_init(slave_controller=controller)

        if self.is_master:
            adapter = ADAPTERS[self.settings.child('adapter').value()](
                self.settings.child('address').value()
            )
            self.controller = SR830ThreadSafe(adapter)

        try:
            info = self.controller.id
            initialized = True
        except:
            info = ""
            initialized = False

        return info, initialized

    def move_abs(self, f: DataActuator) -> None:
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target value
        """
        f = self.check_bound(f)
        f = self.set_position_with_scaling(f)
        if self.axis_value == 'Amp':  # Amp axis
            self.controller.sine_voltage = f.value()
        elif self.axis_value == 'Freq':  # Frequency axis
            self.controller.frequency = f.value()

        self.target_value = f
        self.current_value = self.target_value

    def move_rel(self, f: DataActuator) -> None:
        """ Move the actuator to the relative target actuator value defined by
        value

        Parameters
        ----------
        value: (float) value of the relative target frequency
        """
        f = (self.check_bound(self.current_value + f)
             - self.current_value)
        self.target_value = f + self.current_value
        f = self.set_position_relative_with_scaling(f)
        self.move_abs(self.target_value)

    def move_home(self):
        """Call the reference method of the controller

        Set oscillator to 1kHz
        """
        self.move_abs(DataActuator(1e3))

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        pass

    if __name__ == '__main__':
        main(__file__, init=False)