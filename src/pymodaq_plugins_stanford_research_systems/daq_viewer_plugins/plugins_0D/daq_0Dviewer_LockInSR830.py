from typing import Tuple

import pyvisa
import numpy as np

from pymeasure.adapters import VISAAdapter, PrologixAdapter

from pymodaq.control_modules.viewer_utility_classes import (
    DAQ_Viewer_base,
    comon_parameters,
    main
)
from pymodaq.utils.parameter import Parameter, utils
from pymodaq.utils.data import DataFromPlugins, DataToExport

from pyqtgraph.parametertree.Parameter import registerParameterType
from pyqtgraph.parametertree.parameterTypes.basetypes import GroupParameter

from pymodaq_plugins_stanford_research_systems.hardware.sr_830_thread_safe import SR830ThreadSafe
]
CHANNELS = ['x', 'y','magnitude','theta']
rm = pyvisa.ResourceManager()
VISA_RESOURCES = rm.list_resources()
ADAPTERS = dict(VISA=VISAAdapter, Prologix=PrologixAdapter)

for channel in CHANNELS:
    assert hasattr(SR830ThreadSafe, channel)

class ChannelGroup(GroupParameter):
    """Group Parameter listing the different output
    """

    def __init__(self, **opts) -> None:
        opts['type'] = 'sr830channel'
        opts['addText'] = "Add Channel"
        super().__init__(**opts)

    def addNew(self) -> None:
        """Add new channel to viewer
        """
        name_prefix = 'channel'

        child_indexes = [int(par.name()[len(name_prefix) + 1:])
                         for par in self.children()]

        if child_indexes == []:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

        child = {
            'title': f'Measure {newindex:02.0f}',
            'name': f'{name_prefix}{newindex:02.0f}',
            'type': 'itemselect',
            'removable': True,
            'value': dict(all_items=CHANNELS, selected=CHANNELS[0])
        }

        self.addChild(child)


registerParameterType('sr830channel', ChannelGroup, override=True)



class DAQ_0DViewer_LockInSR830(DAQ_Viewer_base):
    """ Instrument plugin class for a OD viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """

    params = [
        {'title': 'Adapter', 'name': 'adapter', 'type': 'list',
         'limits': list(ADAPTERS.keys())},
        {'title': 'VISA Address:', 'name': 'address', 'type': 'list',
         'limits': VISA_RESOURCES},
        {'title': 'ID:', 'name': 'id', 'type': 'str'},
        {'title': 'Channels:', 'name': 'channels', 'type': 'sr830channel'}
    ] + comon_parameters

    def ini_attributes(self) -> None:
        self.controller: SR830ThreadSafe = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """

        def commit_settings(self, param: Parameter) -> None:
            """Apply the consequences of a change of value in the detector settings

            Parameters
            ----------
            param: Parameter
                A given parameter (within detector_settings) whose value has been
                changed by the user
            """
            if param.name() in utils.iter_children(
                    self.settings.child('channels'), []):
                data = []
                for child in self.settings.child('channels').children():
                    labels = child.value()['selected']
                    data.append(
                        DataFromPlugins(
                            name=child.name(),
                            data=[np.array([0]) for _ in labels],
                            labels=labels,
                            dim='Data0D'
                        )
                    )
                self.dte_signal_temp.emit(DataToExport(
                    name="lockinsr830",
                    data=data
                ))

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        self.ini_detector_init(slave_controller=controller)

        if self.is_master:
            adapter = ADAPTERS[self.settings.child('adapter').value()](
                self.settings.child('address').value()
            )
            self.controller = SR830ThreadSafe(adapter)

        self.dte_signal_temp.emit(
            DataToExport(
                name="lockinsr830",
                data=[
                    DataFromPlugins(
                        name="lockinsr830",
                        data=[np.array([0]), np.array([0])],
                        dim="Data0D",
                        labels=["x", "y"]
                    )
                ]
            )
        )

        try:
            info = self.controller.id
            initialized = True
        except:
            info = ""
            initialized = False

        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        pass

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """

        data = []
        for child in self.settings.child('channels').children():
            labels = child.value()['selected'][:]
            subdata = [np.array([getattr(self.controller, label)])
                       for label in labels]
            data.append(DataFromPlugins(
                name=child.name(),
                data=subdata,
                labels=labels,
                dim='Data0D'
            ))
        self.dte_signal.emit(DataToExport(
            name="lockinsr830",
            data=data
        ))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        return ''


if __name__ == '__main__':
    main(__file__, init=False)
