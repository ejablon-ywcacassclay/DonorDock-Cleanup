# DonorDock Data Cleanup

The purpose of this project is to clean up and standardize the DonorDock contact data so that it can be maintained and de-duplicated more easily.

## Overview of design

### Data flow

DonorDock contact data ingested via API -> addresses are standardized via API, and phone numbers are standardized to US format via Python library *phonenumbers* -> data is output to paired CSVs of "before.csv" and "after.csv" for a human to review the changes. Contact records that were not changed will not be output at all, to save effort on human review.

### Main resources/dependencies used

- DonorDock API
- *phonenumbers* Python library
- USPS or Smarty address validation API