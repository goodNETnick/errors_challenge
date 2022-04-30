from nornir import InitNornir
from nornir.core.task import Task
from nornir.core.filter import F
from nornir_napalm.plugins.tasks import napalm_get
import time
import os
import datetime
import getpass
import argparse

def np_get_info(task: Task):
    """
    Nornir task to get info from devices and complete host variables with get_info
    Args:
        task: nornir task object
    """
    # some translations from ansible inventory to nornir napalm
    if task.host["ansible_network_os"] == "ios":
        task.host["napalm_network_os"] = task.host["ansible_network_os"]
    int_counters = task.run(napalm_get, getters=['get_interfaces_counters'])
    task.host["int_counters"] = int_counters.result['get_interfaces_counters']

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple script to find errors on network device interfaces")
    parser.add_argument("-t", dest="update_time", default=10, type=int, help="Refresh timeout")
    parser.add_argument("-g", dest="ans_group", default='cisco_routers', help="Ansible device group")
    args = parser.parse_args()

    update_time = args.update_time
    ans_group = args.ans_group
    dev_access_pswd = getpass.getpass()
    start_time = datetime.datetime.now()
    intrst_stats = ['rx_errors', 'rx_discards', 'tx_errors', 'tx_discards']

    # Collect baselline info (to date the script starts)
    nr = InitNornir(config_file="config.yaml")
    nr.inventory.defaults.password = dev_access_pswd
    baseline_nr = nr.filter(F(groups__contains={ans_group}))
    baseline_get = baseline_nr.run(task=np_get_info)

    # Collect new info (at the moment)
    livenr = InitNornir(config_file="config.yaml")
    livenr.inventory.defaults.password = 'cisco'
    livenr_ios = livenr.filter(F(groups__contains={ans_group}))

    while True:
        os.system('clear')
        print("The time since the launch of the script:", datetime.datetime.now() - start_time)
        # update new info with th output of 'np_get_info'
        livenr_get = livenr_ios.run(task=np_get_info)
        # check if there is new errors
        for host, data in livenr_ios.inventory.hosts.items():
            baseline_err_cntrs = baseline_nr.inventory.hosts[host]['int_counters']
            livenr_err_cntrs = livenr_ios.inventory.hosts[host]['int_counters']
            for intf, counters in baseline_err_cntrs.items():
                for cntr, value in counters.items():
                    if cntr in intrst_stats and baseline_err_cntrs[intf][cntr] != livenr_err_cntrs[intf][cntr]:
                        print("="*55)
                        print(host, intf)
                        print("total errors: ", cntr, "= ", value)
                        print("new errors: ", cntr, "= ", livenr_err_cntrs[intf][cntr] - baseline_err_cntrs[intf][cntr])
        time.sleep(update_time)
