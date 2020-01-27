# server-architecture-simulator

Server architecture simulations framework using discrete events simulations

Can simulate both orchestration or choreography based architectures using discrete event simulations.

## Main features

### Simulation of load generators 

Can use to simulate load generators (jmeter like fashion) to conduct closed system analysis. The tool allows changing the concurrency (no. of users) and think time. Moreover, any custom distribution parameterized by average think time can be passed as the think time distribution. The default distribution is exponential distribution.


### Simulation of servers

Can be used to simulate simple servers with an unbounded service queue and a kernel thread queue. The simulation of kernel thread queue is very crucial because it enables the communication with other servers without busy waiting of the cores. If max thread-pool size < no of users, the kernel thread-pool acts as a bounded connection-pool rather than the unbounded OS-kernel thread-pool. Otherwise, the thread-pool can be considered as an unbounded OS-kernel thread-pool.

Following server parameters can be configured.

 - avg. process_time: average processing time (in milliseconds)
 - no. of cores: number of cores assigned to the server
 - max pool size: upper bound of kernel thread pool
 - time slice: time allocated to a single thread by the scheduler in between two context switches
 - context switch overhead: overhead due to a single context switch (in milliseconds) 
 - process time distribution : allows passing custom process time distributions
 - name : Unique identifier for each node in the system. A unique names for each server is essential for multi-server architectures 
        
### In-build measurements to collect basic metrics

Collect the essential basic metrics at the load generator for each server that the requests are passing through.
  - response times
  - work-in-progress 
  - request initiated time (from each node) - useful to compute the throughput
  

## Basic Usage

### Simple sever-client architecture

1. First initiate a simpy simulation environment

        # initiate simpy simulation environment
        env = simpy.Environment()
    
2. Now initiate a load generator

        # initiate the LoadGenerator with 100 users 
        load_generator = LoadGenerator(env,
                                   avg_think_time=10,
                                   no_of_users=100,
                                   name='lg')
                                   
3. Create a server, and connect the load generator (client) to the server

         server = Server(env,
                      avg_process_time=5,
                      no_of_cores=2,
                      max_pool_size=200,
                      time_slice=10,
                      cs_overhead=2,
                      name='sr')]
         
         load_genertor.connect(server)

4. Finally run the simulation
        
        # run the experiments for 10000 milliseconds
        # time is not measured in system time, therefore thread sleep will have no effect here
        # also any processing/computations to execute the simulation have no effect
        env.run(10000)
        
### Metric Collection
 
    # it is recommended to omit warm up period when reporting the measurements
    # usually this is the time till the system becomes stable
    warm_up_ratio = 0.25

    # response times for each request for the "server-sr"    
    response_times = load_generator.get_response_times(server)
    
    warm_up_limit = int(len(latency_arr) * warm_up_ratio)

    # wip for "server-sr"
    wip = np.mean(load_generator.get_queue_lengths(server)[warm_up_limit:])
    
    avg_latency = np.mean(latency_arr[warm_up_limit:])
    
    # through put comutation
    start_times = load_generator.get_start_times(server)
    tps = len(start_times) / (start_times[-1] - start_times[0]) * 1000

    print("latency : %.2f" % latency)
    print("work-in-progress : %.2f" % wip)
    print('throughput - %.2f' % tps_measure)


### Advanced usage

This tool can be used to simulate complex architectures that invoke multiple servers. This can be simply achieve via using the following code line.

    server_a.connect(server_b)
    
Above will direct any request to the server_a to server_b. 
