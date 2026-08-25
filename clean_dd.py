import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import phonenumbers
import os
import re
import csv

# ================================================================
# PHONE NUMBER STANDARDIZING FUNCTION
# ----------------------------------------------------------------

# fixes a phone number using phonenumbers library.
# assumes phone number is being dialed from a US phone.
# if the phone number is invalid, raises an error;
# if the phone number is valid, formats it in NATIONAL format if a +1 country code,
# and in INTERNATIONAL format if not a +1 country code.
def fix_phone_number(phone_number_string):
    phone_number = phonenumbers.parse(phone_number_string, 'US')

    if not phonenumbers.is_possible_number(phone_number):
        raise phonenumbers.phonenumberutil.NumberParseException(error_type=-1, msg='Not a possible phone number')
    if not phonenumbers.is_valid_number(phone_number):
        raise phonenumbers.phonenumberutil.NumberParseException(error_type=-1, msg='Not a valid phone number')

    if phone_number.country_code == 1:
        return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.NATIONAL)
    else:
        return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

# ================================================================
# ADDRESS STANDARDIZING FUNCTION
# ----------------------------------------------------------------

# corrects a US address using the Smarty API.
# Returns a dictionary of the response.
def fix_us_address(auth_id, auth_token, address_line_1, address_line_2, address_line_3, city, state_or_province, postal_code, country):
    response = requests.get(
        url = 'https://us-street.api.smarty.com/street-address',
        params = {
            'street': address_line_1,
            'street2': address_line_2,
            'city': city,
            'state': state_or_province,
            'zipcode': postal_code,
            'country': country,
            'match': 'enhanced'
        },
        auth=(
            auth_id,
            auth_token
        )
    )

    response.raise_for_status()

    response_dict = response.json()

    return response_dict


def fix_contact(contact_dict):
    # strip leading and trailing whitespace from all fields
    for key in contact_dict:
        val = contact_dict[key]
        if type(val) == str and (val.startswith(' ') or val.endswith(' ')):
            contact_dict[key] = val.strip()

    # retrieve Smarty API credentials from environment variables
    SMARTY_AUTH_ID = os.getenv('SMARTY_AUTH_ID')
    SMART_AUTH_TOKEN = os.getenv('SMART_AUTH_TOKEN')

    # make call to Smarty API to standardize addresses
    if contact_dict['Address1'] is not None and str(contact_dict['Address1']).strip() != '':
        smarty_response_dict = fix_us_address(SMARTY_AUTH_ID, SMART_AUTH_TOKEN, *[contact_dict[key] for key in
                ['Address1', 'Address2', 'Address3', 'City', 'StateOrProvince', 'PostalCode', 'Country']])
    # enhanced_match_codes = smarty_response_dict['enhanced_match'].split()


    # update phone number using phonenumbers package (update Main? Mobile? Both?)
    for phone_number_type in ['MainPhone', 'MobilePhone']:
        # print(f'{phone_number_type} Before Correction: {repr(contact_dict[phone_number_type])}')
        if contact_dict[phone_number_type] and contact_dict[phone_number_type].strip(): # if not empty and not spaces
            try:
                contact_dict[phone_number_type] = fix_phone_number(contact_dict[phone_number_type])
            except phonenumbers.phonenumberutil.NumberParseException as npe:
                contact_dict['BadMobileNumber'] = True
        else:
            contact_dict[phone_number_type] = None
        # print(f'{phone_number_type} After Correction: {repr(contact_dict[phone_number_type])}')

    # print(f'Json dumps result: {json.dumps(contact_dict)}')

# ================================================================
# CLEANUP SCRIPT
# ----------------------------------------------------------------

BATCH_SIZE = 1

csv_schema = ['Id', 'AccountNumber', 'MemberId', 'Title',
        'FirstName', 'MiddleName', 'LastName', 'FullName', 'DisplayName', 'Nickname', 'FormerName',
        'OrganizationName', 'Addressee', 'Salutation', 'Suffix', 'Email', 'DOB',
        'Address1', 'Address2', 'Address3', 'City', 'StateOrProvince', 'PostalCode', 'Country',
        'MainPhone', 'MobilePhone', 'Fax', 'Website',
        'FacebookUsername', 'InstagramUsername', 'LinkedInUsername', 'TwitterUsername',
        'DoNotSolicit', 'Deceased', 'Type', 'Description', 'Stage', 'IntegrationId',
        'Source', 'ExceptionNotes', 'Employer', 'JobTitle', 'Household', 'HouseholdRole',
        'SpouseFirst', 'SpouseLast', 'Badges', 'MarketingLists', 'GiftsInDateRange', 'DonationGiftsInDateRange',
        'EventTicketGiftsInDateRange', 'MembershipGiftsInDateRange', 'VolunteerHoursInDateRange',
        'Owner', 'Affiliation', 'BadAddress', 'Unsubscribed', 'BadMobileNumber', 'SMSUnsubscribed',
        'CustomFields', 'CreatedOn', 'ModifiedOn']

