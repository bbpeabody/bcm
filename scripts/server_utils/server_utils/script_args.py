import logging
import os
import sys

from confuse.exceptions import NotFoundError

from server_utils.config import config
from server_utils.helpers import list_to_string
from server_utils.sit import get_sit_version


def add_aurora_arg(parser):
    local_aucommon = os.path.expanduser(config['aurora']['local_aucommon'].as_str())
    remote_aucommon = config['aurora']['remote_aucommon'].as_str()
    parser.add_argument('-l', '--local', type=str, help=f"Path to local aucommon repo. Defaults to "
                        f"{local_aucommon}.", default=local_aucommon, dest="aurora.local_aucommon")
    parser.add_argument('-r', '--remote', type=str, help=f"Path to remote aucommon repo. Defaults to "
                        f"{remote_aucommon}.", default=remote_aucommon, dest="aurora.remote_aucommon")
    parser.add_argument('--delete', action="store_true", help="Completely remove remote aucommon and re-clone before syncing.",
                        dest="aurora.delete")


def add_autoneg_arg(parser):
    parser.add_argument('-a', '--autoneg', action="store_true", help="Enable auto-negotiation", default=False)


def add_driver_unload_arg(parser):
    parser.add_argument('-u', '--driver-unload', action="store_true", help="Unload the driver before attempting to map"
                                                                           " PCI BAR.", default=False)


def add_filter_mask_arg(parser):
    parser.add_argument('--filter-mask', type=str, help=f"16-bit filter mask in hex. Defaults to F000.",
                        default="F000")

def add_hwrm_include_exclude_arg(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--include', dest='hwrm_include', default=[],
                       action='append', help="Include only HWRM messages types that match this "
                                             "string.  If any part of the message type matches, it "
                                             "will be included. This option may be used multiple "
                                             "times. Example: -i 'port_phy' This would include "
                                             "PORT_PHY_CFG and PORT_PHY_QCFG messages.")
    group.add_argument('-e', '--exclude', dest='hwrm_exclude', default=[],
                       action='append', help="Exclude HWRM messages types that match this "
                                             "string.  If any part of the message type matches, it "
                                             "will be excluded. This option may be used multiple "
                                             "times. Example: -e 'port_phy' This would exclude "
                                             "PORT_PHY_CFG and PORT_PHY_QCFG messages.")


def add_interface_arg(parser):
    parser.add_argument('-i', '--interface', type=str, help="Ethernet interface. By default, all interfaces defined in "
                                                            "config will be used.", default=None)


def add_live_arg(parser):
    parser.add_argument('-l', '--live', action="store_true", help="Use bnxtnvm -live option to install package instead."
                                                                  " bnxtmt nvm pkginstall is used by default.")

def add_package_arg(parser):
    parser.add_argument('-p', '--package', type=str, help="Package file name", default=None)


def add_rpyc_restart_arg(parser):
    parser.add_argument('--rpyc-restart', action="store_true", help="Force a re-sync and restart of the RPyC server. "
                                                                    "This will kill The RPyC server, rsync "
                                                                    "server_utils to the remote, recreate the venv on "
                                                                    "the remote, and restart the RPyC server. This is "
                                                                    "necessary if you make changes to the server_utils "
                                                                    "code.", dest="rpyc.restart")


def add_server_arg(parser, nargs="+"):
    parser.add_argument('server', help="Server name", nargs=nargs)


def add_sit_arg(parser):
    parser.add_argument('--sit', type=str, help="SIT version to use. By default, the lastest SIT will be used.",
                        default="998.999.999.999")
    parser.add_argument('--sit-url', type=str, help="URL where SIT builds are stored. Defaults to "
                                                    f"{config['sit_url'].as_str()}", default=config['sit_url'].as_str())


def add_speed_arg(parser):
    parser.add_argument('-s', '--speed', action='append', help="Ethernet link speed. By default, the highest speed will"
                                                               " be used. If using --autoneg option, --speed option may"
                                                               " be specified multiple times to advertise multiple"
                                                               " speeds.", default=[])


def add_tail_arg(parser):
    parser.add_argument('-f', action="store_true", help="Follow the output like 'tail -f'", dest="tail", default=False)


def add_verbose_arg(parser):
    parser.add_argument('-v', action="append_const", const=1, help="Verbose output. Specify multiple times for more "
                                                                   "output. By default, only error "
                                                                   "messages are printed. -v = warning, -vv = "
                                                                   " info, -vvv = debug. Verbosity level can also be "
                                                                   "specified in the config YAML file.", dest="verbose",
                        default=None)


def arg_error(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


def validate_autoneg(args):
    if not args.autoneg:
        if len(args.speed) > 1:
            arg_error(f"Only one speed may be specified for forced speed mode (no --autoneg option).")


def validate_filter_mask(args):
    args.filter_mask = int(args.filter_mask, 16)
    if args.filter_mask < 0 or args.filter_mask > 65535:
        arg_error(f"Invalid --filter-mask option. Value must be valid hex value between 0x0000 and 0xFFFF.")

def validate_local(args):
    if not os.path.isdir(args.local):
        arg_error(f"Invalid --local option. {args.local} is not a directory.")


def validate_package(args):
    if args.package is None:
        return
    if not os.path.isfile(args.package):
        arg_error(f"Package file name '{args.package}' does not exist.")


def validate_server(args):
    for server in args.server:
        try:
            config['servers'][server].get()
        except NotFoundError:
            arg_error(f"Server '{server}' does not exist in configuration.")


def validate_sit(args):
    sit_version = args.sit.split(".")
    if len(sit_version) < 1 or len(sit_version) > 4:
        arg_error(f"Invalid format for SIT version '{args.sit}'. Valid examples: 218 or 218.1 or 218.1.1.1")
    for _ in range(4 - len(sit_version)):
        sit_version.append(999)
    try:
        sit_url, args.sit = get_sit_version(args.sit_url, sit_version)
        args.sit_url = f"{sit_url}/{args.sit}"
    except ValueError:
        arg_error(f"Invalid SIT version '{args.sit}'. Cannot find version on SIT server.")


def validate_speed(args):
    speed = args.speed
    if not speed:
        return
    speed_table = {
        "1000": 1000,
        "10000": 10000,
        "25000": 25000,
        "40000": 40000,
        "50000": 50000,
        "100000": 100000,
        "200000": 200000,
        "1G": 1000,
        "10G": 10000,
        "25G": 25000,
        "40G": 40000,
        "50G": 50000,
        "100G": 100000,
        "200G": 200000
    }
    translated_speeds = []
    for s in speed:
        if s not in speed_table:
            arg_error(f"Invalid speed setting '{s}'. Valid speed settings are {list_to_string(list(speed_table.keys()))}.")
        translated_speeds.append(speed_table[s])
    args.speed = translated_speeds


def validate_verbose(args):
    if args.verbose is None:
        verbosity_map = dict(
            debug=logging.DEBUG,
            info=logging.INFO,
            warning=logging.WARNING,
            error=logging.ERROR,
            critical=logging.CRITICAL
        )
        verbosity_level = config['verbosity'].as_choice(verbosity_map)
        args.verbose = verbosity_level
    else:
        level = sum(args.verbose)
        if level == 1:
            args.verbose = logging.WARNING
        elif level == 2:
            args.verbose = logging.INFO
        else:
            args.verbose = logging.DEBUG


def validate_args(args):
    this_module = sys.modules[__name__]
    for arg in vars(args):
        try:
            validate_func = getattr(this_module, f"validate_{arg}")
            validate_func(args)
        except AttributeError:
            pass
    # Set all command line options in the global config
    config.set_args(args, dots=True)
