#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.do.modeling.fit_sed Determine the best fit with the observed SED

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import argparse

# Import the relevant PTS classes and modules
from pts.modeling.fitting.sedfitting import SEDFitter
from pts.core.tools import logging, time, parsing, filesystem

# -----------------------------------------------------------------

# Create the command-line parser
parser = argparse.ArgumentParser()

# Logging options
parser.add_argument("--debug", action="store_true", help="add this option to enable debug output")
parser.add_argument("--report", action='store_true', help='write a report file')
parser.add_argument("--config", type=str, help="the name of a configuration file")

# Visualisation
parser.add_argument("--visualise", action="store_true", help="make visualisations")

# Parse the command line arguments
arguments = parser.parse_args()

# -----------------------------------------------------------------

# Set the modeling path
arguments.path = filesystem.cwd()

# -----------------------------------------------------------------

# Determine the log file path
logfile_path = filesystem.join(arguments.path, time.unique_name("log") + ".txt") if arguments.report else None

# Determine the log level
level = "DEBUG" if arguments.debug else "INFO"

# Initialize the logger
log = logging.setup_log(level=level, path=logfile_path)
log.start("Starting fit_sed ...")

# -----------------------------------------------------------------

# Create a SEDFitter object
fitter = SEDFitter.from_arguments(arguments)

# Run the fitter
fitter.run()

# -----------------------------------------------------------------
