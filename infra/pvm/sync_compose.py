#!/usr/bin/env python3
"""
Script to synchronize docker-compose.dev.yml with:
- docker-compose.mac.remote.yml (Windows path mapping for remote Mac)
- docker-compose.dev.minimal.yml (subset of services)
- docker-compose.mac.native.yml (Mac native, CPU-only)
- docker-compose.dev.cpu.yml (Dev environment, CPU-only)

Notes:
- mac.remote converts relative host paths to absolute Windows drive paths.
- mac.native keeps relative paths but strips GPU-related deploy blocks so it
  runs CPU-only on Mac (which lacks NVIDIA support in Docker Desktop).
- dev.cpu keeps relative paths but strips GPU-related deploy blocks so it
  runs CPU-only in the development environment.
"""

import os
import sys


def convert_relative_to_absolute_path(relative_path, base_path):
    """
    Convert a relative path to an absolute path based on the base path.
    
    Args:
        relative_path (str): The relative path to convert
        base_path (str): The base path (O:/product-video-matching)
        
    Returns:
        str: The absolute path
    """
    # Handle environment variable references like ${MODEL_CACHE}
    if '${' in relative_path and '}' in relative_path:
        # For paths like ../../${MODEL_CACHE}:/root/.cache/huggingface
        # Remove the ../ parts and keep the variable
        cleaned_path = relative_path
        while cleaned_path.startswith('../'):
            cleaned_path = cleaned_path[3:]  # Remove '../'
        return f"{base_path}/{cleaned_path}"
    
    # Handle normal relative paths
    if relative_path.startswith('../'):
        # Count how many levels up
        levels_up = relative_path.count('../')
        # Remove the ../ parts
        path_part = relative_path.replace('../', '', levels_up)
        # For simplicity, we'll just append the path to the base path
        # This works because all paths are relative to the repo root
        return f"{base_path}/{path_part}"
    else:
        # Already an absolute path or doesn't need conversion
        return f"{base_path}/{relative_path}"


def process_line(line, base_path, in_volumes_section):
    """
    Process a line and convert relative paths to absolute paths if needed.
    
    Args:
        line (str): The line to process
        base_path (str): The base path (O:/product-video-matching)
        in_volumes_section (bool): Whether we're currently in a volumes section
        
    Returns:
        str: The processed line
    """
    # Check if this is a volume mapping line (indented with a dash and contains a colon)
    if in_volumes_section and line.lstrip().startswith('- ') and ':' in line:
        # Extract the indentation
        indent = len(line) - len(line.lstrip())
        indentation = line[:indent]
        
        # Extract the volume mapping
        stripped_line = line.strip()
        volume_mapping = stripped_line[2:]  # Remove the "- " prefix
        
        # Check if this is a path mapping (contains a colon)
        if ':' in volume_mapping:
            # Split on the first colon to separate host path from container path
            parts = volume_mapping.split(':', 1)
            host_part = parts[0].strip()
            container_part = parts[1]
            
            # Check if the host part is a relative path
            if host_part.startswith('../'):
                # Convert to absolute path
                abs_host_path = convert_relative_to_absolute_path(host_part, base_path)
                # Reconstruct the line
                return f"{indentation}- {abs_host_path}:{container_part}\n"
            elif '${' in host_part and '}' in host_part:
                # Handle environment variable references
                abs_host_path = convert_relative_to_absolute_path(host_part, base_path)
                return f"{indentation}- {abs_host_path}:{container_part}\n"
    
    return line


def filter_services(lines, target_services):
    """
    Filter docker-compose content to include only specified services.
    
    Args:
        lines (list): List of lines from the docker-compose file
        target_services (list): List of service names to keep
        
    Returns:
        list: Filtered lines containing only the specified services
    """
    filtered_lines = []
    current_service = None
    service_indent = 0
    in_services_section = False
    skip_current_service = False
    
    for line in lines:
        stripped_line = line.strip()
        line_indent = len(line) - len(line.lstrip())
        
        # Check if we're in the services section
        if stripped_line == 'services:':
            in_services_section = True
            filtered_lines.append(line)
            continue
        
        # If we hit a top-level section after services, we're done with services
        if in_services_section and line_indent == 0 and stripped_line and not stripped_line.startswith('#'):
            in_services_section = False
            filtered_lines.append(line)
            continue
        
        # If not in services section, include all lines
        if not in_services_section:
            filtered_lines.append(line)
            continue
        
        # In services section - check for service definitions
        if line_indent == 2 and stripped_line.endswith(':') and not stripped_line.startswith('#'):
            # This is a service definition
            current_service = stripped_line[:-1]  # Remove the colon
            service_indent = line_indent
            skip_current_service = current_service not in target_services
            
            if not skip_current_service:
                filtered_lines.append(line)
            continue
        
        # Handle lines within a service
        if current_service is not None:
            # If this line has the same or less indentation than the service definition,
            # we've moved to a new service or section
            if line_indent <= service_indent and stripped_line and not stripped_line.startswith('#'):
                current_service = None
                skip_current_service = False
                # Process this line again as it might be a new service
                if stripped_line.endswith(':'):
                    current_service = stripped_line[:-1]
                    service_indent = line_indent
                    skip_current_service = current_service not in target_services
                
                if not skip_current_service:
                    filtered_lines.append(line)
            else:
                # This line belongs to the current service
                if not skip_current_service:
                    filtered_lines.append(line)
        else:
            # Not in a specific service, include the line
            filtered_lines.append(line)
    
    return filtered_lines


