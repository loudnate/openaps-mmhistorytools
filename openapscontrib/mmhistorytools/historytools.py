from collections import defaultdict
from copy import copy
from datetime import datetime
from datetime import timedelta
from datetime import time
from dateutil import parser

from .models import Bolus, Meal, TempBasal, Exercise, Unit


class ParseHistory(object):
    DURATION_IN_MINUTES_KEY = "duration (min)"

    @staticmethod
    def _event_datetime(event):
        return parser.parse(event["timestamp"])

    def _resolve_tempbasal(self, event, duration):
        start_at = self._event_datetime(event)
        end_at = start_at + timedelta(minutes=duration)

        if end_at > start_at:
            amount = event["rate"]
            unit = Unit.percent_of_basal if event["temp"] == "percent" else Unit.units_per_hour

            return TempBasal(
                start_at=start_at,
                end_at=end_at,
                amount=amount,
                unit=unit,
                description="TempBasal: {}{} over {:d}min".format(
                    amount,
                    '%' if unit == Unit.percent_of_basal else unit,
                    int(round(duration))
                )
            )


class TrimHistory(ParseHistory):
    """Trims a list of historical entries to a specified time window"""
    def __init__(self, history, start_datetime=None, end_datetime=None, duration_hours=None):
        super(TrimHistory, self).__init__()

        if len(history) > 0:
            if start_datetime is None and end_datetime is not None and duration_hours is not None:
                start_datetime = end_datetime - timedelta(hours=duration_hours)
            elif start_datetime is not None and end_datetime is None and duration_hours is not None:
                end_datetime = start_datetime + timedelta(hours=duration_hours)

            if start_datetime is None:
                start_datetime = self._event_datetime(history[-1], 'start_at')

            if end_datetime is None:
                end_datetime = self._event_datetime(history[0], 'end_at')

        self.trimmed_history = []
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime

        self.trimmed_history.extend(self._filter_events_in_range(history))

    @staticmethod
    def _event_datetime(event, *args):
        for key in args + ('dateString', 'display_time', 'date', 'timestamp'):
            value = event.get(key)
            if value:
                try:
                    return parser.parse(value)
                except ValueError:
                    pass

        raise ValueError

    def _filter_events_in_range(self, events):
        start_datetime = self.start_datetime
        end_datetime = self.end_datetime

        def timestamp_in_range(event):
            if event:
                try:
                    start_timestamp = self._event_datetime(event, 'end_at')
                    end_timestamp = self._event_datetime(event, 'start_at')
                except ValueError:
                    return True
                else:
                    if start_datetime <= start_timestamp and end_timestamp <= end_datetime:
                        return True
            return False

        return filter(timestamp_in_range, events)


