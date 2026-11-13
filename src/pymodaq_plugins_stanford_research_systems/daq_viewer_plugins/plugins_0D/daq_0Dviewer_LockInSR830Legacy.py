import numpy as np

from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, main, comon_parameters
from pymodaq.utils.data import DataFromPlugins

from pymodaq_plugins_stanford_research_systems.hardware import sr830


class DAQ_0DViewer_LockInSR830Legacy(DAQ_Viewer_base):
    """ Stanford Research Systems SR830 lock-in amplifier, 0D detector, sending the SCPI-like commands itself.

    Kept for the experiments saved with it (same settings and channel names as before); the plugin
    ``LockInSR830``, which uses the ``pymeasure`` driver, is the recommended one.

    Compatible instruments: SR830. Tested only against a fake of the VISA resource, not on a real instrument.
    Installation: a VISA backend (NI-VISA, or ``pyvisa-py``) and a GPIB interface for GPIB.

    Attributes:
    -----------
    controller: pyvisa.resources.Resource
        The VISA session of the instrument, shared with the slave modules of the same controller.
    """
    channels = ['X', 'Y', 'MAG', 'PHA', 'Aux In 1', 'Aux In 2', 'Aux In 3', 'Aux In 4', 'Ref frequency', 'CH1 display',
                'CH2 display']  # in the order of the answer of SNAP ? 1,2,...,11

    params = comon_parameters + [
        {'title': 'VISA:', 'name': 'VISA_ressources', 'type': 'str', 'value': sr830.DEFAULT_ADDRESS,
         'tip': 'VISA resource of the lock-in, for instance GPIB0::8::INSTR'},
        {'title': 'Manufacturer:', 'name': 'manufacturer', 'type': 'str', 'value': "", 'readonly': True},
        {'title': 'Serial number:', 'name': 'serial_number', 'type': 'str', 'value': "", 'readonly': True},
        {'title': 'Model:', 'name': 'model', 'type': 'str', 'value': "", 'readonly': True},
        {'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 2000, 'default': 2000, 'min': 1000},
        {'title': 'Configuration:', 'name': 'config', 'type': 'group', 'children': [
            {'title': 'Reset:', 'name': 'reset', 'type': 'bool_push', 'value': False},
            {'title': 'Channels in separate viewer:', 'name': 'separate_viewers', 'type': 'bool', 'value': True},
            {'title': 'Channels:', 'name': 'channels', 'type': 'itemselect',
             'value': dict(all_items=channels, selected=['MAG', 'PHA'])},
            {'title': 'Setup:', 'name': 'setup', 'type': 'group', 'children': [
                {'title': 'Setup number:', 'name': 'setup_number', 'type': 'int', 'value': 1, 'min': 1, 'max': 9},
                {'title': 'Save setup:', 'name': 'save_setup', 'type': 'bool_push', 'value': False},
                {'title': 'Load setup:', 'name': 'load_setup', 'type': 'bool_push', 'value': False}, ]}
        ]},
    ]

    def ini_attributes(self):
        self.controller = None

    def ini_detector(self, controller=None):
        """Open the VISA session (master) or take the one of the master (slave)

        Returns
        -------
        info: str
        initialized: bool
        """
        if self.is_master:
            self.controller = sr830.open_visa(self.settings['VISA_ressources'], self.settings['timeout'])
        else:
            self.controller = controller

        idn = self.controller.query('OUTX1;*IDN?;').rstrip('\n').split(',')  # manufacturer, model, serial, firmware
        for name, value in zip(('manufacturer', 'model', 'serial_number'), idn):
            self.settings.child(name).setValue(value)
        self.emit_empty_data()
        return ','.join(idn), True

    def close(self):
        """Close the VISA session, only the master owns it"""
        if self.is_master and self.controller is not None:
            self.controller.close()

    def grab_data(self, Naverage=1, **kwargs):
        """Record the selected channels at the same instant

        Parameters
        ----------
        Naverage: int
            Number of averages, done by PyMoDAQ
        """
        values = self.controller.query_ascii_values('SNAP ? 1,2,3,4,5,6')  # SNAP records 2 to 6 values at once
        values.extend(self.controller.query_ascii_values('SNAP ? 7,8,9,10,11'))
        selected_channels = self.settings['config', 'channels']['selected']
        data = [np.array([values[self.channels.index(channel)]]) for channel in selected_channels]
        self.dte_signal.emit(DataToExport(name='SR830', data=self.create_dwas(data)))

    def emit_empty_data(self):
        """Show the viewers of the selected channels before the first grab"""
        n_channels = len(self.settings['config', 'channels']['selected'])
        self.dte_signal_temp.emit(DataToExport(
            name='SR830', data=self.create_dwas([np.array([0.]) for _ in range(n_channels)])))

    def create_dwas(self, data):
        """The data of the selected channels, in a viewer each or all in one"""
        selected_channels = self.settings['config', 'channels']['selected']
        if self.settings['config', 'separate_viewers']:
            return [DataFromPlugins(name=channel, data=[array], dim='Data0D', labels=[channel])
                    for channel, array in zip(selected_channels, data)]
        return [DataFromPlugins(name='SR830', data=data, dim='Data0D', labels=selected_channels)]

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings"""
        if param.name() == 'channels':
            self.emit_empty_data()
        elif self.controller is None:
            return
        elif param.name() == 'timeout':
            self.controller.timeout = param.value()
        elif param.name() == 'load_setup':
            self.controller.write('RSET{:d};'.format(self.settings['config', 'setup', 'setup_number']))
            param.setValue(False)
        elif param.name() == 'save_setup':
            self.controller.write('SSET{:d};'.format(self.settings['config', 'setup', 'setup_number']))
            param.setValue(False)
        elif param.name() == 'reset':
            self.controller.write('*RST')
            param.setValue(False)

    def stop(self):
        """Nothing to stop: the grab is a snapshot"""
        return ''


if __name__ == '__main__':
    main(__file__, init=False)
