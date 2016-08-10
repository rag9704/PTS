#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.launch.timing Contains the TimingTable class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from ..basics.table import SmartTable

# -----------------------------------------------------------------

class TimingTable(SmartTable):

    """
    This class ...
    """

    column_info = [("Simulation name", str, None, "Name of the simulation"),
                   ("Timestamp", str, None, "Timestamp"),
                   ("Host id", str, None, "Remote host ID"),
                   ("Cluster name", str, None, "Remote cluster name"),
                   ("Cores", int, None, "number of cores"),
                   ("Threads per core", int, None, "number of threads per core"),
                   ("Processes", int, None, "number of processes"),
                   ("Wavelengths", int, None, "number of wavelengths"),
                   ("Packages", int, None, "number of photon packages per wavelength"),
                   ("Dust cells", int, None, "number of dust cells"),
                   ("Self-absorption", bool, None, "self-absorption enabled"),
                   ("Transient heating", bool, None, "transient (non-LTE) heating enabled"),
                   ("Data-parallel", bool, None, "data parallelization enabled"),
                   ("Total runtime", float, "s", "total simulation time"),
                   ("Setup time", float, "s", "time spent in simulation setup"),
                   ("Stellar emission time", float, "s", "time spent shooting stellar photon packages"),
                   ("Spectra calculation time", float, "s", "time spent in calculation of dust emission spectra"),
                   ("Dust emission time", float, "s", "time spent shooting dust emission photon packages"),
                   ("Writing time", float, "s", "time spent writing to disk"),
                   ("Waiting time", float, "s", "time spent waiting for other processes"),
                   ("Communication time", float, "s", "time spent in inter-process communication"),
                   ("Intermediate time", float, "s", "time spent in between other phases")]

    # -----------------------------------------------------------------

    def add_entry(self, name, timestamp, host_id, cluster_name, cores, threads_per_core, processes, wavelengths,
                  packages, cells, selfabsorption, transient_heating, data_parallel, total_runtime, setup_time,
                  stellar_time, spectra_time, dust_time, writing_time, waiting_time, communication_time,
                  intermediate_time):

        """
        This function ...
        :param name:
        :param timestamp:
        :param host_id:
        :param cluster_name:
        :param cores:
        :param threads_per_core:
        :param processes:
        :param wavelengths:
        :param packages:
        :param cells:
        :param selfabsorption:
        :param transient_heating:
        :param data_parallel:
        :param total_runtime:
        :param setup_time:
        :param stellar_time:
        :param spectra_time:
        :param dust_time:
        :param writing_time:
        :param waiting_time:
        :param communication_time:
        :param intermediate_time:
        :return:
        """

        #if cluster_name is None: cluster_name = "--"

        values = [name, timestamp, host_id, cluster_name, cores, threads_per_core, processes, wavelengths, packages,
                  cells, selfabsorption, transient_heating, data_parallel, total_runtime, setup_time, stellar_time,
                  spectra_time, dust_time, writing_time, waiting_time, communication_time, intermediate_time]

        # Resize string columns for longer entries
        self._resize_string_columns(values)

        # Add a row to the table
        self.add_row(values)

# -----------------------------------------------------------------
