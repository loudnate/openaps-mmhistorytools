"""
mmhistorytools - tools for cleaning, condensing, and reformatting history data


"""
from .version import __version__

import argparse
from dateutil.parser import parse
import json
import sys

from openaps.uses.use import Use

from historytools import CleanHistory, ReconcileHistory, ResolveHistory, NormalizeRecords


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
    return [clean, reconcile, resolve, normalize]


def _opt_date(timestamp):
    """Parses a date string if defined

    :param timestamp: The date string to parse
    :type timestamp: basestring
    :return: A datetime object if a timestamp was specified
    :rtype: datetime.datetime|NoneType
    """
    if timestamp is not None:
        return parse(timestamp)


def _opt_json_file(filename):
    """Parses a filename as JSON input if defined

    :param filename: The path to the file to parse
    :type filename: basestring
    :return: A decoded JSON object if a filename was specified
    :rtype: dict|list|NoneType
    """
    if filename is not None:
        return json.load(argparse.FileType('r')(filename))


class BaseUse(Use):
    def get_params(self, args):
        return dict(infile=argparse.FileType('r')(args.infile))

    def configure_app(self, app, parser):
        """Define command arguments.

        Only primitive types should be used here to allow for serialization and partial application
        in via openaps-report.
        """
        parser.add_argument(
            'infile',
            nargs='?',
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
        params.update(start_datetime=_opt_date(args.start), end_datetime=_opt_date(args.end))

        return params

    def configure_app(self, app, parser):
        super(clean, self).configure_app(app, parser)

        parser.add_argument(
            '--start',
            default=None,
            help='The initial timestamp of the window to return'
        )
        parser.add_argument(
            '--end',
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


class resolve(BaseUse):
    """Converts events in a sequence of pump history to generalized record types

Each record is a dictionary representing one of the following types, as denoted by the "type" key:
- `Bolus`: Insulin delivery events in Units, or Units/hour
- `Meal`: Grams of carbohydrate
- `TempBasal`: Paced insulin delivery events in Units/hour, or Percent of scheduled basal
The following history events are parsed:
- TempBasal and TempBasalDuration are combined into TempBasal records
- PumpSuspend and PumpResume are combined into TempBasal records of 0%
- Square Bolus is converted to a Bolus record
- Normal Bolus is converted to a Bolus record
- BolusWizard carb entry is converted to a Meal record
- JournalEntryMealMarker is converted to a Meal record
Events that are not related to the record types or seem to have no effect are dropped.
"""

    def get_params(self, args):
        params = super(resolve, self).get_params(args)
        params.update(current_datetime=_opt_date(args.now))

        return params

    def configure_app(self, app, parser):
        super(resolve, self).configure_app(app, parser)

        parser.add_argument(
            '--now',
            default=None,
            help='The timestamp of when the history sequence was read'
        )

    def main(self, args, app):
        params = self.get_params(args)

        tool = ResolveHistory(json.load(params.pop('infile')), **params)

        return tool.resolved_records


class normalize(BaseUse):
    """Adjusts the time and amount of records relative to a basal schedule and a timestamp

If `--basal-profile` is provided, the TempBasal `amount` is replaced with a relative dose in
Units/hour. A single TempBasal record might split into multiple records to account for boundary
crossings in the basal schedule.
If `--zero-at` is provided, the values for the `start_at` and `end_at` keys are replaced with signed
integers representing the number of minutes from `--zero-at`.
"""

    def get_params(self, args):
        params = super(normalize, self).get_params(args)
        params.update(
            basal_schedule=_opt_json_file(args.basal_profile),
            zero_datetime=_opt_date(args.zero_at)
        )

        return params

    def configure_app(self, app, parser):
        super(normalize, self).configure_app(app, parser)

        parser.add_argument(
            '--basal-profile',
            default=None,
            help='A file containing a basal profile by which to adjust TempBasal records'
        )

        parser.add_argument(
            '--zero-at',
            default=None,
            help='The timestamp by which to adjust record timestamps'
        )

    def main(self, args, app):
        params = self.get_params(args)

        tool = NormalizeRecords(
            json.load(params.pop('infile')),
            **params
        )

        return tool.normalized_records

