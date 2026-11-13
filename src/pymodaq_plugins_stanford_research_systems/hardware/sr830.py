"""Access to the SR830 lock-in amplifier, shared by the instrument plugins.

Nothing here talks to the instrument when the module is imported (the VISA backend may be missing on the machine, a
plugin must stay importable): the resources are listed and opened on request only.
"""
from typing import Iterable, List, Optional

from pymeasure.instruments.srs.sr830 import SR830

#: What ``SNAP`` can record (``SR830.SNAP_ENUMERATION``), with the unit of each value
CHANNELS = ['X', 'Y', 'R', 'Theta', 'Aux In 1', 'Aux In 2', 'Aux In 3', 'Aux In 4', 'Frequency', 'CH1', 'CH2']
CHANNEL_UNITS = {'X': 'V', 'Y': 'V', 'R': 'V', 'Theta': 'deg', 'Aux In 1': 'V', 'Aux In 2': 'V', 'Aux In 3': 'V',
                 'Aux In 4': 'V', 'Frequency': 'Hz', 'CH1': '', 'CH2': ''}  # CH1 and CH2 follow the display setting
DEFAULT_ADDRESS = 'GPIB0::8::INSTR'  # the factory GPIB address of the SR830 is 8


def visa_resources() -> List[str]:
    """The VISA resources found on this computer, an empty list if there is no VISA backend"""
    try:
        from pyvisa import ResourceManager
        return list(ResourceManager().list_resources())
    except Exception:  # no backend installed: the user types the address
        return []


def open_sr830(address: str) -> SR830:
    """Open the SR830 at a VISA address (``GPIB0::8::INSTR``, ``ASRL3::INSTR``...)"""
    return SR830(address)


def close_sr830(controller: SR830) -> None:
    """Release the VISA session (``SR830.shutdown`` only flags the instrument as shut down)"""
    controller.adapter.close()


def snap(controller: SR830, names: Iterable[str]) -> List[float]:
    """Record the values of channels at the same instant, as many as asked

    ``SNAP`` records 2 to 6 values: ask by groups of 6. The driver adds ``Y`` to a lonely last value, dropped here.
    """
    names = list(names)
    values: List[float] = []
    for start in range(0, len(names), 6):
        group = names[start:start + 6]
        values.extend(controller.snap(*group)[:len(group)])
    return values


def open_visa(address: str, timeout_ms: int = 2000):
    """Open the instrument as a plain VISA resource (for the plugin that sends the commands itself)"""
    from pyvisa import ResourceManager
    resource = ResourceManager().open_resource(address)
    resource.timeout = timeout_ms
    return resource
