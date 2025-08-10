"""
Basic tests for EKS Upgrade Assessment Toolkit
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config.parser import ConfigParser
from assessment.compatibility import CompatibilityChecker
from generators.reports import ReportGenerator


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of the toolkit."""
    
    def test_config_parser_import(self):
        """Test that ConfigParser can be imported."""
        self.assertIsNotNone(ConfigParser)
    
    def test_compatibility_checker_import(self):
        """Test that CompatibilityChecker can be imported."""
        self.assertIsNotNone(CompatibilityChecker)
    
    def test_report_generator_import(self):
        """Test that ReportGenerator can be imported."""
        self.assertIsNotNone(ReportGenerator)
    
    def test_compatibility_checker_initialization(self):
        """Test that CompatibilityChecker can be initialized."""
        checker = CompatibilityChecker()
        self.assertIsNotNone(checker)
    
    def test_supported_versions(self):
        """Test that supported versions are defined."""
        checker = CompatibilityChecker()
        self.assertGreater(len(checker.EKS_SUPPORTED_VERSIONS), 0)
        self.assertIn("1.28", checker.EKS_SUPPORTED_VERSIONS)


if __name__ == '__main__':
    unittest.main()
