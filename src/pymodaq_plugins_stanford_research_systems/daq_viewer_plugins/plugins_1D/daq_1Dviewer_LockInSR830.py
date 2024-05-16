from typing import List
from time import perf_counter
from qtpy.QtCore import QThread
import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from pymeasure.instruments.srs.sr830 import SR830
from pyvisa import ResourceManager

from pymodaq_plugins_stanford_research_systems.daq_viewer_plugins.plugins_0D.daq_0Dviewer_LockInSR830 import (
    DAQ_0DViewer_LockInSR830)


class DAQ_1DViewer_LockInSR830(DAQ_0DViewer_LockInSR830):
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
        {'title': 'Npts:', 'name': 'npts', 'type': 'int', 'min': 1, 'max': 16380, 'value': 10},
        ] + DAQ_0DViewer_LockInSR830.params

    def ini_detector(self, controller=None):
        info, initialized = super().ini_detector(controller)
        self.settings.child('acq', 'separate_viewers').show(False)
        self.settings.child('acq', 'channels').show(False)

        self.dte_signal_temp.emit(DataToExport(name='SR830', data=[
            DataFromPlugins('CH1', data=[np.zeros((self.settings['npts'],))], labels=['CH1']),
            DataFromPlugins('CH2', data=[np.zeros((self.settings['npts'],))], labels=['CH2']),
        ]))
        return info, initialized

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
        self.controller.clear()
        rate = self.settings['acq', 'sampling_rate']
        self.controller.reset_buffer()
        start = perf_counter()
        self.controller.start_scan()
        counts = self.settings['npts']
        self.controller.wait_for_buffer(counts, timeout=60, timestep=0.01)
        print(f'acq time: {perf_counter() - start}s, should be: {counts / rate}')
        ch1 = self.controller.get_buffer(1)
        ch2 = self.controller.get_buffer(2)
        self.controller.pause_scan()

        self.dte_signal.emit(DataToExport(name='SR830', data=[
            DataFromPlugins('CH1', data=[ch1], labels=['CH1']),
            DataFromPlugins('CH2', data=[ch2], labels=['CH2']),
        ]))


if __name__ == '__main__':
    main(__file__, init=False)
