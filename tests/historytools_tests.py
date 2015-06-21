from datetime import datetime
from datetime import time
from dateutil import parser
import json
import os
import sys
import unittest

from openapscontrib.mmhistorytools.historytools import CleanHistory
from openapscontrib.mmhistorytools.historytools import NormalizeRecords
from openapscontrib.mmhistorytools.historytools import ReconcileHistory
from openapscontrib.mmhistorytools.historytools import ResolveHistory
from openapscontrib.mmhistorytools.models import Bolus, Meal, TempBasal


def get_file_at_path(path):
    return "{}/{}".format(os.path.dirname(os.path.realpath(sys.argv[0])), path)


class CleanHistoryTestCase(unittest.TestCase):
    def test_duplicate_bolus_wizard_carbs(self):
        with open(get_file_at_path("fixtures/bolus_wizard_duplicates.json")) as fp:
            pump_history = json.load(fp)

        h = CleanHistory(pump_history)

        self.assertListEqual(
            [
                {
                    "_type": "BolusWizard",
                    "bg": 0,
                    "bg_target_high": 120,
                    "_description": "BolusWizard 2015-06-05T18:57:22 head[2], body[15] op[0x5b]",
                    "timestamp": "2015-06-05T18:57:22",
                    "_body": "0a50003c285a000040000000004078",
                    "_head": "5b00",
                    "unabsorbed_insulin_total": 0.0,
                    "correction_estimate": 0.0,
                    "date": 1433527042000.0,
                    "_date": "56b912650f",
                    "bolus_estimate": 1.6,
                    "bg_target_low": 90,
                    "carb_ratio": 8.0,
                    "food_estimate": 1.6,
                    "carb_input": 10,
                    "sensitivity": 40
                },
                {
                    "_type": "BolusWizard",
                    "bg": 0,
                    "bg_target_high": 120,
                    "_description": "BolusWizard 2015-06-05T18:54:43 head[2], body[15] op[0x5b]",
                    "timestamp": "2015-06-05T18:54:43",
                    "_body": "1e50003c285a0000c800000000c878",
                    "_head": "5b00",
                    "unabsorbed_insulin_total": 0.0,
                    "correction_estimate": 0.0,
                    "date": 1433526883000.0,
                    "_date": "6bb612650f",
                    "bolus_estimate": 5.0,
                    "bg_target_low": 90,
                    "carb_ratio": 8.0,
                    "food_estimate": 5.0,
                    "carb_input": 30,
                    "sensitivity": 40
                },
                {
                    "_type": "BolusWizard",
                    "bg": 0,
                    "bg_target_high": 120,
                    "_description": "BolusWizard 2015-06-05T18:44:54 head[2], body[15] op[0x5b]",
                    "timestamp": "2015-06-05T18:44:54",
                    "_body": "4150003c285a0001b000000001b078",
                    "_head": "5b00",
                    "unabsorbed_insulin_total": 0.0,
                    "correction_estimate": 0.0,
                    "date": 1433526294000.0,
                    "_date": "76ac12650f",
                    "bolus_estimate": 10.8,
                    "appended": [
                        {
                            "_type": "UnabsorbedInsulinBolus",
                            "_description": "UnabsorbedInsulinBolus unknown head[35], body[0] "
                                            "op[0x5c]",
                            "data": [
                                {
                                    "amount": 2.0,
                                    "age": 146
                                },
                                {
                                    "amount": 0.4,
                                    "age": 316
                                },
                                {
                                    "amount": 0.4,
                                    "age": 326
                                },
                                {
                                    "amount": 0.4,
                                    "age": 336
                                },
                                {
                                    "amount": 0.4,
                                    "age": 346
                                },
                                {
                                    "amount": 0.4,
                                    "age": 356
                                },
                                {
                                    "amount": 0.4,
                                    "age": 366
                                },
                                {
                                    "amount": 0.4,
                                    "age": 376
                                },
                                {
                                    "amount": 0.4,
                                    "age": 386
                                },
                                {
                                    "amount": 0.45,
                                    "age": 396
                                },
                                {
                                    "amount": 4.35,
                                    "age": 406
                                }
                            ],
                            "_body": "",
                            "_head": "5c23509204103c14104614105014105a141"
                                     "06414106e14107814108214128c14ae9614",
                            "_date": ""
                        }
                    ],
                    "bg_target_low": 90,
                    "carb_ratio": 8.0,
                    "food_estimate": 10.8,
                    "carb_input": 65,
                    "sensitivity": 40
                }
            ],
            [event for event in h.clean_history if event["_type"] == "BolusWizard"]
        )

    def test_resume_without_suspend(self):
        pump_history = [
            {
                "_type": "PumpResume",
                "_description": "PumpResume 2015-06-06T20:50:01 head[2], body[0] op[0x1f]",
                "date": 1433620201000.0,
                "timestamp": "2015-06-06T20:50:01",
                "_body": "",
                "_head": "1f20",
                "_date": "41b214060f"
            },
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T18:12:34"
            }
        ]

        h = CleanHistory(pump_history)

        self.assertListEqual(pump_history + [{
            "_type": "PumpSuspend",
            "timestamp": "2015-06-06T18:12:34"
        }], h.clean_history)

    def test_resume_without_suspend_with_range(self):
        pump_history = [
            {
                "_type": "PumpResume",
                "_description": "PumpResume 2015-06-06T20:50:01 head[2], body[0] op[0x1f]",
                "date": 1433620201000.0,
                "timestamp": "2015-06-06T20:50:01",
                "_body": "",
                "_head": "1f20",
                "_date": "41b214060f"
            },
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T18:12:34"
            }
        ]

        h = CleanHistory(pump_history, start_datetime=datetime(2015, 06, 06, 12, 56, 34))

        self.assertListEqual(pump_history + [{
            "_type": "PumpSuspend",
            "timestamp": "2015-06-06T12:56:34"
        }], h.clean_history)

    def test_suspend_without_resume(self):
        pump_history = [
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T22:12:34"
            },
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T21:12:34"
            },
            {
                "_type": "PumpSuspend",
                "_description": "PumpSuspend 2015-06-06T20:49:57 head[2], body[0] op[0x1e]",
                "date": 1433620197000.0,
                "timestamp": "2015-06-06T20:49:57",
                "_body": "",
                "_head": "1e01",
                "_date": "79b114060f"
            }
        ]

        h = CleanHistory(pump_history)

        self.assertListEqual(
            [
                {
                    "_type": "OtherEvent",
                    "timestamp": "2015-06-06T22:12:34"
                },
                {
                    "_type": "OtherEvent",
                    "timestamp": "2015-06-06T21:12:34"
                },
                {
                    "_type": "PumpResume",
                    "timestamp": "2015-06-06T22:12:34"
                },
                {
                    "_type": "PumpSuspend",
                    "_description": "PumpSuspend 2015-06-06T20:49:57 head[2], body[0] op[0x1e]",
                    "date": 1433620197000.0,
                    "timestamp": "2015-06-06T20:49:57",
                    "_body": "",
                    "_head": "1e01",
                    "_date": "79b114060f"
                }
            ],
            h.clean_history
        )

    def test_suspend_without_resume_with_range(self):
        pump_history = [
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T22:12:34"
            },
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T21:12:34"
            },
            {
                "_type": "PumpSuspend",
                "_description": "PumpSuspend 2015-06-06T20:49:57 head[2], body[0] op[0x1e]",
                "date": 1433620197000.0,
                "timestamp": "2015-06-06T20:49:57",
                "_body": "",
                "_head": "1e01",
                "_date": "79b114060f"
            }
        ]

        h = CleanHistory(pump_history, end_datetime=datetime(2015, 06, 07, 02, 02, 01))

        self.assertListEqual(
            [
                {
                    "_type": "OtherEvent",
                    "timestamp": "2015-06-06T22:12:34"
                },
                {
                    "_type": "OtherEvent",
                    "timestamp": "2015-06-06T21:12:34"
                },
                {
                    "_type": "PumpResume",
                    "timestamp": "2015-06-07T02:02:01"
                },
                {
                    "_type": "PumpSuspend",
                    "_description": "PumpSuspend 2015-06-06T20:49:57 head[2], body[0] op[0x1e]",
                    "date": 1433620197000.0,
                    "timestamp": "2015-06-06T20:49:57",
                    "_body": "",
                    "_head": "1e01",
                    "_date": "79b114060f"
                }
            ],
            h.clean_history
        )

    def test_suspend_without_resume_with_trimming_range(self):
        pump_history = [
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T22:12:34"
            },
            {
                "_type": "OtherEvent",
                "timestamp": "2015-06-06T21:12:34"
            },
            {
                "_type": "PumpSuspend",
                "_description": "PumpSuspend 2015-06-06T20:49:57 head[2], body[0] op[0x1e]",
                "date": 1433620197000.0,
                "timestamp": "2015-06-06T20:49:57",
                "_body": "",
                "_head": "1e01",
                "_date": "79b114060f"
            }
        ]

        h = CleanHistory(pump_history, end_datetime=datetime(2015, 06, 06, 21, 00, 00))

        self.assertListEqual(
            [
                {
                    "_type": "PumpResume",
                    "timestamp": "2015-06-06T21:00:00"
                },
                {
                    "_type": "PumpSuspend",
                    "_description": "PumpSuspend 2015-06-06T20:49:57 head[2], body[0] op[0x1e]",
                    "date": 1433620197000.0,
                    "timestamp": "2015-06-06T20:49:57",
                    "_body": "",
                    "_head": "1e01",
                    "_date": "79b114060f"
                }
            ],
            h.clean_history
        )


