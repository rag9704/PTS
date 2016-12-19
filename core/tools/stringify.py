#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.tools.stringify Provides useful functions for converting objects of various types to strings.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import warnings
import numpy as np
from types import NoneType

# Import the relevant PTS classes and modules
from ..basics.filter import Filter
from ..basics.range import RealRange, IntegerRange, QuantityRange

# -----------------------------------------------------------------

def stringify(value):

    """
    This function ...
    :param value:
    :return:
    """

    if isinstance(value, list):

        strings = []
        ptype = None
        for entry in value:

            parsetype, val = stringify_not_list(entry)

            if ptype is None: ptype = parsetype
            elif ptype != parsetype: raise ValueError("Nonuniform list")

            strings.append(val)

        return ptype + "_list", ",".join(strings)

    elif isinstance(value, tuple):

        strings = []
        ptype = None
        for entry in value:

            parsetype, val = stringify_not_list(entry)

            if ptype is None: ptype = parsetype
            elif ptype != parsetype: raise ValueError("Nonuniform tuple")

            strings.append(val)

        return ptype + "_tuple", ",".join(strings)

    else: return stringify_not_list(value)

# -----------------------------------------------------------------

def stringify_not_list(value):

    """
    This function ...
    :param value:
    :return:
    """

    from astropy.units import Quantity
    from astropy.coordinates import Angle
    from pts.magic.basics.coordinate import SkyCoordinate
    from pts.magic.basics.stretch import SkyStretch

    if isinstance(value, bool): return "boolean", str(value)
    elif isinstance(value, int): return "integer", str(value)
    elif isinstance(value, float) or isinstance(value, np.float32) or isinstance(value, np.float64): return "real", repr(value)
    elif isinstance(value, basestring): return "string", value
    elif isinstance(value, Quantity): return "quantity", repr(value.value) + " " + str(value.unit).replace("solMass", "Msun").replace("solLum", "Lsun").replace(" ", "")
    elif isinstance(value, Angle): return "angle", repr(value.value) + " " + str(value.unit).replace(" ", "")
    elif isinstance(value, NoneType): return "None", "None"
    elif isinstance(value, RealRange): return "real_range", repr(value)
    elif isinstance(value, IntegerRange): return "integer_range", repr(value)
    elif isinstance(value, QuantityRange): return "quantity_range", repr(value)
    elif isinstance(value, SkyCoordinate): return "skycoordinate", repr(value.ra.value) + " " + str(value.ra.unit) + "," + repr(value.dec.value) + " " + str(value.dec.unit)
    elif isinstance(value, SkyStretch): return "skystretch", repr(value.ra.value) + " " + str(value.ra.unit) + "," + repr(value.dec.value) + " " + str(value.dec.unit)
    elif isinstance(value, Filter): return "filter", str(value)
    else: raise ValueError("Unrecognized type: " + str(type(value)))

# -----------------------------------------------------------------

def str_from_angle(angle):

    try: return str(angle.to("deg").value) + " deg"
    except AttributeError: return str(angle)

# -----------------------------------------------------------------

def str_from_quantity(quantity, unit=None):

    """
    This function ...
    :param quantity:
    :param unit:
    :return:
    """

    if unit is not None:

        if not quantity.__class__.__name__ == "Quantity": raise ValueError("Value is not a quantity, so unit cannot be converted")
        return str(quantity.to(unit).value)

    elif quantity.__class__.__name__ == "Quantity":

        to_string = str(quantity.value) + " " + str(quantity.unit).replace(" ", "")
        return to_string.replace("solMass", "Msun").replace("solLum", "Lsun")

    else:

        warnings.warn("The given value is not a quantity but a scalar value. No guarantee can be given that the parameter value"
                      "is specified in the correct unit")
        return str(quantity)

# -----------------------------------------------------------------

def str_from_bool(boolean):
    return str(boolean).lower()

# -----------------------------------------------------------------