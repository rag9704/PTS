#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.modeling.fitting.advancedparameterexplorer Contains the AdvancedParameterExplorer class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import the relevant PTS classes and modules
from .parameterexploration import ParameterExplorer
from ...core.tools import tables
from ...core.tools.logging import log
from ...core.launch.options import SchedulingOptions
from ...core.launch.parallelization import Parallelization
from ...core.launch.runtime import RuntimeEstimator
from ...core.basics.distribution import Distribution

# -----------------------------------------------------------------

class AdvancedParameterExplorer(ParameterExplorer):
    
    """
    This class...
    """

    def __init__(self, config=None):

        """
        The constructor ...
        :param config:
        :return:
        """

        # Call the constructor of the base class
        super(AdvancedParameterExplorer, self).__init__(config)

        # -- Attributes --

        # The probability distributions for the different fit parameters
        self.distributions = dict()

        # A dictionary with the scheduling options for the different remote hosts
        self.scheduling_options = dict()

    # -----------------------------------------------------------------

    @classmethod
    def from_arguments(cls, arguments):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Create a new ParameterExplorer instance
        explorer = cls(arguments.config)

        # Set the modeling path
        explorer.config.path = arguments.path

        # Set the number of simulations to launch in the batch
        if arguments.simulations is not None: explorer.config.simulations = arguments.simulations

        # Set the remote host IDs
        if arguments.remotes is not None: explorer.config.remotes = arguments.remotes

        # Set the limits of the FUV luminosity of the young stellar population
        if arguments.young is not None:
            explorer.config.young_stars.min = arguments.young[0]
            explorer.config.young_stars_max = arguments.young[1]

        # Set the limits of the FUV luminosity of the ionizing stellar population
        if arguments.ionizing is not None:
            explorer.config.ionizing_stars.min = arguments.ionizing[0]
            explorer.config.ionizing_stars.max = arguments.ionizing[1]

        # Set the limits of the dust mass
        if arguments.dust is not None:
            explorer.config.dust.min = arguments.dust[0]
            explorer.config.dust.max = arguments.dust[1]

        # Return the new instance
        return explorer

    # -----------------------------------------------------------------

    def run(self):

        """
        This function ...
        :return:
        """

        # 1. Call the setup function
        self.setup()

        # 2. Load the current parameter table
        self.load_table()

        # 3. Load the ski file
        self.load_ski()

        # Load the probability distributions for the different parameters
        self.load_distributions()

        # 4. Set the combinations of parameter values
        self.set_parameters()

        # 5. Set the parallelization schemes for the different remote hosts
        self.set_parallelization()

        # 6. Estimate the runtimes for the different remote hosts
        self.estimate_runtimes()

        # 7. Launch the simulations for different parameter values
        self.simulate()

        # 8. Writing
        self.write()

    # -----------------------------------------------------------------

    def load_distributions(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading the probability distributions for the different fit parameters ...")

        # Loop over the different fit parameters
        for parameter_name in self.parameter_names:

            # Load the probability distribution
            distribution = Distribution.from_file(self.distribution_table_paths[parameter_name])

            # Set the distribution
            self.distributions[parameter_name] = distribution

    # -----------------------------------------------------------------

    def set_parameters(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Picking random parameter values based on the probability distributions ...")

        # Debugging
        if log.is_debug() and False:

            # Young stars
            x_limits = [self.config.young_stars.min, self.config.young_stars.max]
            #print(self.distributions["FUV young"].cumulative_smooth(x_limits[0], x_limits[1]))
            self.distributions["FUV young"].plot_smooth(x_limits=x_limits, title="Probability distribution from which FUV luminosities of young stars will be drawn")
            self.distributions["FUV young"].plot_smooth(x_limits=x_limits, title="Probability distribution from which FUV luminosities of young stars will be drawn (in log scale)")
            self.distributions["FUV young"].plot_cumulative_smooth(x_limits=x_limits, title="Cumulative distribution of FUV luminosities of young stars")

            # Ionizing stars
            x_limits = [self.config.ionizing_stars.min, self.config.ionizing_stars.max]
            #print(self.distributions["FUV ionizing"].cumulative_smooth(x_limits[0], x_limits[1]))
            self.distributions["FUV ionizing"].plot_smooth(x_limits=x_limits, title="Probability distribution from which FUV luminosities of ionizing stars will be drawn")
            self.distributions["FUV ionizing"].plot_smooth(x_limits=x_limits, title="Probability distribution from which FUV luminosities of ionizing stars will be drawn (in log scale)")
            self.distributions["FUV ionizing"].plot_cumulative_smooth(x_limits=x_limits, title="Cumulative distribution of FUV luminosities of ionizing stars")

            # Dust mass
            x_limits = [self.config.dust.min, self.config.dust.max]
            #print(self.distributions["Dust mass"].cumulative_smooth(x_limits[0], x_limits[1]))
            self.distributions["Dust mass"].plot_smooth(x_limits=x_limits, title="Probability distribution from which dust masses will be drawn")
            self.distributions["Dust mass"].plot_smooth(x_limits=x_limits, title="Probability distribution from which dust masses will be drawn (in log scale)")
            self.distributions["Dust mass"].plot_cumulative_smooth(x_limits=x_limits, title="Cumulative distribution of dust masses")

        # Draw parameters values for the specified number of simulations
        for counter in range(self.config.simulations):

            # Debugging
            log.debug("Calculating random parameter set " + str(counter+1) + " of " + str(self.config.simulations) + " ...")

            # Draw a random FUV luminosity of the young stellar population
            young_luminosity = self.distributions["FUV young"].random(self.config.young_stars.min, self.config.young_stars.max)

            # Draw a random FUV luminosity of the ionizing stellar population
            ionizing_luminosity = self.distributions["FUV ionizing"].random(self.config.ionizing_stars.min, self.config.ionizing_stars.max)

            # Draw a random dust mass
            dust_mass = self.distributions["Dust mass"].random(self.config.dust.min, self.config.dust.max)

            # Add the combination of parameter values to the list
            combination = (young_luminosity, ionizing_luminosity, dust_mass)
            self.parameters.append(combination)

    # -----------------------------------------------------------------

    def set_parallelization(self):

        """
        This function sets the parallelization scheme for those remote hosts used by the batch launcher that use
        a scheduling system (the parallelization for the other hosts is left up to the batch launcher and will be
        based on the current load of the correponding system).
        :return:
        """

        # Inform the user
        log.info("Setting the parallelization scheme for the remote host(s) that use a scheduling system ...")

        # Loop over the IDs of the hosts used by the batch launcher that use a scheduling system
        for host in self.launcher.scheduler_hosts:

            # Debugging
            log.debug("Setting the parallelization scheme for host '" + host.id + "' ...")

            # Get the number of cores per node for this host
            cores_per_node = host.clusters[host.cluster_name].cores

            # Determine the number of cores corresponding to 4 full nodes
            cores = cores_per_node * 4

            # Use 1 core for each process (assume there is enough memory)
            processes = cores

            # Determine the number of threads per core
            if host.use_hyperthreading: threads_per_core = host.clusters[host.cluster_name].threads_per_core
            else: threads_per_core = 1

            # Create a Parallelization instance
            parallelization = Parallelization(cores, threads_per_core, processes)

            # Debugging
            log.debug("Parallelization scheme: " + str(parallelization))

            # Set the parallelization for this host
            self.launcher.set_parallelization_for_host(host.id, parallelization)

    # -----------------------------------------------------------------

    def estimate_runtimes(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Estimating the runtimes based on the results of previous runs ...")

        # Get the number of photon packages (per wavelength) for this batch of simulations
        current_packages = self.ski.packages()

        # Create a RuntimeEstimator instance
        estimator = RuntimeEstimator.from_file(self.timing_table_path)

        # Initialize a dictionary to contain the estimated walltimes for the different hosts with scheduling system
        walltimes = dict()

        # Loop over the hosts which use a scheduling system and estimate the walltime
        for host_id in self.launcher.scheduler_host_ids:

            # Debugging
            log.debug("Estimating the runtime for host '" + host_id + "' ...")

            # Get the parallelization scheme that we have defined for this remote host
            parallelization = self.launcher.parallelization_for_host(host_id)

            # Estimate the runtime for the current number of photon packages and the current remote host
            runtime = estimator.runtime_for(host_id, current_packages, parallelization)

            # Debugging
            log.debug("The estimated runtime for this host is " + str(runtime) + " seconds")

            # Set the estimated walltime
            walltimes[host_id] = runtime

        # Create and set scheduling options for each host that uses a scheduling system
        for host_id in walltimes: self.scheduling_options[host_id] = SchedulingOptions.from_dict({"walltime": walltimes[host_id]})

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing ...")

        # Create and write a table with the parameter values for each simulation
        self.write_parameter_table()

    # -----------------------------------------------------------------

    def write_parameter_table(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Writing the parameter table ...")

        # Set the units of the parameter table
        self.table["FUV young"].unit = "Lsun_FUV"
        self.table["FUV ionizing"].unit = "Lsun_FUV"
        self.table["Dust mass"].unit = "Msun"

        # Write the parameter table
        tables.write(self.table, self.parameter_table_path, format="ascii.ecsv")

# -----------------------------------------------------------------
