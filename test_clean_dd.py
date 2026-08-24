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
    
class TestFixContactFunction(unittest.TestCase):
    test_contact = dict(zip(clean_dd.csv_schema, ['efwa2342uh34u2ih87fg', 'DD-1', None, 'Mr.', 'John', None, 'Doe', 'John Doe', 'John Doe', None, None, None, 'John Doe', 'Dear John Doe', None, 'john.doe@email.com', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, False, False, 'INDIVIDUAL', None, 'PROSPECT', 'ebuhf57d7feu9', None, None, None, None, None, None, None, None, '', None, None, None, None, None, None, None, 'FALSE', None, None, None, None, [], '2026-07-24T19:25:26.527', '2026-08-19T21:31:47.197']))

    def test_whitespace_stripping(self):
        whitespace_test_contact = self.test_contact.copy()
        whitespace_test_contact['FirstName'] = ' John'
        whitespace_test_contact['LastName'] = 'Doe  '
        whitespace_test_contact['Title'] = ' Mr. '
        clean_dd.fix_contact(whitespace_test_contact)
        self.assertEqual(whitespace_test_contact, self.test_contact)

    def test_phone_number_invalid(self):
        invalid_phone_test_contact = self.test_contact.copy()
        invalid_phone_test_contact['MainPhone'] = '123456789'
        clean_dd.fix_contact(invalid_phone_test_contact)
        self.assertEqual(invalid_phone_test_contact['BadMobileNumber'], True)

if __name__ == '__main__':
    unittest.main()