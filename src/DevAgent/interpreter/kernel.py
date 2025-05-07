class KernelController:

  """
    Manages kernels within a Jupyter Server.

    This component is responsible for creating, deleting, and interacting with
    kernels running in a Jupyter Server. It uses the Jupyter Server API to
    perform operations and relies on a StateManager for persistence.
    """

  def __init__(self, connection_info: Dict[str, Any], state_manager: StateManager):
    """
        Initialize the kernel controller.

        Parameters
        ----------
        connection_info : Dict[str, Any]
          Connection information for the Jupyter Server
        state_manager : StateManager
          State manager for persistence
        """
    pass

  def list_kernels(self) -> List[Dict[str, Any]]:
    """
        List all kernels managed by this controller.

        Returns
        -------
        List[Dict[str, Any]]
          List of kernel information
        """
    pass

  def create_kernel(
    self,
    name: str,
    kernel_spec: str = "python3",
    env: Optional[Dict[str, str]] = None,
  ) -> str:
    """
        Create a new kernel.

        Parameters
        ----------
        name : str
          Kernel name
        kernel_spec : str
          Kernel specification name
        env : Optional[Dict[str, str]]
          Environment variables

        Returns
        -------
        str
          Kernel ID

        Raises
        ------
        ValueError
          If kernel already exists
        RuntimeError
          If kernel creation fails
        """
    pass

  def start_kernel(self, name: str) -> None:
    """
        Start a kernel if not already running.

        Parameters
        ----------
        name : str
          Kernel name

        Raises
        ------
        ValueError
          If kernel doesn't exist
        RuntimeError
          If kernel start fails
        """
    pass

  def restart_kernel(self, name: str) -> None:
    """
        Restart a kernel.

        Parameters
        ----------
        name : str
          Kernel name

        Raises
        ------
        ValueError
          If kernel doesn't exist
        RuntimeError
          If kernel restart fails
        """
    pass

  def stop_kernel(self, name: str, missing_ok: bool = False) -> None:
    """
        Stop a kernel.

        Parameters
        ----------
        name : str
          Kernel name
        missing_ok : bool
          If True, don't raise error if kernel doesn't exist

        Raises
        ------
        ValueError
          If kernel doesn't exist and missing_ok is False
        RuntimeError
          If kernel stop fails
        """
    pass

  def delete_kernel(self, name: str, missing_ok: bool = False) -> None:
    """
        Delete a kernel: stop if running and remove state.

        Parameters
        ----------
        name : str
          Kernel name
        missing_ok : bool
          If True, don't raise error if kernel doesn't exist

        Raises
        ------
        ValueError
          If kernel doesn't exist and missing_ok is False
        RuntimeError
          If kernel deletion fails
        """
    pass

  def execute(self, name: str, code: str, timeout: float = 30.0) -> Tuple[str, Optional[str]]:
    """
        Execute code on a kernel and return results.

        Parameters
        ----------
        name : str
          Kernel name
        code : str
          Python code to execute
        timeout : float
          Timeout in seconds

        Returns
        -------
        Tuple[str, Optional[str]]
          (stdout, stderr or None)

        Raises
        ------
        ValueError
          If kernel doesn't exist
        RuntimeError
          If execution fails
        TimeoutError
          If execution times out
        """
    pass

  def is_running(self, name: str) -> bool:
    """
        Check if a kernel is running.

        Parameters
        ----------
        name : str
          Kernel name

        Returns
        -------
        bool
          True if kernel is running
        """
    pass

  def connect_console(self, name: str) -> Any:
    """
        Create a console connection to a kernel.

        Parameters
        ----------
        name : str
          Kernel name

        Returns
        -------
        Any
          Console connection object

        Raises
        ------
        ValueError
          If kernel doesn't exist or is not running
        """
    pass

  def restore_kernels(self) -> List[str]:
    """
        Restore previously running kernels.

        This method uses the state manager to identify kernels that were
        previously running and restarts them.

        Returns
        -------
        List[str]
          List of restored kernel names

        Raises
        ------
        RuntimeError
          If kernel restoration fails
        """
    pass
