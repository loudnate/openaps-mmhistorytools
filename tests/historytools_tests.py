from datetime import datetime
import json
import os
import sys
import unittest

from openapscontrib.mmhistorytools.historytools import CleanHistory, ReconcileHistory


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
                            "_description": "UnabsorbedInsulinBolus unknown head[35], body[0] op[0x5c]",
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
                            "_head": "5c23509204103c14104614105014105a14106414106e14107814108214128c14ae9614",
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
                    "_description": "TempBasalDuration 2015-06-06T20:50:15 head[2], body[0] op[0x16]",
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
                    "_description": "TempBasalDuration 2015-06-06T20:39:45 head[2], body[0] op[0x16]",
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
                    "_description": "TempBasalDuration 2015-06-06T19:05:17 head[2], body[0] op[0x16]",
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
                    "_description": "TempBasalDuration generated due to interleaved PumpSuspend event",
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
                    "_description": "TempBasalDuration 2015-06-13T14:37:58 head[2], body[0] op[0x16]",
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


if __name__ == "__main__":
    unittest.main()
