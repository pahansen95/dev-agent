import os
import signal
import logging
import platform
import time
import json
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ProcessObserver:

  """Service that observes OS processes for kernels."""

  def __init__(self):
    """Initialize the process observer."""
    self.system = platform.system()
    logger.debug(f"Initialized ProcessObserver for {self.system}")

  def is_process_running(self, pid: int) -> bool:
    """
        Check if a process with given PID is running.
        
        Args:
            pid: The process ID to check
            
        Returns:
            True if the process is running, False otherwise
        """
    try:
      # Different approach based on OS
      if self.system == "Windows":
        # Windows - use tasklist command
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False)
        return str(pid) in result.stdout
      else:
        # Unix-like - send signal 0 to check process existence
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
      # Process does not exist
      return False
    except PermissionError:
      # Process exists but we don't have permission to send signals
      # (but we can see it exists)
      return True
    except Exception as e:
      logger.error(f"Error checking if process {pid} is running: {e}")
      return False

  def observe_process(self, pid: int) -> Dict[str, Any]:
    """
        Observe metrics for a running process.
        
        Args:
            pid: The process ID to observe
            
        Returns:
            Dictionary with process metrics
        """
    metrics = {"pid": pid, "running": False, "timestamp": time.time()}

    if not self.is_process_running(pid):
      return metrics

    metrics["running"] = True

    try:
      # Different approach based on OS
      if self.system == "Windows":
        # Windows - use wmic command
        try:
          result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}", "get", "WorkingSetSize,KernelModeTime,UserModeTime,CommandLine", "/format:csv"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2)

          lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
          if len(lines) >= 2: # Header and data
            parts = lines[1].split(',')
            if len(parts) >= 5: # Node, CommandLine, KernelMode, UserMode, WorkingSet
              metrics["command"] = parts[1]
              metrics["cpu_kernel_time"] = int(parts[2]) / 10000000 # Convert 100ns to seconds
              metrics["cpu_user_time"] = int(parts[3]) / 10000000 # Convert 100ns to seconds
              metrics["memory_rss"] = int(parts[4]) / 1024 # Convert bytes to KB
        except Exception as e:
          logger.error(f"Error getting Windows process details for PID {pid}: {e}")

      elif self.system == "Darwin" or self.system == "Linux":
        # macOS or Linux - use ps command
        try:
          result = subprocess.run(["ps", "-p", str(pid), "-o", "pid,ppid,rss,vsz,pcpu,pmem,command"], capture_output=True, text=True, check=False, timeout=2)

          lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
          if len(lines) >= 2: # Header and data
            parts = lines[1].split(None, 6) # Split by whitespace
            if len(parts) >= 7:
              metrics["ppid"] = int(parts[1])
              metrics["memory_rss"] = int(parts[2]) # RSS in KB
              metrics["memory_vsz"] = int(parts[3]) # VSZ in KB
              metrics["cpu_percent"] = float(parts[4]) # CPU percentage
              metrics["memory_percent"] = float(parts[5]) # Memory percentage
              metrics["command"] = parts[6] # Command
        except Exception as e:
          logger.error(f"Error getting Unix process details for PID {pid}: {e}")

      # Try to get open files for the process (Unix-like only)
      if self.system != "Windows":
        try:
          lsof_result = subprocess.run(["lsof", "-p", str(pid), "-n", "-F"], capture_output=True, text=True, check=False, timeout=2)

          # Count number of open files
          open_files = len([line for line in lsof_result.stdout.split('\n') if line.startswith('f')])
          metrics["open_files"] = open_files
        except Exception:
          pass # lsof might not be available or have permission issues

    except Exception as e:
      logger.error(f"Error observing process {pid}: {e}")

    return metrics

  def get_child_processes(self, pid: int) -> list[int]:
    """
        Get all child process IDs for a given parent PID.
        
        Args:
            pid: The parent process ID
            
        Returns:
            List of child process IDs
        """
    child_pids = []

    try:
      # Different approach based on OS
      if self.system == "Windows":
        # Windows - use wmic command
        result = subprocess.run(
          ["wmic", "process", "where", f"ParentProcessId={pid}", "get", "ProcessId", "/format:csv"], capture_output=True, text=True, check=False, timeout=5)

        lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        for line in lines[1:]: # Skip header
          parts = line.split(',')
          if len(parts) >= 2:
            try:
              child_pids.append(int(parts[1]))
            except (ValueError, IndexError):
              pass

      elif self.system == "Darwin" or self.system == "Linux":
        # macOS or Linux - use ps command
        result = subprocess.run(["ps", "-o", "pid", "--ppid", str(pid)], capture_output=True, text=True, check=False, timeout=5)

        lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        for line in lines[1:]: # Skip header
          try:
            child_pids.append(int(line))
          except ValueError:
            pass

    except Exception as e:
      logger.error(f"Error getting child processes of {pid}: {e}")

    return child_pids

  def detach_process(self, pid: int) -> bool:
    """
        Detach a process to ensure it continues after parent exits.
        
        Args:
            pid: The process ID to detach
            
        Returns:
            True if successful, False otherwise
        """
    # This is mainly effective on Unix-like systems. Windows handles
    # process independence differently via job objects or service creation.
    # For this Python-based approach, we're limited in what we can do.

    if not self.is_process_running(pid):
      logger.warning(f"Cannot detach process {pid}: not running")
      return False

    try:
      if self.system == "Windows":
        # Not much we can do on Windows from Python
        logger.debug(f"Process detachment on Windows is handled differently - {pid} should persist")
        return True

      else: # Unix-like
        # Send SIGHUP to detach terminals and SIGCONT to ensure it's running
        try:
          os.kill(pid, signal.SIGHUP)
          os.kill(pid, signal.SIGCONT)
          logger.debug(f"Detached process {pid}")
          return True
        except Exception as e:
          logger.error(f"Error detaching process {pid}: {e}")
          return False

    except Exception as e:
      logger.error(f"Error in detach_process for {pid}: {e}")
      return False

  def get_process_exit_code(self, pid: int) -> Optional[int]:
    """
        Get the exit code of a process that has terminated.
        
        Args:
            pid: The process ID
            
        Returns:
            Exit code if available, None if process is still running or not found
        """
    if self.is_process_running(pid):
      return None # Process is still running

    try:
      # This is difficult to get after the fact in most systems
      # We would typically capture this when a process is waited on

      # For Linux, we can check /proc/{pid}/status if it just exited
      if self.system == "Linux":
        proc_status = Path(f"/proc/{pid}/status")
        if proc_status.exists():
          with open(proc_status, 'r') as f:
            for line in f:
              if line.startswith('ExitCode:'):
                try:
                  return int(line.split(':')[1].strip())
                except (ValueError, IndexError):
                  pass

      # For macOS and Windows, it's generally not available
      # after the process has exited and we didn't wait for it

    except Exception as e:
      logger.error(f"Error getting exit code for process {pid}: {e}")

    return None

  def get_kernel_pid_from_connection_file(self, connection_file: str) -> Optional[int]:
    """
        Extract PID from connection file if available.
        
        Args:
            connection_file: Path to the Jupyter connection file
            
        Returns:
            Process ID if found, None otherwise
        """
    if not connection_file or not Path(connection_file).exists():
      return None

    try:
      with open(connection_file, 'r') as f:
        connection_info = json.load(f)

        # Check for Jupyter's process info (not standard)
        if "pid" in connection_info:
          pid = int(connection_info["pid"])
          if self.is_process_running(pid):
            return pid

      # If not in file directly, try heuristic approach
      # Check processes with "jupyter-kernel" or similar in command line
      file_name = Path(connection_file).name
      kernel_id = file_name.split('-')[-1].split('.')[0]

      if self.system == "Windows":
        cmd = ["wmic", "process", "where", "CommandLine like '%jupyter-kernel%'", "get", "ProcessId,CommandLine", "/format:csv"]
      else: # Unix-like
        cmd = ["ps", "-e", "-o", "pid,command", "|", "grep", "jupyter-kernel"]

      try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, shell=(self.system != "Windows"))

        for line in result.stdout.split('\n'):
          if kernel_id in line:
            parts = line.strip().split()
            for part in parts:
              try:
                pid = int(part)
                if self.is_process_running(pid):
                  return pid
              except ValueError:
                continue
      except Exception:
        pass

    except Exception as e:
      logger.error(f"Error extracting PID from connection file {connection_file}: {e}")

    return None
