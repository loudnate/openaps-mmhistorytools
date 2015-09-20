import datetime
import json


class BaseRecord(dict):
    def __init__(self, start_at=None, end_at=None, amount=None, unit=None, description=None):
        """Constructs a record dict

        :param start_at: The start of the record
        :type start_at: datetime.datetime
        :param end_at: The end time of the record
        :type end_at: datetime.datetime
        :param amount: The numeric description of the record
        :type amount: int|float
        :param unit: The unit describing `amount`
        :type unit: str
        :param description: A human summary of the record
        :type description: basestring
        """
        kwargs = {
            "type": self.__class__.__name__,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "amount": amount,
            "unit": unit,
            "description": description
        }

        super(BaseRecord, self).__init__((), **kwargs)


class Bolus(BaseRecord):
    pass


class Meal(BaseRecord):
    pass


class TempBasal(BaseRecord):
    pass


class Exercise(BaseRecord):
    pass


class Unit(object):
    grams = "g"
    percent_of_basal = "percent"
    units = "U"
    units_per_hour = "U/hour"
    event = "event"


class RecordJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.replace(microsecond=0).isoformat()
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            return o.isoformat()
        else:
            return super(RecordJSONEncoder, self).default(o)