def main():

    # ================================================================
    # LOADING START DATE
    # ----------------------------------------------------------------

    with open('start_date.txt', 'r') as f:
        start_date = f.readline().strip()
        # example date: 2026-07-24T19:25:27.980
        iso_timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z?'
        print(repr(start_date))
        if not re.fullmatch(iso_timestamp_pattern, start_date):
            raise ValueError('Start Date in helper file is not valid')
        id_of_last_checked = f.readline().strip()

    # Load DD credentials
    DD_API_URL = 'https://public-api.donordock.com/api/v1'
    DD_API_KEY = os.getenv('DD_SANDBOX_API_KEY')
    DD_API_SECRET = os.getenv('DD_SANDBOX_API_SECRET')
    DD_TENANT_ID = os.getenv('DD_SANDBOX_TENANT_ID')

    # Log whether DD credentials loaded
    print('DD_API_KEY loaded:', DD_API_KEY is not None)
    print('DD_API_SECRET loaded:', DD_API_SECRET is not None)
    print('DD_TENANT_ID:', repr(DD_TENANT_ID))

    # do-while loop pattern.
    # Loop ends when no contact records are left. Loop also breaks when API rate limits are reached.
    while True:

        # ================================================================
        # API REQUEST FOR DATA TO STANDARDIZE
        # ----------------------------------------------------------------
        
        response = requests.get(
            url=f'{DD_API_URL}/Contacts',
            params={
                'fromDate': start_date,
                'take': BATCH_SIZE,
                'sortDir': 'ASC'
            },
            headers={
                'X-Tenant-Id': DD_TENANT_ID
            },
            auth=(
                DD_API_KEY,
                DD_API_SECRET
            )
        )

        # raise error if there was one
        response.raise_for_status()
        
        contacts_api_result = response.json() # gives dict containing 'data' list containing a dict for each donor
        contacts_dicts = contacts_api_result['Data']

        # ================================================================
        # GETTING OAUTH CREDENTIALS FOR USPS API
        # ----------------------------------------------------------------

        # client_id = 'your_client_id'
        # client_secret = 'your_client_secret'

        # ================================================================
        # PREPARING OUTPUT FILES
        # ----------------------------------------------------------------

        # create files if empty or not exist
        if not os.path.isfile('before.csv') or os.path.getsize('before.csv') == 0:
            with open('before.csv', 'w', encoding='utf-8', newline='') as before:
                csv.writer(before).writerow(csv_schema)
        if not os.path.isfile('after.csv') or os.path.getsize('after.csv') == 0:
            with open('after.csv', 'w', encoding='utf-8', newline='') as after:
                csv.writer(after).writerow(csv_schema)

        with open('before.csv', 'a', encoding='utf-8', newline='') as before, \
                open('after.csv', 'a', encoding='utf-8', newline='') as after:

            before_writer = csv.DictWriter(f=before, fieldnames=csv_schema)
            after_writer = csv.DictWriter(f=after, fieldnames=csv_schema)

            # ================================================================
            # CLEANUP AND UPDATE LOOP
            # ----------------------------------------------------------------

            # for each record
            date_of_last_checked = start_date
            for contact_dict in contacts_dicts:

                before_contact_dict = contact_dict.copy()

                print(contact_dict.values())

                try:
                    fix_contact(contact_dict)
                except requests.HTTPError as httpe:
                    if httpe.response.status_code == 429:
                        break
                    else:
                        print(httpe.response.status_code)
                        print(httpe.response.content)
                        raise httpe

                date_of_last_checked = contact_dict['CreatedOn']

                # write contact_dict to after in csv format
                # if before_contact_dict != contact_dict:
                before_writer.writerow(before_contact_dict)
                after_writer.writerow(contact_dict)

        if len(contacts_dicts) < BATCH_SIZE:
            break

        start_date = date_of_last_checked

        break

    # ================================================================
    # WRITING END DATE
    # ----------------------------------------------------------------
    
    # with open('start_date.txt', 'w') as f:
    #    f.write(date_of_last_checked + '\n')
    #    f.write(id_of_last_checked)

if __name__ == '__main__':
    main()