class CleanHistory(ParseHistory):
    """Analyze Medtronic pump history and resolves basic inconsistencies

    Responsibilities:
    - De-duplicates bolus wizard entries
    - Ensures suspend/resume records exist in pairs (inserting an extra event as necessary)
    """
    def __init__(self, trimmed_history, start_datetime=None, end_datetime=None):
        """Initializes a new instance of the history parser

        :param trimmed_history: A list of pump history events, in reverse-chronological order
        :type trimmed_history: list(dict)
        :param start_datetime: The start time of history events. If not provided, the oldest
        record's timestamp is used
        :type start_datetime: datetime
        :param end_datetime: The end time of history events. If not provided, the latest record's
        timestamp is used
        :type end_datetime: datetime
        """
        self.clean_history = []
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime

        if len(trimmed_history) > 0:
            if self.start_datetime is None:
                self.start_datetime = self._event_datetime(trimmed_history[-1])

            if self.end_datetime is None:
                self.end_datetime = self._event_datetime(trimmed_history[0])

        # Temporary parsing state
        self._boluswizard_events_by_body = defaultdict(list)
        self._last_resume_event = None
        self._last_temp_basal_duration_event = None

        for event in trimmed_history:
            self.add_history_event(event)

        # The pump was suspended before the history window began
        if self._last_resume_event is not None:
            self.add_history_event({
                "_type": "PumpSuspend",
                "timestamp": self.start_datetime.isoformat()
            })

    def add_history_event(self, event):
        try:
            decoded = getattr(self, "_decode_{}".format(event["_type"].lower()))(event)
        except AttributeError:
            decoded = [event]

        self.clean_history.extend(decoded or [])

    def _decode_boluswizard(self, event):
        event_datetime = self._event_datetime(event)

        # BolusWizard records can appear as duplicates with one containing appended data.
        # Criteria are records are less than 1 min apart and have identical bodies
        for seen_event in self._boluswizard_events_by_body[event["_body"]]:
            if abs(self._event_datetime(seen_event) - event_datetime) <= timedelta(minutes=1):
                return None

        self._boluswizard_events_by_body[event["_body"]].append(event)

        return [event]

    def _decode_pumpresume(self, event):
        self._last_resume_event = event

        return [event]

    def _decode_pumpsuspend(self, event):
        events = [event]

        if self._last_resume_event is None:
            events.insert(0, {
                "_type": "PumpResume",
                "timestamp": self.end_datetime.isoformat(),
            })
        else:
            self._last_resume_event = None

        return events

    def _decode_tempbasal(self, event):
        assert self._last_temp_basal_duration_event["timestamp"] == event["timestamp"], \
            "Partial temp basal record found. Please re-run with a larger history window."

        return [event]

    def _decode_tempbasalduration(self, event):
        self._last_temp_basal_duration_event = event

        return [event]


class ReconcileHistory(ParseHistory):
    """Analyze Medtronic pump history and reconciles dependencies between records

    Responsibilities:
    - Modifies temporary basal duration to account for cancelled and overlapping basals
    - Duplicates and modifies temporary basal records to account for delivery pauses when suspended
    """
    def __init__(self, clean_history):
        """Initializes a new instance of the history parser

        The input history is expected to have no open-ended suspend windows, which can be resolved
        by the CleanHistory class.

        :param clean_history: A list of pump history events in reverse-chronological order
        :type clean_history: list(dict)
        """
        self.reconciled_history = []

        # Temporary parsing state
        self._last_suspend_event = None
        self._last_temp_basal_event = None
        self._last_temp_basal_duration_event = None

        for event in reversed(clean_history):
            self.add_history_event(event)

    def add_history_event(self, event):
        try:
            decoded = getattr(self, "_decode_{}".format(event["_type"].lower()))(event)
        except AttributeError:
            decoded = [event]

        for decoded_event in decoded:
            self.reconciled_history.insert(0, decoded_event)

    def _basal_event_datetimes(self, basal_event):
        basal_start_datetime = self._event_datetime(basal_event)
        basal_end_datetime = basal_start_datetime + timedelta(
            minutes=basal_event[self.DURATION_IN_MINUTES_KEY]
        )
        return basal_start_datetime, basal_end_datetime

    def _trim_last_temp_basal_to_datetime(self, trim_datetime):
        if self._last_temp_basal_duration_event is not None:
            basal_event = self._last_temp_basal_duration_event
            basal_start_datetime, basal_end_datetime = self._basal_event_datetimes(basal_event)

            if basal_end_datetime > trim_datetime:
                basal_event[self.DURATION_IN_MINUTES_KEY] = (
                    trim_datetime - basal_start_datetime
                ).total_seconds() / 60.0

    def _decode_pumpresume(self, event):
        events = [event]

        if self._last_temp_basal_duration_event is not None:
            suspend_datetime = self._event_datetime(self._last_suspend_event)
            resume_datetime = self._event_datetime(event)
            basal_duration_event = self._last_temp_basal_duration_event
            _, basal_end_datetime = self._basal_event_datetimes(basal_duration_event)

            self._trim_last_temp_basal_to_datetime(suspend_datetime)

            if basal_end_datetime > resume_datetime:
                # Duplicate and restart the temp basal still scheduled
                new_basal_duration_event = copy(basal_duration_event)
                new_basal_rate_event = copy(self._last_temp_basal_event)

                # Adjust start time
                for new_event in (new_basal_duration_event, new_basal_rate_event):
                    for key in ("_date", "timestamp"):
                        if key in event:
                            new_event[key] = event[key]
                    new_event["_description"] = "{} generated due to interleaved PumpSuspend" \
                                                " event".format(new_event["_type"])

                # Adjust duration
                new_basal_duration_event[self.DURATION_IN_MINUTES_KEY] = int(
                    (basal_end_datetime - resume_datetime).total_seconds() / 60.0
                )

                events.append(new_basal_rate_event)
                events.append(new_basal_duration_event)

        return events

    def _decode_pumpsuspend(self, event):
        self._last_suspend_event = event

        return [event]

    def _decode_tempbasal(self, event):
        self._last_temp_basal_event = event

        return [event]

    def _decode_tempbasalduration(self, event):
        self._trim_last_temp_basal_to_datetime(self._event_datetime(event))

        self._last_temp_basal_duration_event = event

        return [event]


