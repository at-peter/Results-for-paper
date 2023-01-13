import sys
import numpy as np
import os
import random
import collections
from os.path import dirname, abspath
from copy import deepcopy
from sacred import Experiment, SETTINGS
from sacred.observers import FileStorageObserver, MongoObserver
# from sacred.observers import QueuedMongoObserver
from sacred.utils import apply_backspaces_and_linefeeds
import sys
import torch as th
from utils.logging import get_logger
import yaml
import pymongo 
import ssl
from run import run
import configparser
from datetime import datetime

now = datetime.now()
date_time = now.strftime('%H:%M:%S:%f_%m/%d/%Y')
db_config = configparser.ConfigParser()
db_config.read(os.getcwd()+"\\db_config.ini")

SETTINGS['CAPTURE_MODE'] = "no" # set to "no" if you want to see stdout/stderr in console
logger = get_logger()

ex = Experiment()
ex.logger = logger
ex.captured_out_filter = apply_backspaces_and_linefeeds

results_path = os.path.join(dirname(dirname(abspath(__file__))), "results")
# results_path = "/home/ubuntu/data"

@ex.main
def my_main(_run, _config, _log):
    # Setting the random seed throughout the modules
    config = config_copy(_config)
    np.random.seed(config["seed"])
    th.manual_seed(config["seed"])
    config['env_args']['seed'] = config["seed"]

    # run the framework
    run(_run, config, _log)


def _get_config(params, arg_name, subfolder):
    config_name = None
    for _i, _v in enumerate(params):
        if _v.split("=")[0] == arg_name:
            config_name = _v.split("=")[1]
            del params[_i]
            break

    if config_name is not None:
        with open(os.path.join(os.path.dirname(__file__), "config", subfolder, "{}.yaml".format(config_name)), "r") as f:
            try:
                config_dict = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                assert False, "{}.yaml error: {}".format(config_name, exc)
        return config_dict


def recursive_dict_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = recursive_dict_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def config_copy(config):
    if isinstance(config, dict):
        return {k: config_copy(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [config_copy(v) for v in config]
    else:
        return deepcopy(config)


if __name__ == '__main__':
   
    params = deepcopy(sys.argv)
    th.set_num_threads(1)

    # Get the defaults from default.yaml
    with open(os.path.join(os.path.dirname(__file__), "config", "default.yaml"), "r") as f:
        try:
            config_dict = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            assert False, "default.yaml error: {}".format(exc)

    # Load algorithm and env base configs
    env_config = _get_config(params, "--env-config", "envs")
    alg_config = _get_config(params, "--config", "algs")
    # config_dict = {**config_dict, **env_config, **alg_config}
    config_dict = recursive_dict_update(config_dict, env_config)
    config_dict = recursive_dict_update(config_dict, alg_config)

    try:
        map_name = config_dict["env_args"]["map_name"]
    except:
        map_name = config_dict["env_args"]["key"]    
    
    
    # now add all the config to sacred
    ex.add_config(config_dict)
    
    for param in params:
        if param.startswith("env_args.map_name"):
            map_name = param.split("=")[1]
        elif param.startswith("env_args.key"):
            map_name = param.split("=")[1]

    # Save to disk by default for sacred
    logger.info("Saving to FileStorageObserver in results/sacred.")
    file_obs_path = os.path.join(results_path, f"sacred/{config_dict['name']}/{map_name}")
    

    # client = pymongo.MongoClient(db_config['mongodb']['db_url'],
    #                                 ssl = True, 
    #                                 ssl_cert_reqs= ssl.CERT_NONE
    # )

    # client = pymongo.MongoClient("mongodb+srv://peteradmin:peteradmin@testcluster1.zerxv.mongodb.net/testdatebase?retryWrites=true&w=majority",
    # ssl=True,
    # ssl_cert_reqs=ssl.CERT_NONE
    # )
    # ex.observers.append(QueuedMongoObserver(db_name="ipppo_wtf_test", client=client, collection_prefix=config_dict['name'] + date_time)) #url='172.31.5.187:27017'))
    ex.observers.append(FileStorageObserver.create("./results/ia2c_lbf_50_step_extra"))
    # ex.observers.append(MongoObserver())
    
    ex.run_commandline(params)

