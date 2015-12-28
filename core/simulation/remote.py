#!/usr/bin/env python
# -*- coding: utf8 -*-
# *****************************************************************
# **       PTS -- Python Toolkit for working with SKIRT          **
# **       © Astronomical Observatory, Ghent University          **
# *****************************************************************

## \package pts.core.simulation.remote Contains the SkirtRemote class, used for launching, checking and retreiving
#  remote SKIRT simulations.

# -----------------------------------------------------------------

# Ensure Python 3 compatibility
from __future__ import absolute_import, division, print_function

# Import standard modules
import os
import tempfile

# Import the relevant PTS classes and modules
from ..basics.remote import Remote
from .jobscript import JobScript
from ..tools import time, inspection
from ..test.resources import ResourceEstimator
from .simulation import RemoteSimulation

# -----------------------------------------------------------------

class SkirtRemote(Remote):

    """
    This class ...
    """

    def __init__(self):

        """
        The constructor ...
        :return:
        """

        # Call the constructor of the base class
        super(SkirtRemote, self).__init__()

        # -- Attributes --

        # Variables storing paths to the remote SKIRT installation location
        self.skirt_path = None
        self.skirt_dir = None
        self.skirt_run_dir = None
        self.local_skirt_run_dir = None

        # Initialize an empty list for the simulation queue
        self.queue = []

    # -----------------------------------------------------------------

    def setup(self, host_id, cluster=None):

        """
        This function ...
        :return:
        """

        # Call the setup function of the base class
        super(SkirtRemote, self).setup(host_id, cluster)

        # Obtain some information about the SKIRT installation on the remote machine
        output = self.execute("which skirt")

        # Determine the path to the SKIRT executable
        self.skirt_path = output[0]  # only one line is expected

        # We want absolute paths
        if self.skirt_path.startswith("~"):

            # Change the SKIRT path to the full, absolute path
            self.skirt_path = os.path.join(self.home_directory, self.skirt_path[2:])

        # Determine the path to the SKIRT directory
        self.skirt_dir = self.skirt_path.split("/release")[0]

        # Determine the path to the SKIRT run directory
        self.skirt_run_dir = os.path.join(self.skirt_dir, "run")

        # Determine the path to the local SKIRT run directory
        self.local_skirt_host_run_dir = os.path.join(inspection.skirt_run_dir, self.host.id)

        # Create the local SKIRT run directory for this host if it doesn't already exist
        if not os.path.isdir(self.local_skirt_host_run_dir): os.makedirs(self.local_skirt_host_run_dir)

        # Give a warning if the remote SKIRT version is different from the local SKIRT version
        local_version = inspection.skirt_version().split("built on")[0]
        remote_version = self.skirt_version.split("built on")[0]
        if remote_version != local_version: self.log.warning("Remote SKIRT version is different from local SKIRT version")

    # -----------------------------------------------------------------

    def add_to_queue(self, arguments, name=None, scheduling_options=None):

        """
        This function ...
        :param arguments:
        :return:
        """

        # Inform the user
        self.log.info("Adding simulation to the queue...")

        # First create a copy of the arguments
        arguments = arguments.copy()

        # Create the remote simulation directory
        remote_simulation_path = self.create_simulation_directory(arguments)
        remote_simulation_name = os.path.basename(remote_simulation_path)

        # Set the name if none is given
        if name is None: name = remote_simulation_name

        # Make preparations for this simulation
        local_ski_path, local_input_path, local_output_path = self.prepare(arguments, remote_simulation_path)

        # If the remote host uses a scheduling system, submit the simulation right away
        if self.host.scheduler:

            # Submit the simulation to the remote scheduling system
            simulation_id = self.schedule(arguments, name, scheduling_options, local_ski_path, remote_simulation_path)

        # If no scheduling system is used, just store the SKIRT arguments in a list for now and execute the complete
        # list of simulations later on (when 'start_queue' is called)
        else:

            # Add the SkirtArguments object to the queue
            self.queue.append(arguments)

            # Generate a new simulation ID based on the ID's currently in use
            simulation_id = self._new_simulation_id()

        # Create a simulation object and return it
        simulation = self.create_simulation_object(arguments, name, simulation_id, remote_simulation_path, local_ski_path, local_input_path, local_output_path)
        return simulation

    # -----------------------------------------------------------------

    def start_queue(self, screen_name=None, local_script_path=None, screen_output_path=None):

        """
        This function ...
        :return:
        """

        # Raise an error if a connection to the remote has not been made
        if not self.connected: raise RuntimeError("Not connected to the remote")

        # If a scheduling system is used by the remote host, we don't need to do anything, simulations added to the queue
        # are already waiting to be executed (or are already being executed)
        if self.host.scheduler:
            self.log.warning("The remote host uses its own scheduling system so calling 'start_queue' will have no effect")
            return

        # Inform the user
        self.log.info("Starting the queued simulations remotely...")

        # Create a unique screen name indicating we are running SKIRT simulations if none is given
        if screen_name is None: screen_name = time.unique_name("SKIRT")

        # If the path for the shell script is not given, create a named temporary file
        if local_script_path is None:
            script_file = tempfile.NamedTemporaryFile()
            local_script_path = script_file.name

        # If a path is given, create a script file at the specified location
        else: script_file = open(local_script_path, 'w')

        # Write a general header to the batch script
        script_file.write("#!/bin/sh\n")
        script_file.write("# Batch script for running SKIRT on a remote system\n")
        script_file.write("\n")

        # Loop over the items in the queue
        for arguments in self.queue:

            # Write the command string to the job script
            script_file.write(arguments.to_command(self.skirt_path, self.host.mpi_command, scheduler=False, to_string=True) + "\n")

        # Write to disk
        script_file.flush()

        # Copy the script to the remote host
        self.upload(local_script_path, self.skirt_run_dir)

        # Rename the remote script
        local_script_name = os.path.basename(local_script_path)
        remote_script_name = screen_name + ".sh"
        remote_script_path = os.path.join(self.skirt_run_dir, remote_script_name)
        self.rename_file(self.skirt_run_dir, local_script_name, remote_script_name)

        # Close the script file (if it is temporary it will automatically be removed)
        script_file.close()

        # Make the shell script executable
        self.execute("chmod +x " + remote_script_path, output=False)

        # Record the screen output: 'script' command
        if screen_output_path is not None: self.execute("script " + screen_output_path)

        # Create the screen session and execute the batch script
        self.execute("screen -S " + screen_name + " -d -m " + remote_script_path, output=False)

        # Remove the remote shell script
        self.execute("rm " + remote_script_path, output=False)

        # Clear the queue
        self.clear_queue()

        # Return the screen name
        return screen_name

    # -----------------------------------------------------------------

    def clear_queue(self):

        """
        This function ...
        :return:
        """

        self.queue = []

    # -----------------------------------------------------------------

    def run(self, arguments, name=None, scheduling_options=None):

        """
        This function ...
        :return:
        """

        # Raise an error if a connection to the remote has not been made
        if not self.connected: raise RuntimeError("Not connected to the remote")

        # Raise an error if there are other simulations currently waiting in the queue
        if len(self.queue) > 0: raise RuntimeError("The simulation queue is not empty")

        # Add the simulation arguments to the queue
        simulation = self.add_to_queue(arguments, name, scheduling_options)

        # Start the queue if that is not left up to the remote's own scheduling system
        if not self.host.scheduler:
            screen_name = self.start_queue(name)
            simulation.screen_name = screen_name

        # Return the simulation object
        return simulation

    # -----------------------------------------------------------------

    def create_simulation_directory(self, arguments):

        """
        This function ...
        :return:
        """

        # Create a unique name for the simulation directory
        skifile_name = os.path.basename(arguments.ski_pattern).split(".ski")[0]
        remote_simulation_name = time.unique_name(skifile_name, separator="__")

        # Determine the full path of the simulation directory on the remote system
        remote_simulation_path = os.path.join(self.skirt_run_dir, remote_simulation_name)

        # Create the remote simulation directory
        self.execute("mkdir " + remote_simulation_path, output=False)

        # Return the path to the remote simulation directory
        return remote_simulation_path

    # -----------------------------------------------------------------

    def prepare(self, arguments, remote_simulation_path):

        """
        This function ...
        :return:
        """

        # Determine the full paths to the input and output directories on the remote system
        remote_input_path = os.path.join(remote_simulation_path, "in")

        # If an output path is defined in the remote host configuration file, use it for the simulation output
        if self.host.output_path is not None:

            # Get the name of the remote simulation directory and use use that name for the output directory
            remote_simulation_name = os.path.basename(remote_simulation_path)
            remote_output_path = os.path.join(self.host.output_path, remote_simulation_name)

        # If an output path is not specified by the user, place a directory called 'out' next to the simulation's 'in' directory
        else: remote_output_path = os.path.join(remote_simulation_path, "out")

        # Change the parameters to accomodate for the fact that we are running remotely
        # but store the paths to the local output directory because we want to copy the
        # results later
        local_input_path = arguments.input_path
        local_output_path = arguments.output_path

        if local_input_path is None: remote_input_path = None

        arguments.input_path = remote_input_path
        arguments.output_path = remote_output_path

        # Create the remote input directory if necessary
        if remote_input_path is not None: self.execute("mkdir " + remote_output_path, output=False)

        # Create the remote output directory
        self.execute("mkdir " + remote_output_path, output=False)

        local_ski_path = arguments.ski_pattern
        ski_name = os.path.basename(local_ski_path)
        remote_ski_path = os.path.join(remote_simulation_path, ski_name)
        arguments.ski_pattern = remote_ski_path

        # Copy the input directory and the ski file to the remote host
        self.upload(local_ski_path, remote_simulation_path)
        if local_input_path is not None: self.upload(local_input_path, remote_input_path)

        # Return the paths of the local ski file and the local input and output directories
        return local_ski_path, local_input_path, local_output_path

    # -----------------------------------------------------------------

    def create_simulation_file(self, arguments, name, simulation_id, remote_simulation_path, local_ski_path, local_input_path, local_output_path):

        """
        This function ...
        :return:
        """

        # Create the simulation file
        simulation_file_path = os.path.join(self.local_skirt_host_run_dir, str(simulation_id) + ".sim")
        simulation_file = open(simulation_file_path, 'w')

        # Determine the simulation name from the ski file name if none is given
        #if name is None: name = os.path.basename(arguments.ski_pattern).split(".")[0]

        # Add the simulation information
        simulation_file.write("simulation name: " + name + "\n")
        simulation_file.write("local skifile path: " + local_ski_path + "\n")
        simulation_file.write("remote skifile path: " + arguments.ski_pattern + "\n")
        simulation_file.write("local input directory: " + str(local_input_path) + "\n") # can be None
        simulation_file.write("local output directory: " + local_output_path + "\n")
        simulation_file.write("remote input directory: " + str(arguments.input_path) + "\n") # can be None
        simulation_file.write("remote simulation directory: " + str(remote_simulation_path) + "\n")
        simulation_file.write("remote output directory: " + arguments.output_path + "\n")
        simulation_file.write("submitted at: " + time.timestamp() + "\n")

        # Close the file
        simulation_file.close()

        # Return the path to the simulation file
        return simulation_file_path

    # -----------------------------------------------------------------

    def create_simulation_object(self, arguments, name, simulation_id, remote_simulation_path, local_ski_path, local_input_path, local_output_path):

        """
        This function ...
        :param arguments:
        :param name:
        :param simulation_id:
        :param remote_simulation_path:
        :param local_ski_path:
        :param local_input_path:
        :param local_output_path:
        :return:
        """

        # Create a new remote simulation object
        simulation = RemoteSimulation(local_ski_path, local_input_path, local_output_path)

        # Set other attributes
        simulation.id = simulation_id
        simulation.name = name
        simulation.remote_ski_path = arguments.ski_pattern
        simulation.remote_simulation_path = remote_simulation_path
        simulation.remote_input_path = arguments.input_path
        simulation.remote_output_path = arguments.output_path
        simulation.submitted_at = time.now()

        # Return the simulation object
        return simulation

    # -----------------------------------------------------------------

    def schedule(self, arguments, name, scheduling_options, local_ski_path, remote_simulation_path):

        """
        This function ...
        :return:
        """

        # Inform the suer
        self.log.info("Scheduling simulation on the remote host")

        if scheduling_options is None:

            processors = arguments.parallel.processes * arguments.parallel.threads
            nodes, ppn = self.get_requirements(processors)

            scheduling_options = {}
            scheduling_options["nodes"] = nodes
            scheduling_options["ppn"] = ppn
            #scheduling_options["walltime"] = ...
            #scheduling_options["jobscript_path"] = ...
            scheduling_options["mail"] = False
            scheduling_options["full_node"] = True

        # We want to estimate the walltime here if it is not passed to this function
        if "walltime" not in scheduling_options:

            factor = 1.2

            # Create and run a ResourceEstimator instance
            estimator = ResourceEstimator()
            #estimator.run(local_ski_path, arguments.parallel.processes, arguments.parallel.threads)
            estimator.run(local_ski_path, 1, 1)

            # Return the estimated walltime
            #walltime = estimator.walltime * factor
            walltime = estimator.walltime_for(arguments.parallel.processes, arguments.parallel.threads) * factor

        else: walltime = scheduling_options["walltime"]

        if "nodes" not in scheduling_options: raise ValueError("The number of nodes is not defined in the scheduling options")
        if "ppn" not in scheduling_options: raise ValueError("The number of processors per node is not defined in the scheduling options")
        nodes = scheduling_options["nodes"]
        ppn = scheduling_options["ppn"]

        mail = scheduling_options["mail"] if "mail" in scheduling_options else False
        full_node = scheduling_options["full_node"] if "full_node" in scheduling_options else False

        # Create a job script next to the (local) simulation's ski file
        if "jobscript_path" not in scheduling_options:
            local_simulation_path = os.path.dirname(local_ski_path)
            local_jobscript_path = os.path.join(local_simulation_path, "job.sh")
        else: local_jobscript_path = scheduling_options["jobscript_path"]
        jobscript_name = os.path.basename(local_jobscript_path)
        jobscript = JobScript(local_jobscript_path, arguments, self.host.clusters[self.host.cluster_name], self.skirt_path, self.host.mpi_command, self.host.modules, walltime, nodes, ppn, name=name, mail=mail, full_node=full_node)

        # Copy the job script to the remote simulation directory
        remote_jobscript_path = os.path.join(remote_simulation_path, jobscript_name)
        self.upload(local_jobscript_path, remote_simulation_path)

        ## Swap clusters
        # Then, swap to the desired cluster and launch the job script
        #output = subprocess.check_output("module swap cluster/" + self._clustername + "; qsub " + self._path, shell=True, stderr=subprocess.STDOUT)

        # Submit the job script to the remote scheduling system
        #output = self.execute("qsub " + remote_jobscript_path, contains_extra_eof=True)
        output = self.execute("qsub " + remote_jobscript_path)

        # The queu number of the submitted job is used to identify this simulation
        simulation_id = int(output[0].split(".")[0])

        # Return the simulation ID
        return simulation_id

    # -----------------------------------------------------------------

    def start(self, arguments):

        """
        This function ...
        :return:
        """

        # Inform the user
        self.log.info("Starting simulation on the remote host")

        # Send the command to the remote machine using a screen session so that we can safely detach from the
        # remote shell
        command = arguments.to_command(self.skirt_path, self.host.mpi_command, self.host.scheduler, to_string=True)
        self.execute("screen -d -m " + command, output=False)

        # Generate a new simulation ID based on the ID's currently in use
        simulation_id = self._new_simulation_id()

        # Return the simulation ID
        return simulation_id

    # -----------------------------------------------------------------

    def _simulation_ids_in_use(self):

        """
        This function ...
        :return:
        """

        # Check the contents of the local run directory to see which simulation id's are currently in use
        current_ids = []
        for item in os.listdir(self.local_skirt_host_run_dir):

            # Determine the full path to this item
            path = os.path.join(self.local_skirt_host_run_dir, item)

            # If this item is a directory or it is hidden, skip it
            if os.path.isdir(path) or item.startswith("."): continue

            # If the file has the 'sim' extension, get the simulation ID and add it to the list
            current_ids.append(int(item.split(".sim")[0]))

        # Return the list of currently used ID's
        return current_ids

    # -----------------------------------------------------------------

    def _new_simulation_id(self):

        """
        This function ...
        :param count:
        :return:
        """

        # Get a list of the ID's currently in use
        current_ids = self._simulation_ids_in_use()

        # Sort the current simulation ID's and find the lowest 'missing' integer number
        if len(current_ids) > 0:
            current_ids = sorted(current_ids)
            simulation_id = max(current_ids)+1
            for index in range(max(current_ids)):
                if current_ids[index] != index:
                    simulation_id = index
                    break

            # Return the simulation ID
            return simulation_id

        # If no simulation ID's are currently in use, return 0
        else: return 0

    # -----------------------------------------------------------------

    def _new_simulation_ids(self, count):

        """
        This function ...
        :param count:
        :return:
        """

        # Get a list of the ID's currently in use
        current_ids = self._simulation_ids_in_use()

        # Initialize a list to contain the new ID's
        new_ids = []

        # Sort the current simulation ID's and find the lowest 'missing' integer number
        if len(current_ids) > 0:
            current_ids = sorted(current_ids)
            for index in range(max(current_ids)):
                if current_ids[index] != index:
                    new_ids.append(index)
                    if len(new_ids) == count: return new_ids

            # Complement with new ID's
            max_id = max(new_ids)
            missing = count - len(new_ids)

            for index in range(max_id+1, max_id+1+missing):

                new_ids.append(index)

            return new_ids

        # If no simulation ID's are currently in use, return a list of the integers from 0 to count-1
        else: return range(count)

    # -----------------------------------------------------------------

    def retrieve(self):

        """
        This function ...
        :return:
        """

        # Raise an error if a connection to the remote has not been made
        if not self.connected: raise RuntimeError("Not connected to the remote")

        # Initialize a list to contain the simulations that have been retrieved
        simulations = []

        # Loop over the different entries of the status list
        for path, simulation_status in self.status:

            # Skip already retrieved simulations
            if simulation_status == "retrieved": continue

            # Finished simulations
            elif simulation_status == "finished":

                # Open the simulation file
                simulation = RemoteSimulation.from_file(path)

                # If retrieve file types are not defined, download the complete output directory
                if simulation.retrieve_types is None or simulation.retrieve_types == "None":

                    # Download the simulation output
                    self.download(simulation.remote_output_path, simulation.output_path)

                # If retrieve file types are defined, download these files seperately to the local filesystem
                else:

                    # Create a list for the paths of the files that have to be copied to the local filesystem
                    copy_paths = []

                    # Loop over the files that are present in the remoute output directory
                    for filename in self.files_in_path(simulation.remote_output_path):

                        # Determine the full path to the output file
                        filepath = os.path.join(simulation.remote_output_path, filename)

                        # Loop over the different possible file types and add the filepath if the particular type is in the list of types to retrieve
                        if filename.endswith("_ds_isrf.dat"):
                            if "isrf" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif "_ds_temp" in filename and filename.endswith(".fits"):
                            if "temp" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif filename.endswith("_sed.dat"):
                            if "sed" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif filename.endswith("_total.fits"):
                            if "image" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif filename.endswith("_ds_celltemps.dat"):
                            if "celltemp" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif "_log" in filename and filename.endswith(".txt"):
                            if "log" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif filename.endswith("_wavelengths.dat"):
                            if "wavelengths" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif "_ds_grid" in filename and filename.endswith(".dat"):
                            if "grid" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif "_ds_grho" in filename and filename.endswith(".fits"):
                            if "grho" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif "_ds_trho" in filename and filename.endswith(".fits"):
                            if "trho" in simulation.retrieve_types: copy_paths.append(filepath)
                        elif filename.endswith("_ds_convergence.dat"):
                            if "convergence" in simulation.retrieve_types: copy_paths.append(filepath)

                    # Download the list of files to the local output directory
                    self.download(copy_paths, simulation.output_path)

                # If retreival was succesful, add this information to the simulation file
                with open(path, "a") as simulation_file:
                    simulation_file.write("retrieved at: " + time.timestamp() + "\n")

                # Remove the remote input, if requested
                if simulation.remove_remote_input: self.remove_directory(simulation.remote_input_path)

                # Remove the remote output, if requested
                if simulation.remove_remote_output: self.remove_directory(simulation.remote_output_path)

                # If both the input and output directories have to be removed, the remote simulation directory
                # can be removed too
                if simulation.remove_remote_simulation_path: self.remove_directory(simulation.remote_simulation_path)

                # Add the simulation to the list of retrieved simulations
                simulations.append(simulation)

        # Return the list of retrieved simulations
        return simulations

    # -----------------------------------------------------------------

    @property
    def skirt_version(self):

        """
        This function ...
        :return:
        """

        # Execute SKIRT with incorrect argument list and get its output
        output = self.execute("skirt --version")

        # Return the relevant portion of the output
        return "SKIRT" + output[0].partition("SKIRT")[2]

    # -----------------------------------------------------------------

    @property
    def status(self):

        """
        This function ..
        :return:
        """

        # Initialize a list to contain the statuses
        entries = []

        # If the remote host does not use a scheduling system
        if not self.host.scheduler:

            # Search for files in the local SKIRT run/host_id directory
            for item in os.listdir(self.local_skirt_host_run_dir):

                # If the item is not a simulation file or it is hidden, skip it
                if not item.endswith(".sim") or item.startswith("."): continue

                # Determine the full path to the simulation file
                path = os.path.join(self.local_skirt_host_run_dir, item)

                # Open the simulation file
                simulation = RemoteSimulation.from_file(path)

                # The name of the ski file (the simulation prefix)
                ski_name = simulation.prefix()

                # The path to the simulation log file
                remote_log_file_path = os.path.join(simulation.remote_output_path, ski_name + "_log.txt")

                # Get the simulation status from the remote log file if not yet retrieved
                if simulation.retrieved: simulation_status = "retrieved"
                else: simulation_status = self.status_from_log_file(remote_log_file_path, simulation.screen_name, ski_name)

                # Add the simulation properties to the list
                entries.append((path, simulation_status))

        # If the remote has a scheduling system for launching jobs
        else:

            # Obtain job status information through the 'qstat' command
            output = self.execute("qstat")

            # Create a dictionary that contains the status of the different jobs that are scheduled or running on the cluster
            queue_status = dict()

            # Check every line in the output
            for line in output:

                # If this line mentions a job
                if "master15" in line:

                    # Get the job ID
                    jobid = int(line.split(".")[0])

                    # Split the line
                    splitted_line = line.split(" ")

                    # Get the status (Q=queued, R=running)
                    if "short" in splitted_line: position = splitted_line.index("short")
                    elif "long" in splitted_line: position = splitted_line.index("long")
                    else: continue
                    jobstatus = splitted_line[position-1]

                    # Add the status of this job to the dictionary
                    queue_status[jobid] = jobstatus

            # Search for files in the SKIRT run directory
            for item in os.listdir(self.local_skirt_host_run_dir):

                # If the item is not a simulation file or it is hidden, skip it
                if not item.endswith(".sim") or item.startswith("."): continue

                # Determine the full path to the simulation file
                path = os.path.join(self.local_skirt_host_run_dir, item)

                # Open the simulation file
                simulation = RemoteSimulation.from_file(path)

                # The name of the ski file (the simulation prefix)
                ski_name = simulation.prefix()

                # The path to the simulation log file
                remote_log_file_path = os.path.join(simulation.remote_output_path, ski_name + "_log.txt")

                # Get the job ID from the name of the simulation file
                job_id = int(os.path.splitext(item)[0])

                # Check if the simulation has already been retrieved
                if simulation.retrieved: simulation_status = "retrieved"

                # Check if the job ID is in the list of queued or running jobs
                elif job_id in queue_status:

                    # Check the status of this simulation
                    job_status = queue_status[job_id]

                    # This simulation is still queued
                    if job_status == 'Q': simulation_status = "queued"

                    # This simulation is currently running
                    elif job_status == 'R': simulation_status = self.running_status_from_log_file(remote_log_file_path)

                    # If the job has been cancelled, check whether some part of the log file was already present
                    # (the simulation was running but was aborted) or the log file is not present (the simulation is cancelled)
                    elif job_status == "C":

                        if self.is_file(remote_log_file_path): simulation_status = "aborted"
                        else: simulation_status = "cancelled"

                    # This simulation has an unknown status, check the log file
                    else: simulation_status = self.status_from_log_file_job(remote_log_file_path, ski_name)

                # If the simulation is not in the list of jobs
                else: simulation_status = self.status_from_log_file_job(remote_log_file_path, ski_name)

                # Add the simulation properties to the list
                entries.append((path, simulation_status))

        # Return the list of simulation properties
        return entries

    # -----------------------------------------------------------------

    def status_from_log_file(self, file_path, screen_name, simulation_prefix):

        """
        This function ...
        :param file_path:
        :return:
        """

        # If the log file exists
        if self.is_file(file_path):

            # Get the last two lines of the remote log file
            output = self.execute("tail -2 " + file_path)

            # Get the last line of the actual simulation
            if " Available memory: " in output[1]: last = output[0]
            else: last = output[1]

            # Interpret the content of the last line
            if " Finished simulation " + simulation_prefix in last: simulation_status = "finished"
            elif " *** Error: " in last: simulation_status = "crashed"
            else:
                # The simulation is either still running or has been aborted
                if self.is_active_screen(screen_name): simulation_status = self.running_status_from_log_file(file_path)
                else: simulation_status = "aborted"

        # If the log file does not exist, the simulation has not started yet or has been cancelled
        else:

            # The simulation has not started or it's screen session has been cancelled
            if self.is_active_screen(screen_name): simulation_status = "queued"
            else: simulation_status = "cancelled"

        # Return the string that indicates the simulation status
        return simulation_status

    # -----------------------------------------------------------------

    def status_from_log_file_job(self, file_path, simulation_prefix):

        """
        This function ...
        :param file_path:
        :param job_id:
        :param simulation_prefix:
        :return:
        """

        # Check whether the log file exists
        if self.is_file(file_path):

            # Get the last two lines of the remote log file
            output = self.execute("tail -2 " + file_path)

            # Get the last line of the actual simulation
            if " Available memory: " in output[1]: last = output[0]
            else: last = output[1]

            # Interpret the content of the last line
            if " Finished simulation " + simulation_prefix in last: simulation_status = "finished"
            elif " *** Error: " in last: simulation_status = "crashed"

            # The simulation cannot be running because we would have seen it in the qstat output
            # So with a partial log file, it must have been aborted
            else: simulation_status = "aborted"

        # If the log file does not exist, the simulation has been cancelled (if it would just be still scheduled
        # we would have encountered it's job ID in the qstat output)
        else: simulation_status = "cancelled"

        # Return the string that indicates the simulation status
        return simulation_status

    # -----------------------------------------------------------------

    def running_status_from_log_file(self, file_path):

        """
        This function ...
        :return:
        """

        output = self.read_text_file(file_path)

        phase = None
        cycle = None
        progress = None

        for line in output:

            if "Starting setup" in line: phase = "setup"
            elif "Starting the stellar emission phase" in line: phase = "stellar emission"
            elif "Launched stellar emission photon packages" in line:

                progress = float(line.split("packages: ")[1].split("%")[0])

            elif "Starting the first-stage dust self-absorption cycle" in line: phase = "self-absorption [stage 1"
            elif "Launched first-stage dust self-absorption cycle" in line:

                cycle = int(line.split("cycle ")[1].split(" photon packages")[0])
                progress = float(line.split("packages: ")[1].split("%")[0])

            elif "Starting the second-stage dust self-absorption cycle" in line: phase = "self-absorption [stage 2"
            elif "Launched second-stage dust self-absorption cycle" in line:

                cycle = int(line.split("cycle ")[1].split(" photon packages")[0])
                progress = float(line.split("packages: ")[1].split("%")[0])

            elif "Starting the last-stage dust self-absorption cycle" in line: phase = "self-absorption [stage 3"
            elif "Launched last-stage dust self-absorption cycle" in line:

                cycle = int(line.split("cycle ")[1].split(" photon packages")[0])
                progress = float(line.split("packages: ")[1].split("%")[0])

            elif "Starting the dust emission phase" in line: phase = "dust emission"
            elif "Launched dust emission photon packages" in line: progress = float(line.split("packages: ")[1].split("%")[0])
            elif "Starting writing results" in line: phase = "writing"

        if "self-absorption" in phase: return "running: " + str(phase) + ", cycle " + str(cycle) + "] " + str(progress) + "%"
        elif "stellar emission" in phase or "dust emission" in phase: return "running: " + str(phase) + " " + str(progress) + "%"
        else: return "running: " + str(phase)

# -----------------------------------------------------------------