class ResolveHistory(ParseHistory):
    """Converts Medtronic pump history to a sequence of general record types

    Each record is a dictionary representing one of the following types:

    - `Bolus`: Insulin delivery events in Units, or Units/hour
    - `Meal`: Grams of carbohydrate
    - `TempBasal`: Paced insulin delivery events in Units/hour, or Percent of scheduled basal
    - `Exercise`: Exercise event

    The following history events are parsed:

    - TempBasal and TempBasalDuration are combined into TempBasal records
    - PumpSuspend and PumpResume are combined into TempBasal records of 0%
    - Square Bolus is converted to a Bolus record
    - Normal Bolus is converted to a Bolus record
    - BolusWizard carb entry is converted to a Meal record
    - JournalEntryMealMarker is converted to a Meal record
    - JournalEntryExerciseMarker is converted to an Exercise record

    Events that are not related to the record types or seem to have no effect are dropped.
    """
    def __init__(self, reconciled_history):
        """Initializes a new instance of the history parser

        The input history is expected to have no open-ended suspend windows, which can be resolved
        by the CleanHistory class.

        :param reconciled_history: A list of pump history events in reverse-chronological order
        :type reconciled_history: list(dict)
        """
        self.resolved_records = []

        # Temporary parsing state
        self._resume_datetime = None
        self._suspend_datetime = None
        self._temp_basal_duration = None

        for event in reconciled_history:
            self.add_history_event(event)

    def add_history_event(self, event):
        try:
            decoded = getattr(self, "_decode_{}".format(event["_type"].lower()))(event)
        except AttributeError:
            pass
        else:
            if decoded is not None:
                self.resolved_records.append(decoded)

    def _decode_bolus(self, event):
        start_at = self._event_datetime(event)
        delivered = event["amount"]
        programmed = event["programmed"]

        if max(delivered, programmed) > 0:
            if event["type"] == "square":
                duration = event["duration"]
                rate = programmed / (duration / 60.0)
                end_at = start_at + timedelta(minutes=duration)

                # If the pump was suspended at any time during the bolus, adjust the duration
                # to reflect the delivered amount
                if self._suspend_datetime and end_at > self._suspend_datetime:
                    duration = int(duration * delivered / programmed)
                    end_at = start_at + timedelta(minutes=duration)
                    programmed = delivered

                return Bolus(
                    start_at=start_at,
                    end_at=end_at,
                    amount=rate,
                    unit=Unit.units_per_hour,
                    description="Square bolus: {}U over {}min".format(programmed, duration)
                )

            else:
                return Bolus(
                    start_at=start_at,
                    end_at=start_at,
                    amount=delivered,
                    unit=Unit.units,
                    description="Normal bolus: {}U".format(programmed)
                )

    def _decode_boluswizard(self, event):
        return self._decode_journalentrymealmarker(event)

    def _decode_journalentrymealmarker(self, event):
        carb_input = event["carb_input"]
        start_at = self._event_datetime(event)

        if carb_input:
            return Meal(
                start_at=start_at,
                end_at=start_at,
                amount=carb_input,
                unit=Unit.grams,
                description='{}: {}g'.format(event["_type"], carb_input)
            )

    def _decode_journalentryexercisemarker(self, event):
        num_events = 1
        start_at = self._event_datetime(event)

        return Exercise(
            start_at=start_at,
            end_at=start_at,
            amount=num_events,
            unit=Unit.event,
            description=event["_type"]
        )

    def _decode_pumpresume(self, event):
        self._resume_datetime = self._event_datetime(event)

    def _decode_pumpsuspend(self, event):
        assert self._resume_datetime is not None, "Unbalanced Suspend/Resume events found"

        start_at = self._event_datetime(event)
        end_at = self._resume_datetime

        self._resume_datetime = None
        self._suspend_datetime = start_at

        if end_at > start_at:
            return TempBasal(
                start_at=self._event_datetime(event),
                end_at=end_at,
                amount=0,
                unit=Unit.percent_of_basal,
                description="Pump Suspend"
            )

    def _decode_tempbasal(self, event):
        assert self._temp_basal_duration is not None, "Temp basal duration not found"

        return self._resolve_tempbasal(event, self._temp_basal_duration)

    def _decode_tempbasalduration(self, event):
        self._temp_basal_duration = event[self.DURATION_IN_MINUTES_KEY]


