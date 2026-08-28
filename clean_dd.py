import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import phonenumbers
import os
import re
import csv
from datetime import datetime, timedelta

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

smarty_request_count = 0

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
            'match': 'enhanced',
            'candidates': 10
        },
        auth=(
            auth_id,
            auth_token
        )
    )
    global smarty_request_count
    smarty_request_count += 1
    print(f'smarty_request_count in fix_us_address: {smarty_request_count}\n')

    response.raise_for_status()

    print(response.content)

    response_dict = response.json()

    return response_dict

# Checks whether Smarty response indicates the address is deliverable.
# Pass in the Smarty response as a Python dictionary
def is_deliverable(smarty_response_dict):
    # ensures that the parameter dictionary contains data
    if 'analysis' not in smarty_response_dict:
        return False
    analysis = smarty_response_dict['analysis']
    # dpv_match_code of Y means the address is valid.
    # dpv_vacant of N means the address has been specifically labeled as deliverable.
    return 'dpv_match_code' in analysis \
            and analysis['dpv_match_code'] == 'Y' \
            and 'dpv_vacant' in analysis \
            and analysis['dpv_vacant'] == 'N'

# Fixes a contact record. Pass in the contact as a dictionary of its values.
# Removes leading + trailing whitespace from string fields,
# standardizes phone numbers, and
# validates addresses.
# Throws errors if Smarty request fails in a way other than rate limiting.
# Otherwise, returns True if fix succeeds, and False if it fails.
# The contact dictionary is modified directly.
def fix_contact(contact_dict):
    # strip leading and trailing whitespace from all fields
    for key in contact_dict:
        val = contact_dict[key]
        if type(val) == str and (val.startswith(' ') or val.endswith(' ')):
            contact_dict[key] = val.strip()

    # retrieve Smarty API credentials from environment variables
    SMARTY_AUTH_ID = os.getenv('SMARTY_AUTH_ID')
    SMARTY_AUTH_TOKEN = os.getenv('SMARTY_AUTH_TOKEN')

    # make call to Smarty API to standardize addresses
    if contact_dict['Address1'] is not None and str(contact_dict['Address1']).strip() != '' and contact_dict['Type'] != 'Organization':
        smarty_response_dict = fix_us_address(SMARTY_AUTH_ID, SMARTY_AUTH_TOKEN, *[contact_dict[key] for key in
                ['Address1', 'Address2', 'Address3', 'City', 'StateOrProvince', 'PostalCode', 'Country']])
        
        if len(smarty_response_dict) == 1 and is_deliverable(smarty_response_dict[0]):
            matched_address_dict = smarty_response_dict[0]
            contact_dict['Address1'] = matched_address_dict['delivery_line_1']
            contact_dict['Address2'] = matched_address_dict['delivery_line_2'] if 'delivery_line_2' in matched_address_dict.keys() else None
            # we ignore address line 3 because that is what seems to happen inside DonorDock's integration of Smarty autocomplete.

            contact_dict['City'] = matched_address_dict['components']['city_name']
            contact_dict['StateOrProvince'] = matched_address_dict['components']['state_abbreviation']
            contact_dict['PostalCode'] = f'{matched_address_dict['components']['zipcode']}-{matched_address_dict['components']['plus4_code']}'
            contact_dict['Country'] = 'US' # international addresses aren't USPS deliverable

            contact_dict['County'] = matched_address_dict['metadata']['county_name'] # Adding County to the output
        else:
            contact_dict['BadAddress'] = True

    # update phone number using phonenumbers package (update Main? Mobile? Both?)
    for phone_number_type in ['MainPhone', 'MobilePhone']:
        # print(f'{phone_number_type} Before Correction: {repr(contact_dict[phone_number_type])}')
        if contact_dict[phone_number_type] and str(contact_dict[phone_number_type]).strip(): # if not empty and not spaces
            try:
                contact_dict[phone_number_type] = fix_phone_number(contact_dict[phone_number_type])
            except phonenumbers.phonenumberutil.NumberParseException as npe:
                contact_dict['BadMobileNumber'] = True
        else:
            contact_dict[phone_number_type] = None
        # print(f'{phone_number_type} After Correction: {repr(contact_dict[phone_number_type])}')

    # print(f'Json dumps result: {json.dumps(contact_dict)}')

# Performs the API request for the DonorDock data.
def get_dd_contact_data(dd_api_key, dd_api_secret, dd_tenant_id, batch_size, start_date):
    dd_api_url = 'https://public-api.donordock.com/api/v1'

    response = requests.get(
        url=f'{dd_api_url}/Contacts',
        params={
            'fromDate': start_date,
            'take': batch_size,
            'sortDir': 'ASC'
        },
        headers={
            'X-Tenant-Id': dd_tenant_id
        },
        auth=(
            dd_api_key,
            dd_api_secret
        )
    )

    # raise error if there was one
    response.raise_for_status()
    
    contacts_api_result = response.json() # gives dict containing 'data' list containing a dict for each donor
    contacts_dicts = contacts_api_result['Data']

    return contacts_dicts

