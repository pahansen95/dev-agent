"""
LLM service utility module.

Provides interfaces and implementations for language model services.
"""

import json
import random
import time
import urllib.request
import urllib.error
from typing import Protocol

class LLMService(Protocol):
    """Protocol for language model service interactions."""

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Generate a completion from the language model.
        
        Args:
            system_prompt: The system instructions to guide the model behavior
            user_prompt: The specific user query or content to process
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0)
        
        Returns:
            The generated completion text
        """
        ...

class AzureOpenAIService:
    """Azure OpenAI API implementation of the LLM service."""

    def __init__(
        self, 
        endpoint: str, 
        api_key: str, 
        deployment_name: str, 
        api_version: str = "2023-05-15",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> None:
        """
        Initialize the Azure OpenAI service.
        
        Args:
            endpoint: The API endpoint URL
            api_key: Authentication key for the API
            deployment_name: The model deployment identifier
            api_version: API version to use
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Base delay between retries in seconds
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment_name = deployment_name
        self.api_version = api_version
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _send_request(self, url: str, data: dict, headers: dict, retry_count: int = 0) -> dict:
        """
        Send HTTP request with retry logic.
        
        Args:
            url: The request URL
            data: The request payload as a dictionary
            headers: HTTP headers
            retry_count: Current retry attempt
            
        Returns:
            Response data as a dictionary
            
        Raises:
            RuntimeError: If all retry attempts fail
        """
        try:
            # Convert data to JSON and encode
            json_data = json.dumps(data).encode('utf-8')

            # Create the request
            req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")

            # Send the request
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))

        except urllib.error.HTTPError as e:
            # Get error details if available
            error_msg = f"HTTP error: {e.code} {e.reason}"
            try:
                error_details = json.loads(e.read().decode('utf-8'))
                error_msg += f"\nDetails: {error_details}"
            except:
                pass

            # Handle retry logic
            if retry_count < self.max_retries and (e.code >= 500 or e.code == 429):
                # Calculate backoff with exponential increase and jitter
                delay = self.retry_delay * (2**retry_count) * (0.5 + random.random())
                print(f"Request failed with {e.code}. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                return self._send_request(url, data, headers, retry_count + 1)
            else:
                raise RuntimeError(error_msg) from e

        except Exception as e:
            raise RuntimeError(f"Request failed: {str(e)}") from e

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Generate a completion using Azure OpenAI API.
        
        Args:
            system_prompt: The system instructions to guide the model behavior
            user_prompt: The specific user query or content to process
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0)
            
        Returns:
            The generated completion text
            
        Raises:
            RuntimeError: If the API request fails after retries
        """
        # Prepare the request body
        request_body = {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                }, 
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Prepare the request URL
        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"

        # Prepare headers
        headers = {"Content-Type": "application/json", "api-key": self.api_key}

        # Send request with retry logic
        response_data = self._send_request(url, request_body, headers)

        # Extract and return the content
        return response_data["choices"][0]["message"]["content"]

class MockLLMService:
    """Mock implementation of the LLM service for testing."""

    def __init__(self, responses: dict = None) -> None:
        """
        Initialize the mock LLM service.
        
        Args:
            responses: Optional dictionary of pre-defined responses
        """
        self.responses = responses or {}
        
    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        Generate a mock completion.
        
        Args:
            system_prompt: The system instructions (unused in mock)
            user_prompt: The user query (used as key for pre-defined responses)
            max_tokens: Maximum tokens (unused in mock)
            temperature: Temperature (unused in mock)
            
        Returns:
            A pre-defined response or a generic response
        """
        # Look for an exact match in pre-defined responses
        if user_prompt in self.responses:
            return self.responses[user_prompt]
            
        # For section titles, generate a mock response
        if "section_title" in user_prompt:
            title_match = r"section titled \"([^\"]+)\""
            import re
            match = re.search(title_match, user_prompt)
            if match:
                section_title = match.group(1)
                return f"ADD content for section: {section_title}\n\nThis is mock content for {section_title}.\n\nChanges:\nADD: {section_title} - Added mock content"
                
        # Default generic response
        return "Generated content based on the provided prompt.\n\nChanges:\nADD: Default Section - Added generic content"