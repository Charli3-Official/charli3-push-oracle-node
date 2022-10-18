"""Main file for the backend"""
import logging
import asyncio
import argparse
from logging import config
import yaml
from backend.api import NodeContractApi, chainQueryTypes, apiTypes
from backend.core.oracle import Oracle, OracleSettings
from backend.runner import FeedUpdater

parser = argparse.ArgumentParser(
    prog='Charli3 Backends for Node Operator',
    description='Charli3 Backends for Node Opetor.'
)

parser.add_argument(
    '-c', '--configfile',
    help='Specify a file to override default configuration',
    default="config.yml"
)

arguments = parser.parse_args()

with open(arguments.configfile, "r", encoding='UTF-8') as ymlfile:
    configyaml = yaml.load(ymlfile, Loader=yaml.FullLoader)

ini_oracle = configyaml['Oracle']

oracle = Oracle(
    ini_oracle['oracle_owner'],
    ini_oracle['oracle_curr'],
    ini_oracle['oracle_address'],
    (ini_oracle['fee_asset_currency'], ini_oracle['fee_asset_name'])
)

ini_nodecontractapi = configyaml['NodeContractApi']

PGCONF = None
if "PostgresConfig" in configyaml:
    PGCONF = configyaml['PostgresConfig']
node = NodeContractApi(
    oracle,
    **ini_nodecontractapi,
    pgconfig=PGCONF
)

ini_oraclesettings = configyaml['OracleSettings']
for key, value in ini_oraclesettings.items():
    try:
        if key != 'node_pkhs':
            ini_oraclesettings[key] = int(value)
    except ValueError:
        ini_oraclesettings[key] = value

sett = OracleSettings(**ini_oraclesettings)

ini_rate = configyaml['Rate']
rrate_tp = ini_rate['type']
del ini_rate['type']
rateclass = apiTypes[rrate_tp](**ini_rate)

ini_updater = configyaml['Updater']
ini_chainquery = configyaml['ChainQuery']

tp = ini_chainquery["type"]
if ini_chainquery["type"] == 'blockfrost':
    ini_chainquery["oracle_address"] = ini_oracle['oracle_address']
del ini_chainquery["type"]


chain = chainQueryTypes[tp](**ini_chainquery)

updater = FeedUpdater(
    int(ini_updater['update_inter']),
    sett,
    node,
    rateclass,
    chain
)

numeric_level = getattr(logging, ini_updater["verbosity"], None)

level_colors = [
    "\033[0m",  # No Set
    "\033[36m",  # Debug
    "\033[34m",  # Info
    "\033[33m",  # Warning
    "\033[31m",  # Error
    "\033[1;31m"  # Critical
]

logconfig = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format":
                "%(level_color)s[%(name)s:%(levelname)s]%(end_color)s [%(asctime)s] %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            "level": getattr(logging, ini_updater["verbosity"], None),
            "level_colors": level_colors
        },
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)fs",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        }
    },
    "handlers": {
        "standard": {
            "class": "logging.StreamHandler",
            "formatter": "standard"
        }
    },
    "loggers": {
        "": {
            "handlers": ["standard"],
            "level": logging.INFO
        }
    }
}

if 'awslogger' in configyaml:
    logconfig['handlers']['kinesis'] = {
        "class": "backend.logfiles.KinesisFirehose.DeliveryStreamHandler",
        "formatter": "json", "configyml": configyaml['awslogger']
    }
    logconfig['loggers']['']['handlers'].append('kinesis')


logging.config.dictConfig(logconfig)

old_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.node = ini_nodecontractapi['pkh']
    record.feed = ini_oracle['oracle_curr']
    record.level_color = level_colors[record.levelno//10]
    record.end_color = "\033[0m"
    return record


logging.setLogRecordFactory(_record_factory)

asyncio.run(updater.run())
