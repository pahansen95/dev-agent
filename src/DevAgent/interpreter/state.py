class StateManager:

  """
    Manages persistent state for kernels and interpreters.

    This component is responsible for saving and retrieving state information
    for kernels and interpreter sessions. It provides a consistent interface
    for state persistence regardless of the underlying storage mechanism.
    """

  def __init__(self, base_dir: Union[str, Path]):
    """
        Initialize the state manager.

        Parameters
        ----------
        base_dir : Union[str, Path]
          Base directory for state files
        """
    pass

  def save_kernel_state(
    self,
    name: str,
    kernel_id: str,
    kernel_spec: str = "python3",
    env: Optional[Dict[str, str]] = None,
    running: bool = True,
  ) -> None:
    """
        Save kernel state for persistence.

        Parameters
        ----------
        name : str
          Kernel name
        kernel_id : str
          Jupyter kernel ID
        kernel_spec : str
          Kernel specification name
        env : Optional[Dict[str, str]]
          Environment variables
        running : bool
          Whether the kernel is currently running
        """
    pass

  def get_kernel_state(self, name: str) -> Optional[Dict[str, Any]]:
    """
        Get saved kernel state.

        Parameters
        ----------
        name : str
          Kernel name

        Returns
        -------
        Optional[Dict[str, Any]]
          Kernel state or None if not found
        """
    pass

  def update_kernel_state(self, name: str, **kwargs) -> None:
    """
        Update kernel state with new values.

        Parameters
        ----------
        name : str
          Kernel name
        **kwargs
          Values to update
        """
    pass

  def delete_kernel_state(self, name: str) -> None:
    """
        Delete kernel state.

        Parameters
        ----------
        name : str
          Kernel name
        """
    pass

  def get_running_kernels(self) -> List[Dict[str, Any]]:
    """
        Get list of kernels marked as running.

        Returns
        -------
        List[Dict[str, Any]]
          List of kernel states for running kernels
        """
    pass

  def list_kernels(self) -> List[Dict[str, Any]]:
    """
        List all kernels with their state.

        Returns
        -------
        List[Dict[str, Any]]
          List of all kernel states
        """
    pass
