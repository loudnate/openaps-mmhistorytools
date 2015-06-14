# mmhistorytools
An [openaps](https://github.com/openaps/openaps) plugin for cleaning, condensing, and reformatting medtronic history data

## Getting started
### Installing from source for development
Clone the repository and link via setuptools:
```bash
$ python setup.py develop
```

### Adding to your openaps project
```bash
$ openaps vendor add openapscontrib.mmhistorytools
$ openaps device add mmhistorytools mmhistorytools
```

## Usage
Use the device help menu to see available commands.
```bash
$ openaps use mmhistorytools -h
usage: openaps-use mmhistorytools [-h] USAGE ...

optional arguments:
  -h, --help  show this help message and exit

## Device mmhistorytools:
  vendor openapscontrib.mmhistorytools
  
  mmhistorytools - tools for cleaning, condensing, and reformatting history data
  
      

  USAGE       Usage Details
    cleanup   Removes inconsistencies from a sequence of pump history
```

Use the command help menu to see available arguments.
```bash
$ openaps use mmhistorytools cleanup -h
usage: openaps-use mmhistorytools cleanup [-h] [--start START] [--end END]
                                          [infile]

Removes inconsistencies from a sequence of pump history

positional arguments:
  infile         JSON-encoded history data to clean

optional arguments:
  -h, --help     show this help message and exit
  --start START  The initial timestamp of the window to return
  --end END      The final timestamp of the window to return

Tasks performed by this pass:
 - De-duplicates BolusWizard records
 - Creates PumpSuspend and PumpResume records to complete missing pairs
 - Removes any records whose timestamps don't fall into the specified window
 - Adjusts TempBasalDuration records for overlapping entries
```