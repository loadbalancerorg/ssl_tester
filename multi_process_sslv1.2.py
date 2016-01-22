#!/usr/bin/python
#######################################################
# Multithreaded SSL Load tester for load testing pound
# Mark Brookes 26/01/12
#
#
#######################################################


import multiprocessing
import os
import time
# import httplib
import urllib2
import ssl
import Queue
import itertools
import signal
import csv
from random import randint

processes = 14
host = 'https://192.168.134.113'
file = '/index.html'
process_stats_list = []  # a list of instances containing process_stats
# seconds
test_time = 60


class process_stats:
    def __init__(self, time_taken_to_complete="not_set", total_connections="not_set", average_conns_per_sec="not_set",
                 process_id="not_set"):
        self.time_taken_to_complete = time_taken_to_complete
        self.total_connections = total_connections
        self.average_conns_per_sec = average_conns_per_sec
        self.process_id = process_id


def add_process_stats(process_stats_instance, process_stats_list):
    process_stats_list.append(process_stats_instance)
    return


def process_info():
    print('module name: ', __name__)
    print('parent process: ', os.getppid())
    print('process id: ', os.getpid())


def handler(signum, frame):
    print('hello')


def f(results):
    # process_info()
    connection_counter = 0
    response_status = 200
    process_id = str(os.getpid())
    print(process_id + " Started")
    start_time = time.time()
    runtime = int(start_time) + int(test_time)
    while int(time.time()) <= runtime and response_status == 200:
        try:
            process_time_taken = time.time() - start_time
            conn = urllib2.urlopen(host, timeout=2)
            response_status = conn.getcode()
            conn.close()

            if response_status != 200:
                print("REQUEST FAILED: " + process_id + " " + str(connection_counter) + " " + str(resp.status))
                continue
        # may not work.
        except ssl.SSLError:
            print("SSL TIMEOUT ERROR: " + process_id + " Connections Completed: " + str(connection_counter))
            continue
        except KeyboardInterrupt:
            print("INTERRUPTED!")
            print(connection_counter)
            break
        # add successful connections to the connection counter
        connection_counter = connection_counter + 1
        results.put([process_id, connection_counter, process_time_taken])

    print(process_id + " Ended " + str(connection_counter) + " Time Taken: " + str(process_time_taken))


def generate_stats_file(stats_list):
    uni_pids = []
    for row in stats_list:
        if row[0] not in uni_pids:
            uni_pids.append(row[0])

    total_conns = {0: 0}
    connection_rate = {}
    for pid in uni_pids:
        start_second = 0
        end_second = 1
        x = True
        while x:

            # filter the list so you only get the results for 1 process id at a time
            filtered_by_process_id = [item for item in stats_list if
                                      item[0] == pid and item[2] >= start_second and item[2] <= end_second and item[
                                          2] <= test_time]
            # if there are no results returned we have reached the end of the list
            if len(filtered_by_process_id) is 0:
                x = False
                continue
            if end_second not in total_conns:
                total_conns[end_second] = 0

            max_list = max(filtered_by_process_id)
            total_conns[end_second] = max_list[1] + total_conns[end_second]

            start_second += 1
            end_second += 1
    print(total_conns)
    key_list = total_conns.keys()
    key_list.sort(key=int)
    # calculate the connection rate
    conn_rate = {}
    while key_list:
        start_value = total_conns[key_list.pop(0)]
        try:
            end_value = total_conns[key_list[0]]
        except IndexError:
            continue
        conn_rate[key_list[0]] = int(end_value) - int(start_value)

    conn_rate[0] = os.uname()[1]
    print(conn_rate)
    with open('data.csv', 'wb') as csvfile:
        x = csv.DictWriter(csvfile, fieldnames=sorted(conn_rate.keys(), key=int), delimiter=',', quotechar='|',
                           quoting=csv.QUOTE_MINIMAL)
        x.writeheader()
        x.writerow(conn_rate)


if __name__ == '__main__':
    delay = '0.0{}'.format(randint(1, 9))
    time.sleep(float(delay))
    print('Start delayed {} seconds'.format(delay))
    results = multiprocessing.Queue()
    for i in range(processes):
        p = multiprocessing.Process(target=f, args=(results,))
        # insert delay to processes to stop all making requests
        # at the same time.
        time.sleep(0.05)
        p.start()
        p.join

    stats_list = []
    while len(multiprocessing.active_children()) > 0:

        try:
            throughput_stats = results.get(True, 1)
            stats_list.append(throughput_stats)
        except Queue.Empty:
            print("No More Data From Processes (This is normal)")

            # print "process_id" + str(throughput_stats[0])
            # print "counter" + str(throughput_stats[1])
            # print "timer" + str(throughput_stats[2])
    # print (stats_list)
    # take the generated stats and create a csv to be used for graphing
    generate_stats_file(stats_list)
    unique_pids = []
    for stats in stats_list:
        # print stats[0]
        if stats[0] not in unique_pids:
            unique_pids.append(stats[0])

    for pids in unique_pids:
        max_time = 0
        # print pids
        process_stats_obj = process_stats(process_id=pids)
        # print "here"
        # print process_stats_obj.process_id
        for stats in stats_list:
            if pids == stats[0]:  # extract max time and maximum connections for each process
                if stats[2] > max_time:
                    max_time = stats[2]
                    process_stats_obj.time_taken_to_complete = stats[2]
                    process_stats_obj.total_connections = stats[1]
        # print process_stats_obj.time_taken_to_complete
        # print process_stats_obj.total_connections
        process_stats_obj.average_conns_per_sec = process_stats_obj.total_connections / process_stats_obj.time_taken_to_complete
        # print process_stats_obj.average_conns_per_sec
        add_process_stats(process_stats_obj, process_stats_list)

    total_conn_stat = 0
    average_total_conn_stat = 0
    for process_obj in process_stats_list:
        print("-----------STATS PER PROCESS --------------")
        print("Process Id: " + str(process_obj.process_id))
        print("Total Requests Made: " + str(process_obj.total_connections))
        print("Average Requests /s: " + str(process_obj.average_conns_per_sec))
        print("Time Taken For Process: " + str(process_obj.time_taken_to_complete))
        print("-------------------------------------------")
        average_total_conn_stat = average_total_conn_stat + process_obj.average_conns_per_sec
        total_conn_stat = total_conn_stat + process_obj.total_connections
    print("--------------Total Stats ----------------------")
    print("Total Requests Made: " + str(total_conn_stat))
    print("Total Average Requests /s: " + str(average_total_conn_stat))
    print("------------------------------------------------")
    # print unique_pids
    # TODO print summary stats