def sync_minimal_compose_file(dev_file, target_file, target_services):
    """
    Synchronize a minimal docker-compose file with only specified services.
    
    Args:
        dev_file (str): Path to the development docker-compose file
        target_file (str): Path to the target docker-compose file
        target_services (list): List of service names to include
    """
    try:
        # Read the development compose file
        with open(dev_file, 'r') as f:
            lines = f.readlines()
        
        # Filter to include only target services
        filtered_lines = filter_services(lines, target_services)
        
        # Write the target compose file
        with open(target_file, 'w') as f:
            f.writelines(filtered_lines)
        
        print(f"Successfully synchronized {target_file} from {dev_file} with services: {', '.join(target_services)}")
        return True
        
    except Exception as e:
        print(f"Error synchronizing minimal compose file: {e}")
        return False


def sync_compose_files(dev_file, mac_file, base_path):
    """
    Synchronize docker-compose.dev.yml with docker-compose.mac.remote.yml
    
    Args:
        dev_file (str): Path to the development docker-compose file
        mac_file (str): Path to the macOS docker-compose file
        base_path (str): Base path for absolute paths (O:/product-video-matching)
    """
    try:
        # Read the development compose file
        with open(dev_file, 'r') as f:
            lines = f.readlines()
        
        # Process lines
        processed_lines = []
        in_volumes_section = False
        current_indentation = 0
        
        for line in lines:
            # Check if we're entering or leaving a volumes section
            stripped_line = line.strip()
            if stripped_line.startswith('volumes:'):
                in_volumes_section = True
                # Record the indentation level of the volumes section
                current_indentation = len(line) - len(line.lstrip())
            elif in_volumes_section:
                # Check if we're leaving the volumes section
                # We leave the volumes section when we encounter a line with less indentation
                # or a line that starts a new section (no indentation or less indentation)
                line_indentation = len(line) - len(line.lstrip())
                if line_indentation <= current_indentation and stripped_line and not stripped_line.startswith('#'):
                    # We've left the volumes section
                    in_volumes_section = False
            
            # Process the line
            processed_line = process_line(line, base_path, in_volumes_section)
            processed_lines.append(processed_line)
        
        # Write the mac compose file
        with open(mac_file, 'w') as f:
            f.writelines(processed_lines)
        
        print(f"Successfully synchronized {mac_file} from {dev_file}")
        return True
        
    except Exception as e:
        print(f"Error synchronizing compose files: {e}")
        return False


def remove_gpu_deploy_blocks(lines):
    """
    Remove deploy->resources->reservations->devices blocks that request GPU.

    This is used to produce a CPU-only compose for Mac native environments
    that don't support NVIDIA GPUs under Docker Desktop.

    Args:
        lines (list[str]): Lines from the source compose file

    Returns:
        list[str]: Lines with GPU deploy blocks removed
    """
    result = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Drop stray GPU-hint comments
        if stripped.startswith('#') and 'Uncomment for GPU support' in stripped:
            i += 1
            continue

        if stripped.startswith('deploy:'):
            deploy_indent = len(line) - len(line.lstrip())
            block_lines = [line]
            j = i + 1

            # Collect the deploy block
            while j < n:
                next_line = lines[j]
                next_stripped = next_line.strip()
                next_indent = len(next_line) - len(next_line.lstrip())

                # Stop when indentation decreases to deploy level and it's a non-comment, non-empty line
                if next_stripped and not next_stripped.startswith('#') and next_indent <= deploy_indent:
                    break

                block_lines.append(next_line)
                j += 1

            block_text = ''.join(block_lines)
            # If this deploy block references GPU capabilities, drop it
            if 'capabilities' in block_text and 'gpu' in block_text:
                i = j
                continue
            else:
                # Keep the deploy block as-is
                result.extend(block_lines)
                i = j
                continue

        # Default: keep the line
        result.append(line)
        i += 1

    return result


