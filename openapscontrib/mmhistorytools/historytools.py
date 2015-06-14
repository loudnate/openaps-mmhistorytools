from collections import defaultdict
from datetime import timedelta
from dateutil import parser


class HistoryCleanup(object):
    """
    Responsibilities:
    - Adjusts temporary basal duration for cancelled temp basals and suspends
    - De-duplicates bolus wizard entries
    - Ensures suspend/resume records exist in pairs (inserting an extra event as necessary)
    - Removes any records not in the start_datetime to end_datetime window
    """
    def __init__(self, pump_history, start_datetime=None, end_datetime=None):
        """Initializes a new instance of the Medtronic pump history cleanup parser

        :param pump_history: A list of pump history events, in reverse-chronological order
        :type pump_history: list(dict)
        :param start_datetime: The start time of history events. If not provided, the oldest record's timestamp is used
        :type start_datetime: datetime
        :param end_datetime: The end time of history events. If not provided, the latest record's timestamp is used
        :type end_datetime: datetime
        """
        self.clean_history = []
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime

        if len(pump_history) > 0:
            if self.start_datetime is None:
                self.start_datetime = parser.parse(pump_history[-1]["timestamp"])

            if self.end_datetime is None:
                self.end_datetime = parser.parse(pump_history[0]["timestamp"])

        # Temporary parsing state
        self._boluswizard_events_by_body = defaultdict(list)
        self._last_resume_event = None
        self._last_temp_basal_duration_event = None
        self._last_temp_basal_start_datetime = None

        for event in pump_history:
            self.add_history_event(event)

        # The pump was suspended before the history window began
        if self._last_resume_event is not None:
            self.add_history_event({
                "_type": "PumpSuspend",
                "timestamp": self.start_datetime.isoformat()
            })

    def _filter_events_in_range(self, events):
        start_datetime = self.start_datetime
        end_datetime = self.end_datetime

        def timestamp_in_range(event):
            if event:
                timestamp = parser.parse(event["timestamp"])
                if start_datetime <= timestamp <= end_datetime:
                    return True
            return False

        return filter(timestamp_in_range, events)

    def add_history_event(self, event):
        try:
            decoded = getattr(self, "_decode_{}".format(event["_type"].lower()))(event)
        except AttributeError:
            decoded = [event]

        self.clean_history.extend(self._filter_events_in_range(decoded or []))

    def _decode_boluswizard(self, event):
        event_datetime = parser.parse(event["timestamp"])

        # BolusWizard records can appear as duplicates with one containing appended data.
        # Criteria are records are less than 1 min apart and have identical bodies
        for seen_event in self._boluswizard_events_by_body[event["_body"]]:
            if abs(parser.parse(seen_event["timestamp"]) - event_datetime) <= timedelta(minutes=1):
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
            self._resume_datetime = None

        return events

    def _decode_tempbasal(self, event):
        assert self._last_temp_basal_duration_event["timestamp"] == event["timestamp"], \
            "Partial temp basal record found. Please re-run with a larger history window."

        return [event]

    def _decode_tempbasalduration(self, event):
        duration_in_minutes_key = "duration (min)"

        start_datetime = parser.parse(event["timestamp"])
        end_datetime = start_datetime + timedelta(minutes=event[duration_in_minutes_key])

        # Since only one tempbasal runs at a time, we may have to revise the last one we entered
        if self._last_temp_basal_duration_event is not None:
            last_start_datetime = parser.parse(self._last_temp_basal_duration_event["timestamp"])

            if last_start_datetime < end_datetime:
                end_datetime = last_start_datetime
                event[duration_in_minutes_key] = int(
                    (end_datetime - start_datetime).total_seconds() / 60.0
                )

        self._last_temp_basal_duration_event = event

        return [event]
