#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.launch.batchlauncher Contains the BatchLauncher class.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import math
import traceback
from collections import defaultdict

# Import the relevant PTS classes and modules
from ..basics.configurable import Configurable
from ..simulation.remote import SKIRTRemote
from ..remote.remote import Remote
from .options import LoggingOptions
from ..tools import introspection, time
from ..tools import filesystem as fs
from ..basics.log import log
from ..remote.host import Host, load_host
from .analyser import SimulationAnalyser
from .options import AnalysisOptions
from ..simulation.definition import create_definitions
from ..advanced.parallelizationtool import ParallelizationTool
from ..basics.handle import ExecutionHandle
from ..tools import parallelization as par
from ..simulation.execute import SkirtExec
from ..simulation.input import SimulationInput
from ..simulation.skifile import SkiFile
from ..simulation.arguments import SkirtArguments
from ..tools import formatting as fmt

# -----------------------------------------------------------------

class BatchLauncher(Configurable):

    """
    This class ...
    """

    def __init__(self, *args, **kwargs):

        """
        The constructor ...
        :param kwargs:
        :return:
        """

        # Call the constructor of the base class
        super(BatchLauncher, self).__init__(*args, **kwargs)

        # -- Attributes --

        # The local SKIRT execution context
        self.skirt = SkirtExec()

        # Initialize a list to contain different SKIRTRemote instances for the different remote hosts
        self.remotes = []

        # For some remote hosts, if they use a scheduling system, defines the name of the cluster to be used
        # (the default cluster will be used if not defined)
        self.cluster_names = dict()

        # The queue for locally executed simulations
        self.local_queue = []

        # The queues for the different remote hosts
        self.queues = defaultdict(list)

        # The scheduling options for (some of) the simulations and (some of) the remote hosts. This is a nested
        # dictionary where the first key represents the remote host ID and the next key represents the name of the
        # simulation (see 'name' parameter of 'add_to_queue')
        self.scheduling_options = defaultdict(dict)

        # The assignment from items in the queue to the different remote hosts
        self.assignment = None

        # The parallelization scheme for local execution
        self.parallelization_local = None

        # The parallelization scheme for the different remote hosts
        self.parallelization_hosts = dict()

        # THe parallelization scheme for the different simulations
        self.parallelization_simulations = dict()

        # The paths to the directories for placing the (screen/job) scripts (for manual inspection) for the different remote hosts
        self.script_paths = dict()

        # The list of remote hosts for which the screen output should be saved remotely (for debugging)
        self.save_screen_output = []

        # The simulations that have been launched
        self.launched_simulations = []

        # The simulations that have been retrieved
        self.simulations = []

        # Create a SimulationAnalyser instance
        self.analyser = SimulationAnalyser()

        # The logging options
        self.logging_options = None

        # Create temporary local directory
        self.temp_path = introspection.create_temp_dir(time.unique_name("BatchLauncher"))

        # Original definitions of local simulations (when definitions are changed because of shared input)
        self.original_local_definitions = dict()

    # -----------------------------------------------------------------

    @property
    def uses_remotes(self):

        """
        This function ...
        :return:
        """

        return len(self.config.remotes) > 0 or len(self.remotes) > 0

    # -----------------------------------------------------------------

    @property
    def only_local(self):

        """
        This function ...
        :return:
        """

        return len(self.config.remotes) == 0 and len(self.remotes) == 0

    # -----------------------------------------------------------------

    def in_queue_for_host(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        return len(self.queues[host_id])

    # -----------------------------------------------------------------

    @property
    def shortest_queue_host_id(self):

        """
        This function ...
        :return:
        """

        size = float('inf')
        host_id = None

        for host in self.hosts:
            queue_size = self.in_queue_for_host(host.id)
            if queue_size < size:
                size = queue_size
                host_id = host.id

        # Return the ID of the shortest
        return host_id

    # -----------------------------------------------------------------

    def add_to_queue(self, definition, name, host_id=None, parallelization=None, analysis_options=None, local=False):

        """
        This function ...
        :param definition:
        :param name: a name that is given to the simulation
        :param host_id: the host on which this simulation should be executed
        :param parallelization: individual parallelization scheme for this particular simulation (only allowed if host_id is also specified)
        :param analysis_options: analysis options (if None, analysis options will be created from batch launcher configuration)
        :param local:
        :return:
        """

        # Debugging
        log.debug("Adding simulation '" + name + "' to the queue ...")

        # Check whether the simulation name doesn't contain spaces
        if " " in name: raise ValueError("The simulation name cannot contain spaces")

        # Local execution
        if local or self.nremotes == 0:

            # Add to the local queue
            self.local_queue.append((definition, name, analysis_options))

            # If parallelization is specified, set it
            if parallelization is not None: self.set_parallelization_for_simulation(name, parallelization)

        # If a host ID is specified
        elif host_id is not None:

            # Check if this is a valid host ID
            if not host_id in self.host_ids: raise ValueError("Invalid host ID")

            # Add to the queue of the specified host
            self.queues[host_id].append((definition, name, analysis_options))

            # If parallelization is specified, set it
            if parallelization is not None: self.set_parallelization_for_simulation(name, parallelization)

        else:

            # Check whether, if parallelization is specified, that host ID is also specified
            if parallelization is not None: raise ValueError("If parallelization is specified, host ID must also be specified")

            # Determine the ID of the hosts with the shortest queue (or the first if the queues are equally long)
            host_id = self.shortest_queue_host_id

            # Add to the queue of the host
            self.queues[host_id].append((definition, name, analysis_options))

    # -----------------------------------------------------------------

    def set_cluster_for_host(self, host_id, cluster_name):

        """
        This function ...
        :param host_id:
        :param cluster_name:
        :return:
        """

        self.cluster_names[host_id] = cluster_name

    # -----------------------------------------------------------------

    def set_scheduling_options(self, host_id, name, options):

        """
        This function ...
        :param name:
        :param host_id:
        :param options:
        :return:
        """

        # Set the scheduling options for the specified host and for the specified simulation
        self.scheduling_options[host_id][name] = options

    # -----------------------------------------------------------------

    @property
    def in_queue(self):

        """
        This function ...
        :return:
        """

        # Return the total number of simulations in the queues
        return self.in_local_queue + self.in_remote_queues

    # -----------------------------------------------------------------

    @property
    def in_local_queue(self):

        """
        This function ...
        :return:
        """

        return len(self.local_queue)

    # -----------------------------------------------------------------

    @property
    def in_remote_queues(self):

        """
        This function ...
        :return:
        """

        total = 0
        for host_id in self.host_ids: total += self.in_remote_queue(host_id)
        return total

    # -----------------------------------------------------------------

    @property
    def has_queued_local(self):

        """
        This function ...
        :return:
        """

        return self.in_local_queue > 0

    # -----------------------------------------------------------------

    @property
    def has_queued_remotes(self):

        """
        This function ...
        :return:
        """

        return self.in_remote_queues > 0

    # -----------------------------------------------------------------

    def has_queued_remote(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        return self.in_remote_queue(host_id) > 0

    # -----------------------------------------------------------------

    def in_remote_queue(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        self.in_queue_for_host(host_id)

    # -----------------------------------------------------------------

    @property
    def single_remote(self):

        """
        This function ...
        :return:
        """

        # The setup has not been called yet
        if len(self.remotes) == 0:

            # Warning
            log.warning("The setup has not been called yet, creating temporary remote execution environment (limited to basic capabilities)")

            # Get the single host ID
            host_id = self.single_host_id

            # Create a remote execution context
            remote = Remote()

            # Check whether a cluster name is defined
            cluster_name = self.cluster_names[host_id] if host_id in self.cluster_names else None

            # Setup the remote for the specified host
            remote.setup(host_id, cluster_name=cluster_name)

            # Return the remote environment
            return remote

        elif len(self.remotes) == 1: return self.remotes[0]
        else: raise RuntimeError("Multiple remotes have been configured for this batch launcher")

    # -----------------------------------------------------------------

    @property
    def single_host(self):

        """
        This function ...
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            if len(self.host_ids) != 1: raise RuntimeError("Multiple remotes have been configured for this batch launcher")
            else: return self.hosts[0]

        else: return self.single_remote.host

    # -----------------------------------------------------------------

    @property
    def single_host_id(self):

        """
        This function ...
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            if len(self.host_ids) != 1: raise RuntimeError("Multiple remotes have been configured for this batch launcher")
            else: return self.host_ids[0]

        else: return self.single_remote.host_id

    # -----------------------------------------------------------------

    @property
    def host_ids(self):

        """
        This function returns the IDs of the hosts that will be used by the batch launcher
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            # If a list of remotes is defined
            if self.config.remotes is not None: host_ids = self.config.remotes

            # If a list of remotes is not defined, create a remote for all of the hosts that have a configuration file
            else: host_ids = introspection.remote_host_ids()

            # Return the list of host IDs
            return host_ids

        # If the setup has already been called
        else: return [remote.host_id for remote in self.remotes]

    # -----------------------------------------------------------------

    @property
    def hosts(self):

        """
        This function returns the Host objects for all the hosts that will be used by the batch launcher
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            # Create the list of hosts
            hosts = []
            for host_id in self.host_ids: hosts.append(load_host(host_id))

            # Return the list of hosts
            return hosts

        # If the setup has already been called
        else: return [remote.host for remote in self.remotes]

    # -----------------------------------------------------------------

    @property
    def scheduler_host_ids(self):

        """
        This function returns just the IDS of the hosts which use a scheduling system. This is useful for when example
        the user wants to specify the parallelization scheme only for these hosts, while the parallelization strategy
        for the other hosts can be left up to the BatchLauncher class based on the current load of that system.
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            # Initialize a list to contain the host IDs
            host_ids = []

            # Loop over the IDs of all the hosts used by the BatchLauncher
            for host_id in self.host_ids:

                # Create Host instance
                host = load_host(host_id)

                # If it's a scheduler, add it to the list
                if host.scheduler: host_ids.append(host_id)

            # Return the list of hosts which use a scheduling system
            return host_ids

        # If the setup has already been called
        else: return [remote.host_id for remote in self.remotes if remote.scheduler]

    # -----------------------------------------------------------------

    @property
    def scheduler_hosts(self):

        """
        This function is similar to 'scheduler_host_ids' but returns the Host objects instead of just the IDs of these
        hosts.
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            # Initialize a list to contain the hosts
            hosts = []

            # Loop over the IDs of all the hosts used by the BatchLauncher
            for host_id in self.host_ids:

                # Create a Host instance
                host = load_host(host_id)

                # If it's a scheulder, add it to the list
                if host.scheduler: hosts.append(host)

            # Return the list of hosts
            return hosts

        # If the setup has already been called
        else: return [remote.host for remote in self.remotes if remote.scheduler]

    # -----------------------------------------------------------------

    @property
    def no_scheduler_host_ids(self):

        """
        This function returns just the IDS of the hosts which DON'T use a scheduling system.
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            # Initialize a list to contain the host IDs
            host_ids = []

            # Loop over the IDs of all the hosts used by the BatchLauncher
            for host_id in self.host_ids:

                # Create Host instance
                host = load_host(host_id)

                # If it's not a scheduler, add it to the list
                if not host.scheduler: host_ids.append(host_id)

            # Return the list of hosts which don't use a scheduling system
            return host_ids

        # If the setup has already been called
        else: return [remote.host_id for remote in self.remotes if not remote.scheduler]

    # -----------------------------------------------------------------

    @property
    def no_scheduler_hosts(self):

        """
        This function is similar to 'no_scheduler_host_ids' but returns the Host objects instead of just the IDs of these
        hosts.
        :return:
        """

        # If the setup has not been called yet
        if len(self.remotes) == 0:

            # Initialize a list to contain the hosts
            hosts = []

            # Loop over the IDs of all the hosts used by the BatchLauncher
            for host_id in self.host_ids:

                # Create a Host instance
                host = load_host(host_id)

                # If it's a not scheulder, add it to the list
                if not host.scheduler: hosts.append(host)

            # Return the list of hosts
            return hosts

        # If the setup has already been called
        else: return [remote.host for remote in self.remotes if not remote.scheduler]

    # -----------------------------------------------------------------

    @property
    def uses_schedulers(self):

        """
        This function ...
        :return:
        """

        return len(self.scheduler_host_ids) > 0

    # -----------------------------------------------------------------

    @property
    def nremotes(self):

        """
        This function ...
        :return:
        """

        return len(self.remotes)

    # -----------------------------------------------------------------

    def set_parallelization_for_local(self, parallelization):

        """
        This function ...
        :param parallelization:
        :return:
        """

        # Set
        self.parallelization_local = parallelization

    # -----------------------------------------------------------------

    def set_parallelization_for_host(self, host_id, parallelization):

        """
        This function ...
        :param host_id:
        :param parallelization:
        :return:
        """

        # Set the parallelization properties for the specified host
        self.parallelization_hosts[host_id] = parallelization

    # -----------------------------------------------------------------

    def set_parallelization_for_simulation(self, name, parallelization):

        """
        This function ...
        :param name:
        :param parallelization:
        :return:
        """

        # Set the parallelization for this host and this simulation
        self.parallelization_simulations[name] = parallelization

    # -----------------------------------------------------------------

    def parallelization_for_host(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        return self.parallelization_hosts[host_id] if host_id in self.parallelization_hosts else None

    # -----------------------------------------------------------------

    def parallelization_for_simulation(self, name):

        """
        This function ...
        :param name:
        :return:
        """

        return self.parallelization_simulations[name] if name in self.parallelization_simulations else None

    # -----------------------------------------------------------------

    def run(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # 1. Call the setup function
        self.setup(**kwargs)

        # 2. Check the input files for all simulations
        self.check_input()

        # 2. Set the parallelization scheme for the remote hosts for which this was not specified by the user
        self.set_parallelization()

        # 3. Launch the simulations
        self.launch()

        # 4. Retrieve the simulations that are finished
        self.try_retrieving()

        # Show the simulations that are finished
        if self.has_simulations and self.config.show: self.show()

        # 5. Analyse the output of the retrieved simulations
        if self.has_simulations: self.try_analysing()

        # Write
        self.write()

    # -----------------------------------------------------------------

    def clear(self):

        """
        This function ...
        :return:
        """

        # Log out from the remotes
        for remote in self.remotes: remote.logout()

        # Clear the list of remotes
        self.remotes = []

        # Clear the cluster names
        self.cluster_names = dict()

        # Clear the queues
        self.local_queue = []
        self.queues = defaultdict(list)

        # Clear the scheduling options
        self.scheduling_options = defaultdict(dict())

        # Clear the assignment
        self.assignment = None

        # Clear the launched simulations
        self.launched_simulations = []

        # Clear the simulations
        self.simulations = []

        # Clear the script path dictionary
        self.script_paths = dict()

    # -----------------------------------------------------------------

    @property
    def has_remotes(self):

        """
        This function ...
        :return: 
        """

        return len(self.remotes) > 0

    # -----------------------------------------------------------------

    def setup(self, **kwargs):

        """
        This function ...
        :param kwargs:
        :return:
        """

        # Call the setup function of the base class
        super(BatchLauncher, self).setup(**kwargs)

        # Setup the remote instances
        if not self.has_remotes: self.setup_remotes()

        # Create the logging options
        self.logging_options = LoggingOptions()
        self.logging_options.set_options(self.config.logging)

        # Add simulation definitions for ski file present in the current working directory (if nothing is added to the queue manually)
        if self.in_queue == 0: self.load_queue()

        # If attached mode is enabled, check whether all remotes are non-schedulers
        if self.config.attached and self.uses_schedulers: raise ValueError("Cannot use attached mode when remotes with scheduling system are used")

        # If dry mode is enabled, check whether all remotes are non-schedulers
        if self.config.dry and self.uses_schedulers: log.warning("Using dry mode when remotes with scheduling system are used can be impractical, since it requires uploading and submitting each seperate job script")

    # -----------------------------------------------------------------

    def setup_remotes(self):

        """
        This function ...
        :return:
        """

        # If a list of remotes is defined
        if self.config.remotes is not None: host_ids = self.config.remotes
        else: host_ids = []

        # If a list of remotes is not defined, execute locally
        if len(host_ids) == 0: log.warning("No remote set: simulations will be performed locally")

        # Loop over all the remote host ids
        for host_id in host_ids:

            # Create a remote SKIRT execution context
            remote = SKIRTRemote()

            # Check whether a cluster name is defined
            cluster_name = self.cluster_names[host_id] if host_id in self.cluster_names else None

            # Setup the remote for the specified host, check if succesful
            if not remote.setup(host_id, cluster_name=cluster_name):
                log.warning("Remote host '" + host_id + "' is down")
                continue

            # Add the remote to the list of remote objects
            self.remotes.append(remote)

        # Check if any remotes are initialized
        if len(host_ids) > 0 and len(self.remotes) == 0: raise RuntimeError("None of the remotes are available")

    # -----------------------------------------------------------------

    def load_queue(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Loading ski files in the current working directory into the queue ...")

        # Create simulation definitions from the working directory and add them to the queue
        for definition in create_definitions(self.config.path, self.config.output, self.config.input, recursive=self.config.recursive):

            # Add the definition to the queue
            self.add_to_queue(definition, definition.prefix)

    # -----------------------------------------------------------------

    def get_definition_for_local_simulation(self, simulation_name):

        """
        This function ...
        :param simulation_name:
        :return:
        """

        for definition, name, _ in self.local_queue:
            if name == simulation_name: return definition

        raise ValueError("No simulation found in the local queue with the name '" + simulation_name + "'")

    # -----------------------------------------------------------------

    def check_input(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Checking the input of the simulations that are run locally ...")

        # A dictionary with the simulation names for each input file that is shared
        shared_input = defaultdict(list)

        # Check which definitions in the local queue use the same input
        for definition, simulation_name, analysis_options in self.local_queue:

            # Skip simulations without input
            if definition.input_path is None: continue

            # Convert definition input to actual SimulationInput object
            simulation_input = SimulationInput.from_any(definition.input_path)

            # Loop over the input files
            for filename, filepath in simulation_input:

                # Set
                shared_input[filepath].append((simulation_name, filename))

            # Set the simulation input object
            definition.input_path = simulation_input

        # New paths for each shared input file
        new_paths = dict()

        # List of participating simulations
        participating_simulations = set()

        # Loop over the filepaths that are shared
        for filepath in shared_input:

            # Not shared
            if len(shared_input[filepath]) < 2: continue

            # Add all corresponding simulations to the list of participating simulations
            for simulation_name, _ in shared_input[filepath]: participating_simulations.add(simulation_name)

            # Generate a unique filename for this file
            original_filename = fs.name(filepath)
            extension = fs.get_extension(original_filename)
            bare_original_filename = fs.strip_extension(original_filename)
            new_filename = time.unique_name(bare_original_filename, precision="micro") + "." + extension

            # Copy the file to the temporary directory
            fs.copy_file(filepath, self.temp_path, new_name=new_filename)
            new_filepath = fs.join(self.temp_path, new_filename)

            # Set the new path
            new_paths[filepath] = new_filepath

        # Copy the rest of the input files of the participating simulations
        for simulation_name in participating_simulations:

            # Get the definition
            definition = self.get_definition_for_local_simulation(simulation_name)

            # Set the original definition
            self.original_local_definitions[simulation_name] = definition.copy()

            # Get the original simulation input specification
            original_simulation_input = definition.input_path

            # Set the input path to the temporary directory path
            definition.input_path = self.temp_path

            # Open the ski file
            ski = SkiFile(definition.ski_path)

            # List of shared filenames for this simulation
            shared_filenames_for_simulation = []

            # Loop over the shared input files, set the new file name
            for filepath in shared_input:

                ski_filename = None
                for sim_name, filename in shared_input[filepath]:
                    if sim_name == simulation_name:
                        ski_filename = filename
                        break
                else: continue

                # Get the new filepath
                new_filepath = new_paths[filepath]
                new_filename = fs.name(new_filepath)

                # Change in the ski file
                ski.change_input_filename(ski_filename, new_filename)

                # Add to list
                shared_filenames_for_simulation.append(new_filename)

            # Loop over other input files for this simulation, also copy them to the temporary directory with a unique name
            for filename in ski.input_files:

                # Already changed
                if filename in shared_filenames_for_simulation: continue

                # Get path for this filename
                filepath = original_simulation_input[filename]

                # Generate unique filename
                extension = fs.get_extension(filename)
                bare_filename = fs.strip_extension(filename)
                new_filename = time.unique_name(bare_filename, precision="micro") + "." + extension

                # Save to temporary directory
                fs.copy_file(filepath, self.temp_path, new_name=new_filename)

                # Change filename in ski
                ski.change_input_filename(filename, new_filename)

            # Save the ski file
            new_ski_path = fs.join(self.temp_path, time.unique_name(simulation_name, precision="micro") + ".ski")
            ski.saveto(new_ski_path)

            # Set the new ski path to the definition
            definition.ski_path = new_ski_path

    # -----------------------------------------------------------------

    def set_parallelization(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting parallelization schemes ...")

        # Set parallelization scheme for local execution
        if self.parallelization_local is None: self.set_parallelization_local()

        # Set parallelization schemes for remote execution
        self.set_parallelization_remote()

    # -----------------------------------------------------------------

    def set_parallelization_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the parallelization scheme for local execution ...")

        # Get properties of the local machine
        nnodes = par.nnodes()
        nsockets = par.sockets_per_node()
        ncores = par.cores_per_socket()
        memory = par.virtual_memory().to("Gbyte")
        threads_per_core = par.nthreads_per_core()
        hyperthreading = threads_per_core > 1
        mpi = introspection.has_mpi()

        # Loop over the simulations in the local queue
        for definition, simulation_name, _ in self.local_queue:

            # Create the parallelization tool
            tool = ParallelizationTool()

            # Set configuration options
            tool.config.ski = definition.ski_path
            tool.config.input = definition.input_path

            # Set host properties
            tool.config.nnodes = nnodes
            tool.config.nsockets = nsockets
            tool.config.ncores = ncores
            tool.config.memory = memory

            # MPI available and used
            tool.config.mpi = mpi
            tool.config.hyperthreading = hyperthreading
            tool.config.threads_per_core = threads_per_core

            # Number of dust cells
            tool.config.ncells = None  # number of dust cells (relevant if ski file uses a tree dust grid)

            # Don't show
            tool.config.show = False

            # Run the parallelization tool
            tool.run()

            # Get the parallelization scheme
            parallelization = tool.parallelization

            # Debugging
            log.debug("The parallelization scheme for simulation '" + simulation_name + "' is " + str(parallelization))

            # Set the parallelization scheme for this host
            self.set_parallelization_for_simulation(simulation_name, parallelization)

    # -----------------------------------------------------------------

    def set_parallelization_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Setting the parallelization schemes for the different remote hosts (for hosts and simulation for which"
                 " the parallelization scheme has not been defined yet) ...")

        # Loop over the different remote hosts
        for remote in self.remotes:

            # Check whether the parallelization has already been defined by the user for this remote host
            if remote.host_id in self.parallelization_hosts: continue

            # Debugging
            log.debug("Getting properties of remote host '" + remote.host_id + "' ...")

            # If the remote uses a scheduling system
            if remote.scheduler:

                # Set host properties
                nnodes = self.config.nnodes
                nsockets = remote.host.cluster.sockets_per_node
                ncores = remote.host.cluster.cores_per_socket
                memory = remote.host.cluster.memory

                mpi = True
                hyperthreading = remote.host.use_hyperthreading
                threads_per_core = remote.host.cluster.threads_per_core

            # Remote does not use a scheduling system
            else:

                # Get host properties
                nnodes = 1
                nsockets = int(math.floor(remote.free_sockets))
                ncores = remote.cores_per_socket
                memory = remote.free_memory

                mpi = True
                hyperthreading = remote.host.use_hyperthreading
                threads_per_core = remote.threads_per_core

            # Debugging
            log.debug("Setting the parallelization schemes for host '" + remote.host_id + "' ...")

            # Loop over the simulations in the queue for the current remote host
            for definition, simulation_name, _ in self.queues[remote.host_id]:

                # Debugging
                log.debug("Setting the parallelization scheme for simulation '" + simulation_name + "' ...")

                # Create the parallelization tool
                tool = ParallelizationTool()

                # Set configuration options
                tool.config.ski = definition.ski_path
                tool.config.input = definition.input_path

                # Set host properties
                tool.config.nnodes = nnodes
                tool.config.nsockets = nsockets
                tool.config.ncores = ncores
                tool.config.memory = memory

                # MPI available and used
                tool.config.mpi = mpi
                tool.config.hyperthreading = hyperthreading
                tool.config.threads_per_core = threads_per_core

                # Number of dust cells
                tool.config.ncells = None  # number of dust cells (relevant if ski file uses a tree dust grid)

                # Don't show
                tool.config.show = False

                # Run the parallelization tool
                tool.run()

                # Get the parallelization scheme
                parallelization = tool.parallelization

                # Debugging
                log.debug("The parallelization scheme for simulation '" + simulation_name + "' is " + str(parallelization))

                # Set the parallelization scheme for this host
                self.set_parallelization_for_simulation(simulation_name, parallelization)

    # -----------------------------------------------------------------

    def set_script_path(self, host_id, path):

        """
        This function ...
        :param host_id:
        :param path:
        :return:
        """

        # Debugging
        log.debug("Setting the local script path for remote host '" + host_id + "' to '" + path + "' ...")

        # Set the path to the script paths dictionary for the remote host
        self.script_paths[host_id] = path

    # -----------------------------------------------------------------

    def enable_screen_output(self, host_id):

        """
        This function ...
        :param host_id:
        :return:
        """

        # Debugging
        log.debug("Saving the screen output remotely will be enabled for remote host '" + host_id + "' ...")

        # Add the ID of the host to the list
        self.save_screen_output.append(host_id)

    # -----------------------------------------------------------------

    def launch(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching the simulations ...")

        # The complete list of simulations
        simulations = []

        # Launch locally
        if self.has_queued_local: simulations += self.launch_local()

        # Launch remotely
        if self.has_queued_remote: simulations += self.launch_remote()

        # Set the launched simulations
        self.launched_simulations = simulations

    # -----------------------------------------------------------------

    def launch_local(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching simulations locally ...")

        # Initialize a list of simulations
        simulations = []

        # Loop over the simulation in the queue for this remote host
        total_queued = len(self.local_queue)
        for index in range(total_queued):

            # Get the last item from the queue (it is removed)
            definition, name, analysis_options_item = self.local_queue.pop()

            # Get the parallelization scheme that has been defined for this simulation
            parallelization_item = self.parallelization_for_simulation(name)
            if parallelization_item is not None: pass # OK
            elif self.parallelization_local is not None: parallelization_item = self.parallelization_local
            else: raise RuntimeError("Parallelization has not been defined for local simulation '" + name + "' and no general parallelization scheme has been set for local execution")

            # Get original definition if applicable
            if name in self.original_local_definitions: original_definition = self.original_local_definitions[name]
            else: original_definition = None

            # Generate the analysis options: THIS DOES NOT MODIFY THE DEFINITION
            options_definition = original_definition if original_definition is not None else definition
            logging_options, analysis_options = self.generate_options(name, options_definition, analysis_options_item, local=True)

            # Perform the simulation locally
            try:

                # Inform the user
                log.info("Launching simulation " + str(index + 1) + " out of " + str(total_queued) + " in the local queue ...")

                # Run the simulation
                simulation = self.skirt.run(definition, logging_options=logging_options,
                                            parallelization=parallelization_item, silent=(not log.is_debug()),
                                            show_progress=self.config.show_progress)

                # Overwrite the simulation object when the definition had been altered by this class
                if original_definition is not None:

                    # Get modified prefix and original prefix
                    prefix = simulation.prefix()
                    original_prefix = original_definition.prefix

                    # Change the names of the output files so that they start with the right prefix (and not the timestamped prefix of the temporarily created ski file)
                    for filename in fs.files_in_path(simulation.output_path, returns="name", extensions=True):
                        if not filename.startswith(prefix): continue
                        original_filename = filename.replace(prefix, original_prefix)
                        fs.rename_file(simulation.output_path, filename, original_filename)

                    # Create new simulation object
                    arguments = SkirtArguments.from_definition(original_definition, logging_options, parallelization_item)
                    simulation = arguments.simulations(simulation_name=name)

                # Success
                log.success("Finished simulation " + str(index + 1) + " out of " + str(total_queued) + " in the local queue ...")

                # Set the parallelization scheme
                simulation.parallelization = parallelization_item

                # Set the analysis options
                simulation.set_analysis_options(analysis_options)

                # Add analyser classes
                if self.config.analysers is not None:
                    for class_path in self.config.analysers: simulation.add_analyser(class_path)

                # Add the simulation to the list
                simulations.append(simulation)

                # Also add the simulation directly to the list of simulations to be analysed
                self.simulations.append(simulation)

            # Error occured during simulation
            except Exception:

                # Show error messages and traceback; cancel all following simulations
                log.error("Launching simulation '" + name + "' failed:")
                traceback.print_exc()
                log.error("Cancelling following simulations in the queue ...")
                break

        # Return the list of simulations
        return simulations

    # -----------------------------------------------------------------

    def launch_remote(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Launching simulations on the remote hosts ...")

        # Initialize a list of simulations
        simulations = []

        # Loop over the different remotes
        for remote in self.remotes:

            # Schedule simulations for the current remote host
            simulations_remote = self.schedule_simulations(remote)

            # Start the simulations
            self.start_simulations(remote, simulations_remote)

            # Add the simulations of this remote to the total list of simulations
            simulations += simulations_remote

        # Return the list of simulations
        return simulations

    # -----------------------------------------------------------------

    def schedule_simulations(self, remote):

        """
        This function ...
        :param remote
        :return: 
        """

        # Inform the user
        log.info("Scheduling simulations on remote host '" + remote.host_id + "' ...")

        # The remote input path
        remote_input_path = None

        # Get the parallelization scheme for this remote host
        parallelization_host = self.parallelization_for_host(remote.host_id)

        # Cache the simulation objects scheduled to the current remote
        simulations_remote = []

        # Loop over the simulation in the queue for this remote host
        total_queued_host = len(self.queues[remote.host_id])
        for index in range(total_queued_host):

            # Get the last item from the queue (it is removed)
            definition, name, analysis_options_item = self.queues[remote.host_id].pop()

            # Get the parallelization scheme that has been defined for this simulation
            parallelization_item = self.parallelization_for_simulation(name)

            # If no parallelization scheme has been defined for this simulation, use the parallelization scheme
            # defined for the current remote host
            if parallelization_item is None: parallelization_item = parallelization_host

            # Check whether scheduling options are defined for this simulation and for this remote host
            if remote.host_id in self.scheduling_options and name in self.scheduling_options[remote.host_id]:
                scheduling_options = self.scheduling_options[remote.host_id][name]
            else: scheduling_options = None

            # Generate the analysis options
            logging_options, analysis_options = self.generate_options(name, definition, analysis_options_item)

            # Queue the simulation
            try:

                # Inform the user
                log.info("Adding simulation " + str(index + 1) + " out of " + str(total_queued_host) + " to the queue of remote host " + remote.host_id + " ...")

                # Add to the queue
                simulation = remote.add_to_queue(definition, logging_options, parallelization_item, name=name,
                                                 scheduling_options=scheduling_options, remote_input_path=remote_input_path,
                                                 analysis_options=analysis_options, emulate=self.config.emulate)
                simulations_remote.append(simulation)

                # Success
                log.success("Added simulation " + str(index + 1) + " out of " + str(total_queued_host) + " to the queue of remote host " + remote.host_id)

                # Set the parallelization scheme of the simulation (important since SKIRTRemote does not know whether
                # hyperthreading would be enabled if the user provided the parallelization_item when adding the
                # simulation to the queue
                simulation.parallelization = parallelization_item

                # If the input directory is shared between the different simulations
                if self.config.shared_input and remote_input_path is None: remote_input_path = simulation.remote_input_path

                ## SET OPTIONS

                # Remove remote files
                simulation.remove_remote_input = not self.config.keep and not self.config.shared_input
                simulation.remove_remote_output = not self.config.keep
                simulation.remove_remote_simulation_directory = not self.config.keep and not self.config.shared_input

                # Retrieval
                simulation.retrieve_types = self.config.retrieve_types

                # Add analyser classes
                if self.config.analysers is not None:
                    for class_path in self.config.analysers: simulation.add_analyser(class_path)

                # Save the simulation object
                simulation.save()

            # Exception was raised
            except Exception:

                log.error("Adding simulation '" + name + "' to the queue failed:")
                traceback.print_exc()
                log.error("Cancelling following simulations in the queue for remote host '" + remote.host_id + "' ...")
                break

        # Return the simulations scheduled for the host
        return simulations_remote

    # -----------------------------------------------------------------

    def start_simulations(self, remote, simulations_remote):

        """
        This function ...
        :param remote:
        :param simulations_remote:
        :return: 
        """

        # Inform the user
        log.info("Starting the simulations on remote host '" + remote.host_id + "' ...")

        # Determine queue name (name of the screen session or the remote simulation queue)
        queue_name = time.unique_name("batch_launcher")

        # Set a path for the script file to be saved to locally (for manual inspection)
        if remote.host_id in self.script_paths: local_script_path = fs.join(self.script_paths[remote.host_id], queue_name + "_" + remote.host_id  + ".sh")
        else: local_script_path = None

        # Set a path for the screen output to be saved remotely (for debugging)
        if remote.host_id in self.save_screen_output:
            remote_skirt_dir_path = remote.skirt_dir
            remote_skirt_screen_output_path = fs.join(remote_skirt_dir_path, "screen")
            if not remote.is_directory(remote_skirt_screen_output_path): remote.create_directory(remote_skirt_screen_output_path)
            this_screen_output_path = fs.join(remote_skirt_screen_output_path, queue_name)
            remote.create_directory(this_screen_output_path)
            screen_output_path = this_screen_output_path
        else: screen_output_path = None

        # Start the queue
        jobscripts_path = self.script_paths[remote.host_id] if remote.host_id in self.script_paths else None
        handles = remote.start_queue(queue_name=queue_name, group_simulations=self.config.group_simulations,
                                     group_walltime=self.config.group_walltime, use_pts=self.config.use_pts,
                                     local_script_path=local_script_path, screen_output_path=screen_output_path,
                                     jobscripts_path=jobscripts_path, attached=self.config.attached, dry=self.config.dry)

        # SET THE EXECUTION HANDLES
        # Loop over the simulation for this remote
        for simulation in simulations_remote:

            # If all simulations should have the same handle
            if isinstance(handles, ExecutionHandle): simulation.handle = handles
            else: simulation.handle = handles[simulation.name] # get the handle for this particular simulation
            simulation.save()

    # -----------------------------------------------------------------

    def generate_options(self, name, definition, analysis_options_item, local=False):

        """
        This function ...
        :param name:
        :param definition:
        :param analysis_options_item:
        :param local:
        :return:
        """

        # Set add_timing and add_memory settings
        if local:
            add_timing = self.config.add_timing_local
            add_memory = self.config.add_memory_local
        else: add_timing = add_memory = True

        # Check whether analysis options are specified
        if analysis_options_item is None:

            # Get a copy of the default logging options, create the default analysis options and adjust logging options according to the analysis options
            logging_options = self.logging_options.copy()

            # Create analysis options
            analysis_options_item = self.create_analysis_options(definition, name, logging_options, add_timing=add_timing, add_memory=add_memory)

        # AnalysisOptions object
        elif isinstance(analysis_options_item, AnalysisOptions):

            # Get the default logging options
            logging_options = self.logging_options

        # Dict-like analysis options
        elif isinstance(analysis_options_item, dict):

            # Create the default analysis options from the configuration of the batch launcher
            default_analysis_options = self.create_analysis_options(definition, name, add_timing=add_timing, add_memory=add_memory)

            # Set the options specified in the analysis_options_item dictionary
            default_analysis_options.set_options(analysis_options_item)

            # Set the modified default analysis options object as the analysis options for this item
            analysis_options_item = default_analysis_options

            # Get logging options
            logging_options = self.logging_options.copy()

            # Check the analysis options
            analysis_options_item.check(logging_options)

        # Invalid type for the analysis options
        else: raise ValueError("Invalid type for the analysis options of simulation " + name + ": " + str(type(analysis_options_item)) + " (must be dictionary-like or AnalyisOptions instance)")

        # Return the logging and analysis options
        return logging_options, analysis_options_item

    # -----------------------------------------------------------------

    def try_retrieving(self):

        """
        This function ...
        :return:
        """

        try: self.retrieve()
        except Exception, err:
            log.error("Retrieving simulations failed:")
            traceback.print_exc()

    # -----------------------------------------------------------------

    def retrieve(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Retrieving the output of finished simulations ...")

        # Loop over the different remotes
        for remote in self.remotes:

            # Debugging info
            log.debug("Retrieving finished simulations from remote " + remote.system_name + " ...")

            # Get a list of the simulations that have been succesfully retrieved and add the corresponding
            # simulation objects to the list
            self.simulations += remote.retrieve()

    # -----------------------------------------------------------------

    @property
    def nsimulations(self):

        """
        This function ...
        :return:
        """

        return len(self.simulations)

    # -----------------------------------------------------------------

    @property
    def has_simulations(self):

        """
        Thisf unction ...
        :return:
        """

        return self.nsimulations > 0

    # -----------------------------------------------------------------

    def show(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Showing the output of retrieved simulations ...")

        # Loop over the simulations
        print("")
        for simulation in self.simulations:

            # Print the simulation name
            print(fmt.blue + simulation.prefix() + fmt.reset + ":")

            # Show the output
            simulation.output.show(line_prefix="  ")

    # -----------------------------------------------------------------

    def try_analysing(self):

        """
        This function ...
        :return:
        """

        try: self.analyse()
        except Exception, err:
            log.error("Analysing finished simulations failed:")
            traceback.print_exc()

    # -----------------------------------------------------------------

    def analyse(self):

        """
        This function ...
        :return:
        """

        # Inform the user
        log.info("Analysing the output of retrieved simulations ...")

        # Loop over the list of simulations and analyse them
        for simulation in self.simulations:

            # Run the analyser on the simulation
            self.analyser.run(simulation=simulation)

            # Clear the analyser
            self.analyser.clear()

    # -----------------------------------------------------------------

    def write(self):

        """
        This function ...
        :return: 
        """

        # Inform the user
        log.info("Writing ...")

    # -----------------------------------------------------------------

    def create_analysis_options(self, definition, simulation_name, logging_options=None, add_timing=True, add_memory=True):

        """
        This function ...
        :param definition:
        :param simulation_name:
        :param logging_options:
        :param add_timing:
        :param add_memory:
        :return:
        """

        # Create the analysis options object
        analysis_options = AnalysisOptions()
        analysis_options.set_options(self.config.analysis)

        # Determine the path to the extraction directory for this simulation
        if self.config.analysis.extraction.path is None:
            extraction_path = fs.join(definition.base_path, "extr")
            # the ski files of multiple simulations can be int he same directory
            if fs.is_directory(extraction_path): extraction_path = fs.join(definition.base_path, definition.name, "extr")
        elif self.config.analysis.relative: extraction_path = fs.join(definition.base_path, self.config.analysis.extraction.path)
        else: extraction_path = fs.join(self.config.analysis.extraction.path, simulation_name)

        # Create the extraction directory only if it is necessary
        if analysis_options.any_extraction:
            if not fs.is_directory(extraction_path): fs.create_directory(extraction_path, recursive=True)
            analysis_options.extraction.path = extraction_path

        # Set the extraction path to None otherwise
        else: analysis_options.extraction.path = None

        # Determine the path to the plotting directory for this simulation
        if self.config.analysis.plotting.path is None:
            plotting_path = fs.join(definition.base_path, "plot")
            # the ski files of multiple simulations can be in the same directory
            if fs.is_directory(plotting_path): plotting_path = fs.join(definition.base_path, simulation_name, "plot")
        elif self.config.analysis.relative: plotting_path = fs.join(definition.base_path, self.config.analysis.plotting.path)
        else: plotting_path = fs.join(self.config.analysis.plotting.path, simulation_name)

        # Create the plotting directory only if it is necessary
        if analysis_options.any_plotting:
            if not fs.is_directory(plotting_path): fs.create_directory(plotting_path, recursive=True)
            analysis_options.plotting.path = plotting_path

        # Set the plotting path to None otherwise
        else: analysis_options.plotting.path = None

        # Determine the 'misc' directory for this simulation (and create it if necessary)
        if self.config.analysis.misc.path is None:
            misc_path = fs.join(definition.base_path, "misc")
            # the ski files of multiple simulations can be int he same directory
            if fs.is_directory(misc_path): misc_path = fs.join(definition.base_path, simulation_name, "misc")
        elif self.config.analysis.relative: misc_path = fs.join(definition.base_path, self.config.analysis.misc.path)
        else: misc_path = fs.join(self.config.analysis.misc.path, simulation_name)

        # Create the misc directory only if it is necessary
        if analysis_options.any_misc:
            if not fs.is_directory(misc_path): fs.create_directory(misc_path, recursive=True)
            analysis_options.misc.path = misc_path

        # Set the misc path to None otherwise
        else: analysis_options.misc.path = None

        # Set timing and memory table paths (if specified for this batch launcher)
        if self.config.timing_table_path is not None and add_timing:

            # Set the table path
            analysis_options.timing_table_path = self.config.timing_table_path

            # Check whether the extract timing option has been enabled
            if not analysis_options.extraction.timeline:
                log.warning("Timeline extraction will be enabled for writing to the timing table ...")
                analysis_options.extraction.timeline = True

        # Set memory table path
        if self.config.memory_table_path is not None and add_memory:

            # Set
            analysis_options.memory_table_path = self.config.memory_table_path

            # Check whether the extract memory option has been enabled
            if not analysis_options.extraction.memory:
                log.warning("Memory extraction will be enabled for writing to the mrmory table ...")
                analysis_options.extraction.memory = True

        # Check the analysis options
        if logging_options is not None: analysis_options.check(logging_options)

        # Return the analysis options
        return analysis_options

# -----------------------------------------------------------------
