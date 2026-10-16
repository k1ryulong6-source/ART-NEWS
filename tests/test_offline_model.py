import unittest
from unittest.mock import Mock

from backend.editorial import numbers
from backend.offline_model import OfflineTranslator


class OfflineLiteralProtectionTests(unittest.TestCase):
    def translator(self):
        # Exercise numeric recovery without loading weights or making calls.
        translator = OfflineTranslator.__new__(OfflineTranslator)
        translator.translate_plain = Mock(return_value='译文')
        return translator

    def test_numeric_artwork_title_does_not_merge_adjacent_literals(self):
        translator = self.translator()
        source = 'His installation titled 66 76 26 opens at the museum.'
        result = translator.translate(source, 'en')
        self.assertIn('66 76 26', result)
        self.assertLessEqual(numbers(source), numbers(result))

    def test_amounts_preserve_units_including_abbreviated_millions(self):
        translator = self.translator()
        source = 'Costs fell from $200 million to $70M, across 3,065 venues.'
        result = translator.translate(source, 'en')
        self.assertIn('$200 million', result)
        self.assertIn('$70M', result)
        self.assertIn('3,065', result)
        self.assertLessEqual(numbers(source), numbers(result))

    def test_dates_times_and_numeric_parentheses_stay_intact(self):
        translator = self.translator()
        source = 'Visit on 2026/10/15 at 18:30 for the show (Room 66, 2026).'
        result = translator.translate(source, 'en')
        for literal in ('2026/10/15', '18:30', '(Room 66, 2026)'):
            self.assertIn(literal, result)
        self.assertLessEqual(numbers(source), numbers(result))

    def test_valid_first_pass_needs_no_extra_inference(self):
        translator = self.translator()
        translator.translate_plain.return_value = '票价为600日元。'
        self.assertEqual(translator.translate('Tickets cost 600 yen.', 'en'), '票价为600日元。')
        translator.translate_plain.assert_called_once()
