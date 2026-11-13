import numpy as np

from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import main
from pymodaq.utils.data import DataFromPlugins, Axis

from pymodaq_plugins_stanford_research_systems.daq_viewer_plugins.plugins_0D.daq_0Dviewer_LockInSR830 import (
    DAQ_0DViewer_LockInSR830)


class DAQ_1DViewer_LockInSR830(DAQ_0DViewer_LockInSR830):
    """ Stanford Research Systems SR830 lock-in amplifier, 1D detector: the buffer of the instrument.

    The instrument records ``Npts`` points of its two display channels (CH1 and CH2) at its sampling rate, in its
    buffer, and the plugin reads the buffer once it is full. The time axis follows the sampling rate.

    Compatible instruments, installation and tests: see :class:`DAQ_0DViewer_LockInSR830`.
    """
    params = [
        {'title': 'Npts:', 'name': 'npts', 'type': 'int', 'min': 1, 'max': 16380, 'value': 10},
        ] + DAQ_0DViewer_LockInSR830.params

    def ini_detector(self, controller=None):
        info, initialized = super().ini_detector(controller)
        self.settings.child('acq', 'separate_viewers').show(False)
        self.settings.child('acq', 'channels').show(False)
        self.emit_empty_data()
        return info, initialized

    def time_axis(self) -> Axis:
        """The time of each point of the buffer, in s (index only while the instrument samples on a trigger)"""
        npts = self.settings['npts']
        rate = self.controller.sample_frequency if self.controller is not None else None
        if not rate:
            return Axis('index', data=np.arange(npts))
        return Axis('time', units='s', data=np.arange(npts) / rate)

    def emit_empty_data(self):
        """Show the viewers before the first grab"""
        zeros = np.zeros((self.settings['npts'],))
        self.dte_signal_temp.emit(DataToExport(name='SR830', data=[
            DataFromPlugins('CH1', data=[zeros], dim='Data1D', labels=['CH1'], axes=[self.time_axis()]),
            DataFromPlugins('CH2', data=[zeros], dim='Data1D', labels=['CH2'], axes=[self.time_axis()])]))

    def commit_settings(self, param: Parameter):
        if param.name() == 'npts':
            self.emit_empty_data()
        else:
            super().commit_settings(param)

    def grab_data(self, Naverage=1, **kwargs):
        """Fill the buffer of the instrument, then read the two channels

        Parameters
        ----------
        Naverage: int
            Number of averages, done by PyMoDAQ
        """
        npts = self.settings['npts']
        rate = self.controller.sample_frequency
        self.controller.clear()
        self.controller.reset_buffer()
        self.controller.start_scan()
        # the buffer fills in npts / rate seconds; wait for twice that time (at least one second) before giving up
        timeout = max(2 * npts / rate, 1.) if rate else 60.
        self.controller.wait_for_buffer(npts, timeout=timeout, timestep=0.01)  # pauses the buffer, even on a timeout
        if self.controller.buffer_count < npts:
            raise TimeoutError(f'the buffer of the SR830 did not fill with {npts} points in {timeout:.0f} s')
        ch1 = self.controller.get_buffer(1, end=npts)
        ch2 = self.controller.get_buffer(2, end=npts)
        self.controller.pause_scan()
        axis = self.time_axis()
        self.dte_signal.emit(DataToExport(name='SR830', data=[
            DataFromPlugins('CH1', data=[ch1], dim='Data1D', labels=['CH1'], axes=[axis]),
            DataFromPlugins('CH2', data=[ch2], dim='Data1D', labels=['CH2'], axes=[axis])]))

    def stop(self):
        """Stop the recording in the buffer of the instrument"""
        if self.controller is not None:
            self.controller.pause_scan()
        return ''


if __name__ == '__main__':
    main(__file__, init=False)
