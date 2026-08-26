import unittest
import clean_dd
import os
from phonenumbers.phonenumberutil import NumberParseException

class TestPhoneNumberFunction(unittest.TestCase):
    def test_fixable_us_phone_numbers(self):
        test_cases = [
            '7012322547',
            '701-232-2547',
            '70-1-2322547',
            '701232-2547',
            '+17012322547'
        ]

        for phone in test_cases:
            with self.subTest(phone=phone):
                self.assertEqual(
                    clean_dd.fix_phone_number(phone),
                    '(701) 232-2547'
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
            '701232254',
            '701232254x',
            'foo@bar.com'
        ]

        for phone in test_cases:
            with self.subTest(phone=phone):
                with self.assertRaises(NumberParseException):
                    clean_dd.fix_phone_number(phone)

class TestFixUSAddressFunction(unittest.TestCase):
    test_address = {
        'address_line_1': '4650 38th Ave S Ste 110',
        'address_line_2': None,
        'address_line_3': None,
        'city': 'Fargo',
        'state_or_province': 'ND',
        'postal_code': 58104,
        'country': 'US'
    }

    test_auth_id = os.getenv('SMARTY_AUTH_ID')
    test_auth_token = os.getenv('SMARTY_AUTH_TOKEN')

    def test_deliverable_address(self):
        deliverable_test_address = self.test_address.copy()
        output = clean_dd.fix_us_address(auth_id=self.test_auth_id, auth_token=self.test_auth_token, **deliverable_test_address)
        self.assertTrue(len(output) == 1)
        self.assertTrue(clean_dd.is_deliverable(output[0]))

    def test_invalid_address(self):
        invalid_test_address = self.test_address.copy()
        invalid_test_address['address_line_1'] = '4 38th Ave S Ste 1'
        output = clean_dd.fix_us_address(auth_id=self.test_auth_id, auth_token=self.test_auth_token, **invalid_test_address)
        self.assertFalse(clean_dd.is_deliverable(output[0]))

class TestIncrementDateFunction(unittest.TestCase):
    def test_normal_date(self):
        test_date = '2026-07-24T19:25:27.357'
        self.assertEqual(clean_dd.increment_date(test_date), '2026-07-24T19:25:27.358')

    def test_hour_changing(self):
        test_date = '2026-07-24T19:25:27.999'
        self.assertEqual(clean_dd.increment_date(test_date), '2026-07-24T19:25:28.000')
    
    def test_day_changing(self):
        test_date = '2026-07-24T23:59:59.999'
        self.assertEqual(clean_dd.increment_date(test_date), '2026-07-25T00:00:00.000')
            

class TestFixContactFunction(unittest.TestCase):
    test_contact = dict(zip(clean_dd.csv_schema, ['efwa2342uh34u2ih87fg', 'DD-1', None, 'Mr.', 'John', None, 'Doe', 'John Doe', 'John Doe', None, None, None, 'John Doe', 'Dear John Doe', None, 'john.doe@email.com', None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, False, False, 'INDIVIDUAL', None, 'PROSPECT', 'ebuhf57d7feu9', None, None, None, None, None, None, None, None, '', None, None, None, None, None, None, None, 'FALSE', None, None, None, None, [], '2026-07-24T19:25:26.527', '2026-08-19T21:31:47.197', None]))

    maxDiff = None

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

    def test_address_invalid(self):
        # this address is not a real place
        test_address = {
            'Address1': '40 38th Ave S',
            'Address2': 'Ste 1',
            'Address3': None,
            'City': 'Fargo',
            'StateOrProvince': 'ND',
            'PostalCode': '58104',
            'Country': 'US'
        }
        expected = self.test_contact.copy()
        expected.update(test_address)
        expected.update({'BadAddress': True})
        invalid_address_test_contact = self.test_contact.copy()
        invalid_address_test_contact.update(test_address)
        clean_dd.fix_contact(invalid_address_test_contact)
        self.assertEqual(invalid_address_test_contact, expected)

    def test_address_deliverable_correctable(self):
        # this address is real and deliverable
        test_address = {
            'Address1': '4650 38th Ave S',
            'Address2': 'Ste 110',
            'Address3': None,
            'City': 'Fargo',
            'StateOrProvince': 'ND',
            'PostalCode': '58104',
            'Country': 'US'
        }
        expected_address = {
            'Address1': '4650 38th Ave S Ste 110',
            'Address2': None,
            'Address3': None,
            'City': 'Fargo',
            'StateOrProvince': 'ND',
            'PostalCode': '58104-8529',
            'Country': 'US',
            'County': 'Cass'
        }

        expected = self.test_contact.copy()
        expected.update(expected_address)

        invalid_address_test_contact = self.test_contact.copy()
        invalid_address_test_contact.update(test_address)

        clean_dd.fix_contact(invalid_address_test_contact)
        self.assertEqual(invalid_address_test_contact, expected)


if __name__ == '__main__':
    unittest.main()