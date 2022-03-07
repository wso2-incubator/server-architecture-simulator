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

STATUS_PROCESSING = 'processing'
STATUS_WAITING = 'waiting'
STATUS_ONHOLD = 'onhold'
STATUS_COMPLETED = 'completed'


class DataPacket:

    def __init__(self, env, user_id):
        self.env = env
        self.user_id = user_id

        self.node_stats = {}
        self.current_node = {}
        self.status = {}

    def send_server(self, service):
        stat = APIStat(self.env, service)

        if self.node_stats.get(service.name) is None:
            self.node_stats[service.name] = []
            self.status[service.name] = []
            self.current_node[service.name] = []

        self.node_stats[service.name].append(stat)
        self.status[service.name].append(STATUS_WAITING)

    def arrive_server(self, service):
        name = service.name
        stat = self.node_stats[name][-1]
        stat.update_at_server()
        self.register_current_node(name)
        self.status[name][-1] = STATUS_PROCESSING

    def depart_server(self, service):
        name = service.name
        self.status[name][-1] = STATUS_COMPLETED

    def receive_client(self, service):
        stat = self.node_stats[service.name][-1]
        stat.update_at_client()

    def set_onhold(self, service):
        self.status[service.name][-1] = STATUS_ONHOLD

    def release_onhold(self, service):
        self.status[service.name][-1] = STATUS_PROCESSING

    def read_status(self, service):
        return self.status[service.name][-1]

    def get_response_time(self, service):
        return [stat.response_time for stat in self.node_stats[service.name]]

    def get_waiting_time(self, service):
        return [stat.waiting_time for stat in self.node_stats[service.name]]

    def get_queue_length(self, service):
        return [stat.queue_length for stat in self.node_stats[service.name]]

    def get_processing_time(self, service):
        return [stat.processing_time for stat in self.node_stats[service.name]]

    def get_processed_time(self, service):
        return [stat.elapsed_time for stat in self.node_stats[service.name]]

    def get_req_start_time(self, service):
        return [stat.get_start_time() for stat in self.node_stats[service.name]]

    def process_data(self, service, time_slice):
        stat = self.node_stats[service.name][-1]
        processing_time = stat.processing_time
        if processing_time > time_slice:
            stat.processing_time -= time_slice
            stat.elapsed_time += time_slice
            return time_slice
        else:
            stat.processing_time = 0
            stat.elapsed_time += processing_time
            return processing_time

    def register_current_node(self, name):
        self.current_node[name].append(0)

    def move_next_node(self, name):
        self.current_node[name][-1] += 1

    def look_current_node(self, name):
        return self.current_node[name][-1]


class APIStat:

    def __init__(self, env, service):
        self.env = env
        self.service = service
        self._start_time = env.now

        self.processing_time = None
        self.elapsed_time = None

        self.waiting_time = None
        self.response_time = None
        self.queue_length = None

    def get_start_time(self):
        return self._start_time

    def update_at_server(self):
        self.waiting_time = self.env.now - self.get_start_time()
        self.processing_time = self.service.compute_processing_time()
        self.elapsed_time = 0
        self.queue_length = len(self.service.get_input_queue().items) + self.service.thread_count + len(
            self.service.get_input_queue().put_queue) + 1  # 1 is for the current pack

    def update_at_client(self):
        self.response_time = self.env.now - self.get_start_time()
