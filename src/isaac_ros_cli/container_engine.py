# Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto. Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Container engine detection and management."""

import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class EngineType(Enum):
    """Supported container engines."""
    DOCKER = "docker"
    PODMAN = "podman"


def detect_container_engine(preference: str = "auto") -> Tuple[EngineType, str]:
    """
    Detect which container engine to use.
    
    Parameters
    ----------
    preference : str
        User preference: 'auto', 'docker', or 'podman'.
        If 'auto', detect which engine is available (Docker preferred).
    
    Returns
    -------
    engine_type : EngineType
        The detected or selected engine type.
    engine_bin : str
        The binary name to use for commands.
    
    Raises
    ------
    RuntimeError
        If no container engine is available or the preferred one is not found.
    """
    if preference == "docker":
        if _is_engine_available("docker"):
            return EngineType.DOCKER, "docker"
        raise RuntimeError("Docker was specified but is not available")
    
    elif preference == "podman":
        if _is_engine_available("podman"):
            return EngineType.PODMAN, "podman"
        raise RuntimeError("Podman was specified but is not available")
    
    else:  # auto
        # Prefer Docker if available
        if _is_engine_available("docker"):
            return EngineType.DOCKER, "docker"
        elif _is_engine_available("podman"):
            return EngineType.PODMAN, "podman"
        else:
            raise RuntimeError("No container engine (Docker or Podman) is available")


def _is_engine_available(engine: str) -> bool:
    """Check if a container engine is available and responsive."""
    try:
        subprocess.run(
            [engine, "ps"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_rootless_podman() -> bool:
    """
    Check if Podman is running in rootless mode.
    
    Returns
    -------
    bool
        True if Podman is running in rootless mode, False otherwise.
    """
    try:
        result = subprocess.run(
            ["podman", "info", "--format", "{{.Host.Security.Rootless}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().lower() == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_container_socket_path(engine_type: EngineType) -> str:
    """
    Get the socket path for the container engine.
    
    Parameters
    ----------
    engine_type : EngineType
        The container engine type.
    
    Returns
    -------
    str
        The socket path for the container engine.
    """
    if engine_type == EngineType.DOCKER:
        return "/var/run/docker.sock"
    
    elif engine_type == EngineType.PODMAN:
        # Check if rootless
        if is_rootless_podman():
            xdg_runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
            if xdg_runtime_dir:
                return f"{xdg_runtime_dir}/podman/podman.sock"
            # Fallback to typical location
            return f"/run/user/{os.getuid()}/podman/podman.sock"
        else:
            # Root Podman uses the same location as Docker
            return "/run/podman/podman.sock"
    
    return "/var/run/docker.sock"  # Default fallback


def is_selinux_enabled() -> bool:
    """
    Check if SELinux is enabled and enforcing.
    
    Returns
    -------
    bool
        True if SELinux is enabled and enforcing, False otherwise.
    """
    try:
        result = subprocess.run(
            ["getenforce"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().lower() == "enforcing"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_volume_mount_suffix(engine_type: EngineType, writable: bool = True) -> str:
    """
    Get the volume mount suffix for SELinux context.
    
    Parameters
    ----------
    engine_type : EngineType
        The container engine type.
    writable : bool
        Whether the volume mount is writable. Defaults to True.
        SELinux relabeling (:Z) is only needed for writable volumes.
    
    Returns
    -------
    str
        The volume mount suffix (e.g., ':Z' for Podman with SELinux on writable volumes, '' otherwise).
    """
    # Only add SELinux context for Podman with writable volumes
    if engine_type == EngineType.PODMAN and is_selinux_enabled() and writable:
        return ":Z"
    return ""