class ReconcileHistoryTestCase(unittest.TestCase):
    def test_overlapping_temp_basals(self):
        with open(get_file_at_path("fixtures/temp_basal_cancel.json")) as fp:
            pump_history = json.load(fp)

        h = ReconcileHistory(pump_history)

        self.assertListEqual(
            [
                {
                    "_type": "TempBasalDuration",
                    "duration (min)": 0,
                    "_description": "TempBasalDuration 2015-06-06T20:50:15 head[2], body[0] "
                                    "op[0x16]",
                    "date": 1433620215000.0,
                    "timestamp": "2015-06-06T20:50:15",
                    "_body": "",
                    "_head": "1600",
                    "_date": "4fb214060f"
                },
                {
                    "_type": "TempBasal",
                    "temp": "percent",
                    "_description": "TempBasal 2015-06-06T20:50:15 head[2], body[1] op[0x33]",
                    "date": 1433620215000.0,
                    "timestamp": "2015-06-06T20:50:15",
                    "_body": "08",
                    "_head": "3300",
                    "rate": 0,
                    "_date": "4fb214060f"
                },
                {
                    "_type": "TempBasalDuration",
                    "duration (min)": 10,
                    "_description": "TempBasalDuration 2015-06-06T20:39:45 head[2], body[0] "
                                    "op[0x16]",
                    "date": 1433619585000.0,
                    "timestamp": "2015-06-06T20:39:45",
                    "_body": "",
                    "_head": "1601",
                    "_date": "6da714060f"
                },
                {
                    "_type": "TempBasal",
                    "temp": "percent",
                    "_description": "TempBasal 2015-06-06T20:39:45 head[2], body[1] op[0x33]",
                    "date": 1433619585000.0,
                    "timestamp": "2015-06-06T20:39:45",
                    "_body": "08",
                    "_head": "3396",
                    "rate": 150,
                    "_date": "6da714060f"
                },
                {
                    "_type": "TempBasalDuration",
                    "duration (min)": 60,
                    "_description": "TempBasalDuration 2015-06-06T19:05:17 head[2], body[0] "
                                    "op[0x16]",
                    "date": 1433613917000.0,
                    "timestamp": "2015-06-06T19:05:17",
                    "_body": "",
                    "_head": "1602",
                    "_date": "518513060f"
                },
                {
                    "_type": "TempBasal",
                    "temp": "percent",
                    "_description": "TempBasal 2015-06-06T19:05:17 head[2], body[1] op[0x33]",
                    "date": 1433613917000.0,
                    "timestamp": "2015-06-06T19:05:17",
                    "_body": "08",
                    "_head": "33c8",
                    "rate": 200,
                    "_date": "518513060f"
                }
            ],
            [event for event in h.reconciled_history if event["_type"].startswith("TempBasal")]
        )

    def test_suspended_temp_basal(self):
        with open(get_file_at_path("fixtures/temp_basal_suspend.json")) as fp:
            pump_history = json.load(fp)

        h = ReconcileHistory(pump_history)

        self.assertListEqual(
            [
                {
                    "_type": "TempBasalDuration",
                    "duration (min)": 37,
                    "_description": "TempBasalDuration generated due to interleaved PumpSuspend "
                                    "event",
                    "date": 1434204002000.0,
                    "timestamp": "2015-06-13T15:00:02",
                    "_body": "",
                    "_head": "1602",
                    "_date": "42800f0d0f"
                },
                {
                    "_type": "TempBasal",
                    "temp": "percent",
                    "_description": "TempBasal generated due to interleaved PumpSuspend event",
                    "date": 1434204002000.0,
                    "timestamp": "2015-06-13T15:00:02",
                    "_body": "08",
                    "_head": "3378",
                    "rate": 120,
                    "_date": "42800f0d0f"
                },
                {
                    "_type": "PumpResume",
                    "_description": "PumpResume 2015-06-13T15:00:02 head[2], body[0] op[0x1f]",
                    "date": 1434204002000.0,
                    "timestamp": "2015-06-13T15:00:02",
                    "_body": "",
                    "_head": "1f20",
                    "_date": "42800f0d0f"
                },
                {
                    "_type": "PumpSuspend",
                    "_description": "PumpSuspend 2015-06-13T14:54:19 head[2], body[0] op[0x1e]",
                    "date": 1434203659000.0,
                    "timestamp": "2015-06-13T14:54:19",
                    "_body": "",
                    "_head": "1e01",
                    "_date": "53b60e0d0f"
                },
                {
                    "_type": "TempBasalDuration",
                    "duration (min)": 16,
                    "_description": "TempBasalDuration 2015-06-13T14:37:58 head[2], body[0] "
                                    "op[0x16]",
                    "date": 1434202678000.0,
                    "timestamp": "2015-06-13T14:37:58",
                    "_body": "",
                    "_head": "1602",
                    "_date": "7aa50e0d0f"
                },
                {
                    "_type": "TempBasal",
                    "temp": "percent",
                    "_description": "TempBasal 2015-06-13T14:37:58 head[2], body[1] op[0x33]",
                    "date": 1434202678000.0,
                    "timestamp": "2015-06-13T14:37:58",
                    "_body": "08",
                    "_head": "3378",
                    "rate": 120,
                    "_date": "7aa50e0d0f"
                }
            ],
            [event for event in h.reconciled_history if event["_type"] in ("TempBasal",
                                                                           "TempBasalDuration",
                                                                           "PumpSuspend",
                                                                           "PumpResume")]
        )


