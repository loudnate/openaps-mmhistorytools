"""
mmhistorytools - tools for cleaning, condensing, and reformatting history data


"""
from .version import __version__

import argparse
from dateutil.parser import parse
import json

from openaps.uses.use import Use

from historytools import TrimHistory, CleanHistory, ReconcileHistory
from historytools import ResolveHistory, NormalizeRecords
from historytools import AppendDoseToHistory
from historytools import append_reservoir_entry_to_history
from historytools import convert_reservoir_history_to_temp_basal


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
    return [
        trim,
        clean,
        reconcile,
        resolve,
        normalize,
        prepare,
        append_dose,
        append_reservoir,
        resolve_reservoir
    ]


def _opt_date(timestamp):
    """Parses a date string if defined

    :param timestamp: The date string to parse
    :type timestamp: basestring
    :return: A datetime object if a timestamp was specified
    :rtype: datetime.datetime|NoneType
    """
    if timestamp:
        return parse(timestamp)


def _opt_json_file(filename):
    """Parses a filename as JSON input if defined

    :param filename: The path to the file to parse
    :type filename: basestring
    :return: A decoded JSON object if a filename was specified
    :rtype: dict|list|NoneType
    """
    if filename:
        return json.load(argparse.FileType('r')(filename))


def _opt_date_or_json_file(value):
    try:
        return _opt_date(_opt_json_file(value))
    except argparse.ArgumentTypeError:
        return _opt_date(value)


class BaseUse(Use):
    def configure_app(self, app, parser):
        """Define command arguments.

        Only primitive types should be used here to allow for serialization and partial application
        in via openaps-report.
        """
        parser.add_argument(
            'infile',
            nargs=argparse.OPTIONAL,
            default='-',
            help='JSON-encoded history data'
        )

    def get_params(self, args):
        return dict(infile=args.infile)

    def get_program(self, params):
        """Parses params into history parser constructor arguments

        :param params:
        :type params: dict
        :return:
        :rtype: tuple(list, dict)
        """
        return [json.load(argparse.FileType('r')(params['infile']))], dict()


# noinspection PyPep8Naming
class trim(BaseUse):
    """Trims a sequence of pump history to a specified time window"""

    def configure_app(self, app, parser):
        super(trim, self).configure_app(app, parser)

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
        parser.add_argument(
            '--duration',
            default=None,
            help='The length of the window to return, in hours'
        )

    def get_params(self, args):
        params = super(trim, self).get_params(args)

        args_dict = dict(**args.__dict__)

        for key in ('start', 'end', 'duration'):
            value = args_dict.get(key)
            if value is not None:
                params[key] = value

        return params

    def get_program(self, params):
        args, kwargs = super(trim, self).get_program(params)

        kwargs.update(
            start_datetime=_opt_date_or_json_file(params.get('start')),
            end_datetime=_opt_date_or_json_file(params.get('end')),
            duration_hours=float(params['duration']) if 'duration' in params else None
        )

        return args, kwargs

    def main(self, args, app):
        args, kwargs = self.get_program(self.get_params(args))

        tool = TrimHistory(*args, **kwargs)

        return tool.trimmed_history


# noinspection PyPep8Naming
class clean(BaseUse):
    """Resolve inconsistencies from a sequence of pump history

Tasks performed by this pass:
 - De-duplicates BolusWizard records
 - Creates PumpSuspend and PumpResume records to complete missing pairs
    """
    def configure_app(self, app, parser):
        super(clean, self).configure_app(app, parser)

        parser.add_argument(
            '--start',
            default=None,
            help='The initial timestamp of the known window, used to simulate missing '
                 'suspend/resume events'
        )
        parser.add_argument(
            '--end',
            default=None,
            help='The final timestamp of the history window, used to simulate missing '
                 'suspend/resume events'
        )

    def get_params(self, args):
        params = super(clean, self).get_params(args)

        if 'start' in args and args.start:
            params.update(start=args.start)

        if 'end' in args and args.end:
            params.update(end=args.end)

        return params

    def get_program(self, params):
        args, kwargs = super(clean, self).get_program(params)
        kwargs.update(
            start_datetime=_opt_date(params.get('start')),
            end_datetime=_opt_date(params.get('end'))
        )

        return args, kwargs

    def main(self, args, app):
        args, kwargs = self.get_program(self.get_params(args))

        tool = CleanHistory(*args, **kwargs)

        return tool.clean_history


