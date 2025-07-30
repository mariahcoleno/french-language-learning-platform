"""
Tests for French grammar checking functionality using LanguageTool.
Validates detection of common French grammar errors like past participle
and gender agreement mistakes.
"""

import unittest
import language_tool_python

class TestLanguageTool(unittest.TestCase):
    def setUp(self):
        self.tool = language_tool_python.LanguageTool('fr')

    def test_grammar_check(self):
        """Test detection of French grammar errors in sample text."""
        text = "Je suis aller chez mon mère"
        matches = self.tool.check(text)
        
        # Expected errors
        expected_errors = [
            {"error": "aller", "suggestions": ["allé", "allés", "allée", "allées"]},
            {"error": "mon mère", "suggestions": ["ma mère"]}
        ]
        
        # Verify number of errors
        self.assertEqual(len(matches), 2, "Should find exactly 2 grammar errors")
        
        # Verify each error
        for match, expected in zip(matches, expected_errors):
            error_text = text[match.offset: match.offset + match.errorLength]
            self.assertEqual(error_text, expected["error"], f"Expected error '{expected['error']}'")
            self.assertTrue(set(expected["suggestions"]).issubset(set(match.replacements)),
                           f"Expected suggestions {expected['suggestions']} in {match.replacements}")

    def tearDown(self):
        self.tool.close()

if __name__ == '__main__':
    unittest.main()
