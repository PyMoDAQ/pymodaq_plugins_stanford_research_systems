# -*- coding: utf-8 -*-
"""
Created on Thu Jun 14 15:14:54 2018

@author: Weber Sébastien
@email: seba.weber@gmail.com
"""
from qtpy.QtCore import Signal
from easydict import EasyDict as edict

from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, main, comon_parameters
from collections import OrderedDict

import numpy as np
import re

##checking VISA ressources
try:
    from pyvisa import ResourceManager

    VISA_rm = ResourceManager()
    devices = list(VISA_rm.list_resources())
    device = ''
    for dev in devices:
        if 'GPIB' in dev:
            device = dev
            break
except Exception as e:
    devices = []
    device = ''
    raise e


class DAQ_0DViewer_LockInSR830Legacy(DAQ_Viewer_base):
    """
        ==================== ========================
        **Attributes**        **Type**
        *data_grabed_signal*  instance of Signal
        *VISA_rm*             ResourceManager
        *com_ports*           
        *params*              dictionnary list
        *inst*
        *settings*
        ==================== ========================
    """
    data_grabed_signal = Signal(list)
    channels = ['X', 'Y', 'MAG', 'PHA', 'Aux In 1', 'Aux In 2', 'Aux In 3', 'Aux In 4', 'Ref frequency', 'CH1 display',
                'CH2 display']

    params = comon_parameters + [
        {'title': 'VISA:', 'name': 'VISA_ressources', 'type': 'list', 'limits': devices, 'value': device},
        {'title': 'Manufacturer:', 'name': 'manufacturer', 'type': 'str', 'value': ""},
        {'title': 'Serial number:', 'name': 'serial_number', 'type': 'str', 'value': ""},
        {'title': 'Model:', 'name': 'model', 'type': 'str', 'value': ""},
        {'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 2000, 'default': 2000, 'min': 1000},
        {'title': 'Configuration:', 'name': 'config', 'type': 'group', 'children': [
            {'title': 'Reset:', 'name': 'reset', 'type': 'bool_push', 'value': False},
            {'title': 'Channels in separate viewer:', 'name': 'separate_viewers', 'type': 'bool', 'value': True},
            {'title': 'Channels:', 'name': 'channels', 'type': 'itemselect',
             'value': dict(all_items=channels, selected=['MAG', 'PHA'])},
            {'title': 'Setup:', 'name': 'setup', 'type': 'group', 'children': [
                {'title': 'Setup number:', 'name': 'setup_number', 'type': 'int', 'value': 0},
                {'title': 'Save setup:', 'name': 'save_setup', 'type': 'bool', 'value': False},
                {'title': 'Load setup:', 'name': 'load_setup', 'type': 'bool', 'value': False}, ]}
        ]},
    ]

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self.controller = None

    def query_data(self, cmd):
        try:
            res = self.controller.query(cmd)
            searched = re.search('\n', res)
            status_byte = res[searched.start() + 1]
            overload_byte = res[searched.start() + 3]
            if searched.start != 0:
                data = np.array([float(x) for x in res[0:searched.start()].split(",")])
            else:
                data = None
            return (status_byte, overload_byte, data)
        except:
            return ('\x01', '\x00', None)

    def query_string(self, cmd):
        try:
            res = self.controller.query(cmd)
            searched = re.search('\n', res)
            status_byte = res[searched.start() + 1]
            overload_byte = res[searched.start() + 3]
            if searched.start != 0:
                str = res[0:searched.start()]
            else:
                str = ""
            return (status_byte, overload_byte, str)
        except:
            return ('\x01', '\x00', "")

    def ini_detector(self, controller=None):
        """
            Initialisation procedure of the detector.

            Returns
            -------

                The initialized status.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False, info="", x_axis=None, y_axis=None, controller=None))
        try:

            if self.settings.child(('controller_status')).value() == "Slave":
                if controller is None:
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller = controller
            else:
                VISA_rm = ResourceManager()
                self.controller = VISA_rm.open_resource(self.settings.child(('VISA_ressources')).value())

            self.controller.timeout = self.settings.child(('timeout')).value()
            idn = self.controller.query('OUTX1;*IDN?;')
            idn = idn.rstrip('\n')
            idn = idn.rsplit(',')
            if len(idn) >= 0:
                self.settings.child(('manufacturer')).setValue(idn[0])
            if len(idn) >= 1:
                self.settings.child(('model')).setValue(idn[1])
            if len(idn) >= 2:
                self.settings.child(('serial_number')).setValue(idn[2])

            # self.reset()

            self.status.controller = self.controller
            self.status.initialized = True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def reset(self):
        self.controller.write('*RST')

    def grab_data(self, Naverage=1, **kwargs):
        """
            | Start new acquisition.
            | grab the current values.
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================
        """
        data_tot = []
        data = self.controller.query_ascii_values('SNAP ? 1,2,3,4,5,6')
        data.extend(self.controller.query_ascii_values('SNAP ? 7,8,9,10,11'))
        selected_channels = self.settings.child('config', 'channels').value()['selected']
        data_to_export = [np.array([data[ind]]) for ind in [self.channels.index(sel) for sel in selected_channels]]

        if self.settings.child('config', 'separate_viewers').value():
            for ind_channel, dat in enumerate(data_to_export):
                data_tot.append(DataFromPlugins(name=selected_channels[ind_channel], data=[dat], dim='Data0D',
                                                labels=[selected_channels[ind_channel]]))
            self.data_grabed_signal.emit(data_tot)
        else:
            self.data_grabed_signal.emit(
                [DataFromPlugins(name='SR830', data=data_to_export, dim='Data0D', labels=selected_channels)])

    def commit_settings(self, param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================= ============================
            **Parameters**   **Type**                         **Description**
            *param*         instance of pyqtgraph.parameter   The parameter to be checked.
            =============== ================================= ============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            if param.name() == 'timeout':
                self.controller.timeout = self.settings.child(('timeout')).value()

            if param.name() == 'load_setup':
                self.controller.write(
                    'RSET{:d};'.format(self.settings.child('config', 'setup', 'setup_number').value()))
                param.setValue(False)

            if param.name() == 'save_setup':
                self.controller.write(
                    'SSET{:d};'.format(self.settings.child('config', 'setup', 'setup_number').value()))
                param.setValue(False)

            elif param.name() == 'channels':
                data_init = []
                for channel in param.value()['selected']:
                    if self.settings.child('config', 'separate_viewers').value():
                        data_init.append(DataFromPlugins(name=channel, data=[np.array([0])], dim='Data0D'))
                    else:
                        data_init.append(np.array([0]))
                if self.settings.child('config', 'separate_viewers').value():
                    self.data_grabed_signal_temp.emit(data_init)
                else:
                    self.data_grabed_signal_temp.emit([DataFromPlugins(name='SR830', data=data_init, dim='Data0D')])
            elif param.name() == 'reset':
                self.reset()
                param.setValue(False)

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))

    def close(self):
        """
            close the current instance of the visa session.
        """
        self.controller.close()

    def stop(self):
        pass


if __name__ == '__main__':
    main(__file__, init=False)