class NormalizeRecords(object):
    """Adjusts the time and basal amounts of records relative to a basal schedule and a timestamp

    If a `basal_schedule` is provided, the TempBasal `amount` is replaced with a relative dose in
    Units/hour. TempBasal records might be split into multiples to account for boundary crossings in
    the basal schedule.

    If a `zero_datetime` is provided, the values for the `start_at` and `end_at` keys are
    replaced with signed integers representing the number of minutes from zero.
    """
    def __init__(self, resolved_records, basal_schedule=None, zero_datetime=None):
        """Initializes a new instance of the record parser

        The record input is expected to be in the format returned by the ResolveHistory class.

        If `basal_schedule` or `zero_datetime` are not provided, than the record changes are not
        made.

        :param resolved_records: A list of pump records in reverse-chronological order
        :type resolved_records: list(.models.BaseRecord)
        :param basal_schedule: A list of basal rates scheduled by time in chronological order
        :type basal_schedule: list(dict)
        :param zero_datetime: The timestamp by which to center the relative times
        :type zero_datetime: datetime
        """
        self.normalized_records = []

        self.basal_schedule = basal_schedule

        for event in resolved_records:
            self.add_history_event(event)

        if zero_datetime is not None:
            for event in self.normalized_records:
                for key in [key for key in event.iterkeys() if key.endswith("_at")]:
                    event[key] = int(round((
                        parser.parse(event[key]) - zero_datetime
                    ).total_seconds() / 60))

    def add_history_event(self, event):
        try:
            decoded = getattr(self, "_decode_{}".format(event["type"].lower()))(event)
        except AttributeError:
            decoded = [event]

        self.normalized_records.extend(decoded or [])

    def _basal_rates_in_range(self, start_datetime, end_datetime):
        """Returns a list of the current basal rates effective between the specified times

        :param start_datetime:
        :type start_datetime: datetime
        :param end_datetime:
        :type end_datetime: datetime
        :return: A list of basal rates
        :rtype: list(dict)

        :raises AssertionError: The argument values are invalid
        """
        assert (start_datetime <= end_datetime)

        max_datetime = datetime.combine(start_datetime.date() + timedelta(days=1), time.min)

        if end_datetime > max_datetime:
            return self._basal_rates_in_range(start_datetime, max_datetime) + self._basal_rates_in_range(max_datetime, end_datetime)

        start_date = start_datetime.date()

        start_index = 0
        end_index = len(self.basal_schedule)

        for index, basal_rate in enumerate(self.basal_schedule):
            basal_start = datetime.combine(start_date, parser.parse(basal_rate["start"]).time())
            if start_datetime >= basal_start:
                start_index = index
            if end_datetime < basal_start:
                end_index = index
                break

        return map(lambda x: {
            "start": datetime.combine(start_datetime.date(), parser.parse(x["start"]).time()),
            "rate": x["rate"]
        }, self.basal_schedule[start_index:end_index])

    def _basal_adjustments_in_range(
            self,
            start_datetime,
            end_datetime,
            percent=None,
            absolute=None,
            description=""
    ):
        """Returns a list of TempBasal objects representing the specified adjustment to basal rate

        :param start_datetime: The start time of the basal adjustment
        :type start_datetime: datetime
        :param end_datetime: The end time of the basal adjustment
        :type end_datetime: datetime
        :param percent: A multiplier to apply to the current basal rate
        :type percent: int
        :param absolute: A specified temporary basal absolute, in U/hour
        :type absolute: float
        :param description: A description to attach to each new event
        :type description: basestring

        :return: A list of TempBasal objects
        :rtype: list(TempBasal)

        :raises AssertionError: The arguments are either missing or invalid
        """
        assert (start_datetime < end_datetime)
        assert (end_datetime - start_datetime < timedelta(hours=24))
        assert (percent is not None or absolute is not None)

        temp_basal_events = []
        basal_rates = self._basal_rates_in_range(start_datetime, end_datetime)

        for index, basal_rate in enumerate(basal_rates):
            # Find the delta of the new rate
            rate = absolute
            if percent is not None:
                rate = basal_rate["rate"] * percent / 100.0

            amount = rate - basal_rate["rate"]

            if index == 0:
                t0 = start_datetime
            else:
                t0 = basal_rate["start"]

            if index == len(basal_rates) - 1:
                t1 = end_datetime
            else:
                t1 = basal_rates[index + 1]["start"]

            if t1 - t0 > timedelta(minutes=0):
                temp_basal_events.insert(0, TempBasal(
                    start_at=t0,
                    end_at=t1,
                    amount=amount,
                    unit=Unit.units_per_hour,
                    description=description
                ))

        return temp_basal_events

    def _decode_tempbasal(self, event):
        if self.basal_schedule is not None:
            start_datetime = parser.parse(event["start_at"])
            end_datetime = parser.parse(event["end_at"])

            if end_datetime - start_datetime > timedelta(minutes=0):
                adjustment = "percent" if event["unit"] == Unit.percent_of_basal else "absolute"

                events = self._basal_adjustments_in_range(
                    start_datetime,
                    end_datetime,
                    description=event.get("description"),
                    **{adjustment: event["amount"]}
                )

                return events


