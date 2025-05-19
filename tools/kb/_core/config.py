"""
Configuration management for Knowledge Base Generator.

Provides a centralized configuration system that handles settings from multiple
sources with clear precedence rules, validation, and convenient access patterns.
"""

import os
import json
import argparse
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, TypedDict, Union, List, cast


class ConfigSection(Enum):
    """Configuration sections."""
    ACTION = "action"
    OUTPUT = "output"
    PROCESSING = "processing"
    LLM = "llm"
    TEMPLATE = "template"
    GUIDANCE = "guidance"
    RENDER = "render"


class OutputConfig(TypedDict, total=False):
    """Output configuration."""
    format: str  # Output format (markdown, html)
    file: Optional[str]  # Output file path


class ProcessingConfig(TypedDict, total=False):
    """Processing configuration."""
    max_header_level: int  # Maximum header level to include
    chunk_size: int  # Size of chunks for processing large files


class LLMConfig(TypedDict, total=False):
    """Language model configuration."""
    service: str  # Service type (azure, openai, mock)
    endpoint: Optional[str]  # API endpoint URL
    api_key: Optional[str]  # API key
    deployment: Optional[str]  # Model deployment ID
    max_tokens: int  # Maximum tokens per request
    temperature: float  # Temperature for generation


class TemplateConfig(TypedDict, total=False):
    """Template configuration."""
    file: Optional[str]  # Template file path
    name: str  # Template name to use


class GuidanceConfig(TypedDict, total=False):
    """Guidance configuration."""
    file: Optional[str]  # Guidance file path
    name: str  # Guidance name to use
    inline: Optional[Dict[str, str]]  # Inline guidance parameters


class RenderConfig(TypedDict, total=False):
    """Render configuration."""
    base_file: str  # Base file for patch application
    patch_dir: str  # Directory containing patches


class ConfigSchema(TypedDict, total=False):
    """Schema for KB Generator configuration."""
    action: str
    output: OutputConfig
    processing: ProcessingConfig
    llm: Optional[LLMConfig]
    template: TemplateConfig
    guidance: GuidanceConfig
    render: Optional[RenderConfig]


