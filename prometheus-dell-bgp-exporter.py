#!/usr/bin/python3

import time
import re
import os
import json
import yaml
from subprocess import Popen, PIPE
from prometheus_client import start_http_server
from prometheus_client.core import Gauge, GaugeMetricFamily, CounterMetricFamily, REGISTRY


bgps = { 'bgpPeerAdminStatus': [], 'bgpPeerRemoteAddr': [], 'bgpPeerState': [], 'bgpVrfName': [], 'bgpPeerRemoteAs': [],
         'bgpPeerRemotePort': [], 'bgpPeerLocalAddr': [], 'bgpPeerLocalPort': [], 'bgpPeerFsmEstablishedTime': [],
         'bgpPeerInTotalMessages': [], 'bgpPeerOutTotalMessages': [], 'bgpPeerInUpdates': [], 'bgpPeerOutUpdates': []
}

def get_duration_sec(duration):
    total_seconds = 0
    a_duration = duration.split()
    for i in range(len(a_duration)):
        if ':' in a_duration[i]:
            a_a_duration = a_duration[i].split(":")
            total_seconds = total_seconds + int(a_a_duration[0]) * 3600 + int(a_a_duration[1]) * 60 + int(a_a_duration[2])
        elif 'week' in a_duration[i+1]:
            total_seconds = total_seconds + int(a_duration[i]) * 7 * 24 * 3600
        elif 'day' in a_duration[i+1]:
            total_seconds = total_seconds + int(a_duration[i]) * 24 * 3600
    return str(total_seconds)

def get_configuration():
    file = "/etc/default/prometheus-dell-bgp-exporter.yaml"
    with open(file,"r") as file_object:
        generator_obj = yaml.load_all(file_object,Loader=yaml.SafeLoader)
        for data in generator_obj:
            config_data = data
    return config_data


