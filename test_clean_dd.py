import unittest
import clean_dd
from phonenumbers.phonenumberutil import NumberParseException

class TestPhoneNumberFunction(unittest.TestCase):
    def test_fixable_us_phone_numbers(self):
        test_cases = [
            '7013888242',
            '701-388-8242',
            '70-1-388-8242',
            '701388-8242',
            '+17013888242'
        ]

        for phone in test_cases:
            with self.subTest(phone=phone):
                self.assertEqual(
                    clean_dd.fix_phone_number(phone),
                    '(701) 388-8242'
                )

    def test_fixable_intl_phone_numbers(self):
        test_cases = [
            ('011 44 20 7946 0123', '+44 20 7946 0123')
        ]

        for phone, expected in test_cases:
            with self.subTest(phone=phone):
                self.assertEqual(
                    clean_dd.fix_phone_number(phone),
                    expected
                )

    def test_unfixable_phone_numbers(self):
        test_cases = [
            '701388824',
            '701388824x',
            'foo@bar.com'
        ]

        for phone in test_cases:
            with self.subTest(phone=phone):
                with self.assertRaises(NumberParseException):
                    clean_dd.fix_phone_number(phone)
    
class TestMainFunction(unittest.TestCase):
    def 

if __name__ == '__main__':
    unittest.main()