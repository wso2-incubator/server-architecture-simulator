"""
 Copyright (c) 2020, WSO2 Inc. (http://www.wso2.org) All Rights Reserved.

  WSO2 Inc. licenses this file to you under the Apache License,
  Version 2.0 (the "License"); you may not use this file except
  in compliance with the License.
  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing,
  software distributed under the License is distributed on an
  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
  KIND, either express or implied.  See the License for the
  specific language governing permissions and limitations
  under the License.
"""
import os

import numpy as np
import pandas as pd
import simpy

from component import Server, LoadGenerator

# example ==================================================
# +++++++++++++++++++ HOW TO RUN SIMULATOR +++++++++++++++++
# simulated data flow ---- execution flow ---- request flow
############################################################
# jmeter --> server 0 --> server 1 --> server 3 --> server 1 --> server 0 --> server 2 --> server 0 --> jmeter


if __name__ == '__main__':

    # parameters to load generator
    concurrency = 100  # no of users simulated
    avg_think_time = 0

    # parameters to define server resources and configurations
    no_of_cores = 4
    pool_size = 10
    time_slice = 5
    cs_overhead = 0  # overhead due to context switches

    # initiate simpy simulation environment
    env = simpy.Environment()

    # create an array of servers
    servers_arr = [Server(env,
                          avg_process_time=0,
                          no_of_cores=no_of_cores,
                          max_pool_size=100,
                          time_slice=time_slice,
                          cs_overhead=cs_overhead,
                          name='0'),

                   # Server(env,
                   #        avg_process_time=2,
                   #        no_of_cores=4,
                   #        max_pool_size=pool_size,
                   #        time_slice=time_slice,
                   #        cs_overhead=cs_overhead,
                   #        name='1'),

                   Server(env,
                          avg_process_time=10,
                          no_of_cores=2,
                          max_pool_size=pool_size,
                          time_slice=time_slice,
                          cs_overhead=cs_overhead,
                          name='2'),

                   # Server(env,
                   #        avg_process_time=50,
                   #        no_of_cores=2,
                   #        max_pool_size=pool_size,
                   #        time_slice=time_slice,
                   #        cs_overhead=cs_overhead,
                   #        name='3')
                   ]

    # load generator (jmeter equivalent)
    load_generator = LoadGenerator(env,
                                   avg_think_time=avg_think_time,
                                   no_of_users=concurrency,
                                   name='1')

    # connect jmeter and the server0
    load_generator.connect(servers_arr[0])

    # invoke server 1 and 2 from server 0
    servers_arr[0].connect(servers_arr[1])
    # servers_arr[0].connect(servers_arr[1])
    # servers_arr[0].connect(servers_arr[1])

    print("simulation started")

    # run the experiments for 10000 milliseconds
    # time is not measured in system time, therefore thread sleep will have no effect here
    # also any processing/computations to execute the simulation have no effect
    env.run(10000)

    # it is recommended to omit warm up period when reporting the measurements
    warm_up_ratio = 0.25

    api_name_suffix = "ballerina/http/Client#get#"
    data_dir = "set4/c=%d" % concurrency
    meta_filename = "meta.csv"
    meta_file = None

    TIME_STAMP_PROPERTY = "timestamp"
    AVG_RESPONSE_TIME_COL = "avg_response_time"
    THROUGHPUT_COL = "throughput"
    IN_PROGRESS_REQ_COUNT_COL = "in_progress_req"
    ENV_NAME_COL = "env_name"

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    else:
        meta_path = os.path.join(data_dir, meta_filename)
        if os.path.exists(meta_path):
            meta_file = pd.read_csv(meta_path)

    if meta_file is None:
        meta_file = pd.DataFrame({
            "api_name": [],
            "file_name": []
        })

    for i, server in enumerate(servers_arr):
        print("\n====== server %d ======" % i)
        api_name = "".join([api_name_suffix, server.name, ".com"])
        file_name = server.name + "z.csv"

        meta_file = meta_file.append({
            "api_name": api_name,
            "file_name": file_name
        }, ignore_index=True)

        latency_arr = load_generator.get_response_times(server)
        start_times = load_generator.get_start_times(server)

        warm_up_limit = int(len(latency_arr) * warm_up_ratio)

        time_stamps = start_times[warm_up_limit:]
        _length = len(time_stamps)
        latency = latency_arr[warm_up_limit:]
        wip = load_generator.get_queue_lengths(server)[warm_up_limit:]
        tps = np.divide(wip, latency) * 1000  # little's low
        env_name = ["sim"] * _length

        data_dic = {
            AVG_RESPONSE_TIME_COL: latency,
            IN_PROGRESS_REQ_COUNT_COL: wip,
            THROUGHPUT_COL: tps,
            ENV_NAME_COL: env_name,
            TIME_STAMP_PROPERTY: time_stamps
        }

        data_df = pd.DataFrame(data_dic)

        data_df.to_csv(os.path.join(data_dir, file_name))

        # here we compute the tps using little's law
        # it is possible to use process start times to compute tps
        tps_computed = np.mean(tps)

        tps_measure = len(start_times) / (start_times[-1] - start_times[0]) * 1000

        print('no of request completed %d ' % int(len(latency_arr)))
        print("latency : %.2f" % np.mean(latency))
        print("work-in-progress : %.2f" % np.mean(wip))
        print('throughput measured - %.2f' % tps_measure)
        print('throughput computed - %.2f (using little\'s law)' % tps_computed)
        print()

    meta_file.to_csv(os.path.join(data_dir, meta_filename))