# Increments a date string that's passed in in ISO format by one millisecond.
# Used to skip over the record that was just checked.
def increment_date(iso_date):
    dt = datetime.fromisoformat(iso_date)
    dt += timedelta(milliseconds=1)
    return dt.isoformat(timespec="milliseconds")

# Prepares the output CSV files with headers,
# if they are empty or missing.
def prepare_output_files():
    # create files if empty or not exist
    if not os.path.isfile('before.csv') or os.path.getsize('before.csv') == 0:
        with open('before.csv', 'w', encoding='utf-8', newline='') as before:
            csv.writer(before).writerow(csv_schema)
    if not os.path.isfile('after.csv') or os.path.getsize('after.csv') == 0:
        with open('after.csv', 'w', encoding='utf-8', newline='') as after:
            csv.writer(after).writerow(csv_schema)

# Attempts to fix the contact that is passed in. Returns True if successful, and False if there are any HTTPErrors.
# If there are any unexpected HTTP errors, the function raises them.
def try_fix_contact(contact_dict: dict):
    try:
        fix_contact(contact_dict)
    except requests.HTTPError as httpe:
        if httpe.response.status_code == 429: # 429 is acceptable, and means we should wait until next available time
            return False
        elif httpe.response.status_code in [401, 403]:
            print(httpe.response.content)
            print(httpe.response.status_code)
            return False
        else:
            print(httpe.response.content)
            print(httpe.response.status_code)
            raise httpe
    else:
        return True

# ================================================================
# CLEANUP SCRIPT
# ----------------------------------------------------------------

BATCH_SIZE = 1 # Number of contacts retrieved per DonorDock query
SMARTY_REQUEST_BREAKPOINT = 1 # Max number of Smarty requests. Records stop being processed after this number of requests have been made.

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
        'CustomFields', 'CreatedOn', 'ModifiedOn', 'County']

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

    # ================================================================
    # LOADING DD CREDENTIALS
    # ----------------------------------------------------------------

    DD_API_KEY = os.getenv('DD_SANDBOX_API_KEY')
    DD_API_SECRET = os.getenv('DD_SANDBOX_API_SECRET')
    DD_TENANT_ID = os.getenv('DD_SANDBOX_TENANT_ID')

    # Log whether DD credentials loaded
    print('DD_API_KEY loaded:', DD_API_KEY is not None)
    print('DD_API_SECRET loaded:', DD_API_SECRET is not None)
    print('DD_TENANT_ID loaded:', DD_TENANT_ID is not None)

    # do-while loop pattern.
    # Loop ends when no contact records are left. Loop also breaks when API rate limits are reached.
    stop_loop = False
    while not stop_loop:

        # ================================================================
        # API REQUEST FOR DATA TO STANDARDIZE
        # ----------------------------------------------------------------
        
        contacts_dicts = get_dd_contact_data(dd_api_key=DD_API_KEY, dd_api_secret=DD_API_SECRET,
                                            dd_tenant_id=DD_TENANT_ID, batch_size=BATCH_SIZE, start_date=start_date)
        
        # ================================================================
        # PREPARING OUTPUT FILES
        # ----------------------------------------------------------------

        prepare_output_files()

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

                contact_dict.update({'County': None}) # add blank County field to enable inclusion in output

                before_contact_dict = contact_dict.copy() # saves initial state of contact

                print(contact_dict.values())

                # if fix_contact does not succeed, stop execution.
                if not try_fix_contact(contact_dict):
                    stop_loop = True
                    break

                date_of_last_checked = contact_dict['CreatedOn']

                # write contact_dict to after in csv format
                if before_contact_dict != contact_dict:
                    before_writer.writerow(before_contact_dict)
                    after_writer.writerow(contact_dict)

                print(f'smarty_request_count: {smarty_request_count}\n')
                print(f'SMARTY_REQUEST_BREAKPOINT: {SMARTY_REQUEST_BREAKPOINT}\n')

                start_date = increment_date(date_of_last_checked)

                if smarty_request_count >= SMARTY_REQUEST_BREAKPOINT:
                    stop_loop = True
                    break
        
        if len(contacts_dicts) < BATCH_SIZE: # this would mean we reached the end of the DonorDock data
            break

    # ================================================================
    # WRITING END DATE
    # ----------------------------------------------------------------
    
    with open('start_date.txt', 'w') as f:
       f.write(start_date)

if __name__ == '__main__':
    main()