class AppendDoseToHistory(ParseHistory):
    """Append a dose record or records to a list of history records.

    The expected dose record format is a dictionary with a key named "recieved" (sic).
    If that key isn't present, or its value is false, the record is ignored.
    """
    def __init__(self, clean_history, doses, should_resolve_doses=False):
        """Initializes a new instance of the history parser

        :param clean_history: A list of pump history events in reverse-chronological order
        :type clean_history: list(dict)
        :param doses: A single dose event, or a list of dose events in chronological order
        :type doses: list(dict)|dict
        :param should_resolve_doses: Whether the dose records should be resolved to match the input history
        :type should_resolve_doses: bool
        """
        self.appended_history = clean_history

        # Try to determine if the history input is already resolved
        self.should_resolve = should_resolve_doses or (len(clean_history) > 0 and 'start_at' in clean_history[0])

        if isinstance(doses, dict):
            doses = [doses]

        for event in doses:
            if self.was_event_received(event):
                # Determine if the dose duration should be modified on append.
                reconcile_with = None
                if self.should_resolve and \
                        event['type'] == 'TempBasal' and \
                        len(clean_history) > 0 and \
                        clean_history[0].get('type') == 'TempBasal':
                    reconcile_with = clean_history[0]

                    # Ignore out-of-date doses
                    if reconcile_with['start_at'] > event['timestamp']:
                        continue

                self.add_history_event(event)

                if reconcile_with is not None:
                    decoded_event = self.appended_history[0]
                    if decoded_event['start_at'] > reconcile_with['start_at']:
                        decoded_event['start_at'] = max(decoded_event['start_at'], reconcile_with.get('end_at'))

    @staticmethod
    def was_event_received(event):
        if event.get('recieved', False):
            return True
        else:
            try:
                return event['requested']['duration'] == event['duration']
            except (KeyError, TypeError):
                return False

    def add_history_event(self, event):
        try:
            decoded = getattr(self, '_decode_{}'.format(event['type'].lower()))(event)
        except AttributeError:
            decoded = [event]

        for decoded_event in decoded:
            self.appended_history.insert(0, decoded_event)

    def _decode_tempbasal(self, event):
        amount_event = copy(event)
        amount_event['_type'] = amount_event.pop('type')

        duration_event = copy(event)
        duration_event['_type'] = '{}Duration'.format(duration_event.pop('type'))
        duration_event[self.DURATION_IN_MINUTES_KEY] = duration_event.pop('duration')

        events = [amount_event, duration_event]

        if self.should_resolve:
            events = filter(None, [self._resolve_tempbasal(amount_event, duration_event[self.DURATION_IN_MINUTES_KEY])])

        return events


