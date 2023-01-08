#!/usr/bin/env python
from socket import *
import sys, time
from threading import Thread, Event
from Queue import *


# PROTOCOL STACK - One folder per layer of VANET protocol stack. It may include more than one entity. Each entity is a different thread.
# VANET protocol stack data link layer - multicast communication - basic emulation of logical and link layer communication.
from data_link.multicast import *

# VANET protocol stack transport & network layer - it may include: topology management, information dissemination within a ROI, location-based routing
from transport_network.geonetworking import *

# VANET protocol stack facilities layer (common services to all applications)- it may include: cooperative awareness messages, event management message
from facilities.common_services import *

# VANET protocol stack application layer - application business logic
from application.application import *

# OBU-interface with vehicles - it may include: car motor control funtions, other sensors/actuator interfaces, location information
from in_vehicle_network.car_control import *

# RSU interface with legacy systems - it may include: traffic light control funtions, other sensors/actuator interfaces, location information
from rsu_legacy_systems.rsu_control import *

# QUEUES - used to tranfer messages between adjacent layers of the protocol stack
my_system_rxd_queue=Queue()
movement_control_txd_queue=Queue()

ca_service_txd_queue=Queue()
den_service_txd_queue=Queue()
services_rxd_queue=Queue()


geonetwork_txd_queue=Queue()
geonetwork_rxd_ca_queue=Queue()
geonetwork_rxd_den_queue=Queue()
beacon_rxd_queue=Queue()

multicast_txd_queue=Queue()
multicast_rxd_queue=Queue()

# EVENTS  -  flags used to coordinate threads activities
# start_flag - set when all threads started to triggered the execution of each thread logic
start_flag=Event()


# VARIABLES  -  shared by different threads
# coordinates - dictionary with node's location in the format (x,y,time)
# obd_2_interface - dictionary with the vehicle's dynamic in the format (speed, direction, heading)
coordinates = dict()
obd_2_interface = dict()
bus_capacity = 5

