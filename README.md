# DonorDock Data Cleanup

The purpose of this project is to clean up and standardize the DonorDock contact data so that it can be maintained and de-duplicated more easily.

## How to use

### To run the script

Running the script requires:
- Installing all required packages via pip
- Getting and loading in all required API keys and secrets, plus the DonorDock Tenant ID\*, into the right environment variables

\*The DonorDock Tenant ID is hard to find. You can email DonorDock Support to ask for it, but the easier way that doesn't require any waiting is:
- Go to Settings Menu (top right) -> Integrations -> POINT, then click Create POINT Key
- Copy the Tenant ID from the POINT key
- Click Revoke Point Key
The Tenant ID is the identifier for your organization, so it doesn't matter where you get it from, it will always be the same.

You will also need to have a few files for the script to pull from.

If you are cleaning from a list of IDs, you need:
- list_of_ids.txt -- expected to be one ID per line and nothing else
- id_of_last_checked.txt -- can be created as an empty file. Allows program to continue where it left off if it hits the max Smarty requests and stops.

If you are cleaning as a scheduled task, you need:
- start_date.txt -- can start as an empty file. Records the date of the last record that was checked.
Note that even when importing records in bulk, their creation dates are still separated by several milliseconds, allowing us to increment the date of the last record checked by 1 ms to get the next record without repeats.

### To analyze results

To analyze the output, import before.csv and after.csv into Excel, then run conditional formatting on all cells of the *after* table using the following formula: =A1<>before!A1

Also suggest viewing side-by-side to see changes more easily, and zooming out to comb through all fields more quickly.

Other than removing leading and trailing whitespace (which I have never actually encountered in the DonorDock data, so it's possible they already remove it on their back-end), the only fields that are modified are:
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
- BadMainNumber\*
- MobilePhone
- BadMobileNumber
plus
- County\*\*

It should be fine to remove all other fields if desired, except for *Id* which may be necessary for importing the validated data back into DonorDock.

\*BadMainNumber is not a field that DonorDock uses; it is added here to provide more detailed flagging, so the human reviewing the output can tell more easily which phone number was flagged.
\*\*A note about County: DonorDock mysteriously does not provide the County field via their API, despite it being present in their data and their manual exporting. Furthermore, County is autocompleted by their current Smarty integration when manually entering an address. Thus, County must be included in the corrected (i.e. *after*) data, but it can't be retrieved for the initial (i.e. *before*) data, so it will show as blank for any field that is not being corrected by the Smarty API. This is not a concern, however, because blank fields did not overwrite filled ones upon DonorDock import based on my testing.

## Overview of design

### Data flow

DonorDock contact data ingested via API -> phone numbers are standardized to US format via Python library *phonenumbers* -> addresses standardized via Smarty API -> data is output to "before.csv" for data before cleaning and "after.csv" for data after cleaning, so that a human can review the changes. Contact records that were not changed will not be output at all, saving effort on human review.

### Flags for bad data

For Phone Numbers:
If the Main Phone or Mobile Phone are not valid, the flags BadMainNumber or BadMobileNumber respectively are set to True.

For Address:
If the address is not determined to be *deliverable*, the BadAddress flag will be set to True.

These fields are used because they already exist in the database. Because they already exist and have a purpose, they will not be modified unless the phone number or address is specifically determined to be invalid, thus they won't be set to False even if the phone numbers or the address seem to be valid.

### Main resources/dependencies used

- DonorDock API
- *phonenumbers* Python library
- Smarty address validation API

### Design decisions and changes

The original design was going to be a scheduled microservice, hosted on the web, which would retrieve any new records hourly from DonorDock, clean up their phone number using the *phonenumbers* library and address using the USPS API, then put the updated records back into DonorDock automatically.

The first change was to change to a human-in-the-loop design and abandon the automatic putting of updates because of the risks involved with unsupervised modifications to the donor data.

Then, the USPS API was abandoned in favor of Smarty. There were a few reasons for this:
1. The USPS API had recently changed to no longer having a free option, forcing us to consider other options
2. The USPS API returns addresses in ALL CAPS, which was not desirable
3. DonorDock already uses the Smarty API for autocompleting manually-entered addresses, so using Smarty for validation

## Files

### clean_dd.py
Hosts most of the useful functions for processing a contact. Also contains a main method that processes contacts by creation date.

### 

## Challenges and things learned

- DonorDock API does not expose County via API, despite it being in their data. However, if a field is blank, it doesn't seem to overwrite any existing fields when imported into DonorDock.
- USPS API makes addresses into **ALL CAPS**, which looks very weird, and the API is not intended to be used for cleaning databases.
- Smarty API will consider ANY address to be valid if it has what's known as a [unique zipcode](https://www.smarty.com/articles/unique-zip-codes). It will even tell you that the address is *in the USPS database*, even if it's completely bogus. To work around this, the script checks for addresses that are *deliverable*, basically meaning they are valid AND have been delivered to before.
- DonorDock API also does not expose Contact Status, so there is absolutely no way of knowing whether a contact that you request is Active or Inactive. If it's Inactive, that means it is not meant to be used.

## Diagrams

Diagrams created using Plant UML.

### Activity diagram of clean_from_list_of_ids execution
![Flowchart of donor data cleansing workflow. The process retrieves donor records from the DonorDock API, validates eligible addresses using Smarty, updates records with standardized addresses when a single deliverable match is found, flags invalid addresses and phone numbers, writes original and updated data to CSV files, and repeats for each donor record until all records have been processed.](https://www.plantuml.com/plantuml/png/RP91Rjj034NtSug_b86W1x0MJOfikcXG8Bq0BL8MqT6CmA4KkwUlHrF3HT6D896V3_zJV2vEvkiSGzZVmd5POyIeLXpAVGWcYz2jVXO7anD6opDUSyhsceUVUFd-zQRI4Tr41SHiKieJj40JwwQyKdm29KRAVfjxo_wUemxgdm_mIHAwgvH308v54jy9y8ptcSolVG0gNYuqUBmY9y5CFaoDgWKiKJSnEaNv1tc3hWkJor_ODbof4ekWI_cFieZZ2_7BG_d3Ljc5YNKCxHcEv2xpubKmP3CP7CjKNQLrFecLVj_6Hb7v7h5zxI7_Dr9HnIan6UilOOpPPl8-t1qw7e1gqoJAHianHZfNqzz8qrjZPTiB-QHHMkaHvHxXmzG5sVIiYMBjdsJC9f-6ikrRRLlZsg7HnMgZRyU199Ts6-qqy35f57IjN2DhgNzBYvS3glUkhkjwg2UMbn2U9V4wnzy0)
