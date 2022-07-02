"""Main file for the backend"""
import logging
import re
import asyncio
import argparse
import configparser

from backend.api import NodeContractApi, ChainQuery, apiTypes
from backend.core.oracle import Oracle, OracleSettings
from backend.runner import FeedUpdater

parser = argparse.ArgumentParser(
    prog='Charli3 Backends for Node Operator',
    description='Charli3 Backends for Node Opetor.'
)
parser.add_argument(
    '-c','--configfile',
    help='Specify a file to override default configuration',
    default="config.ini"
)

arguments = parser.parse_args()

conffile = configparser.ConfigParser()
conffile.read(arguments.configfile)

ini_oracle = dict(conffile.items('Oracle'))
oracle = Oracle(
    ini_oracle['oracle_owner'],
    ini_oracle['oracle_curr'],
    (ini_oracle['fee_asset_currency'], ini_oracle['fee_asset_name'])
)

ini_nodecontractapi = dict(conffile.items('NodeContractApi'))
node = NodeContractApi(
    oracle,
    **ini_nodecontractapi
)

ini_oraclesettings = dict(conffile.items('OracleSettings'))
for key, value in ini_oraclesettings.items():
    try:
        ini_oraclesettings[key] = int(value)
    except ValueError:
        ini_oraclesettings[key] = value
ini_oraclesettings['node_pkhs'] = re.findall(r"[0-9A-Za-z]{56}",ini_oraclesettings['node_pkhs'])
sett = OracleSettings(**ini_oraclesettings)

ini_rate = dict(conffile.items('rate'))
rrate_tp = ini_rate['type']
del ini_rate['type']
rateclass = apiTypes[rrate_tp](**ini_rate)


ini_updater = dict(conffile.items('Updater'))
ini_chainquery = dict(conffile.items('ChainQuery'))
updater = FeedUpdater(
        int(ini_updater['update_inter']),
        sett,
        node,
        rateclass,
        ChainQuery(ini_chainquery['api_url'])
    )

numeric_level = getattr(logging, ini_updater["verbosity"], None)
logging.basicConfig(
    format="%(level_color)s[%(name)s:%(levelname)s]%(end_color)s [%(asctime)s] %(message)s",
    level=numeric_level)

old_factory = logging.getLogRecordFactory()

level_colors = [
    "\033[0m", # No Set
    "\033[36m", # Debug
    "\033[34m", # Info
    "\033[33m", # Warning
    "\033[31m", # Error
    "\033[1;31m" # Critical
]

def _record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.level_color = level_colors[record.levelno//10]
    record.end_color = "\033[0m"
    return record

logging.setLogRecordFactory(_record_factory)

asyncio.run(updater.run())