class ConfigManager:
    """Manages configuration from multiple sources with validation."""

    # Default configuration values
    DEFAULT_CONFIG: ConfigSchema = {
        "action": "render",
        "output": {
            "format": "markdown",
            "file": None
        },
        "processing": {
            "max_header_level": 6,
            "chunk_size": 65536
        },
        "llm": None,
        "template": {
            "file": None,
            "name": "default"
        },
        "guidance": {
            "file": None,
            "name": "default",
            "inline": None
        },
        "render": {
            "base_file": "base.md",
            "patch_dir": "patches"
        }
    }

    def __init__(self) -> None:
        """Initialize with default configuration."""
        self.config: ConfigSchema = self._deep_copy(self.DEFAULT_CONFIG)

    @staticmethod
    def _deep_copy(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a deep copy of a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Deep copy of the configuration
        """
        return json.loads(json.dumps(config))

    def get_config(self) -> ConfigSchema:
        """
        Get the current configuration.
        
        Returns:
            Complete configuration schema
        """
        return self.config

    def get_section(self, section: Union[ConfigSection, str]) -> Dict[str, Any]:
        """
        Get a specific configuration section.
        
        Args:
            section: Configuration section name or enum
            
        Returns:
            Configuration section
            
        Raises:
            KeyError: If the section doesn't exist
        """
        section_name = section.value if isinstance(section, ConfigSection) else section
        
        if section_name not in self.config:
            raise KeyError(f"Configuration section '{section_name}' not found")
            
        return cast(Dict[str, Any], self.config.get(section_name, {}))

    def set_section(self, section: Union[ConfigSection, str], config: Dict[str, Any]) -> None:
        """
        Set a specific configuration section.
        
        Args:
            section: Configuration section name or enum
            config: Configuration values
        """
        section_name = section.value if isinstance(section, ConfigSection) else section
        self.config[section_name] = config

    def update_section(self, section: Union[ConfigSection, str], config: Dict[str, Any]) -> None:
        """
        Update a configuration section with new values.
        
        Args:
            section: Configuration section name or enum
            config: Configuration values to update
            
        Raises:
            KeyError: If the section doesn't exist
        """
        section_name = section.value if isinstance(section, ConfigSection) else section
        
        if section_name not in self.config:
            raise KeyError(f"Configuration section '{section_name}' not found")
            
        # Get the current section
        current_section = self.get_section(section_name)
        
        # Update with new values
        if isinstance(current_section, dict):
            current_section.update(config)
        else:
            self.config[section_name] = config

    def load_from_file(self, filepath: str) -> None:
        """
        Load configuration from a JSON file and merge with current config.
        
        Args:
            filepath: Path to the configuration file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file contains invalid JSON
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                
            # Merge file config with current config
            self._merge_config(file_config)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {str(e)}")

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # LLM configuration
        if os.environ.get('AZURE_OPENAI_ENDPOINT'):
            if not self.config.get('llm'):
                self.config['llm'] = {}
                
            llm_config = cast(LLMConfig, self.config['llm'])
            llm_config['service'] = 'azure'
            llm_config['endpoint'] = os.environ.get('AZURE_OPENAI_ENDPOINT')
            llm_config['api_key'] = os.environ.get('AZURE_OPENAI_KEY')
            llm_config['deployment'] = os.environ.get('AZURE_OPENAI_DEPLOYMENT')
        
        # Output configuration
        output_format = os.environ.get('KB_OUTPUT_FORMAT')
        output_file = os.environ.get('KB_OUTPUT_FILE')
        
        if output_format or output_file:
            output_config = cast(OutputConfig, self.config['output'])
            if output_format:
                output_config['format'] = output_format
            if output_file:
                output_config['file'] = output_file
        
        # Guidance configuration
        guidance_name = os.environ.get('KB_GUIDANCE_NAME')
        guidance_file = os.environ.get('KB_GUIDANCE_FILE')
        
        if guidance_name or guidance_file:
            guidance_config = cast(GuidanceConfig, self.config['guidance'])
            if guidance_name:
                guidance_config['name'] = guidance_name
            if guidance_file:
                guidance_config['file'] = guidance_file
        
        # Template configuration
        template_name = os.environ.get('KB_TEMPLATE_NAME')
        template_file = os.environ.get('KB_TEMPLATE_FILE')
        
        if template_name or template_file:
            template_config = cast(TemplateConfig, self.config['template'])
            if template_name:
                template_config['name'] = template_name
            if template_file:
                template_config['file'] = template_file

    def load_from_args(self, args: argparse.Namespace) -> None:
        """
        Load configuration from command-line arguments.
        
        Args:
            args: Parsed command-line arguments
        """
        # Action
        if hasattr(args, 'action') and args.action:
            self.config['action'] = args.action
        
        # Output options
        output_config = cast(OutputConfig, self.config['output'])
        if hasattr(args, 'output_format') and args.output_format:
            output_config['format'] = args.output_format
        if hasattr(args, 'output_file') and args.output_file:
            output_config['file'] = args.output_file
        
        # Guidance options
        guidance_config = cast(GuidanceConfig, self.config['guidance'])
        if hasattr(args, 'guidance_file') and args.guidance_file:
            guidance_config['file'] = args.guidance_file
        if hasattr(args, 'guidance_name') and args.guidance_name:
            guidance_config['name'] = args.guidance_name
        if hasattr(args, 'guidance_inline') and args.guidance_inline:
            guidance_params = self._parse_inline_guidance(args.guidance_inline)
            guidance_config['inline'] = guidance_params
            guidance_config['name'] = 'inline'
        
        # Template options
        template_config = cast(TemplateConfig, self.config['template'])
        if hasattr(args, 'template_file') and args.template_file:
            template_config['file'] = args.template_file
        if hasattr(args, 'template_name') and args.template_name:
            template_config['name'] = args.template_name
        
        # Render options
        if hasattr(args, 'base_file') and args.base_file:
            render_config = cast(RenderConfig, self.config['render'])
            render_config['base_file'] = args.base_file
        if hasattr(args, 'patch_dir') and args.patch_dir:
            render_config = cast(RenderConfig, self.config['render'])
            render_config['patch_dir'] = args.patch_dir

    def _parse_inline_guidance(self, guidance_str: str) -> Dict[str, str]:
        """
        Parse inline guidance parameters from a string.
        
        Format: key1=value1,key2=value2,...
        
        Args:
            guidance_str: Comma-separated key-value pairs
            
        Returns:
            Dictionary of guidance parameters
            
        Raises:
            ValueError: If the format is invalid
        """
        guidance_params: Dict[str, str] = {}
        
        try:
            pairs = guidance_str.split(",")
            for pair in pairs:
                key, value = pair.split("=", 1)
                guidance_params[key.strip()] = value.strip()
        except ValueError:
            raise ValueError(f"Invalid guidance parameter format: {guidance_str}")
        
        return guidance_params

    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge a new configuration with the current configuration.
        
        Args:
            new_config: New configuration to merge
        """
        for section, values in new_config.items():
            if section not in self.config:
                self.config[section] = values
            elif isinstance(self.config[section], dict) and isinstance(values, dict):
                # Recursively merge dictionaries
                self.config[section].update(values)
            else:
                # Replace primitive values
                self.config[section] = values

    def validate(self) -> List[str]:
        """
        Validate the current configuration.
        
        Returns:
            List of validation warnings, empty if no issues found
        """
        warnings = []
        
        # Validate action
        if 'action' not in self.config:
            warnings.append("Missing required 'action' configuration")
        elif self.config['action'] not in ['render', 'generate']:
            warnings.append(f"Invalid action '{self.config['action']}', must be 'render' or 'generate'")
        
        # Validate output format
        output_config = cast(OutputConfig, self.config.get('output', {}))
        if 'format' in output_config and output_config['format'] not in ['markdown', 'html']:
            warnings.append(f"Invalid output format '{output_config['format']}', must be 'markdown' or 'html'")
        
        # Validate LLM configuration if present
        llm_config = cast(Optional[LLMConfig], self.config.get('llm'))
        if llm_config and 'service' in llm_config:
            service = llm_config['service']
            if service == 'azure':
                # Check required Azure OpenAI settings
                required_fields = ['endpoint', 'api_key', 'deployment']
                missing_fields = [field for field in required_fields if not llm_config.get(field)]
                if missing_fields:
                    warnings.append(f"Missing required Azure OpenAI configuration: {', '.join(missing_fields)}")
        
        return warnings

    @classmethod
    def create_default(cls) -> 'ConfigManager':
        """
        Create a configuration manager with default settings.
        
        Returns:
            Configured ConfigManager
        """
        return cls()

    @classmethod
    def create_from_env(cls) -> 'ConfigManager':
        """
        Create a configuration manager from environment variables.
        
        Returns:
            Configured ConfigManager
        """
        config_manager = cls()
        config_manager.load_from_env()
        return config_manager

    @classmethod
    def create_from_file(cls, filepath: str) -> 'ConfigManager':
        """
        Create a configuration manager from a file.
        
        Args:
            filepath: Path to the configuration file
            
        Returns:
            Configured ConfigManager
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file contains invalid JSON
        """
        config_manager = cls()
        config_manager.load_from_file(filepath)
        return config_manager

    @classmethod
    def create_from_args(cls, args: argparse.Namespace) -> 'ConfigManager':
        """
        Create a configuration manager from command-line arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Configured ConfigManager
        """
        config_manager = cls()
        config_manager.load_from_args(args)
        return config_manager

    @classmethod
    def create(
        cls, 
        args: Optional[argparse.Namespace] = None, 
        env: bool = True, 
        config_file: Optional[str] = None
    ) -> 'ConfigManager':
        """
        Create a configuration manager with layered configuration.
        
        Loads configuration in the following order (later sources override earlier ones):
        1. Default values
        2. Configuration file (if provided)
        3. Environment variables (if env=True)
        4. Command-line arguments (if provided)
        
        Args:
            args: Optional parsed command-line arguments
            env: Whether to load from environment variables
            config_file: Optional path to a configuration file
            
        Returns:
            Configured ConfigManager
            
        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the config file contains invalid JSON
        """
        config_manager = cls()
        
        # Load from config file if provided
        if config_file and Path(config_file).exists():
            config_manager.load_from_file(config_file)
        
        # Load from environment variables if enabled
        if env:
            config_manager.load_from_env()
        
        # Load from command-line arguments if provided
        if args:
            config_manager.load_from_args(args)
        
        # Validate the configuration
        warnings = config_manager.validate()
        if warnings:
            print("Configuration warnings:")
            for warning in warnings:
                print(f"- {warning}")
        
        return config_manager


def create_cli_parser() -> argparse.ArgumentParser:
    """
    Create a base CLI parser with common arguments.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(add_help=False)
    
    # Add logging-specific arguments
    parser.add_argument(
        "--log-level", 
        choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"], 
        help="Set logging level"
    )
    parser.add_argument(
        "--log-format", 
        choices=["text", "json"], 
        help="Set log output format"
    )
    parser.add_argument(
        "--log-output", 
        choices=["console", "file", "both"], 
        help="Set log output destination"
    )
    parser.add_argument(
        "--log-file", 
        help="Set log file name (when output is file or both)"
    )
    
    # Add configuration file argument
    parser.add_argument(
        "--config-file", 
        help="Path to configuration file"
    )
    
    return parser