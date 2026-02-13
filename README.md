# Isaac ROS CLI

A command-line interface for managing Isaac ROS development environments.

## Installation

```bash
sudo apt-get install isaac-ros-cli
```

## Usage

```bash
# Show help
isaac-ros --help

# Initialize environment (pick a mode)
sudo isaac-ros init <docker|venv|baremetal>

# Activate environment
isaac-ros activate
```

## Container Engine Support

The Isaac ROS CLI supports both **Docker** and **Podman** container engines. The CLI automatically detects which engine is available and uses it accordingly.

### Features

- **Auto-detection**: Automatically detects Docker or Podman (Docker preferred if both are available)
- **Docker Support**: Full support for Docker with NVIDIA GPU runtime
- **Podman Support**: 
  - Rootless and rootful modes
  - CDI (Container Device Interface) for NVIDIA GPU access
  - SELinux context management (`:Z` flag for writable volumes)
  - Proper cgroup namespace handling (`--cgroupns host` for rootless)

### Configuration

You can configure the container engine preference in `/usr/share/isaac-ros-cli/config.yaml`:

```yaml
# Container engine configuration
# Options: 'auto' (detect), 'docker', or 'podman'
container_engine: auto
```

Alternatively, use the `ISAAC_ROS_CLI_CONFIG` environment variable to specify a custom config file:

```bash
export ISAAC_ROS_CLI_CONFIG=/path/to/custom/config.yaml
isaac-ros activate
```

### Docker vs Podman Differences

| Feature | Docker | Podman |
|---------|--------|--------|
| GPU Access | `--runtime nvidia` | `--device nvidia.com/gpu=all` (CDI) |
| Rootless | Requires docker daemon | Native rootless support |
| SELinux | Not required | Automatic `:Z` flag for writable volumes |
| User Namespace | Standard mapping | Rootless uses host UID mapping |
| Cgroups | Full access | `--cgroupns host` for rootless |

### Requirements

#### For Docker:
- Docker Engine installed
- User in `docker` group
- NVIDIA Container Toolkit (for GPU support)

#### For Podman:
- Podman installed (rootless or rootful)
- NVIDIA Container Toolkit with CDI support (for GPU support)
- For rootless: `$XDG_RUNTIME_DIR/podman/podman.sock` available

## Rebuilding Debian Package

To build a new local copy:
```bash
make build
```
