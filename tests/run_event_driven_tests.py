"""
Test runner for the event-driven interpreter architecture.

This script runs the tests for the event-driven interpreter architecture
and provides options for running specific test suites.
"""

import unittest
import argparse
import sys
import logging

from test_event_driven_interpreter import TestEventDrivenInterpreter, TestEventDrivenCLI

def setup_argument_parser():
  """Set up the argument parser for the test runner."""
  parser = argparse.ArgumentParser(description="Run tests for the event-driven interpreter architecture")

  parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
  parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
  parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")

  return parser

def main():
  """Main entry point for the test runner."""
  parser = setup_argument_parser()
  args = parser.parse_args()

  # Configure logging based on verbosity
  log_level = logging.DEBUG if args.verbose else logging.INFO
  logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

  # Create test suite
  suite = unittest.TestSuite()

  # Determine which tests to run
  if args.unit_only:
    suite.addTest(unittest.makeSuite(TestEventDrivenInterpreter))
  elif args.integration_only:
    suite.addTest(unittest.makeSuite(TestEventDrivenCLI))
  else:
    # Run all tests
    suite.addTest(unittest.makeSuite(TestEventDrivenInterpreter))
    suite.addTest(unittest.makeSuite(TestEventDrivenCLI))

  # Run tests
  runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
  result = runner.run(suite)

  # Return appropriate exit code
  return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
  sys.exit(main())
