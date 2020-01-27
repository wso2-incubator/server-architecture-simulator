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
        self.node_stats[service.name] = stat
        self.status[service.name] = STATUS_WAITING

    def arrive_server(self, service):
        name = service.name
        stat = self.node_stats[name]
        stat.update_at_server()
        self.register_current_node(name)
        self.status[name] = STATUS_PROCESSING

    def depart_server(self, service):
        name = service.name
        self.status[name] = STATUS_COMPLETED

    def receive_client(self, service):
        stat = self.node_stats[service.name]
        stat.update_at_client()

    def set_onhold(self, service):
        self.status[service.name] = STATUS_ONHOLD

    def release_onhold(self, service):
        self.status[service.name] = STATUS_PROCESSING

    def read_status(self, service):
        return self.status[service.name]

    def get_response_time(self, service):
        return self.node_stats[service.name].response_time

    def get_waiting_time(self, service):
        return self.node_stats[service.name].waiting_time

    def get_queue_length(self, service):
        return self.node_stats[service.name].queue_length

    def get_processing_time(self, service):
        return self.node_stats[service.name].processing_time

    def get_processed_time(self, service):
        return self.node_stats[service.name].elapsed_time

    def get_req_start_time(self, service):
        return self.node_stats[service.name].start_time

    def process_data(self, service, time_slice):
        processing_time = self.node_stats[service.name].processing_time
        if processing_time > time_slice:
            self.node_stats[service.name].processing_time -= time_slice
            self.node_stats[service.name].elapsed_time += time_slice
            return time_slice
        else:
            self.node_stats[service.name].processing_time = 0
            self.node_stats[service.name].elapsed_time += processing_time
            return processing_time

    def register_current_node(self, name):
        if name in self.current_node:
            raise Exception('service : %s is already registered in current nodes' % name)
        self.current_node[name] = 0

    def move_next_node(self, name):
        self.current_node[name] += 1

    def look_current_node(self, name):
        return self.current_node[name]


class APIStat:

    def __init__(self, env, service):
        self.env = env
        self.service = service
        self.start_time = env.now

        self.processing_time = None
        self.elapsed_time = None

        self.waiting_time = None
        self.response_time = None
        self.queue_length = None

    def update_at_server(self):
        self.waiting_time = self.env.now - self.start_time
        self.processing_time = self.service.compute_processing_time()
        self.elapsed_time = 0
        self.queue_length = len(self.service.get_input_queue().items) + self.service.thread_count + len(
            self.service.get_input_queue().put_queue)

    def update_at_client(self):
        self.response_time = self.env.now - self.start_time
