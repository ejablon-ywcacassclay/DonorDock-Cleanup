import json
import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import phonenumbers
import os
import re

# FOR TESTING ONLY -- REMOVE FOR PROD

# 2026-07-24T19:25:27.98

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
# PHONE NUMBER STANDARDIZING FUNCTION
# ----------------------------------------------------------------

# corrects a US address using the USPS API.
# If a match is found, it returns the standardized address.
# If a match is not found, it returns None.
'''
def fix_us_address(oauth_token, address_line_1, address_line_2, address_line_3, city, state_or_province, postal_code, country):
    url = 'https://apis-tem.usps.com/addresses/v3'
    headers = {
        "Content-type": "application/json",
        "Authorization": "Bearer aaaaa3LRm6frS4FwZvB3ZMZwdKVNMCEBpBvlFwbT"
    }

    requests.get(
        url=url,
        headers=headers
'''

# ================================================================
# CLEANUP SCRIPT
# ----------------------------------------------------------------

#def clean_up(batch_size, start_date, id_of_last_modified):
    

def main():
    print(('#' * 60 + '\n') * 3)

    # ================================================================
    # LOADING START DATE
    # ----------------------------------------------------------------

    with open('start_date.txt', 'r') as f:
        start_date = f.readline().strip()
        iso_timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z?'
        print(repr(start_date))
        if not re.fullmatch(iso_timestamp_pattern, start_date):
            raise ValueError('Start Date in helper file is not valid')
        id_of_last_updated = f.readline().strip()

    # ================================================================
    # API REQUEST FOR DATA TO STANDARDIZE
    # ----------------------------------------------------------------
    
    API_URL = 'https://public-api.donordock.com/api/v1'
    API_KEY = os.getenv('DD_SANDBOX_API_KEY')
    API_SECRET = os.getenv('DD_SANDBOX_API_SECRET')
    TENANT_ID = os.getenv('DD_SANDBOX_TENANT_ID')

    print('API_KEY loaded:', API_KEY is not None)
    print('API_SECRET loaded:', API_SECRET is not None)
    print('TENANT_ID:', repr(TENANT_ID))
    
    headers = {
        'X-Tenant-Id': TENANT_ID
    }

    auth = (
        API_KEY,
        API_SECRET
    )

    params = {
        'fromDate': start_date,
        'take': 10,
        'sortDir': 'ASC'
    }

    response = requests.get(
        f'{API_URL}/Contacts',
        params=params,
        headers=headers,
        auth=auth
    )

    print(response)

    if response.status_code == 200:
        print(response.json())
    else:
        print(f'Error: {response.status_code}')
    
    contacts_api_result = response.json() # gives dict containing "data" list containing a dict for each donor
    contacts_dicts = contacts_api_result['Data']

    # ================================================================
    # GETTING OAUTH CREDENTIALS FOR USPS API
    # ----------------------------------------------------------------

    client_id = 'your_client_id'
    client_secret = 'your_client_secret'

    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url='https://apis-tem.usps.com/oauth2/v3/token',
        client_id=client_id,
        client_secret=client_secret
    )

    # ================================================================
    # CLEANUP AND UPDATE LOOP
    # ----------------------------------------------------------------

    # for each record
    date_of_last_updated = start_date
    for contact_dict in contacts_dicts:
        
        # we strip leading and trailing whitespace from all fields
        for key in contact_dict:
            contact_dict[key] = None if not contact_dict[key] or not contact_dict[key].strip() else contact_dict[key].strip()

        # make call to USPS API to standardize addresses
        # if status = 200:
        #     update address in contact_dict based on result
        # else if error 429:
        #     save contact_dict['CreatedOn'] as the start date for the next update run
        #     break loop and end execution
        # if any other error:
        #     contact_dict['BadAddress'] = True

        # update phone number using phonenumbers package (update Main? Mobile? Both?)
        print(f'Main Phone Before Correction: {repr(contact_dict['MainPhone'])}')
        if contact_dict['MainPhone'] and contact_dict['MainPhone'].strip():
            try:
                contact_dict['MainPhone'] = fix_phone_number(contact_dict['MainPhone'])
            except phonenumbers.phonenumberutil.NumberParseException as npe:
                contact_dict['BadMobileNumber'] = True
        else:
            contact_dict['MainPhone'] = None
        print(f'Main Phone After Correction: {repr(contact_dict['MainPhone'])}')
    
        print(f'Mobile Phone Before Correction: {repr(contact_dict['MobilePhone'])}')
        if contact_dict['MobilePhone'] and contact_dict['MobilePhone'].strip():
            try:
                contact_dict['MobilePhone'] = fix_phone_number(contact_dict['MobilePhone'])
            except phonenumbers.phonenumberutil.NumberParseException as npe:
                contact_dict['BadMobileNumber'] = True
        else:
            contact_dict['MobilePhone'] = None
        print(f'Mobile Phone After Correction: {repr(contact_dict['MobilePhone'])}')
        
        print(f'Json dumps result: {json.dumps(contact_dict)}')

        date_of_last_updated = contact_dict['CreatedOn']

        # make call to DonorDock API to PUT the updates
        # *OR*, put updates into a CSV file for review.
        response = requests.put(
            url = f'{API_URL}/Contacts/{contact_dict['Id']}',
            json = contact_dict,
            headers = headers,
            auth = auth
        )


    #    print(f'\nResponse: {response}')
    #    print(f'\nStatus code: {response.status_code}')
    #    print(f'\nResponse content: {response.content}')
    #    print(f'\nRequest url: {response.request.url}')
    #    print(f'\nRequest headers: {response.request.headers}')
        print(f'\nRequest body: {response.request.body}')
    
    
        date_of_last_updated = contact_dict['CreatedOn']
        if response.status_code == 200:
            id_of_last_updated = contact_dict['Id']
        else:
            break
        
        print(f'start date: {start_date}, end date: {date_of_last_updated}')
    
        response = requests.get(
            url = f'{API_URL}/Contacts/{contact_dict['Id']}',
            headers = headers,
            auth = auth
        )
    
        print(f'\nUpdated Contact: {response.content}')


    # ================================================================
    # WRITING END DATE
    # ----------------------------------------------------------------
    
    #with open('start_date.txt', 'w') as f:
    #    f.write(date_of_last_updated + '\n')
    #    f.write(id_of_last_updated)

if __name__ == '__main__':
    main()