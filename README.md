# DonorDock Data Cleanup

The purpose of this project is to clean up and standardize the DonorDock contact data so that it can be maintained and de-duplicated more easily.

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