import unittest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from unit.interpreter.domain.test_value_objects import *
from unit.interpreter.domain.test_model import *
from unit.interpreter.infrastructure.test_event_bus import *
from unit.interpreter.application.test_app_service import *
from integration.interpreter.test_integration import *

if __name__ == "__main__":
    unittest.main()