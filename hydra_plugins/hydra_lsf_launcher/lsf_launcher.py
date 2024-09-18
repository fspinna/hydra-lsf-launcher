import os
import sys
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, List, Optional, Any
from omegaconf import DictConfig, OmegaConf, open_dict, read_write

from hydra.core.config_store import ConfigStore
from hydra.core.hydra_config import HydraConfig
from hydra.core.utils import (
    JobReturn,
    JobStatus,
    configure_log,
    _save_config,
    JobRuntime,
)
from hydra.plugins.launcher import Launcher
from hydra.types import HydraContext, TaskFunction

log = logging.getLogger(__name__)


@dataclass
class LsfLauncherConfig:
    _target_: str = "hydra_plugins.hydra_lsf_launcher.lsf_launcher.LsfLauncher"
    n: int = 1  # Number of CPU cores
    # R: str = "rusage[mem=1024]"  # Resource requirement string
    M: str = "2GB"  # Memory requirement
    W: str = "60:00"  # Walltime
    q: str = "ext_batch"  # Queue name
    verbose: bool = True
    bsub_args: Optional[str] = None  # Additional bsub options


ConfigStore.instance().store(
    group="hydra/launcher", name="lsf", node=LsfLauncherConfig
)


class LsfLauncher(Launcher):
    def __init__(
        self,
        q="ext_batch",
        n: int = 1,
        # R: str = "rusage[mem=1024]",
        M: str = "2GB",
        W: str = "60:00",
        verbose=True,
        bsub_args: Optional[str] = None,
    ) -> None:
        self.n = n
        # self.R = R
        self.q = q
        self.M = M
        self.W = W
        self.verbose = verbose
        self.bsub_args = bsub_args

    def setup(
        self,
        *,
        hydra_context: HydraContext,
        task_function: TaskFunction,
        config: DictConfig,
    ) -> None:
        self.config = config
        self.hydra_context = hydra_context
        self.task_function = task_function
        self.script_name = os.path.abspath(sys.argv[0])

    def launch(
        self, job_overrides: Sequence[Sequence[str]], initial_job_idx: int
    ) -> List[JobReturn]:
        sweep_dir = Path(self.config.hydra.sweep.dir)
        sweep_dir.mkdir(parents=True, exist_ok=True)

        log.info(
            f"LSF Launcher is submitting {len(job_overrides)} jobs to LSF scheduler"
        )
        log.info(f"Sweep output dir: {sweep_dir}")

        runs: List[JobReturn] = []

        for idx, overrides in enumerate(job_overrides):
            idx = initial_job_idx + idx
            log.info(f"Submitting job #{idx} with overrides: {overrides}")

            # Load the sweep configuration for this job
            sweep_config = self.hydra_context.config_loader.load_sweep_config(
                self.config, list(overrides)
            )

            # Set hydra.sweep.subdir and other job-specific configurations
            with open_dict(sweep_config):
                sweep_config.hydra.sweep.subdir = f"{idx}"
                sweep_config.hydra.job.id = f"job_id_for_{idx}"
                sweep_config.hydra.job.num = idx

            # Determine the output directory
            output_dir = self._get_job_output_dir(sweep_config)

            # Update hydra.runtime.output_dir
            with read_write(sweep_config.hydra.runtime):
                sweep_config.hydra.runtime.output_dir = os.path.abspath(output_dir)

            # Update HydraConfig with the job's configuration
            HydraConfig.instance().set_config(sweep_config)

            # Create the output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Handle working directory
            chdir = sweep_config.hydra.job.get("chdir", True)

            # Save configuration files in the job directory
            self._save_configurations(sweep_config, output_dir)

            # Build the command to run the task
            cmd = [
                sys.executable,
                self.script_name,
            ] + list(overrides)

            # If chdir is True, adjust the command to change directory
            if chdir:
                cmd = ["bash", "-c", f"cd {output_dir} && {' '.join(cmd)}"]

            # Base bsub command
            bsub_cmd = [
                "bsub",
                "-q",
                self.q,
                "-n",
                str(self.n),
                "-W",
                self.W,
                "-M",
                self.M,
                "-J",
                f"job_{idx}",
                "-o",
                f"{output_dir}/job_{idx}.out",
                "-e",
                f"{output_dir}/job_{idx}.err",
            ]

            # Add any additional bsub options
            if self.bsub_args:
                import shlex

                additional_options = shlex.split(self.bsub_args)
                bsub_cmd.extend(additional_options)

            # Final command to submit
            full_cmd = bsub_cmd + cmd

            # Submit the job to LSF and capture the output
            if self.verbose:
                log.info(f"Running command: {' '.join(full_cmd)}")
            submission = subprocess.run(
                full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Extract job ID from LSF output
            job_id = self._parse_job_id(submission.stdout)

            # Create a JobReturn object for this job
            ret = JobReturn(
                overrides=list(overrides),
                cfg=None,
                hydra_cfg=None,
                working_dir=output_dir,
                task_name=JobRuntime.instance().get("name"),
                status=JobStatus.COMPLETED if job_id else JobStatus.FAILED,
                _return_value=None,
            )
            runs.append(ret)

        # Reset HydraConfig to the original config after job submission
        HydraConfig.instance().set_config(self.config)

        return runs

    def _get_job_output_dir(self, config: DictConfig) -> str:
        output_dir = config.hydra.sweep.dir
        job_subdir = config.hydra.sweep.subdir
        if job_subdir is not None:
            output_dir = os.path.join(output_dir, job_subdir)
        return output_dir

    def _save_configurations(self, config: DictConfig, output_dir: str):
        # Extract the task configuration (excluding hydra)
        task_cfg = config.copy()
        with open_dict(task_cfg):
            del task_cfg["hydra"]

        # Save the configuration files using Hydra's save_config
        hydra_output = Path(output_dir) / ".hydra"
        hydra_output.mkdir(parents=True, exist_ok=True)

        _save_config(task_cfg, "config.yaml", hydra_output)
        _save_config(config.hydra, "hydra.yaml", hydra_output)
        _save_config(config.hydra.overrides.task, "overrides.yaml", hydra_output)

    def _parse_job_id(self, bsub_output: str) -> Optional[str]:
        # Parse the job ID from bsub output
        import re

        match = re.search(r"Job <(\d+)> is submitted to queue", bsub_output)
        if match:
            return match.group(1)
        else:
            return None