def append_reservoir_entry_to_history(history, reservoir, date, lookback_hours=4.0):
    """Append a reservoir value and clock time to a history of reservoir entries.

    :param history: The existing history of reservoir values, in chronological order
    :type history: list(dict)
    :param reservoir: The new reservoir value
    :type reservoir: float
    :param date: The current date
    :type date: datetime
    :param lookback_hours: The length of history to keep
    :type lookback_hours: float
    :return: A new list of historical reservoir values
    :rtype: list(dict)
    """
    history.append({
        'date': date.isoformat(),
        'amount': reservoir,
        'unit': Unit.units
    })

    start_at = (date - timedelta(hours=lookback_hours)).isoformat()

    return filter(lambda y: y['date'] >= start_at, history)


def convert_reservoir_history_to_temp_basal(history):
    """

    :param history: The history of reservoir values, in chronological order
    :type history: list(dict)
    :return: A list of resolved TempBasal doses
    :rtype: list(TempBasal)
    """
    # It takes a MM pump about 40s to deliver 1 Unit while bolusing
    # Source: http://www.healthline.com/diabetesmine/ask-dmine-speed-insulin-pumps#3
    # In addition, a basal rate of 30 U/hour would deliver 0.5 U/min
    max_drop_per_minute = 2.0
    last_entry = history[0]
    last_datetime = parser.parse(last_entry['date'])
    doses = []

    for entry in history[1:]:
        entry_datetime = parser.parse(entry['date'])
        volume_drop = last_entry['amount'] - entry['amount']
        minutes_elapsed = (entry_datetime - last_datetime).total_seconds() / 60.0

        if 0 <= volume_drop <= max_drop_per_minute * minutes_elapsed:
            doses.insert(
                0,
                TempBasal(
                    start_at=last_datetime,
                    end_at=entry_datetime,
                    amount=volume_drop * 60.0 / minutes_elapsed,
                    unit=Unit.units_per_hour,
                    description='Reservoir decreased {}U over {:.2f}min'.format(volume_drop, minutes_elapsed)
                )
            )

        last_entry = entry
        last_datetime = entry_datetime

    return doses