def get_os10_metrics(host, user, password):
    global bgps
    local_bgps = { 'bgpPeerAdminStatus': [], 'bgpPeerRemoteAddr': [], 'bgpPeerState': [], 'bgpVrfName': [], 'bgpPeerRemoteAs': [],
                   'bgpPeerRemotePort': [], 'bgpPeerLocalAddr': [], 'bgpPeerLocalPort': [], 'bgpPeerFsmEstablishedTime': [],
                   'bgpPeerInTotalMessages': [], 'bgpPeerOutTotalMessages': [], 'bgpPeerInUpdates': [], 'bgpPeerOutUpdates': []
    }
    metrics = []
    vrfs = []
    line = ""
    states = { "Idle": "1", "Connect": "2", "Active": "3", "Opensent": "4", "Openconfirm": "5", "Established": "6" }
    sshpasswd = f"sshpass -p {password} ssh {user}@{host}"
    command = sshpasswd + ' ' + '"show running-configuration vrf"'
    output = Popen(command,shell=True, stdout=PIPE, stderr=PIPE, close_fds=True, universal_newlines=True).communicate()[0]
    for line in output.split("\n"):
        if 'ip vrf' in line:
            a_line = line.split()
            vrfs.append({ 'name': a_line[2].strip(), 'neighbors': [] })
    metrics.append({ 'vrfs': vrfs })
    for i in range(len(metrics)):
        vrfs = metrics[i]['vrfs']
        for j in range(len(vrfs)):
            name = vrfs[j]['name']
            has_bgp = False
            command = sshpasswd + ' ' + '"show ip bgp vrf' + ' ' + name + ' ' + 'neighbors"'
            output = Popen(command,shell=True, stdout=PIPE, stderr=PIPE, close_fds=True, universal_newlines=True).communicate()[0]
            for line in output.split("\n"):
                if 'BGP not active' in line:
                    break
                if 'BGP neighbor' in line:
                    if 'external link' in line or 'internal link' in line:
                        has_bgp = True
                        a_line = line.split()
                        bgp_neighbor = a_line[3].replace(",", "")
                        local_bgps['bgpPeerRemoteAddr'].append(bgp_neighbor)
                        remote_as = a_line[6].replace(",", "")
                        local_bgps['bgpPeerRemoteAs'].append(remote_as)
                        local_as = a_line[9]
                    else:
                        has_bgp = False
                if has_bgp == False:
                    continue
                if 'BGP version' in line:
                    a_line = line.split()
                    remote_router = a_line[6].strip()
                elif 'BGP state' in line:
                    a_line = line.split()
                    state = a_line[2].capitalize()
                    state = state.replace(",", "")
                    admin_status = '2'
                    if state == "Idle":
                        admin_status = '1'
                    local_bgps['bgpPeerAdminStatus'].append(admin_status)
                    peer_state = states[state]
                    local_bgps['bgpPeerState'].append(peer_state)
                    duration = " ".join(a_line[i] for i in range(7, len(a_line)))
                    total_fsm = get_duration_sec(duration.strip())debug2: channel 0: window 999209 sent adjust 49367

                    local_bgps['bgpPeerFsmEstablishedTime'].append(total_fsm)
                elif 'Received' in line:
                    a_line = line.split()
                    msg_received = a_line[1]
                    local_bgps['bgpPeerInTotalMessages'].append(msg_received)
                    in_receive = True
                elif 'updates' in line and in_receive:
                    a_line = line.split()
                    upt_received = a_line[len(a_line)-2]
                    local_bgps['bgpPeerInUpdates'].append(upt_received)
                    in_receive = False
                elif 'Sent' in line:
                    a_line = line.split()
                    msg_sent = a_line[1]
                    local_bgps['bgpPeerOutTotalMessages'].append(msg_sent)
                elif 'Description' in line:
                    a_line = line.split()
                    description  = " ".join(a_line[i] for i in range(1, len(a_line)))
                    description = name + " - " + description
                    local_bgps['bgpVrfName'].append(description)
                elif 'updates' in line:
                    a_line = line.split()
                    upt_sent = a_line[len(a_line)-2]
                    local_bgps['bgpPeerOutUpdates'].append(upt_sent)
                elif 'Local host' in line:
                    a_line = line.split()
                    bgp_local = a_line[2].replace(",", "")
                    local_bgps['bgpPeerLocalAddr'].append(bgp_local)
                    bgp_port_local = a_line[len(a_line)-1]
                    local_bgps['bgpPeerLocalPort'].append(bgp_port_local)
                elif 'Foreign host' in line:
                    a_line = line.split()
                    bgp_port_remote = a_line[len(a_line)-1]
                    local_bgps['bgpPeerRemotePort'].append(bgp_port_remote)
                    neighbors = vrfs[j]['neighbors']
                    found_local_as = False
                    if len(neighbors):
                        for neigh in neighbors:
                            if neigh['local_AS'] == local_as:
                                found_local_as = True
                                found_peer = False
                                for peer in neigh['peers']:
                                    if peer['remote_AS'] == remote_as:
                                        peer['ips'].append({ 'description': description, 'remote_router': remote_router, 'bgp_neighbor': bgp_neighbor, 'bgp_port_remote': bgp_port_remote, 'bgp_local': bgp_local, 'bgp_port_local': bgp_port_local, 'data': { 'admin_status': admin_status, 'peer_state': peer_state, 'duration': total_fsm, 'msg_received': msg_received, 'upt_received': upt_received, 'msg_sent': msg_sent, 'upt_sent': upt_sent } } )
                                        found_peer = True
                                        break
                                if found_peer == False:
                                    neigh['peers'].append({ 'remote_AS': remote_as,  'ips': [ { 'description': description, 'remote_router': remote_router, 'bgp_neighbor': bgp_neighbor, 'bgp_port_remote': bgp_port_remote, 'bgp_local': bgp_local, 'bgp_port_local': bgp_port_local, 'data': { 'admin_status': admin_status, 'peer_state': peer_state, 'duration': total_fsm, 'msg_received': msg_received, 'upt_received': upt_received, 'msg_sent': msg_sent, 'upt_sent': upt_sent } } ] } )
                                break
                    if found_local_as == False:
                        neighbors.append({ 'local_AS': local_as, 'peers': [ { 'remote_AS': remote_as,  'ips': [ { 'description': description, 'remote_router': remote_router, 'bgp_neighbor': bgp_neighbor, 'bgp_port_remote': bgp_port_remote, 'bgp_local': bgp_local, 'bgp_port_local': bgp_port_local, 'data': { 'admin_status': admin_status, 'peer_state': peer_state, 'duration': total_fsm, 'msg_received': msg_received, 'upt_received': upt_received, 'msg_sent': msg_sent, 'upt_sent': upt_sent } } ] } ] } )

    bgps = local_bgps.copy()


gauge = Gauge('gauge_name', 'gauge description')