def sync_mac_native_compose(dev_file, native_file):
    """
    Produce a Mac-native compose that runs CPU-only by removing GPU deploy blocks.

    Args:
        dev_file (str): Path to the development docker-compose file
        native_file (str): Path to the mac native docker-compose file to write
    """
    try:
        with open(dev_file, 'r') as f:
            lines = f.readlines()

        processed_lines = remove_gpu_deploy_blocks(lines)

        with open(native_file, 'w') as f:
            f.writelines(processed_lines)

        print(f"Successfully synchronized {native_file} from {dev_file} (CPU-only)")
        return True
    except Exception as e:
        print(f"Error synchronizing mac native compose file: {e}")
        return False


def sync_dev_cpu_compose(dev_file, cpu_file):
    """
    Produce a development compose that runs CPU-only by removing GPU deploy blocks.

    Args:
        dev_file (str): Path to the development docker-compose file
        cpu_file (str): Path to the dev CPU docker-compose file to write
    """
    try:
        with open(dev_file, 'r') as f:
            lines = f.readlines()

        processed_lines = remove_gpu_deploy_blocks(lines)

        with open(cpu_file, 'w') as f:
            f.writelines(processed_lines)

        print(f"Successfully synchronized {cpu_file} from {dev_file} (CPU-only)")
        return True
    except Exception as e:
        print(f"Error synchronizing dev CPU compose file: {e}")
        return False


def main():
    """Main function to synchronize docker-compose files."""
    # Define the base path for Windows
    base_path = "O:/product-video-matching"

    # Define file paths
    dev_file = os.path.join(os.path.dirname(__file__), 'docker-compose.dev.yml')
    mac_file = os.path.join(os.path.dirname(__file__), 'docker-compose.mac.remote.yml')
    mac_native_file = os.path.join(os.path.dirname(__file__), 'docker-compose.mac.native.yml')
    dev_cpu_file = os.path.join(os.path.dirname(__file__), 'docker-compose.dev.cpu.yml')
    minimal_file = os.path.join(os.path.dirname(__file__), 'docker-compose.dev.minimal.yml')

    # Check if dev file exists
    if not os.path.exists(dev_file):
        print(f"Error: Development compose file not found: {dev_file}")
        return False

    success = True

    # Synchronize the full files (dev => mac)
    print("Synchronizing docker-compose.dev.yml => docker-compose.mac.remote.yml...")
    mac_success = sync_compose_files(dev_file, mac_file, base_path)
    if mac_success:
        print("[OK] Mac synchronization completed successfully.")
    else:
        print("[ERROR] Mac synchronization failed.")
        success = False

    # Synchronize the minimal file (dev => main-api.front-end with dependencies)
    print("\nSynchronizing docker-compose.dev.yml => docker-compose.dev.minimal.yml...")
    # Include required infrastructure services as dependencies
    target_services = ['postgres', 'pgweb', 'rabbitmq', 'redis', 'redis-insight', 'main-api', 'front-end']
    minimal_success = sync_minimal_compose_file(dev_file, minimal_file, target_services)
    if minimal_success:
        print("[OK] Main-API + Front-end + dependencies synchronization completed successfully.")
    else:
        print("[ERROR] Main-API + Front-end + dependencies synchronization failed.")
        success = False

    # Synchronize the mac native (CPU-only) file (dev => mac.native)
    print("\nSynchronizing docker-compose.dev.yml => docker-compose.mac.native.yml (CPU-only)...")
    mac_native_success = sync_mac_native_compose(dev_file, mac_native_file)
    if mac_native_success:
        print("[OK] Mac native (CPU-only) synchronization completed successfully.")
    else:
        print("[ERROR] Mac native (CPU-only) synchronization failed.")
        success = False

    # Synchronize the dev CPU (CPU-only) file (dev => dev.cpu)
    print("\nSynchronizing docker-compose.dev.yml => docker-compose.dev.cpu.yml (CPU-only)...")
    dev_cpu_success = sync_dev_cpu_compose(dev_file, dev_cpu_file)
    if dev_cpu_success:
        print("[OK] Dev CPU (CPU-only) synchronization completed successfully.")
    else:
        print("[ERROR] Dev CPU (CPU-only) synchronization failed.")
        success = False

    if success:
        print("\n[SUCCESS] All docker-compose synchronizations completed successfully.")
        return True
    else:
        print("\n[FAILED] Some docker-compose synchronizations failed.")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
