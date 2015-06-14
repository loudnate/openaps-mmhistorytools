from openaps.uses.use import Use


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
    return []


class cleanup(Use):
    """Modifies Medtronic read_history_data output to account for inconsistencies.

    Specifically:
     - De-duplicates BolusWizard records
     - Creates PumpSuspend and PumpResume records to complete missing pairs
     - Removes any records whose timestamps don't fall into the specified window
     - Adjusts TempBasalDuration records for overlapping entries
    """
    def get_params(self, args):
        return dict(input=args.input)

    def configure_app(self, app, parser):
        pass
