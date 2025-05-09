#!/usr/bin/env python
"""
Test runner for DevAgent CLI tests.

This script runs both unit tests and integration tests for the DevAgent CLI.
"""

import unittest
import sys
import os
import argparse

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from test_cli import TestCLIArgumentParser, TestOntologyCommands, TestInterpreterSessionCommands, TestInterpreterKernelCommands, TestMainFunction
from test_cli_integration import TestCLIIntegration

def run_unit_tests(verbosity=1):
    """Run unit tests for the CLI."""
    print("=== Running CLI Unit Tests ===")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCLIArgumentParser))
    suite.addTests(loader.loadTestsFromTestCase(TestOntologyCommands))
    suite.addTests(loader.loadTestsFromTestCase(TestInterpreterSessionCommands))
    suite.addTests(loader.loadTestsFromTestCase(TestInterpreterKernelCommands))
    suite.addTests(loader.loadTestsFromTestCase(TestMainFunction))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests(verbosity=1):
    """Run integration tests for the CLI."""
    print("\n=== Running CLI Integration Tests ===")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCLIIntegration))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run DevAgent CLI tests")
    parser.add_argument(
        "--unit-only", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration-only", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Increase output verbosity"
    )
    
    args = parser.parse_args()
    verbosity = 2 if args.verbose else 1
    
    # Determine which tests to run
    run_unit = not args.integration_only
    run_integration = not args.unit_only
    
    success = True
    
    # Run the tests
    if run_unit:
        unit_success = run_unit_tests(verbosity)
        success = success and unit_success
    
    if run_integration:
        integration_success = run_integration_tests(verbosity)
        success = success and integration_success
    
    # Return exit code based on test success
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())