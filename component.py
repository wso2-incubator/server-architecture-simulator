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

import simpy
import logging
import random
import numpy as np
from abc import abstractmethod, ABC

from model import DataPacket, STATUS_ONHOLD, STATUS_PROCESSING, STATUS_COMPLETED

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SEED = 42
random.seed(SEED)


class __Node:
    def __init__(self, env, name):
        # store simpy environment
        self.env = env

        # main input queue
        self.input_queue = simpy.Store(env)

        self.name = name

    def get_input_queue(self):
        return self.input_queue

    @abstractmethod
    def initiate(self):
        pass

    @abstractmethod
    def register_tasks(self, service):
        pass

    def connect(self, service):
        self.register_tasks(service)
        service.initiate()

    def send(self, data: DataPacket, service, input_queue):
        data.send_server(service)
        service.get_input_queue().put(data)
        return input_queue.get(filter=lambda x: True if x.user_id == data.user_id else False)


class Client(__Node, ABC):
    def __init__(self, env, name):
        super().__init__(env, name)
        self.name = "client-%s" % str(self.name)
        self.input_queue = simpy.FilterStore(env)

        self.connected_service = None
        self.served_requests = []

    def invoke(self, user_id):
        # create request
        request = DataPacket(self.env, user_id)

        # send request and wait till response
        response = yield self.send(request, self.connected_service, self.input_queue)
        request.receive_client(self.connected_service)
        self.served_requests.append(request)

    def get_start_times(self, service):
        st_arr = []
        for request in self.served_requests:
            st = request.get_req_start_time(service)
            if st is None:
                logger.warning('request start time is not computed for service %s' % service.name)
            else:
                st_arr.append(st)
        return st_arr

    def get_processing_times(self, service):
        pt_arr = []
        for request in self.served_requests:
            pt = request.get_processed_time(service)
            if pt is None:
                logger.warning('processing time is not computed for service %s' % service.name)
            else:
                pt_arr.append(pt)
        return pt_arr

    def get_response_times(self, service):
        rt_arr = []
        for request in self.served_requests:
            rt = request.get_response_time(service)
            if rt is None:
                logger.warning('response time is not computed for service %s' % service.name)
            else:
                rt_arr.append(rt)
        return rt_arr

    def get_queue_lengths(self, service):
        ql_arr = []
        for request in self.served_requests:
            ql = request.get_queue_length(service)
            if ql is None:
                logger.warning('queue length is not computed for service %s' % service.name)
            else:
                ql_arr.append(ql)
        return ql_arr

    def initiate(self):
        pass

    def register_tasks(self, service):
        self.connected_service = service
        service.out_pipe = self.input_queue


class LoadGenerator(Client):
    def __init__(self, env, name, avg_think_time, no_of_users=100, think_time_dist=lambda x: random.expovariate(1 / x)):
        """
        initiate a load generator for closed system simulations
        simulates jmeter
        :param env: simpy environment
        :param avg_think_time: average think time prior to sending request
        :param no_of_users: no of users to simulate
        :param think_time_dist : allows passing custom think time distributions
        :param name: name of the instance
        """
        self.avg_think_time = avg_think_time
        self.no_of_users = no_of_users
        self.think_time_dist = think_time_dist

        super().__init__(env, name)
        self.name = "generator-%s" % str(self.name)

    def __execute(self, user_id):
        while True:
            # user thinks
            if self.avg_think_time > 0:
                think_time = self.think_time_dist(self.avg_think_time)
                yield self.env.timeout(think_time)

            yield from self.invoke(user_id)

    def initiate(self):
        for user_id in range(self.no_of_users):
            self.env.process(self.__execute(user_id))


class Server(__Node, ABC):

    def __init__(self, env, name, avg_process_time, no_of_cores=4, max_pool_size=100, time_slice=1, cs_overhead=0.1,
                 process_time_dist=lambda x: random.expovariate(1 / x)):
        """
        initialized an server instance
        :param env: simply environment
        :param avg_process_time: average processing time
        :param no_of_cores: number of cores assigned to the server
        :param max_pool_size: size of the main thread pool
        :param time_slice: time given to a single thread by the scheduler
        :param cs_overhead: context switch overhead
        :param process_time_dist : allows passing custom process time distributions
        :param name: name of the instance
        """

        # workload params
        self.avg_process_time = avg_process_time
        self.no_of_cores = no_of_cores

        self.max_pool_size = max_pool_size
        self.time_slice = time_slice
        self.cs_overhead = cs_overhead
        self.process_time_dist = process_time_dist

        # application params
        self.task_queue = [self]

        super().__init__(env, name)
        self.name = "server-%s" % str(self.name)

        # current thread count
        self.thread_count = 0

        # store responses
        self.pool_queue = simpy.Store(env)
        self.response_queue = simpy.FilterStore(env)

        # should be initiated
        self.out_pipe = None

    def __kernel(self):
        while True:
            if self.thread_count < self.max_pool_size:
                if self.avg_process_time > 0:
                    request = yield self.get_input_queue().get()
                    request.arrive_server(self)

                else:
                    raise Exception("${avg_processing_time} should be greater than zero")

                # acquire a thread
                self.thread_count += 1
                yield self.pool_queue.put(request)
            else:
                yield self.env.timeout(0.1)

    def __execute(self):
        env = self.env
        input_queue = self.pool_queue
        time_slice = self.time_slice

        while True:

            request = yield input_queue.get()
            current_node = request.look_current_node(self.name)
            current_status = request.read_status(self)
            cs_overhead = self.cs_overhead

            if current_status == STATUS_PROCESSING:
                if current_node == 0:  # and process_time > 0
                    processing_time = request.process_data(self, time_slice)
                    if processing_time == time_slice:
                        # do some processing
                        yield env.timeout(time_slice)
                    else:
                        # process rest of the request
                        if processing_time > 0:
                            yield env.timeout(processing_time)
                        else:
                            logger.warning("process time <= 0 but still trying to process")

                        # move to next task
                        request.move_next_node(self.name)

                    # round robin scheduling
                    input_queue.put(request)
                else:  # have already processed the data
                    if len(self.task_queue) > current_node:  # invoke other services
                        next_service = self.task_queue[current_node]
                        request.set_onhold(self)
                        response = self.send(request, next_service, self.response_queue)

                        # round robin scheduling
                        input_queue.put(request)

                    else:  # serving request is completed
                        # release a thread
                        self.thread_count -= 1
                        request.depart_server(self)
                        yield self.out_pipe.put(request)

            elif current_status == STATUS_ONHOLD:
                next_service = self.task_queue[current_node]
                if request.read_status(next_service) == STATUS_COMPLETED:
                    request.receive_client(next_service)
                    request.move_next_node(self.name)
                    request.release_onhold(self)
                else:
                    if cs_overhead <= 0:
                        yield env.timeout(0.1)
                # round robin scheduling
                input_queue.put(request)
            else:
                raise Exception('undefined execution path')
            # context switch overhead
            if cs_overhead > 0:
                yield env.timeout(cs_overhead)

    def initiate(self):
        self.env.process(self.__kernel())
        for i in range(self.no_of_cores):
            self.env.process(self.__execute())

    def register_tasks(self, service):
        self.task_queue.append(service)
        service.out_pipe = self.response_queue

    def compute_processing_time(self):
        return self.process_time_dist(self.avg_process_time)