# noinspection PyPep8Naming
class reconcile(BaseUse):
    """Reconcile record dependencies from a sequence of pump history

Tasks performed by this pass:
 - Modifies temporary basal duration to account for cancelled and overlapping basals
 - Duplicates and modifies temporary basal records to account for delivery pauses when suspended
    """
    def main(self, args, app):
        args, _ = self.get_program(self.get_params(args))

        tool = ReconcileHistory(*args)

        return tool.reconciled_history


# noinspection PyPep8Naming
class resolve(BaseUse):
    """Converts events in a sequence of pump history to generalized record types

Each record is a dictionary representing one of the following types, as denoted by the "type" key:
- `Bolus`: Insulin delivery events in Units, or Units/hour
- `Meal`: Grams of carbohydrate
- `TempBasal`: Paced insulin delivery events in Units/hour, or Percent of scheduled basal
- `Exercise`: Exercise event
_
The following history events are parsed:
- TempBasal and TempBasalDuration are combined into TempBasal records
- PumpSuspend and PumpResume are combined into TempBasal records of 0%
- Square Bolus is converted to a Bolus record
- Normal Bolus is converted to a Bolus record
- BolusWizard carb entry is converted to a Meal record
- JournalEntryMealMarker is converted to a Meal record
- JournalEntryExerciseMarker is converted to an Exercise record
_
Events that are not related to the record types or seem to have no effect are dropped.
"""
    def main(self, args, app):
        args, _ = self.get_program(self.get_params(args))

        tool = ResolveHistory(*args)

        return tool.resolved_records


# noinspection PyPep8Naming
class normalize(BaseUse):
    """Adjusts the time and amount of records relative to a basal schedule and a timestamp

If `--basal-profile` is provided, the TempBasal `amount` is replaced with a relative dose in
Units/hour. A single TempBasal record might split into multiple records to account for boundary
crossings in the basal schedule.
_
If `--zero-at` is provided, the values for the `start_at` and `end_at` keys are replaced with signed
integers representing the number of minutes from `--zero-at`.
"""
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
            help='The timestamp by which to adjust record timestamps. This can be either a '
                 'filename to a read_clock report or a timestamp string value.'
        )

    def get_params(self, args):
        params = super(normalize, self).get_params(args)
        if 'basal_profile' in args and args.basal_profile:
            params.update(basal_profile=args.basal_profile)

        if 'zero_at' in args and args.zero_at:
            params.update(zero_at=args.zero_at)

        return params

    def get_program(self, params):
        args, kwargs = super(normalize, self).get_program(params)

        zero_at = params.get('zero_at')

        try:
            zero_at = _opt_json_file(zero_at)
        except argparse.ArgumentTypeError:
            pass

        kwargs.update(
            basal_schedule=_opt_json_file(params.get('basal_profile')),
            zero_datetime=_opt_date(zero_at)
        )

        return args, kwargs

    def main(self, args, app):
        args, kwargs = self.get_program(self.get_params(args))

        tool = NormalizeRecords(*args, **kwargs)

        return tool.normalized_records


