"""Fakes of the SR830 (``pymeasure`` driver) and of its VISA session, to run the plugins without instrument."""
import numpy as np

from pymodaq_plugins_stanford_research_systems.hardware.sr830 import CHANNELS


class FakeAdapter:
    def __init__(self):
        self.is_open = True

    def close(self):
        self.is_open = False


class FakeSR830:
    """The part of ``pymeasure.instruments.srs.sr830.SR830`` used by the plugins; records the calls"""
    id = 'Stanford_Research_Systems,SR830,s/n00001,ver1.07'

    def __init__(self, address='FAKE'):
        self.address = address
        self.adapter = FakeAdapter()
        self.calls = []
        self.sample_frequency = 512.
        self.buffer_count = 0
        self.values = {name: float(ind) for ind, name in enumerate(CHANNELS)}

    def snap(self, val1='X', val2='Y', *vals):
        names = [val1, val2, *vals]
        self.calls.append(('snap', tuple(names)))
        return [self.values[name] for name in names]

    def start_scan(self):
        self.calls.append(('start_scan',))
        self.buffer_count = 4000  # the buffer fills instantly

    def wait_for_buffer(self, count, has_aborted=lambda: False, timeout=60, timestep=0.01):
        self.calls.append(('wait_for_buffer', count))

    def get_buffer(self, channel=1, start=0, end=None):
        end = self.buffer_count if end is None else end
        return np.full(end - start, float(channel))

    def pause_scan(self):
        self.calls.append(('pause_scan',))

    def reset_buffer(self):
        self.buffer_count = 0

    def start_buffer(self, fast=True):
        pass

    def clear(self):
        pass

    def shutdown(self):
        self.calls.append(('shutdown',))

    def reset(self):
        self.calls.append(('reset',))

    def load_setup(self, number):
        self.calls.append(('load_setup', number))

    def save_setup(self, number):
        self.calls.append(('save_setup', number))

    def aquireOnTrigger(self, enable=True):
        self.calls.append(('aquireOnTrigger', enable))

