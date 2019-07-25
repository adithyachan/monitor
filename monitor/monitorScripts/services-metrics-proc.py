#!usr/bin/python

from influxdb import InfluxDBClient
#from termcolor import colored
from datetime import datetime, timedelta
import time
import subprocess
import os

def find_last(list, end, n):
    start = list.find(end)
    while start >= 0 and n > 1:
        start = list.find(end, start+len(end))
        n -= 1
    return start

def print_status(service, services_status, services_sub, numServices):
    print("%-40s%-20s%-20s" % ("Service", "Status", "Sub"))
    print("-" * 80)
    for i in range(0, numServices):
        service_align  = '{num:{width}}'.format(num=services[i], width= 40)
        status_align = '{num:{width}}'.format(num=services_status[i], width= 20)
        sub_align = '{num:{width}}'.format(num=services_sub[i], width= 20)
        if services_status[i] == "inactive":
            print (service_align + colored(status_align, 'red') + sub_align)
        else:
            print (service_align + colored(status_align, 'green') + sub_align)

def make_point(service, status, sub):
    points = []
    time = datetime.now() + timedelta(hours=7)
    point = {
        "measurement":"service",
        "time": time.isoformat() + "Z",
        "fields": {
            "name":service,
            "status":status,
            "sub":sub
        }
    }
    points.append(point)
    return points

def make_proc_point(procToMonitor):
    points = []
    time = datetime.now() + timedelta(hours=7)
    for proc, val in procToMonitor.items():
        point1 = {
            "measurement":"cpu",
            "time": time.isoformat() + "Z",
            "fields": {
                proc:val[0]
            }
        }
        point2 = {
            "measurement":"mem",
            "time": time.isoformat() + "Z",
            "fields": {
                proc:val[1]
            }
        }
        points.append(point1)
        points.append(point2)
    return points

def make_system_point(cpu, mem, proc):
    points = []
    time = datetime.now() + timedelta(hours=7)
    measurments = ["cpu", "mem", "processes"]
    point = {}
    for measurement in measurments:
        if measurement == "cpu":
            point = {
                "measurement":measurement,
                "time": time.isoformat() + "Z",
                "fields": {
                    "usage_idle":float(cpu.get("usage_idle")),
                    "n_cpus":float(cpu.get("n_cpus")),
                    "n_threads":float(cpu.get("n_cpus")) * 2
                }
            }
        elif measurement == "mem":
            point = {
                "measurement":measurement,
                "time": time.isoformat() + "Z",
                "fields": {
                    "used":float(mem.get("used")),
                    "total":float(mem.get("total")),
                    "used_percent":float(mem.get("used"))/float(mem.get("total")) * 100

                }
            }
        elif measurement == "processes":
            point = {
                "measurement":measurement,
                "time": time.isoformat() + "Z",
                "fields": {
                    "blocked":int(proc.get("blocked")),
                    "total":int(proc.get("total")),
                    "idle":int(proc.get("idle"))
                }
            }
        points.append(point)
    return points

def read_Config(file):
    lines = file.readlines()
    numServicesToShow = 10
    numServices = 0
    services = []
    quiet = True
    all = True
    for i in range(0, len(lines)):
        if lines[i] == "\n":
            continue
        if lines[i].strip()[0] == "#":
            continue
        else:
            if lines[i][0:lines[i].find(" ")] == "Services":
                s = lines[i][lines[i].find(":") + 1: lines[i].find("\n")]
                if s.strip() == "[all]":
                    continue
                else:
                    all = False
                    for i in range(0, s.count(",") + 1):
                        numServices = s.count(",") + 1
                        services.append(s[find_last(s, "[", i + 1) + 1:find_last(s, "]", i + 1)])
            elif lines[i][0:lines[i].find(" ")] == "Top":
                numServicesToShow = int(lines[i][lines[i].find(":") + 2:lines[i].find("\n")])
            elif lines[i][0:lines[i].find(" ")] == "quiet":
                if lines[i][lines[i].find(":"):lines[i].find("\n")] == 'y':
                    quiet = False
                else:
                    quiet = True
    return quiet, numServices, all, services, numServicesToShow

all = True

client = InfluxDBClient()
configFile = open("monitorScripts/config/conf.txt", 'r')


if (checkFile.read(1) == 'n'):
    makeDB = True
quiet, numServices, all, services, numServicesToShow = read_Config(configFile)

client.create_database("Services")
client.create_database("Metrics")
client.create_database("Processes")





numServicesToShow = 0