class CustomCollector(object):
    def __init__(self):
        pass

    def collect(self):
        #bgps = get_os10_metrics()

        bgpPeerAdminStatus = GaugeMetricFamily('bgpPeerAdminStatus', 'Peer Admin Status', labels=['bgpPeerRemoteAddr'])
        bgpPeerState = GaugeMetricFamily('bgpPeerState', 'Peer State', labels=['bgpPeerRemoteAddr'])
        bgpVrfName = GaugeMetricFamily('bgpVrfName', 'Peer BGP Description', labels=['bgpVrfName', 'bgpPeerRemoteAddr'])
        bgpPeerRemoteAs = GaugeMetricFamily('bgpPeerRemoteAs', 'Remote AS', labels=['bgpPeerRemoteAddr'])
        bgpPeerRemoteAddr = GaugeMetricFamily('bgpPeerRemoteAddr', 'Remote BGP', labels=['bgpPeerRemoteAddr'])
        bgpPeerRemotePort = GaugeMetricFamily('bgpPeerRemotePort', 'Remote BGP Port', labels=['bgpPeerRemoteAddr'])
        bgpPeerLocalAddr = GaugeMetricFamily('bgpPeerLocalAddr', 'Local BGP', labels=['bgpPeerLocalAddr', 'bgpPeerRemoteAddr'])
        bgpPeerLocalPort = GaugeMetricFamily('bgpPeerLocalPort', 'Local BGP Port', labels=['bgpPeerRemoteAddr'])
        bgpPeerFsmEstablishedTime = GaugeMetricFamily('bgpPeerFsmEstablishedTime', 'Established Time', labels=['bgpPeerRemoteAddr'])
        bgpPeerInTotalMessages = GaugeMetricFamily('bgpPeerInTotalMessages', 'Total of Input Messages', labels=['bgpPeerRemoteAddr'])
        bgpPeerOutTotalMessages = GaugeMetricFamily('bgpPeerOutTotalMessages', 'Total of Output Messages', labels=['bgpPeerRemoteAddr'])
        bgpPeerInUpdates = GaugeMetricFamily('bgpPeerInUpdates', 'Total of Input Updates', labels=['bgpPeerRemoteAddr'])
        bgpPeerOutUpdates = GaugeMetricFamily('bgpPeerOutUpdates', 'Total of Output Updates', labels=['bgpPeerRemoteAddr'])

        for i in range(len(bgps['bgpPeerRemoteAddr'])):
            bgpPeerAdminStatus.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerAdminStatus'][i])
            bgpPeerState.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerState'][i])
            bgpVrfName.add_metric([bgps['bgpVrfName'][i], bgps['bgpPeerRemoteAddr'][i]], '1')
            bgpPeerRemoteAs.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerRemoteAs'][i])
            bgpPeerRemoteAddr.add_metric([bgps['bgpPeerRemoteAddr'][i]], '1')
            bgpPeerRemotePort.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerRemotePort'][i])
            bgpPeerLocalAddr.add_metric([bgps['bgpPeerLocalAddr'][i], bgps['bgpPeerRemoteAddr'][i]], '1')
            bgpPeerLocalPort.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerLocalPort'][i])
            bgpPeerFsmEstablishedTime.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerFsmEstablishedTime'][i])
            bgpPeerInTotalMessages.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerInTotalMessages'][i])
            bgpPeerOutTotalMessages.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerOutTotalMessages'][i])
            bgpPeerInUpdates.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerInUpdates'][i])
            bgpPeerOutUpdates.add_metric([bgps['bgpPeerRemoteAddr'][i]], bgps['bgpPeerOutUpdates'][i])

        yield bgpPeerAdminStatus
        yield bgpPeerState
        yield bgpVrfName
        yield bgpPeerRemoteAs
        yield bgpPeerRemoteAddr
        yield bgpPeerRemotePort
        yield bgpPeerLocalAddr
        yield bgpPeerLocalPort
        yield bgpPeerFsmEstablishedTime
        yield bgpPeerInTotalMessages
        yield bgpPeerOutTotalMessages
        yield bgpPeerInUpdates
        yield bgpPeerOutUpdates



if __name__ == "__main__":
    start_http_server(8081)
    REGISTRY.register(CustomCollector())
    while True:
        config = get_configuration()
        device = config['device']
        get_os10_metrics(device['host'], device['user'], device['password'])
        time.sleep(120)
