# mmhistorytools
An [openaps](https://github.com/openaps/openaps) plugin for cleaning, condensing, and reformatting medtronic history data

## Getting started
### Installing from pypi

```bash
sudo easy_install openapscontrib.mmhistorytools
```

### Installing from source for development
Clone the repository and link via setuptools:
```bash
$ python setup.py develop
```

### Adding to your openaps project
```bash
$ openaps vendor add openapscontrib.mmhistorytools
$ openaps device add munge mmhistorytools
```

## Usage
Use the device help menu to see available commands.
```bash
$ openaps use munge -h
usage: openaps-use mmhistorytools [-h] USAGE ...

optional arguments:
  -h, --help  show this help message and exit

## Device mmhistorytools:
  vendor openapscontrib.mmhistorytools

  mmhistorytools - tools for cleaning, condensing, and reformatting history data





  USAGE       Usage Details
    clean     Resolve inconsistencies from a sequence of pump history
    reconcile
              Reconcile record dependencies from a sequence of pump history
    resolve   Converts events in a sequence of pump history to generalized
              record types
    normalize
              Adjusts the time and amount of records relative to a basal
              schedule and a timestamp
```

Use the command help menu to see available arguments.
```bash
$ openaps use munge clean -h
usage: openaps-use mmhistorytools clean [-h] [--start START] [--end END]
                                        infile

Resolve inconsistencies from a sequence of pump history

positional arguments:
  infile         JSON-encoded history data

optional arguments:
  -h, --help     show this help message and exit
  --start START  The initial timestamp of the window to return
  --end END      The final timestamp of the window to return

Tasks performed by this pass:
 - De-duplicates BolusWizard records
 - Creates PumpSuspend and PumpResume records to complete missing pairs
 - Removes any records whose timestamps don't fall into the specified window
```

All `infile` arguments default to accept stdin, so commands can be chained like so:
```bash
openaps use pump read_history_data 0 | openaps use mmhistorytools clean --start 2015-06-13T17:37:58 | openaps use mmhistorytools reconcile | openaps use mmhistorytools resolve --now 2015-06-13T21:37:58 | openaps use mmhistorytools normalize --basal-profile basal.json --zero-at 2015-06-21T15:37:58
```

## Motivation
Pump history records are optimized for storage, and not necessarily for analysis. They are a mix of mutable (`Bolus`) and immutable (`TempBasalDuration`) values. They require additional context to interpret important events, like whether a square bolus is still in delivery or whether it was cancelled, and how much basal insulin was lost during a `PumpSuspend` window.

Interpreting recent historical events is a foundational component in any [openaps](https://github.com/openaps/openaps) project, and this plugin aspires to be a central place for documenting and testing the intricacies of that task.

The `mmhistorytools` plugin vends multiple commands. Each command does a single pass over a set of history and is intentionally limited in scope, prioritizing testability above performance.

## Contributing
Contributions are welcome and encouraged in the form of bugs and pull requests.
