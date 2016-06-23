import argparse
import csv
import pprint
import sys
import requests
import meraki_admins

"""CSV reader for the Meraki Admins wrapper library."""

# TODO: Argparse doesn't preserve spacing in block quotes; need to clean up
DESCRIPTION = """ Bulk add admins to a Meraki Dashboard account from a CSV file.

Files should be comma-separated and must contain the following column headers:

name
email
orgaccess - value must be full, read-only, or none (see optional headers below)

orgid - the name or ID of the Organization the user is to be added to; if the
provided name is non-unique, a prompt will be generated with the ID #'s.

operation - value must be add, modify, or delete

Files can also contain the following optional column pairs in their headers - if
orgaccess is none, at least one pair must be included:

networkid - the name or network ID (written as N_<ID number>) the user is to be
added to
networkaccess - value must be full, read-only, monitor-only, or guest-ambassador
tag - the name of the tag applied to networks to specify grouped access
tagaccess - see permitted values for NETWORKACCESS

If access for multiple tags or networks is to be specified, the CSV should
include them on additional, otherwise blank lines after the other information
for the speicifed user is provided.
"""
VALID_FIELDS = ['name', 'email', 'orgaccess', 'orgid', 'operation',
                'networkid', 'networkaccess', 'tag', 'tagaccess']


PARSER = argparse.ArgumentParser(description=DESCRIPTION)
PARSER.add_argument('csv', help='input file')
PARSER.add_argument('key', help='API key of an admin adding the accounts.')
PARSER.add_argument('-no-confirm',
                    help='Don\'t print list of admins to be added, nor prompt \
                    for confirmation before executing.', action="store_true")

ARGS = PARSER.parse_args()

def __validate_fields(fields):
    for item in fields:
        if item.lower() not in VALID_FIELDS:
            raise ValueError("Unexpected field name %s" % item)

def __network_tag_formatter(row):
    """Convert rows to data structures for network and tag-level access."""
    tag_name = row.pop('tag', None)
    tag_access = row.pop('tagaccess', None)
    formatted_tags = [{"tag":tag_name, "access":tag_access}]
    row['tags'] = formatted_tags

    net_name = row.pop('networkid', None)
    net_access = row.pop('networkaccess', None)
    formatted_net = [{"id":net_name, "access":net_access}]
    row['networks'] = formatted_net

    return row



def build_queue(user_file):
    """Build a list of user objects keyed to the corresponding OrgID
       in each row."""
    queue = {}


    with open(user_file, 'rU') as data:
        try:
            users = csv.DictReader(data)
            __validate_fields(users.fieldnames)
            for row in users:
                row = {k.lower():v for k, v in row.items()} # lowercase headers
                org_id = row.pop('orgid')
                queue.setdefault(org_id, [])
                row = __network_tag_formatter(row)
                queue[org_id].append(row)
            return queue

        except (StopIteration, csv.Error):
            # intentionally not catching the ValueError raise here
            print "ERROR: Invalid CSV format or non-CSV file."
            sys.exit(1)
        except KeyError:
            print "ERROR: Mandatory header orgid missing from CSV."
            sys.exit(1)

def submit_requests(queue, key=ARGS.key):
    """Submit queued requests to each Dashboard org contained within."""

    operations = {"add": meraki_admins.DashboardAdmins.add_admin,
                  "modify": meraki_admins.DashboardAdmins.update_admin,
                  "delete": meraki_admins.DashboardAdmins.del_admin}

    for oid, user_list in queue.items():
        submitter = meraki_admins.DashboardAdmins(oid, key)
        try:
            for user in user_list:
                operation = user.pop('operation')
                # Dashboard requires the param be camel cased
                user['orgAccess'] = user.pop('orgaccess')
                print "IN SUBMITTER"
                print user
                # TODO: Fix handler call for tags here as it's improperly
                # getting raised when checking org-level permissions
                operations[operation](submitter, **user)
        except KeyError:
            pass

def main():
    queue = build_queue(ARGS.csv)
    submit_requests(queue)


if __name__ == '__main__':
    main()
    sys.exit(0)
