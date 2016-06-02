import argparse
import csv
import sys
import requests
import meraki_admins

"""CSV reader for the Meraki Admins wrapper library."""


DESCRIPTION = """ Bulk add admins to a Meraki Dashboard account from a .csv file

Files should be comma-separated and must contain the following,
case-sensitive, column headers:

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
PARSER.add_argument('csv', help='input file', type=argparse.FileType('rU'))
PARSER.add_argument('api key', help='API key of an admin adding the accounts.')
PARSER.add_argument('-no-confirm',
                    help='Don\'t print list of admins to be added, nor prompt \
                    for confirmation before executing.', action="store_true")

args = PARSER.parse_args()

def __validate_fields(fields):
    for item in fields:
        if item not in VALID_FIELDS:
            raise ValueError("Unexpected field name %s" % fields)

def __network_tag_formatter(row):
    tag_name = row.pop('tag', None)
    tag_access = row.pop('tagaccess', None)
    formatted_tags = [{"tag":tag_name, "access":tag_access}]
    row['tags'] = formatted_tags

    net_name = row.pop('networkid', None)
    net_access = row.pop('networkaccess', None)
    formatted_net = [{"id":net_name, "access":net_access}]
    row['networks'] = formatted_net

    return row



def main():

    queue = {}
    operations = {"add": meraki_admins.add_admin,
                  "modify": meraki_admins.update_admin,
                  "delete": meraki_admins.del_admin}

    with open(args.csv, 'rU') as data:
        try:
            __validate_fields(csv.DictReader(data).fieldnames)
            # Build a list of user objects keyed to the corresponding OrgID
            for row in csv.DictReader(data):
                org_id = row.pop('orgid')
                queue.setdefault(org_id, [])
                row = __network_tag_formatter(row)
                queue[org_id].append(row)

        except (StopIteration, csv.Error):
            # intentionally not catching the ValueError raise here
            print "ERROR: Invalid CSV format or non-CSV file."
            sys.exit(1)
        except KeyError:
            print "ERROR: orgid not found in CSV column headers."
            sys.exit(1)


if __name__ == '__main__':
    main()
    sys.exit(0)
