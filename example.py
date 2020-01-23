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
import numpy as np
import simpy

from component import Server, LoadGenerator

if __name__ == '__main__':
    concurrency = 50
    no_of_cores = 4

    processing_time = 5
    think_time = 10

    pool_size = 100
    time_slice = 5
    cs_overhead = 0  # overhead due to context switches

    env = simpy.Environment()

    # request
    # jmeter --> server 0 --> server 1 --> server 3 --> server 1 --> server 0 --> server 2 --> server 0 --> jmeter

    # create an array of servers
    servers_arr = [Server(env,
                          avg_process_time=1,
                          no_of_cores=no_of_cores,
                          max_pool_size=pool_size,
                          time_slice=time_slice,
                          cs_overhead=cs_overhead,
                          name='0'),

                   Server(env,
                          avg_process_time=2,
                          no_of_cores=4,
                          max_pool_size=pool_size,
                          time_slice=time_slice,
                          cs_overhead=cs_overhead,
                          name='1'),

                   Server(env,
                          avg_process_time=5,
                          no_of_cores=2,
                          max_pool_size=pool_size,
                          time_slice=time_slice,
                          cs_overhead=cs_overhead,
                          name='2'),

                   Server(env,
                          avg_process_time=5,
                          no_of_cores=2,
                          max_pool_size=pool_size,
                          time_slice=time_slice,
                          cs_overhead=cs_overhead,
                          name='3')]

    # load generator (jmeter equivalent)
    load_generator = LoadGenerator(env,
                                   avg_think_time=think_time,
                                   no_of_users=concurrency,
                                   name='1')

    # connect jmeter and the server0
    load_generator.connect(servers_arr[0])

    # invoke server 1 and 2 from server 0
    servers_arr[0].connect(servers_arr[1])
    servers_arr[0].connect(servers_arr[2])

    # invoke server 3 from server 1
    servers_arr[1].connect(servers_arr[3])

    # initialized the load generator (will generate 50 users)
    load_generator.initiate()

    print("simulation started")

    # run the experiments for 10000 milliseconds
    # time is not measured in system time, therefore thread sleep will have no effect here
    # also any processing/computations to execute the simulation have no effect
    env.run(10000)

    for i, server in enumerate(servers_arr):
        print("\n====== server %d ======" % i)
        print(np.mean(load_generator.get_response_times(server)))
        print(np.mean(load_generator.get_queue_lengths(server)))
        print(len(load_generator.get_response_times(server)))
