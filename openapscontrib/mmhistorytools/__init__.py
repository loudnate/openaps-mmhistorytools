"""
mmhistorytools - tools for cleaning, condensing, and reformatting history data


"""

import argparse
from dateutil import parser as dateparser
import json
import sys

from openaps.uses.use import Use

from historytools import CleanHistory, ReconcileHistory


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
    return [clean, reconcile]


class BaseUse(Use):
    def get_params(self, args):
        return dict(infile=args.infile)

    def configure_app(self, app, parser):
        parser.add_argument(
            'infile',
            type=argparse.FileType('r'),
            default=sys.stdin,
            help='JSON-encoded history data'
        )


class clean(BaseUse):
    """Resolve inconsistencies from a sequence of pump history

Tasks performed by this pass:
 - De-duplicates BolusWizard records
 - Creates PumpSuspend and PumpResume records to complete missing pairs
 - Removes any records whose timestamps don't fall into the specified window
    """
    def get_params(self, args):
        params = super(clean, self).get_params(args)
        params.update(start_datetime=args.start, end_datetime=args.end)

        return params

    def configure_app(self, app, parser):
        super(clean, self).configure_app(app, parser)

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

        tool = CleanHistory(json.load(params.pop('infile')), **params)

        return tool.clean_history


class reconcile(BaseUse):
    """Reconcile record dependencies from a sequence of pump history

Tasks performed by this pass:
 - Modifies temporary basal duration to account for cancelled and overlapping basals
 - Duplicates and modifies temporary basal records to account for delivery pauses when suspended
    """
    def main(self, args, app):
        params = self.get_params(args)

        tool = ReconcileHistory(json.load(params.pop('infile')))

        return tool.reconciled_history