logFile = open("monitorScripts/logs/log.txt", "a")
logFile.write("script started at:" + str((datetime.now() + timedelta(hours=9))))
if (numServices > numServicesToShow):
    numServicesToShow = numServices

while True:

    if all:
        pullServices = ['systemctl', 'list-unit-files', '-t', 'service']
        services_super_raw = subprocess.run(pullServices, stdout=subprocess.PIPE).stdout.decode("utf-8")
        numServices = services_super_raw.count("\n") - 3

        services_raw = services_super_raw[services_super_raw.find("\n") + 1:find_last(services_super_raw, "\n", numServices + 1)]

        for i in range(0, numServices):
            numServices -= 1
            serviceTemp = services_raw[:services_raw.find(" ")]
            if not("@" in serviceTemp):
                services.append(serviceTemp[:serviceTemp.rfind(".")])
                numServices += 1
            services_raw = services_raw[services_raw.find("\n") + 1:]

    services_status = []
    services_sub = []

    for service in services:
        pullStatus = ['systemctl', 'status', service]
        string_raw = subprocess.run(pullStatus, stdout=subprocess.PIPE).stdout.decode("utf-8")
        string = string_raw[string_raw.find("Active: "):string_raw.find("\n", string_raw.find("Active: "))]
        services_status.append(string[8:string.find("(")].strip())
        services_sub.append(string[string.find("(") + 1:string.find(")")].strip())

    top = ['top', '-b','-n', '1']
    top_string_super_raw = subprocess.run(top, stdout=subprocess.PIPE).stdout.decode("utf-8")

    top_string_raw = top_string_super_raw[:find_last(top_string_super_raw, "\n", 8 + numServicesToShow )]

    processes_string = top_string_raw[find_last(top_string_super_raw, "\n", 7):]


    tempProcFileWrite = open("monitorScripts/.temp.txt", "w+")
    tempProcFileWrite.write(processes_string)

    tempProcFileWrite.close()

    tempProcFileRead = open("monitorScripts/.temp.txt", "r")

    procList = tempProcFileRead.readlines()
    tempProcFileRead.close()


    procDic = {}

    for line in procList:
        if (line[0] == "\n"):
            continue
        else:
            process = line[line.rfind(" "):line.rfind("\n")].strip()
            cpunmem = line[line.find(".") - 3:line.rfind(".") - 6].strip()

            cpu = float(cpunmem[:cpunmem.find(" ")])
            mem = float(cpunmem[cpunmem.find(" "):])
            procDic[process] = [cpu, mem]

    cpu_string = top_string_raw[find_last(top_string_raw, "\n", 2) + 1:find_last(top_string_raw, "\n", 3)]
    mem_string = top_string_raw[find_last(top_string_raw, "\n", 3) + 1:find_last(top_string_raw, "\n", 4)]
    proc_string = top_string_raw[top_string_raw.find("\n") + 1:find_last(top_string_raw, "\n", 2)]

    cores = ['getconf', '_NPROCESSORS_ONLN']
    cores_string = subprocess.run(cores, stdout=subprocess.PIPE).stdout.decode("utf-8")

    cpu = {
        "usage_idle":cpu_string[find_last(cpu_string, ",", 3) + 1:find_last(cpu_string, ",", 4) - 3].strip(),
        "n_cpus":int(cores_string.strip())
    }

    mem = {
        "used":mem_string[find_last(mem_string, ",", 2) + 1:find_last(mem_string, ",", 3) - 4].strip(),
        "total":mem_string[mem_string.find(":") + 1:mem_string.find(",") - 5].strip()
    }


    proc = {
        "total":proc_string[proc_string.find(":") + 1:proc_string.find(",") - 5].strip(),
        "blocked":proc_string[find_last(proc_string, ",", 3) + 1:find_last(proc_string, ",", 4) - 7].strip(),
        "idle":proc_string[find_last(proc_string, ",", 2) + 1:find_last(proc_string, ",", 3) - 8].strip()
    }
    #print_status(service, services_status, services_sub, numServices)

    client.write_points(make_proc_point(procDic), time_precision="u", database="Processes", protocol = 'json')
    client.write_points(make_system_point(cpu, mem, proc), time_precision="u", database="Metrics", protocol = 'json')

    if (quiet):
        logFile.write("Last write at:" + str(datetime.now()))

    for i in range(0, numServices):
        client.write_points(make_point(services[i], services_status[i], services_sub[i]), time_precision="u", database="Services", batch_size=None, protocol = u'json')
    time.sleep(7)
