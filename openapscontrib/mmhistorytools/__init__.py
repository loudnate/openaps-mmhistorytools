"""
mmhistorytools - tools for cleaning, condensing, and reformatting history data
"""

import argparse
from dateutil import parser as dateparser
import json
import sys

from openaps.uses.use import Use

from historytools import HistoryCleanup


# set_config is needed by openaps for all vendors.
# set_config is used by `device add` commands so save any needed
# information.
# See the medtronic builtin module for an example of how to use this
# to save needed information to establish sessions (serial numbers,
# etc).
def set_config(args, device):
    # no special config
    return


# display_device allows our custom vendor implementation to include
# special information when displaying information about a device using
# our plugin as a vendor.
def display_device(device):
    # no special information needed to run
    return ''


# openaps calls get_uses to figure out how how to use a device using
# agp as a vendor.  Return a list of classes which inherit from Use,
# or are compatible with it:
def get_uses(device, config):
    # make an Example, openaps use command
    # add your Uses here!
    return [cleanup]


class cleanup(Use):
    """Removes inconsistencies from a sequence of pump history

Tasks performed by this pass:
 - De-duplicates BolusWizard records
 - Creates PumpSuspend and PumpResume records to complete missing pairs
 - Removes any records whose timestamps don't fall into the specified window
 - Adjusts TempBasalDuration records for overlapping entries
    """
    def get_params(self, args):
        return dict(infile=args.infile, start_datetime=args.start, end_datetime=args.end)

    def configure_app(self, app, parser):
        parser.add_argument(
            'infile',
            nargs='?',
            type=argparse.FileType('r'),
            default=sys.stdin,
            help='JSON-encoded history data to clean'
        )
        parser.add_argument(
            '--start',
            type=dateparser.parse,
            default=None,
            help='The initial timestamp of the window to return'
        )
        parser.add_argument(
            '--end',
            type=dateparser.parse,
            default=None,
            help='The final timestamp of the window to return'
        )

    def main(self, args, app):
        params = self.get_params(args)

        tool = HistoryCleanup(json.load(params.pop('infile')), **params)

        return tool.clean_history
