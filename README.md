# DonorDock Data Cleanup

The purpose of this project is to clean up and standardize the DonorDock contact data so that it can be maintained and de-duplicated more easily.

## How to use

### To run the script

Running the script requires:
- Installing all required packages via pip
- Loading all required API keys and secrets and DD Tenant ID into the right environment variables

### To analyze results

To analyze the output, import before.csv and after.csv into Excel, then run conditional formatting on all cells of the *after* table using the following formula: =A1<>before!A1

Also suggest viewing side-by-side to see changes more easily, and zooming out to comb through all fields more quickly.

Lastly, the only fields that are ever modified are:
- Address1
- Address2
- Address3
- City
- StateOrProvince
- PostalCode
- Country
- BadAddress
and
- MainPhone
- MobilePhone
- BadMobilePhone
plus
- County\*

It should be fine to remove all other fields if desired, except for *Id* which may be necessary for importing the validated data back into DonorDock.

\*A note about County: DonorDock mysteriously does not provide the County field via their API, despite it being present in their data and their manual exporting. Furthermore, County is autocompleted by their current Smarty integration when manually entering an address. Thus, County must be included in the corrected (i.e. *after*) data, but it can't be retrieved for the initial (i.e. *before*) data, so it will show as blank for any field that is not being corrected by the Smarty API. This is not a concern, however, because blank fields did not overwrite filled ones upon DonorDock import based on my testing.

## Overview of design

### Data flow

DonorDock contact data ingested via API -> addresses are standardized via API, and phone numbers are standardized to US format via Python library *phonenumbers* -> data is output to paired CSVs of "before.csv" and "after.csv" for a human to review the changes. Contact records that were not changed will not be output at all, to save effort on human review.

### Flags for bad data

If either the Main Phone or Mobile Phone are not valid, the flag BadMobileNumber is set to True. This will happen regardless of which phone number is bad.

If the address cannot be found, the BadAddress flag will be set to True.

These fields are used because they already exist in the database. Because they already exist and have a purpose, they will not be modified unless the phone number or address is specifically determined to be invalid, thus they won't be set to False even if the phone numbers or the address seem to be valid.

### Main resources/dependencies used

- DonorDock API
- *phonenumbers* Python library
- USPS or Smarty address validation API

## Challenges and things learned

- DonorDock API does not expose County via API, despite it being in their data. However, if a field is blank, it doesn't seem to overwrite any existing fields when imported into DonorDock.
- USPS API makes addresses into **ALL CAPS**, which looks very weird, and the API is not intended to be used for cleaning databases.
- Smarty API will consider ANY address to be valid if it has what's known as a [unique zipcode](https://www.smarty.com/articles/unique-zip-codes). It will even tell you that the address is *in the USPS database*, even if it's completely bogus. To work around this, the script checks for addresses that are *deliverable*, basically meaning they are valid AND have been delivered to before.