# INPUT ARGUMENTS
# node_id
# node's coordinates - x, y
# car speed - speed
# car direction - backward (´b') or forward('f')
# car heading - heading (N or S or E or O)
# test type - type of debug messages that are usefull for your test - 
##################################################
## MAIN-ITS_core
##################################################
def main(argv):
	global obd_2_interface, coordinates

	command=input('Press enter to start')
	
	#INPUT para INFRASTRUCTURE: 	ITS_core.py I node_id people_waiting
	#Posicao dos nos tipo I sao definidas automaticamente (x = node_id*100 , y = 0).
	if(argv[1] == 'I' and len(argv) == 4): 

		node_id = int(argv[2])
		coordinates = {
			'x':int(node_id * 1000), 
			'y':int(0), 
			't': repr(time.time())
		}
		obd_2_interface = {
			'speed': int(0), 
			'direction': "f", 
			'heading': "O", 
			'status': "0", 
			'node_type': argv[1], 
			'people_waiting':int(argv[3])
		}
		print ('STATUS: node_id: ', node_id, '\n\tcoordinates: ', coordinates, '\n\tobd_2_interface: ', obd_2_interface)
	
	#INPUT para VEHICLE:	ITS_core.py V node_id x y speed n_people_in_bus
	#Direction sempre 'O' e heading sempre 'f'
	elif(argv[1] == 'V' and len(argv) == 7):
		
		node_id = int(argv[2])
		free_seats = bus_capacity - int(argv[6])
		coordinates = {
			'x':int(argv[3]), 
			'y':int(argv[4]), 
			't': repr(time.time())
		}
		obd_2_interface = {
			'speed': int(argv[5]), 
			'direction': "f", 
			'heading': "E", 
			'status': "0",
			'node_type': argv[1],
			'free_seats':free_seats
		}
		print ('STATUS: node_id: ', node_id, '\n\tcoordinates: ', coordinates, '\n\tobd_2_interface: ', obd_2_interface)

	#INPUT para STATIONARY BUS:	ITS_core.py S node_id x y speed
	elif(argv[1] == 'S' and len(argv) == 6):
    		
		node_id = int(argv[2])
		free_seats = 5
		coordinates = {
			'x':int(argv[3]), 
			'y':int(argv[4]), 
			't': repr(time.time())
		}
		obd_2_interface = {
			'speed': int(argv[5]), 
			'direction': "f", 
			'heading': "O", 
			'status': "0",
			'node_type': argv[1], 
			'free_seats':free_seats
		}
	
	else:
		print('ERROR: Invalid arguments:\n')
		print('ITS_core.py I node_id people_waiting\nor\nITS_core.py V node_id x y speed n_people_in_bus\nor\nITS_core.py S node_id x y speed\n')
		sys.exit()
	
	print("\n")
	threads=[]

	try:

		##################################################
		#  Arguments common to all threads:
		#      node_id: node identification
		#      startFlag: status event that indicates that all threads were launched and can start execution
		##################################################

		##################################################
		#     Application layer threads
		##################################################

		# Thread - application_txd: receive data from user/cars/legacy systems
		# Arguments - coordinates: last known coordinates
		#             my_system_rxd_queue: queue to send data to my_system that is relevant for business logic decision-process 
		# 			  ca_service_txd_queue: queue to send data to ca_services_txd
		#             den_service_txd_queue: queue to send data to den_services_txd
		t=Thread(target=application_txd, args=(node_id, start_flag, my_system_rxd_queue, ca_service_txd_queue, den_service_txd_queue))
		t.start()
		threads.append(t)
	

		# Thread - application_rxd: receive data from services_rxd, process it and send it to the user/cars/legacy systems
		# Arguments - car movement: controls the car movement
		#           - services_rxd_queue: queue to get data from ca_service_rxd or den_service_rxd
		#             my_system_rxd_queue: queue to send data to my_system that is relevant for business logic decision-process 
		t=Thread(target=application_rxd, args=(node_id, start_flag, services_rxd_queue, my_system_rxd_queue))
		t.start()
		threads.append(t)
	

		# Thread - my_system: business logic 
		# Arguments - my_system_rxd_queue: queue to receive data from other application layer threads relevant for business logic decision-process 
		#           - movement_control_txd_queue: queue to send commands to control vehicles movement
		t=Thread(target=my_system, args=(node_id, start_flag, coordinates, obd_2_interface, my_system_rxd_queue, movement_control_txd_queue))
		t.start()
		threads.append(t)
	

		##################################################
		#     Facilities layer threads
		##################################################

		# Thread - ca_service_rxd: receive data from application_txd, generates cooperative awaraness and sends the CA message to the geonetwork_txd
		# Arguments - coordinates: last known coordinates
		#             ca_services_txd_queue: queue to get data from application_txd
		#             geonetwork_txd_queue: queue to send data to geonetwork_txd
		t=Thread(target=ca_service_txd, args=(node_id, start_flag, coordinates, obd_2_interface, ca_service_txd_queue, geonetwork_txd_queue))
		t.start()
		threads.append(t)

		# Thread - ca_service_rxd: receive data from geonetwork_rxd, process the CA message and send the result to the application_rxd
		# Arguments - geonetwork_rxd_ca_queue: queue to get data from geonetwork_rxd
		#             ca_service_rxd_queue: queue to send data to application_rxd
		t=Thread(target=ca_service_rxd, args=(node_id, start_flag, geonetwork_rxd_ca_queue, services_rxd_queue,))
		t.start()
		threads.append(t)

		# Thread -  den_service_txd: receive data from application_txd, generates events and sends the DEN message to the geonetwork_txd
		# Arguments - coordinates: last known coordinates
		#             den_services_txd_queue: queue to get data from application_txd
		# #           geonetwork_txd_queue: queue to send data to geonetwork_txd
		t=Thread(target=den_service_txd, args=(node_id, start_flag, coordinates, obd_2_interface, den_service_txd_queue, geonetwork_txd_queue))
		t.start()
		threads.append(t)

		# Thread - den_service_rxd: receive data from geonetwork_rxd, process the DEN message and send the result to the application_rxd
		# Arguments - geonetwork_rxd_den_queue: queue to get data from geonetwork_rxd
		#             services_rxd_queue: queue to send data to application_rxd
		#             services_txd_queue: queue to relay data to geonetwork_txd in case of multi-hop communication
		t=Thread(target=den_service_rxd, args=(node_id, start_flag, geonetwork_rxd_den_queue, services_rxd_queue,))
		t.start()
		threads.append(t)

		##################################################
		#     Transport and network layer threads
		##################################################

		# Thread - geonetwork_txd: receive data from geoenetwork_txd, process the geonetwork information and send the result to the multicast_rxd
		# Arguments - geonetwork_txd_queue: queue to get data from ca_service_txd or den_service_txd
		#             multicast_txd_queue: queue to send data to multicast_txd
		t=Thread(target=geonetwork_txd, args=(node_id, start_flag, geonetwork_txd_queue, multicast_txd_queue,))
		t.start()
		threads.append(t)

		# Thread- geonetwork_rxd: receive data from multicast_rxd, process the geonetwork information and send the result to the services_rxd
		# Arguments - multicast_rxd_queue: queue to get data from multicast_txd
		#             geonetwork_rxd_queue: queue to send data to services_rxd, after being processed
		t=Thread(target=geonetwork_rxd, args=(node_id, start_flag, multicast_rxd_queue, geonetwork_rxd_ca_queue, geonetwork_rxd_den_queue,))
		t.start()
		threads.append(t)

		# Thread - beacon_txd: periodical generation of beacons
		# Arguments - coordinates: last known coordinates
		#             multicast_txd_queue: queue to send beacons to multicast_txd
		t=Thread(target=beacon_txd, args=(node_id, start_flag, coordinates, multicast_txd_queue,))
		t.start()
		threads.append(t)

		# Thread- geonetwork_rxd: receive data from multicast_rxd, process the geonetwork information and send the result to the services_rxd
		# Arguments - multicast_rxd_queue: queue to get data from multicast_rxd
		#             geonetwork_rxd_queue: queue to send data to services_rxd, after being processed
		t=Thread(target=beacon_rxd, args=(node_id, start_flag, beacon_rxd_queue,))
		t.start()
		threads.append(t)

		# Thread- check_loc_table: check loc_table_entries and deleted outdated entries
		# Arguments - no additional argument
		t=Thread(target=check_loc_table, args=(node_id, start_flag,))
		t.start()
		threads.append(t)


		##################################################
		#     Link layer threads
		##################################################

		# Thread - multicast_rxd: receive data from multicast socket, process and send the result to the geonetwork_rxd, after being processed, if needed
		# Arguments - multicast_rxd_queue: queue to send data to geonetwork_rxd
		#            beacon_rxd_queue: queue to send data to beacon_rxd
		t=Thread(target=multicast_rxd, args=(node_id, start_flag, multicast_rxd_queue, beacon_rxd_queue,))
		t.start()
		threads.append(t)

		# Thread - multicast_txd: receive data from geonetwork_txd and send it to the multicast socket
		# Arguments - multicast_txd_queue: queue to get data from transmission from geonetwork_txd
		t=Thread(target=multicast_txd, args=(node_id, start_flag, multicast_txd_queue,))
		t.start()
		threads.append(t)

		##################################################
		#     In-vehicles threads
		##################################################

		# Thread- update_position: update the node coordinates (x,y) to emulate the GPS device
		# Arguments -  coordinates: dictionay with (x,y) coordinates and time instant t of measurement
		#           - obd_2_interface: dictionary with movement information of the car
		t=Thread(target=update_location, args=(node_id, start_flag, coordinates, obd_2_interface,))
		t.start()
		threads.append(t)

		# Thread- update_position: update the node coordinates (x,y) to emulate the GPS device
		# Arguments -  coordinates: dictionay with (x,y) coordinates and time instant t of measurement
		#           - car_movement: dictionary with movement information of the car
		t=Thread(target=movement_control, args=(node_id, start_flag, coordinates, obd_2_interface, movement_control_txd_queue))
		t.start()
		threads.append(t)

		start_flag.set()

	except:
		#exit the program if there is an error when opening one of the threads
		print('STATUS: Error opening one of the threads -  NODE: {}'.format(node_id),'\n')
		for t in threads:
			t.join()
			sys.exit()	
    
	return
	

if __name__=="__main__":
	main(sys.argv[0:])
