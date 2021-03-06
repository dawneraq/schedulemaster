"""
schedulemaster.py

CSCI-4210 Operating Systems F16

This rudimentary simulation of an operating system is a process simulation
model in Python to compare efficiency between first-come first-served,
shortest job first, and round robin process scheduling algorithms.
"""

import sys
import os
import Queue
from process import Process

class ScheduleMaster(object):
	n = 0 # Number of processes to simulate, determined by input file
	m = 1 # Number of processors (i.e. cores) available within the CPU
	t_cs = 8 # Time in ms it takes to perform a context switch
	t_slice = 84 # Time in ms each process is given to complete its
				 # 	CPU burst in round robin

	def __init__(self, input_file):
		self.reset(input_file)

	def reset(self, input_file):
		self.t = 0 # Elapsed time in milliseconds
		self.turnaround_times = []
		self.num_context_switches = 0
		self.num_preemptions = 0
		self.running_process = None
		self.blocked_processes = []
		self.read_input(input_file) # Erase output statistics

	"""
	Any line beginning with a # character is ignored
		(these lines are comments).
	All blank lines are also ignored, including lines containing
		only whitespace characters.
	If an error in the input file format is detected,
		display an error message (handled in process.py).
	"""
	def valid_line(self, line):
		return (not line.isspace()) and line[0] != '#'

	def read_input(self, input_file):
		with open(input_file, 'r') as input_data:
			process_strings = [line.strip() for line in input_data if self.valid_line(line)]
			self.process_list = []

			try:
				for process_string in process_strings:
					process_params = process_string.split('|')
					self.process_list.append(Process(*process_params))
			except TypeError as err:
				print 'Invalid input file format:'
				print '\t', err
				sys.exit(1)

			n = len(self.process_list)

	def show_queue(self):
		queue_representation = '[Q '

		if self.ready_queue.queue:
			queue_representation += ' '.join([process.proc_id for process in self.ready_queue.queue])
		else:
			queue_representation += 'empty'
		
		return queue_representation + ']'

	def simulate(self, algorithm):
		if algorithm == 'SJF':
			self.ready_queue = Queue.PriorityQueue()
		else:
			self.ready_queue = Queue.Queue()
		
		print 'time ' + repr(self.t) + 'ms: Simulator started for ' + algorithm + ' ' + self.show_queue() 

		# TODO Measure turnaround time for each simulated process (this includes context switches).

		while not all([process.has_terminated() for process in self.process_list]):
			# Print whenever a process arrives to the CPU.
			arriving_processes = [process for process in self.process_list if process.initial_arrival_time == self.t]
						
			if algorithm == 'RR':
				self.t_slice -= 1

			if arriving_processes:
				for arriving_process in arriving_processes:
					# Add processes from self.process_list to ready_queue based on algorithm.
					self.ready_queue.put(arriving_process)
					arriving_process.turnaround_start = self.t
					arriving_process.wait_start = self.t
					print 'time ' + repr(self.t) + 'ms: Process ' + arriving_process.proc_id + ' arrived ' + self.show_queue()

			if self.blocked_processes:
				for blocked_tuple in self.blocked_processes:
					blocked_process = blocked_tuple[0]
					unblock_time = blocked_tuple[1]

					if self.t == unblock_time:
						if algorithm == 'SJF':
							self.ready_queue.put(blocked_process, blocked_process.cpu_burst_time)
						else:	
							self.ready_queue.put(blocked_process)

						blocked_process.turnaround_start = self.t
						blocked_process.wait_start = self.t
						print 'time ' + repr(self.t) + 'ms: Process ' + blocked_process.proc_id + ' completed I/O ' + self.show_queue()
						blocked_process.current_job = None
						self.blocked_processes.remove(blocked_tuple)

			if not self.running_process:
				# Print whenever a process starts using the CPU.
				if self.ready_queue.queue:
					self.running_process = self.ready_queue.get()
					self.running_process.wait_times.append(self.t - self.running_process.wait_start)
					self.t += ScheduleMaster.t_cs / 2
					self.num_context_switches += 1
					print 'time ' + repr(self.t) + 'ms: Process ' + self.running_process.proc_id + ' started using the CPU ' + self.show_queue()

			if self.running_process:
				if algorithm == 'RR':
					self.running_process.time_left -= 1			

				if not self.running_process.current_job:
					self.running_process.set_current_job()
					current_operation = self.running_process.current_job
					
				
				if current_operation.job_type == 'burst':
					# Sets remaining_time to the time left for the CPU burst for RR algorithm
					if algorithm == 'RR':
						current_operation.remaining_time = self.running_process.time_left

					if current_operation.remaining_time > 0:
						current_operation.remaining_time -= 1
					else:
						self.running_process.bursts_completed += 1
						remaining_bursts = len([job for job in self.running_process.job_queue.queue if job.job_type == 'burst'])

						if remaining_bursts == 0:
							# Print whenever a process terminates (by finishing its last CPU burst).
							print 'time ' + repr(self.t) + 'ms: Process ' + self.running_process.proc_id + ' terminated ' + self.show_queue()
						else:
							if self.t_slice > 0 and algorithm == 'RR':
								self.t_slice = 84
								self.running_process.time_left = self.running_process.cpu_burst_time
								
							# Print whenever a process finishes using the CPU, i.e. completes its CPU burst.
							print 'time ' + repr(self.t) + 'ms: Process ' + self.running_process.proc_id + ' completed a CPU burst; ' + repr(remaining_bursts) + ' to go ' + self.show_queue()
							self.running_process.set_current_job()
							# Print whenever a process starts performing I/O.
							unblock_time = self.t + self.running_process.io_time
							print 'time ' + repr(self.t) + 'ms: Process ' + self.running_process.proc_id + ' blocked on I/O until time ' + repr(unblock_time) + 'ms ' + self.show_queue()
							self.blocked_processes.append((self.running_process, unblock_time))

						# Account for the time taken to remove each process from the CPU.
						self.running_process.turnaround_times.append(self.t - self.running_process.turnaround_start)
						self.t += ScheduleMaster.t_cs / 2 - 1

						# Prepare to perform a context switch to the next process.
						self.running_process = None						
		
			if algorithm == 'RR':
				# Round Robin t_slice reaching 0 before it has its CPU burst
				if self.t_slice < 0:
					if self.ready_queue.queue:
						# Increment count of preemptions and reset time slice
						self.t_slice = 84
						self.num_preemptions += 1
												
						if self.running_process.time_left <= 0:
							self.running_process.time_left = 0
							continue
						
						# Put process back in queue
						self.ready_queue.put(self.running_process)
						self.running_process.wait_start = self.t
							
						print 'time ' + repr(self.t) + 'ms: Time slice expired; process ' + self.running_process.proc_id + ' preempted with ' + repr(self.running_process.time_left) + 'ms to go ' + self.show_queue()
						
						# Perform context switch to next process
						self.running_process = None
						self.t += ScheduleMaster.t_cs / 2	- 1		
					else:
						self.t_slice = 84
						print 'time ' + repr(self.t) + 'ms: Time slice expired; no preemption because ready queue is empty ' + self.show_queue()

			self.t += 1

		print 'time ' + repr(self.t) + 'ms: Simulator ended for ' + algorithm

		if algorithm != 'RR':
			print ''

	def write_output(self, output_file, algorithm):
		with open(output_file, 'a') as output:
			output.write('Algorithm ' + algorithm + '\n')

			# Print average CPU burst time, calculated from the input data.
			burst_times = [process.cpu_burst_time for process in self.process_list for burst_num in range(process.num_bursts)]
			average_burst_time = '%.2f' % (sum(burst_times) / float(len(burst_times)))
			output.write('-- average CPU burst time: ' + average_burst_time + ' ms\n')

			# Print average wait time.
			wait_times = [time for process in self.process_list for time in process.wait_times]
			average_wait_time = '%.2f' % (sum(wait_times) / float(len(wait_times)))
			output.write('-- average wait time: ' + average_wait_time + ' ms\n')

			# Print average turnaround time.
			turnaround_times = [time for process in self.process_list for time in process.turnaround_times]
			average_turnaround_time = '%.2f' % (sum(turnaround_times) / float(len(turnaround_times)))
			output.write('-- average turnaround time: ' + average_turnaround_time + ' ms\n')

			output.write('-- total number of context switches: ' + repr(self.num_context_switches) + '\n')
			output.write('-- total number of preemptions: ' + repr(self.num_preemptions) + '\n')


def main():
	# Check command line arguments.
	if len(sys.argv) != 3:
		print 'ERROR: Invalid arguments'
		print 'USAGE: ./a.out <input-file> <stats-output-file>'
		sys.exit(2)

	input_file = sys.argv[1]
	output_file = sys.argv[2]

	if os.path.isfile(output_file):
		os.remove(output_file)

	sm = ScheduleMaster(input_file)
	algorithms = ['FCFS', 'SJF', 'RR']

	for algorithm in algorithms:
		sm.simulate(algorithm)
		sm.write_output(output_file, algorithm)
		sm.reset(input_file)

		
if __name__ == "__main__":
	main()