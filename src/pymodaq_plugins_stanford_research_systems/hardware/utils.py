# -*- coding: utf-8 -*-
"""
Created the 17/04/2023

@author: Sebastien Weber
"""
from typing import Tuple
from pyvisa import ResourceManager


def get_resources() -> Tuple[str]:

    rm = ResourceManager()
    resources = rm.list_resources('?*')
    rm.close()
    return resources
