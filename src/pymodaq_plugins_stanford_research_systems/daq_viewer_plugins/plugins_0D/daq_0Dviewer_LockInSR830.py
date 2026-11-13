from typing import List

import numpy as np

from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins

from pymeasure.instruments.srs.sr830 import SR830

from pymodaq_plugins_stanford_research_systems.hardware import sr830


class DAQ_0DViewer_LockInSR830(DAQ_Viewer_base):
    """ Stanford Research Systems SR830 lock-in amplifier, 0D detector (one value per channel).

    The instrument is driven with the ``pymeasure`` driver ``SR830``. Several channels of the instrument can be
    recorded together (``SNAP``), in one viewer or in a viewer each.

    Compatible instruments: SR830 (GPIB, or RS232 through VISA). Tested only against a fake of the driver, not on a
    real instrument.
    Installation: a VISA backend (NI-VISA, or ``pyvisa-py``) and a GPIB interface for GPIB.

    Attributes:
    -----------
    controller: SR830
        The ``pymeasure`` driver of the instrument, shared with the slave modules of the same controller.
    """
    channels = sr830.CHANNELS

    params = comon_parameters + [
        {'title': 'VISA:', 'name': 'device', 'type': 'str', 'value': sr830.DEFAULT_ADDRESS,
         'tip': 'VISA resource of the lock-in, for instance GPIB0::8::INSTR (see the VISA resources of the computer '
                'in NI MAX or with pyvisa)'},
        {'title': 'ID:', 'name': 'id', 'type': 'str', 'value': "", 'readonly': True},
        {'title': 'Acquisition:', 'name': 'acq', 'type': 'group', 'children': [
            {'title': 'Use Trigger:', 'name': 'trigger', 'type': 'bool', 'value': False},
            {'title': 'Channels in separate viewer:', 'name': 'separate_viewers', 'type': 'bool', 'value': True},
            {'title': 'Channels:', 'name': 'channels', 'type': 'itemselect',
             'value': dict(all_items=channels, selected=['CH1', 'CH2'])},
            {'title': 'Sampling (Hz):', 'name': 'sampling_rate', 'type': 'list', 'limits': SR830.SAMPLE_FREQUENCIES},
            ]},
        {'title': 'Configuration:', 'name': 'config', 'type': 'group', 'children': [
            {'title': 'Reset:', 'name': 'reset', 'type': 'bool_push', 'value': False},
            {'title': 'Setup number:', 'name': 'setup_number', 'type': 'int', 'value': 1, 'min': 1, 'max': 9},
            {'title': 'Save setup:', 'name': 'save_setup', 'type': 'bool_push', 'value': False,
             'label': 'Save'},
            {'title': 'Load setup:', 'name': 'load_setup', 'type': 'bool_push', 'value': False,
             'label': 'Load'},
        ]},
    ]

    def ini_attributes(self):
        self.controller: SR830 = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == 'channels':
            self.emit_empty_data()
        elif self.controller is None:
            return
        elif param.name() == 'load_setup':
            self.controller.load_setup(self.settings['config', 'setup_number'])
            param.setValue(False)
        elif param.name() == 'save_setup':
            self.controller.save_setup(self.settings['config', 'setup_number'])
            param.setValue(False)
        elif param.name() == 'reset':
            self.controller.reset()
            param.setValue(False)
        elif param.name() == 'trigger':
            self.controller.aquireOnTrigger(param.value())
        elif param.name() == 'sampling_rate':
            self.controller.sample_frequency = param.value()
            self.show_sampling_rate()  # what the instrument took

    def show_sampling_rate(self):
        """Show the sampling rate of the instrument (None: it samples on a trigger)"""
        rate = self.controller.sample_frequency
        if rate is not None and rate != self.settings['acq', 'sampling_rate']:
            self.settings.child('acq', 'sampling_rate').setValue(rate)

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            The ``SR830`` of the master module (Slave case). None if the module is the master.

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        if self.is_master:
            self.controller = sr830.open_sr830(self.settings['device'])
            self.controller.reset_buffer()
            self.controller.start_buffer(False)
        else:
            self.controller = controller

        self.show_sampling_rate()
        info = self.controller.id
        self.settings.child('id').setValue(info)
        self.emit_empty_data()
        return info, True

    def close(self):
        """Terminate the communication protocol, only the master owns the instrument"""
        if self.is_master and self.controller is not None:
            self.controller.clear()
            self.controller.shutdown()
            sr830.close_sr830(self.controller)

    def grab_data(self, Naverage=1, **kwargs):
        """Record the selected channels at the same instant

        Parameters
        ----------
        Naverage: int
            Number of averages, done by PyMoDAQ (the instrument does not average the snapshots)
        """
        selected_channels = self.settings['acq', 'channels']['selected']
        values = sr830.snap(self.controller, selected_channels)
        self.dte_signal.emit(DataToExport(name='SR830', data=self.create_dwas([np.array([value]) for value in values])))

    def emit_empty_data(self):
        """Show the viewers of the selected channels before the first grab"""
        n_channels = len(self.settings['acq', 'channels']['selected'])
        self.dte_signal_temp.emit(DataToExport(
            name='SR830', data=self.create_dwas([np.array([0.]) for _ in range(n_channels)])))

    def create_dwas(self, data_list_array: List[np.ndarray]) -> List[DataFromPlugins]:
        """ Create a list of DataFromPlugins according to the selected channels

        Parameters
        ----------
        data_list_array: List[np.ndarray]
            The list of numpy ndarray to put into a list of DataFromPlugins

        Returns
        -------
        List[DataFromPlugins]
        """
        selected_channels = self.settings['acq', 'channels']['selected']
        if self.settings['acq', 'separate_viewers']:
            return [DataFromPlugins(f'SR830:{channel}', data=[array], dim='Data0D', labels=[channel],
                                    units=sr830.CHANNEL_UNITS[channel])
                    for channel, array in zip(selected_channels, data_list_array)]
        return [DataFromPlugins('SR830', data=data_list_array, dim='Data0D', labels=selected_channels)]

    def stop(self):
        """Nothing to stop: the grab is a snapshot"""
        return ''


if __name__ == '__main__':
    main(__file__, init=False)
