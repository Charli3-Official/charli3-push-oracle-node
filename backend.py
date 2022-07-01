#!/usr/bin/env python3
import argparse, configparser
import json, sys, re


import asyncio

from backend.api import NodeContractApi, BinanceApi, CoinRate, ChainQuery, apiTypes
from backend.api.node import FailedOperation, PABTimeout
from backend.core.oracle import Oracle, OracleSettings
from backend.runner import FeedUpdater

# SETS THE RULES FOR CLI INTERACTION TO RUN THE SCRIPT
parser = argparse.ArgumentParser(prog='Charli3 Backends for Node Operator',description='Charli3 Backends for Node Opetor.')

# OPTIONS SETTING
parser.add_argument('-c','--configfile', help='Specify a file to override default configuration', default="config.ini")

args = parser.parse_args()

conffile = configparser.ConfigParser()
conffile.read(args.configfile)

if __name__=="__main__":

    ini_oracle = dict(conffile.items('Oracle'))
    ini_nodecontractapi = dict(conffile.items('NodeContractApi'))

    o = Oracle(
        ini_oracle['oracle_owner'],
        ini_oracle['oracle_curr'],
        (ini_oracle['fee_asset_currency'], ini_oracle['fee_asset_name'])
    )

    n = NodeContractApi(
        o,
        **ini_nodecontractapi
    )    
    
    ini_oraclesettings = dict(conffile.items('OracleSettings'))

    for key, value in ini_oraclesettings.items():
        try:
            ini_oraclesettings[key] = int(value)
        except:
            ini_oraclesettings[key] = value

    ini_oraclesettings['node_pkhs'] = re.findall(r"[0-9A-Za-z]{56}",ini_oraclesettings['node_pkhs'])

#    ini_oraclesettings['node_pkhs'] = ini_oraclesettings['node_pkhs'].replace('"','').replace('\n','').replace('\t','').replace('[','').replace(']','').replace(' ','').split(',')
    print(ini_oraclesettings)

    sett = OracleSettings(**ini_oraclesettings)
    
    ini_rate = dict(conffile.items('rate'))

    rrate_tp = ini_rate['type']
    del ini_rate['type']
    rateclass = apiTypes[rrate_tp](**ini_rate)


    ini_updater = dict(conffile.items('Updater'))

    ini_chainquery = dict(conffile.items('ChainQuery'))
    
    f = FeedUpdater(int(ini_updater['update_inter']), sett, n, rateclass, ChainQuery(ini_chainquery['api_url']))
    
    loop = asyncio.run(f.run())