class ResolveHistoryTestCase(unittest.TestCase):
    def test_resolve(self):
        with open(get_file_at_path("fixtures/temp_basal_cancel.json")) as fp:
            pump_history = json.load(fp)

        h = ResolveHistory(pump_history)

        _ = parser.parse

        self.assertListEqual(
            [
                Bolus(
                    start_at=_("2015-06-06T20:46:06"),
                    end_at=_("2015-06-06T20:46:06"),
                    amount=3.9,
                    unit="U",
                    description="Normal bolus: 3.9U"
                ),
                Meal(
                    start_at=_("2015-06-06T20:46:06"),
                    end_at=_("2015-06-06T20:46:06"),
                    amount=32,
                    unit="g",
                    description="BolusWizard"
                ),
                TempBasal(
                    start_at=_("2015-06-06T20:39:45"),
                    end_at=_("2015-06-06T21:09:45"),
                    amount=150,
                    unit="percent",
                    description="TempBasal 150 percent"
                ),
                Bolus(
                    start_at=_("2015-06-06T20:32:26"),
                    end_at=_("2015-06-06T20:32:26"),
                    amount=3.1,
                    unit="U",
                    description="Normal bolus: 3.1U"
                ),
                TempBasal(
                    start_at=_("2015-06-06T19:05:17"),
                    end_at=_("2015-06-06T20:05:17"),
                    amount=200,
                    unit="percent",
                    description="TempBasal 200 percent"
                ),
                Meal(
                    start_at=_("2015-06-06T18:10:28"),
                    end_at=_("2015-06-06T18:10:28"),
                    amount=29,
                    unit="g",
                    description="JournalEntryMealMarker"
                ),
                Meal(
                    start_at=_("2015-06-06T17:55:00"),
                    end_at=_("2015-06-06T17:55:00"),
                    amount=37,
                    unit="g",
                    description="JournalEntryMealMarker"
                ),
                Bolus(
                    start_at=_("2015-06-06T16:07:36"),
                    end_at=_("2015-06-06T16:07:36"),
                    amount=0.45,
                    unit="U",
                    description="Normal bolus: 0.45U"
                ),
                TempBasal(
                    start_at=_("2015-06-06T16:07:52"),
                    end_at=_("2015-06-06T16:24:58"),
                    amount=0,
                    unit="percent",
                    description="Pump Suspend"
                ),
                Meal(
                    start_at=_("2015-06-06T16:07:35"),
                    end_at=_("2015-06-06T16:07:35"),
                    amount=24,
                    unit="g",
                    description="BolusWizard"
                ),
                Bolus(
                    start_at=_("2015-06-06T16:01:28"),
                    end_at=_("2015-06-06T16:01:28"),
                    amount=5.2,
                    unit="U",
                    description="Normal bolus: 5.2U"
                ),
                Meal(
                    start_at=_("2015-06-06T16:01:28"),
                    end_at=_("2015-06-06T16:01:28"),
                    amount=42,
                    unit="g",
                    description="BolusWizard"
                ),
                Bolus(
                    start_at=_("2015-06-06T15:00:24"),
                    end_at=_("2015-06-06T15:00:24"),
                    amount=3.2,
                    unit="U",
                    description="Normal bolus: 3.2U"
                )
            ],
            h.resolved_records
        )

    def test_square_bolus_in_progress(self):
        with open(get_file_at_path("fixtures/square_bolus.json")) as fp:
            pump_history = json.load(fp)

        h = ResolveHistory(pump_history, current_datetime=datetime(2015, 6, 19, 23, 10))

        _ = parser.parse

        self.assertListEqual(
            [
                Bolus(
                    start_at=_("2015-06-19T23:04:25"),
                    end_at=_("2015-06-19T23:04:25"),
                    amount=1.6,
                    unit="U",
                    description="Normal bolus: 1.6U"
                ),
                Meal(
                    start_at=_("2015-06-19T23:04:25"),
                    end_at=_("2015-06-19T23:04:25"),
                    amount=27,
                    unit="g",
                    description="BolusWizard"
                ),
                Bolus(
                    start_at=_("2015-06-19T21:31:15"),
                    end_at=_("2015-06-19T21:31:15"),
                    amount=2.5,
                    unit="U",
                    description="Normal bolus: 2.5U"
                ),
                TempBasal(
                    start_at=_("2015-06-19T21:32:55"),
                    end_at=_("2015-06-20T00:02:55"),
                    amount=1.4,
                    unit="U/hour",
                    description="Square bolus: 2.15U over 150min"
                ),
                Meal(
                    start_at=_("2015-06-19T21:31:15"),
                    end_at=_("2015-06-19T21:31:15"),
                    amount=56,
                    unit="g",
                    description="BolusWizard"
                ),
                Bolus(
                    start_at=_("2015-06-19T21:02:39"),
                    end_at=_("2015-06-19T21:02:39"),
                    amount=2.0,
                    unit="U",
                    description="Normal bolus: 2.0U"
                )
            ],
            h.resolved_records
        )

    def test_square_bolus_cancelled(self):
        with open(get_file_at_path("fixtures/square_bolus.json")) as fp:
            pump_history = json.load(fp)

        h = ResolveHistory(pump_history, current_datetime=datetime(2015, 6, 20, 23, 10))

        _ = parser.parse

        self.assertListEqual(
            [
                TempBasal(
                    start_at=_("2015-06-19T21:32:55"),
                    end_at=_("2015-06-19T23:04:55"),
                    amount=1.4,
                    unit="U/hour",
                    description="Square bolus: 2.15U over 92min"
                )
            ],
            [r for r in h.resolved_records if r["type"] == "TempBasal"]
        )


class BasalScheduleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(get_file_at_path("fixtures/basal.json")) as fp:
            cls.basal_rate_schedule = json.load(fp)


class NormalizeRecordsTestCase(BasalScheduleTestCase):
    def test_basal_rates_in_range(self):
        h = NormalizeRecords([], self.basal_rate_schedule)

        self.assertListEqual(
            self.basal_rate_schedule,
            h.basal_rates_in_range(time(0, 0), time(23, 59))
        )

        self.assertListEqual(
            self.basal_rate_schedule[0:1],
            h.basal_rates_in_range(time(0, 0), time(1, 0))
        )

        self.assertListEqual(
            self.basal_rate_schedule[1:3],
            h.basal_rates_in_range(time(4, 0), time(9, 0))
        )

        self.assertListEqual(
            self.basal_rate_schedule[5:6],
            h.basal_rates_in_range(time(16, 0), time(20))
        )

        with self.assertRaises(AssertionError):
            h.basal_rates_in_range(time(4), time(4))

        with self.assertRaises(AssertionError):
            h.basal_rates_in_range(time(4), time(3))

    def test_basal_adjustments_in_range(self):
        h = NormalizeRecords(
            [],
            self.basal_rate_schedule,
            zero_datetime=datetime(2015, 01, 01, 12)
        )

        with self.assertRaises(AssertionError):
            h._basal_adjustments_in_range(
                datetime(2015, 01, 02),
                datetime(2015, 01, 01),
                percent=100
            )

        with self.assertRaises(AssertionError):
            h._basal_adjustments_in_range(
                datetime(2015, 01, 01),
                datetime(2015, 01, 02, 4),
                percent=100
            )

        with self.assertRaises(AssertionError):
            h._basal_adjustments_in_range(datetime(2015, 01, 01), datetime(2015, 01, 01, 4))

        basal = TempBasal(
            start_at=datetime(2015, 01, 01, 05),
            end_at=datetime(2015, 01, 01, 06),
            amount=0.925,
            unit="U/hour",
            description="Testing"
        )

        self.assertDictEqual(
            basal,
            h._basal_adjustments_in_range(
                datetime(2015, 01, 01, 05),
                datetime(2015, 01, 01, 06),
                percent=200,
                description="Testing"
            )[0]
        )

        self.assertDictEqual(
            basal,
            h._basal_adjustments_in_range(
                datetime(2015, 01, 01, 05),
                datetime(2015, 01, 01, 06),
                absolute=1.85,
                description="Testing"
            )[0]
        )

        self.assertListEqual(
            [
                TempBasal(
                    start_at=datetime(2015, 01, 01, 23),
                    end_at=datetime(2015, 01, 01, 23, 59, 59),
                    amount=-0.45,
                    unit="U/hour",
                    description=""
                ),
                TempBasal(
                    start_at=datetime(2015, 01, 02),
                    end_at=datetime(2015, 01, 02, 02),
                    amount=-0.45,
                    unit="U/hour",
                    description=""
                )
            ],
            h._basal_adjustments_in_range(
                datetime(2015, 01, 01, 23),
                datetime(2015, 01, 02, 02),
                percent=50
            )
        )


