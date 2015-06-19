from collections import namedtuple


BaseRecord = namedtuple('BaseRecord', (
    'type',
    'start_at',
    'end_at',
    'amount',
    'unit',
    'description',
))


class Unit(object):
    units = 'U'
    units_per_minute = 'U/min'


class Record(BaseRecord):
    def __init__(self, *args, **kwargs):
        args = (__name__,) + args
        super(Record, self).__init__(*args, **kwargs)


class Bolus(Record):
    pass


class Meal(Record):
    pass


class TempBasal(Record):
    pass

