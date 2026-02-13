# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Container manager abstraction for Docker and Podman."""

from abc import ABC, abstractmethod
from typing import List, Optional
import subprocess

from isaac_ros_cli.container_engine import (
    EngineType,
    detect_container_engine,
    is_rootless_podman,
    get_container_socket_path,
    get_volume_mount_suffix,
    is_selinux_enabled
)


class ContainerManager(ABC):
    """Abstract base class for container management."""
    
    def __init__(self, engine_bin: str, engine_type: EngineType):
        self.engine_bin = engine_bin
        self.engine_type = engine_type
    
    @abstractmethod
    def get_gpu_flags(self) -> List[str]:
        """Get GPU runtime flags for this container engine."""
        pass
    
    @abstractmethod
    def get_runtime_flags(self) -> List[str]:
        """Get runtime-specific flags."""
        pass
    
    def format_volume_mount(self, host_path: str, container_path: str, 
                          mode: str = "rw") -> str:
        """
        Format a volume mount string.
        
        Parameters
        ----------
        host_path : str
            Path on the host.
        container_path : str
            Path in the container.
        mode : str
            Mount mode (e.g., 'rw', 'ro'). Defaults to 'rw'.
            Note: 'rw' mode is the default for container engines and may be omitted
            from the output string.
        
        Returns
        -------
        str
            Formatted volume mount string.
        """
        # Determine if this is a writable mount for SELinux context
        writable = (mode == "rw" or mode is None or mode == "")
        suffix = get_volume_mount_suffix(self.engine_type, writable=writable)
        
        # Build the mount string
        if mode == "rw" or mode is None or mode == "":
            # For 'rw' mode, we can omit it as it's the default
            return f"{host_path}:{container_path}{suffix}"
        else:
            # For other modes (ro, z, Z, etc.), include the mode
            return f"{host_path}:{container_path}:{mode}{suffix}"
    
    def run_command(self, args: List[str], **kwargs) -> subprocess.CompletedProcess:
        """
        Run a container engine command.
        
        Parameters
        ----------
        args : List[str]
            Command arguments (without the engine binary).
        **kwargs
            Additional arguments to pass to subprocess.run().
        
        Returns
        -------
        subprocess.CompletedProcess
            The result of the command.
        """
        cmd = [self.engine_bin] + args
        return subprocess.run(cmd, **kwargs)
    
    def check_running(self) -> bool:
        """Check if the container engine is running."""
        try:
            result = self.run_command(
                ["ps"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


class DockerManager(ContainerManager):
    """Docker-specific container manager."""
    
    def __init__(self, engine_bin: str = "docker"):
        super().__init__(engine_bin, EngineType.DOCKER)
    
    def get_gpu_flags(self) -> List[str]:
        """Get Docker GPU runtime flags."""
        return ["--runtime", "nvidia"]
    
    def get_runtime_flags(self) -> List[str]:
        """Get Docker-specific runtime flags."""
        return []
    
    def check_buildx_available(self) -> bool:
        """Check if Docker Buildx is available."""
        try:
            self.run_command(
                ["buildx", "inspect", "--bootstrap"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


class PodmanManager(ContainerManager):
    """Podman-specific container manager."""
    
    def __init__(self, engine_bin: str = "podman"):
        super().__init__(engine_bin, EngineType.PODMAN)
        self.is_rootless = is_rootless_podman()
    
    def get_gpu_flags(self) -> List[str]:
        """Get Podman GPU device flags (CDI style)."""
        return ["--device", "nvidia.com/gpu=all"]
    
    def get_runtime_flags(self) -> List[str]:
        """Get Podman-specific runtime flags."""
        flags = []
        
        # Handle cgroup namespace for rootless
        if self.is_rootless:
            flags.extend(["--cgroupns", "host"])
        
        return flags
    
    def check_buildx_available(self) -> bool:
        """Check if Podman build is available."""
        try:
            self.run_command(
                ["build", "--help"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


def create_container_manager(preference: str = "auto") -> ContainerManager:
    """
    Create a container manager instance based on preference.
    
    Parameters
    ----------
    preference : str
        User preference: 'auto', 'docker', or 'podman'.
    
    Returns
    -------
    ContainerManager
        An instance of DockerManager or PodmanManager.
    """
    engine_type, engine_bin = detect_container_engine(preference)
    
    if engine_type == EngineType.DOCKER:
        return DockerManager(engine_bin)
    elif engine_type == EngineType.PODMAN:
        return PodmanManager(engine_bin)
    else:
        raise RuntimeError(f"Unsupported container engine: {engine_type}")
