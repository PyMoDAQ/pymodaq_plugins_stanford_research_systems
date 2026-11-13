"""Behaviour of the SR830 plugins against a fake of the instrument (no hardware, no VISA backend)."""
import pytest

from pymodaq.utils.plugin_testing import make_detector, grab_and_wait
from pymodaq.utils.plugin_testing.harness import _instantiate

from pymodaq_plugins_stanford_research_systems.hardware import sr830
from pymodaq_plugins_stanford_research_systems.daq_viewer_plugins.plugins_0D.daq_0Dviewer_LockInSR830 import (
    DAQ_0DViewer_LockInSR830)
from pymodaq_plugins_stanford_research_systems.daq_viewer_plugins.plugins_1D.daq_1Dviewer_LockInSR830 import (
    DAQ_1DViewer_LockInSR830)

from fake_sr830 import FakeSR830


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(sr830, 'open_sr830', lambda address: FakeSR830(address))


def test_importing_the_plugins_does_not_need_a_visa_backend():
    assert sr830.visa_resources() is not None  # a list, empty when the backend is missing


class TestSR830:
    def test_ini_reads_the_id(self, qapp, fake):
        plugin = make_detector(DAQ_0DViewer_LockInSR830, device='GPIB0::9::INSTR')
        assert plugin.initialized
        assert plugin.controller.address == 'GPIB0::9::INSTR'
        assert 'SR830' in plugin.init_info
        assert plugin.settings['id'] == plugin.init_info
        plugin.close()

    def test_grab_separate_viewers_with_units(self, qapp, fake):
        plugin = make_detector(DAQ_0DViewer_LockInSR830)
        plugin.settings.child('acq', 'channels').setValue(dict(all_items=sr830.CHANNELS, selected=['R', 'Theta']))
        dte = grab_and_wait(plugin)
        assert [dwa.labels for dwa in dte] == [['R'], ['Theta']]
        assert [dwa.units for dwa in dte] == ['V', 'deg']
        assert [float(dwa.data[0][0]) for dwa in dte] == [2., 3.]
        plugin.close()

    def test_grab_one_viewer(self, qapp, fake):
        plugin = make_detector(DAQ_0DViewer_LockInSR830)
        plugin.settings.child('acq', 'separate_viewers').setValue(False)
        dte = grab_and_wait(plugin)
        assert len(dte) == 1 and dte[0].labels == ['CH1', 'CH2']
        plugin.close()

    def test_more_than_six_channels_are_recorded_by_groups(self, qapp, fake):
        plugin = make_detector(DAQ_0DViewer_LockInSR830)
        plugin.settings.child('acq', 'channels').setValue(dict(all_items=sr830.CHANNELS, selected=sr830.CHANNELS[:8]))
        dte = grab_and_wait(plugin)
        assert len(dte) == 8
        assert [call[1] for call in plugin.controller.calls if call[0] == 'snap'] == [
            tuple(sr830.CHANNELS[:6]), tuple(sr830.CHANNELS[6:8])]
        plugin.close()

    def test_setup_and_reset_commands(self, qapp, fake):
        plugin = make_detector(DAQ_0DViewer_LockInSR830)
        plugin.settings.child('config', 'setup_number').setValue(3)
        plugin.commit_settings(plugin.settings.child('config', 'save_setup'))
        plugin.commit_settings(plugin.settings.child('config', 'load_setup'))
        plugin.commit_settings(plugin.settings.child('config', 'reset'))
        assert [call for call in plugin.controller.calls if call[0] != 'snap'] == [
            ('save_setup', 3), ('load_setup', 3), ('reset',)]
        plugin.close()

    def test_only_the_master_releases_the_instrument(self, qapp, fake):
        master = make_detector(DAQ_0DViewer_LockInSR830)
        slave = make_detector(DAQ_0DViewer_LockInSR830, controller=master.controller)
        assert slave.controller is master.controller
        slave.close()
        assert master.controller.adapter.is_open
        master.close()
        assert not master.controller.adapter.is_open

    def test_close_after_a_failed_initialization(self, qapp):
        plugin = _instantiate(DAQ_0DViewer_LockInSR830, None, {})  # as make_detector, without ini_detector
        plugin.close()  # the controller was never created


class TestSR830Buffer:
    def test_grab_the_buffer_with_a_time_axis(self, qapp, fake):
        plugin = make_detector(DAQ_1DViewer_LockInSR830, npts=50)
        dte = grab_and_wait(plugin)
        assert [dwa.labels for dwa in dte] == [['CH1'], ['CH2']]
        assert dte[0].data[0].shape == (50,)
        assert float(dte[1].data[0][0]) == 2.
        axis = dte[0].axes[0]
        assert axis.units == 's'
        assert axis.get_data()[1] == pytest.approx(1 / 512.)
        plugin.close()

    def test_a_buffer_that_does_not_fill_is_an_error(self, qapp, fake):
        plugin = make_detector(DAQ_1DViewer_LockInSR830, npts=50)
        plugin.controller.start_scan = lambda: None  # nothing is recorded
        with pytest.raises(TimeoutError):
            plugin.grab_data()
        plugin.close()