# noinspection PyPep8Naming
class append_dose(BaseUse):
    """Appends a dose record to a sequence of cleaned history

The expected dose record format is a dictionary with a key named "recieved" (sic).
If that key isn't present, or its value is false, the record is ignored.
"""

    def configure_app(self, app, parser):
        super(append_dose, self).configure_app(app, parser)

        parser.add_argument(
            '--dose',
            help='JSON-encoded dosing report'
        )

        parser.add_argument(
            '--resolve',
            action='store_true',
            help='Resolve the dose before appending'
        )

    def get_params(self, args):
        params = super(append_dose, self).get_params(args)

        args_dict = dict(**args.__dict__)

        for key in ('dose', 'resolve'):
            value = args_dict.get(key)
            if value:
                params[key] = value

        return params

    def get_program(self, params):
        args, kwargs = super(append_dose, self).get_program(params)

        args.append(_opt_json_file(params['dose']))

        if params.get('resolve'):
            kwargs['should_resolve_doses'] = True

        return args, kwargs

    def main(self, args, app):
        args, kwargs = self.get_program(self.get_params(args))

        tool = AppendDoseToHistory(*args, **kwargs)

        return tool.appended_history


# noinspection PyPep8Naming
class prepare(BaseUse):
    """Runs a sequence of commands to prepare history for use in prediction and dosing.

This command performs the following commands in sequence:
[clean] -> [reconcile] -> [resolve] -> [normalize:basal-profile]
_
Please refer to the --help documentation of each command for more information.
_
Warning: This command will not return the same level of diagnostic logging as
running all four commands separately. If there is reason to believe an issue
has occurred, output from this command may not be sufficient for debugging.
"""

    def configure_app(self, app, parser):
        super(prepare, self).configure_app(app, parser)

        parser.add_argument(
            '--basal-profile',
            default=None,
            help='A file containing a basal profile by which to adjust TempBasal records'
        )

    def get_params(self, args):
        params = super(prepare, self).get_params(args)
        if 'basal_profile' in args and args.basal_profile:
            params.update(basal_profile=args.basal_profile)

        return params

    def get_program(self, params):
        args, kwargs = super(prepare, self).get_program(params)

        kwargs.update(
            basal_schedule=_opt_json_file(params.get('basal_profile'))
        )

        return args, kwargs

    def main(self, args, app):
        args, kwargs = self.get_program(self.get_params(args))

        clean_history = CleanHistory(*args).clean_history
        reconciled_history = ReconcileHistory(clean_history).reconciled_history
        resolved_records = ResolveHistory(reconciled_history).resolved_records
        normalized_records = NormalizeRecords(resolved_records, **kwargs).normalized_records

        return normalized_records


# noinspection PyPep8Naming
class append_reservoir(BaseUse):
    """Appends a reservoir value and clock time to a sequence of history
    """

    def configure_app(self, app, parser):
        super(append_reservoir, self).configure_app(app, parser)

        parser.add_argument(
            'reservoir',
            help='JSON-encoded reservoir value file'
        )

        parser.add_argument(
            '--clock',
            help='The timestamp at which temp basal dosing should be assumed to end, '
                 'as a JSON-encoded pump clock file'
        )

        parser.add_argument(
            '--hours',
            nargs=argparse.OPTIONAL,
            help='The length of history to keep, in hours'
        )

    def get_params(self, args):
        params = super(append_reservoir, self).get_params(args)

        args_dict = dict(**args.__dict__)

        for key in ('reservoir', 'clock', 'hours'):
            value = args_dict.get(key)
            if value is not None:
                params[key] = value

        return params

    def get_program(self, params):
        args, kwargs = super(append_reservoir, self).get_program(params)

        args += [
            float(_opt_json_file(params.get('reservoir'))),
            parse(_opt_json_file(params.get('clock')))
        ]

        if params.get('hours'):
            kwargs.update(
                lookback_hours=float(params['hours'])
            )

        return args, kwargs

    def main(self, args, app):
        args, kwargs = self.get_program(self.get_params(args))

        return append_reservoir_entry_to_history(*args, **kwargs)


# noinspection PyPep8Naming
class resolve_reservoir(BaseUse):
    """Converts a sequence of pump reservoir history to temporary basal records
    """

    def main(self, args, app):
        args, _ = self.get_program(self.get_params(args))

        return convert_reservoir_history_to_temp_basal(*args)
