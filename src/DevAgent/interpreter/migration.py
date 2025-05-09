import json
import shutil
import time
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DataMigrator:
    """Migrates data from old format to new DDD-based format."""
    
    def __init__(self, old_base_dir: Path, new_base_dir: Path):
        """
        Initialize the migrator.
        
        Args:
            old_base_dir: The old base directory
            new_base_dir: The new base directory
        """
        self.old_base_dir = old_base_dir
        self.new_base_dir = new_base_dir
    
    def migrate(self) -> bool:
        """
        Perform the migration.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting migration from {self.old_base_dir} to {self.new_base_dir}")
        
        try:
            # Create new directory structure
            self._ensure_directory_structure()
            
            # Migrate sessions
            self._migrate_sessions()
            
            # Migrate registries
            self._migrate_registries()
            
            # Migrate symlinks
            self._migrate_symlinks()
            
            # Create flag file to indicate DDD mode
            (self.new_base_dir / ".use_ddd").touch()
            
            logger.info("Migration completed successfully")
            return True
        except Exception as e:
            logger.exception(f"Migration failed: {e}")
            return False
    
    def _ensure_directory_structure(self) -> None:
        """Ensure the new directory structure exists."""
        (self.new_base_dir / "by-name").mkdir(parents=True, exist_ok=True)
        (self.new_base_dir / "by-id" / "sessions").mkdir(parents=True, exist_ok=True)
        (self.new_base_dir / "registry").mkdir(parents=True, exist_ok=True)
    
    def _migrate_sessions(self) -> None:
        """Migrate session data."""
        sessions_dir = self.old_base_dir / "by-id" / "sessions"
        if not sessions_dir.exists():
            logger.warning(f"Sessions directory not found: {sessions_dir}")
            return
        
        # Process each session
        for session_path in sessions_dir.glob("*"):
            session_id = session_path.name
            
            # Read metadata
            metadata_path = session_path / "metadata.json"
            if not metadata_path.exists():
                logger.warning(f"Session metadata not found: {metadata_path}")
                continue
            
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.error(f"Error reading session metadata from {metadata_path}: {e}")
                continue
            
            # Create new session directory
            new_session_path = self.new_base_dir / "by-id" / "sessions" / session_id
            new_session_path.mkdir(parents=True, exist_ok=True)
            (new_session_path / "kernels").mkdir(exist_ok=True)
            
            # Update metadata with new fields if needed
            if "created_at" not in metadata:
                metadata["created_at"] = time.time()
            if "last_activity" not in metadata:
                metadata["last_activity"] = time.time()
            
            # Copy metadata
            with open(new_session_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Process each kernel
            kernels_dir = session_path / "kernels"
            if kernels_dir.exists():
                for kernel_path in kernels_dir.glob("*"):
                    self._migrate_kernel(kernel_path, new_session_path / "kernels" / kernel_path.name)
    
    def _migrate_kernel(self, old_kernel_path: Path, new_kernel_path: Path) -> None:
        """
        Migrate a single kernel.
        
        Args:
            old_kernel_path: The old kernel path
            new_kernel_path: The new kernel path
        """
        new_kernel_path.mkdir(parents=True, exist_ok=True)
        (new_kernel_path / "workspace").mkdir(exist_ok=True)
        
        # Copy metadata and connection info
        metadata_path = old_kernel_path / "metadata.json"
        connection_path = old_kernel_path / "connection.json"
        
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                # Update metadata with new fields if needed
                if "created_at" not in metadata:
                    metadata["created_at"] = time.time()
                if "last_activity" not in metadata:
                    metadata["last_activity"] = time.time()
                if "is_alive" not in metadata:
                    metadata["is_alive"] = False
                
                with open(new_kernel_path / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                logger.error(f"Error migrating kernel metadata: {e}")
                shutil.copy(metadata_path, new_kernel_path / "metadata.json")
        
        if connection_path.exists():
            shutil.copy(connection_path, new_kernel_path / "connection.json")
        
        # Copy workspace content
        old_workspace = old_kernel_path / "workspace"
        new_workspace = new_kernel_path / "workspace"
        
        if old_workspace.exists() and old_workspace.is_dir():
            for item in old_workspace.glob("*"):
                if item.is_file():
                    shutil.copy(item, new_workspace / item.name)
                elif item.is_dir():
                    shutil.copytree(item, new_workspace / item.name)
    
    def _migrate_registries(self) -> None:
        """Migrate registry files."""
        # Copy session registry
        old_session_registry = self.old_base_dir / "registry" / "sessions.json"
        new_session_registry = self.new_base_dir / "registry" / "sessions.json"
        
        if old_session_registry.exists():
            shutil.copy(old_session_registry, new_session_registry)
        else:
            with open(new_session_registry, "w") as f:
                json.dump({}, f)
        
        # Copy kernel registry
        old_kernel_registry = self.old_base_dir / "registry" / "kernels.json"
        new_kernel_registry = self.new_base_dir / "registry" / "kernels.json"
        
        if old_kernel_registry.exists():
            shutil.copy(old_kernel_registry, new_kernel_registry)
        else:
            with open(new_kernel_registry, "w") as f:
                json.dump({}, f)
    
    def _migrate_symlinks(self) -> None:
        """Migrate symlinks."""
        old_by_name = self.old_base_dir / "by-name"
        new_by_name = self.new_base_dir / "by-name"
        
        if not old_by_name.exists():
            return
        
        # Process each named session
        for session_link in old_by_name.glob("*"):
            if not session_link.is_dir():
                continue
            
            session_name = session_link.name
            new_session_link = new_by_name / session_name
            new_session_link.mkdir(exist_ok=True)
            
            # Read session registry to find session ID
            registry_path = self.new_base_dir / "registry" / "sessions.json"
            try:
                with open(registry_path, "r") as f:
                    registry = json.load(f)
            except Exception:
                registry = {}
            
            session_id = registry.get(session_name)
            if not session_id:
                continue
            
            # Find actual session path
            session_path = self.new_base_dir / "by-id" / "sessions" / session_id
            
            # Create symlink for session
            try:
                target_path = os.path.relpath(session_path, new_session_link.parent)
                if new_session_link.exists() and new_session_link.is_symlink():
                    new_session_link.unlink()
                os.symlink(target_path, new_session_link, target_is_directory=True)
            except Exception as e:
                logger.error(f"Error creating session symlink: {e}")
            
            # Process each kernel link
            for kernel_link in session_link.glob("*"):
                if not kernel_link.is_symlink():
                    continue
                
                kernel_name = kernel_link.name
                
                # Find the kernel ID
                target = kernel_link.resolve()
                kernel_id = target.name if target.name.startswith("kid-") else None
                
                if not kernel_id:
                    continue
                
                # Create new kernel symlink
                try:
                    kernel_path = session_path / "kernels" / kernel_id
                    new_kernel_link = new_session_link / kernel_name
                    
                    if new_kernel_link.exists() or new_kernel_link.is_symlink():
                        new_kernel_link.unlink()
                    
                    target_path = os.path.relpath(kernel_path, new_kernel_link.parent)
                    os.symlink(target_path, new_kernel_link, target_is_directory=True)
                except Exception as e:
                    logger.error(f"Error creating kernel symlink: {e}")

def migrate_data(old_dir: Path, new_dir: Path) -> bool:
    """
    Migrate data from old format to new DDD-based format.
    
    Args:
        old_dir: The old data directory
        new_dir: The new data directory
        
    Returns:
        True if successful, False otherwise
    """
    migrator = DataMigrator(old_dir, new_dir)
    return migrator.migrate()