class MungeFixturesTestCase(BasalScheduleTestCase):
    def test_bolus_wizard_duplicates(self):
        with open(get_file_at_path("fixtures/bolus_wizard_duplicates.json")) as fp:
            pump_history = json.load(fp)

        zero_datetime = parser.parse("2015-06-05T19:08:00")

        records = NormalizeRecords(
            ResolveHistory(
                ReconcileHistory(
                    CleanHistory(
                        pump_history
                    ).clean_history
                ).reconciled_history,
                current_datetime=zero_datetime
            ).resolved_records,
            basal_schedule=self.basal_rate_schedule,
            zero_datetime=zero_datetime
        ).normalized_records

        self.assertListEqual(
            [

            ],
            records
        )

    def test_square_bolus(self):
        with open(get_file_at_path("fixtures/square_bolus.json")) as fp:
            pump_history = json.load(fp)

        zero_datetime = parser.parse("2015-06-19T23:04:25")

        records = NormalizeRecords(
            ResolveHistory(
                ReconcileHistory(
                    CleanHistory(
                        pump_history
                    ).clean_history
                ).reconciled_history,
                current_datetime=zero_datetime
            ).resolved_records,
            basal_schedule=self.basal_rate_schedule,
            zero_datetime=zero_datetime
        ).normalized_records

        self.assertListEqual(
            [

            ],
            records
        )

    def test_temp_basal_cancel(self):
        with open(get_file_at_path("fixtures/temp_basal_cancel.json")) as fp:
            pump_history = json.load(fp)

        zero_datetime = parser.parse("2015-06-06T20:50:15")

        records = NormalizeRecords(
            ResolveHistory(
                ReconcileHistory(
                    CleanHistory(
                        pump_history
                    ).clean_history
                ).reconciled_history,
                current_datetime=zero_datetime
            ).resolved_records,
            basal_schedule=self.basal_rate_schedule,
            zero_datetime=zero_datetime
        ).normalized_records

        self.assertListEqual(
            [

            ],
            records
        )

    def test_temp_basal_suspend(self):
        with open(get_file_at_path("fixtures/temp_basal_suspend.json")) as fp:
            pump_history = json.load(fp)

        zero_datetime = parser.parse("2015-06-13T15:37:58")

        records = NormalizeRecords(
            ResolveHistory(
                ReconcileHistory(
                    CleanHistory(
                        pump_history
                    ).clean_history
                ).reconciled_history,
                current_datetime=zero_datetime
            ).resolved_records,
            basal_schedule=self.basal_rate_schedule,
            zero_datetime=zero_datetime
        ).normalized_records

        self.assertListEqual(
            [

            ],
            records
        )

if __name__ == "__main__":
    unittest.main()
