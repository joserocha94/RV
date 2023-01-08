#!/usr/bin/env python
# #####################################################################################################
# SENDING/RECEIVING APPLICATION THREADS - add your business logic here!
## Note: you can use a single thread, if you prefer, but be carefully when dealing with concurrency.
#######################################################################################################
from socket import MsgFlag
import time
from application.message_handler import *
from application.self_driving_test import *
from in_vehicle_network.location_functions import position_read
from application.routes import *

import random
random.seed(1) #CHANGE

# #####################################################################################################
# constants
warm_up_time = 10

#-----------------------------------------------------------------------------------------
# Thread: application transmission. In this example user triggers CA and DEN messages. 
#		CA message generation requires the sender identification and the inter-generation time.
#		DEN message generarion requires the sender identification, and all the parameters of the event.
#		Note: the sender is needed if you run multiple instances in the same system to allow the 
#             application to identify the intended recipiient of the user message.
#		TIPS: i) You may want to add more data to the messages, by adding more fields to the dictionary
# 			  ii)  user interface is useful to allow the user to control your system execution.
#-----------------------------------------------------------------------------------------
def application_txd(node, start_flag, my_system_rxd_queue, ca_service_txd_queue, den_service_txd_queue):

	while not start_flag.isSet():
		time.sleep (1)
	print('STATUS: Ready to start - THREAD: application_txd - NODE: {}'.format(node))

	time.sleep(warm_up_time)
	ca_user_data  = trigger_ca(node)
#	print('STATUS: Message from user - THREAD: application_txd - NODE: {}'.format(node),' - MSG: {}'.format(ca_user_data ),'\n')
	ca_service_txd_queue.put(int(ca_user_data))
	i=0
	while True:
		i=i+1
#		den_user_data = trigger_event(node)
#		print('STATUS: Message from user - THREAD: application_txd - NODE: {}'.format(node),' - MSG: {}'.format(den_user_data ),'\n')
#		den_service_txd_queue.put(den_user_data)
	return


#-----------------------------------------------------------------------------------------
# Thread: application reception. In this example it receives CA and DEN messages. 
# 		Incoming messages are send to the user and my_system thread, where the logic of your system must be executed
# 		CA messages have 1-hop transmission and DEN messages may have multiple hops and validity time
#		Note: current version does not support multihop and time validity. 
#		TIPS: i) if you want to add multihop, you need to change the thread structure and add 
#       		the den_service_txd_queue so that the node can relay the DEN message. 
# 				Do not forget to this also at IST_core.py
#-----------------------------------------------------------------------------------------
def application_rxd(node, start_flag, services_rxd_queue, my_system_rxd_queue):

	while not start_flag.isSet():
		time.sleep (1)
	print('STATUS: Ready to start - THREAD: application_rxd - NODE: {}'.format(node))

	while True :
		msg_rxd=services_rxd_queue.get()
#		print('STATUS: Message received/send - THREAD: application_rxd - NODE: {}'.format(node),' - MSG: {}'.format(msg_rxd),'\n')
		if msg_rxd['node']!=node:
			my_system_rxd_queue.put(msg_rxd)

	return


#-----------------------------------------------------------------------------------------
# Thread: my_system - implements the business logic of your system. This is a very straightforward use case 
# 			to illustrate how to use cooperation to control the vehicle speed. 
# 			The assumption is that the vehicles are moving in the opposite direction, in the same lane.
#			In this case, the system receives CA messages from neigbour nodes and, 
# 			if the distance is smaller than a warning distance, it moves slower, 
# 			and the distance is smaller that the emergency distance, it stops.
#		TIPS: i) we can add DEN messages or process CAM messages in other ways. 
#			  ii) we can interact with other sensors and actuators to decid the actions to execute.
#			  iii) based on your business logic, your system may also generate events. In this case, 
# 				you need to create an event with the same structure that is used for the user and 
#               change the thread structure by adding the den_service_txd_queue so that this thread can send th DEN message. 
# 				Do not forget to this also at IST_core.py
#-----------------------------------------------------------------------------------------
def my_system(node, start_flag, coordinates, obd_2_interface, my_system_rxd_queue, movement_control_txd_queue):

	stop_distance = 20
	slow_down_distance = 100

	bus_capacity = 5

	while not start_flag.isSet():
		time.sleep (1)
	print('STATUS: Ready to start - THREAD: my_system - NODE: {}'.format(node))

	#STATIONARY VEHICLES----------------------------------------------------------------
	while obd_2_interface['node_type']=='S':
		#Wait here until it gets set to 'V'
		msg_rxd=my_system_rxd_queue.get()
		if(msg_rxd['msg_type'] == 'DEN'): #FALTA IMPLEMENTAR O IF E AS MENSAGENS
			obd_2_interface['node_type'] = 'V'
	
	#VEHICLES---------------------------------------------------------------------------
	if (obd_2_interface['node_type'] =='V'):

		nodes_in_route = [2,3,4]#node_ids das paragens
		i=0
		next_stop = nodes_in_route[i]
		
		msg_rxd=my_system_rxd_queue.get()
		while msg_rxd['node'] != next_stop:
			msg_rxd=my_system_rxd_queue.get()
		
		distance(coordinates, obd_2_interface, msg_rxd)

		enter_car(movement_control_txd_queue)
		turn_on_car(movement_control_txd_queue)
		car_move_forward(movement_control_txd_queue)

		started_moving = False
		n_people_leaving = 0

		while True :
			
			if started_moving:
				#numero de pessoas que saem do autocarro definido sempre que autocarro recomeça a andar
				n_people_leaving = random.randint(0, bus_capacity - obd_2_interface['free_seats'])																					
				obd_2_interface['free_seats'] += n_people_leaving
				started_moving = False
			
			msg_rxd=my_system_rxd_queue.get()

			#Considerar mensagens CA apenas da proxima paragem na lista nodes_in_route
			if msg_rxd['msg_type']=='CA' and msg_rxd['node'] == next_stop:

				#RECEIVES: ca_msg= {'msg_type':'CA', 'node':node, 'msg_id':msg_id,'pos_x': x,'pos_y': y,'time':t, 'speed': s, 'dir':d, 'heading':h, 'people_waiting': n}

				nodes_distance = distance (coordinates, obd_2_interface, msg_rxd)
				print(f"Distance:{nodes_distance}\n")
				print (f"CA message from node {msg_rxd['node']} ---> people_waiting: {msg_rxd['people_waiting']}\n")
				
				n_people_waiting = msg_rxd['people_waiting']
				
				if nodes_distance < stop_distance and (n_people_waiting > 0 or n_people_leaving > 0): 
					print ('----------------STOP-------------------')
					stop_car (movement_control_txd_queue)
					#Pessoas entram: atualizar o numero de lugares livres no autocarro 
					time.sleep(10)
					obd_2_interface['free_seats'] = max (obd_2_interface['free_seats'] - n_people_waiting, 0)
					
					#atualizar proximo no na rota
					i+=1
					#Se não há mais paragem na rota, terminar while
					if i == len(nodes_in_route):
						break
					next_stop = nodes_in_route[i]
					
					#recomeçar a andar
					turn_on_car(movement_control_txd_queue)
					car_move_forward(movement_control_txd_queue)
					print ('----------------MOVING FORWARD AGAIN-------------------------')
					started_moving = True

				
				elif nodes_distance < slow_down_distance and (n_people_waiting > 0 or n_people_leaving > 0):
					print ('----------------SLOW DOWN------------------------------')
					car_move_slower(movement_control_txd_queue)
				
				#Se não existem pessoas a entrar ou sair na proxima paragem continuar para a seguinte:
				elif nodes_distance < stop_distance and n_people_waiting == 0 and n_people_leaving == 0:
					#atualizar proximo no na rota
					i+=1
					#Se não há mais paragem na rota, terminar while
					if i == len(nodes_in_route):
						break
					next_stop = nodes_in_route[i]
					started_moving = True

		print("\n-----------END OF ROUTE----------------\n")

	#BUS STOP----------------------------------------------------------------
	elif(obd_2_interface['node_type']=='I'):
		next_bus_list = [1,5]#node_ids dos autocarros
		i=0
		next_bus = next_bus_list[i]
		
		while True :
			
			msg_rxd=my_system_rxd_queue.get()

			#Considerar mensagens CA apenas do proximo autocarro na lista bus_coming
			if msg_rxd['msg_type']=='CA' and msg_rxd['node'] == next_bus:

				#RECEIVES: ca_msg= {'msg_type':'CA', 'node':node, 'msg_id':msg_id,'pos_x': x,'pos_y': y,'time':t,'speed': s, 'dir':d, 'heading':h, 'free_seats':n }
				
				nodes_distance = distance (coordinates, obd_2_interface, msg_rxd)
				print(f"Distance:{nodes_distance}\n")
				print (f"CA message from node {msg_rxd['node']} ---> free_seats: {msg_rxd['free_seats']}\n")
				
				n_free_seats = msg_rxd['free_seats']

				#if there is nobody waiting do nothing
				if obd_2_interface['people_waiting'] == 0:
					continue

				#Bus will stop:
				if obd_2_interface['people_waiting'] > 0:
					
					#Chamar Stationary bus
					if obd_2_interface['people_waiting'] > n_free_seats and nodes_distance < slow_down_distance and nodes_distance > stop_distance:
						print("ENVIAR MENSAGEM AO AUTOCARRO STATIONARY E MUDAR next_bus_list")
					
					#Autocarro parou
					if nodes_distance < stop_distance:
						#time.sleep(5)
						obd_2_interface['people_waiting'] = max (obd_2_interface['people_waiting'] - n_free_seats,0)

			print(f"PEOPLE WAITING: {obd_2_interface['people_waiting']}")
				
	return



##################### autocarro ##################### 
# JR - definir quantas pessoas saem nas paragens -> é um argumento ao lançar o terminal
# JR - autocarro para se: 
#		- tiver lugares vazios e alguém quiser entrar na paragem seguinte
#		- alguém que está lá dentro quiser sair
# SC- implementar tempo de paragem em cada estação
# - calcula "free-seats" e envia à paragem(que chama o novo autocarro)
# - to-do: 1 led por cada pessoa
# SC- autocarro parar na estação terminal
# JR - ignorar mensagens de infraestrura que estão a uma distância maior que X ou por onde ela já passou
# JR - autocarro recebe como argumento um identificador da rota (implementar a definição das rotas no sistema)
# - MÁX: 5 pessoas

##################### infraestrura ################### 
# JG - definir pessoas que entram em cada paragem (gerador aleatório vs estático, decidir depois
# JG - avisar autocarro (que ainda não passou por ela) quantas pessoas lá estão (Mensagem CA)
# JG - ignorar mensagens de autocarros que ja passaram por ela
# - atribuir coordenadas fixas às três paragens.(Guardar através do ID)
# JG - chamar autocarro "morto" após perceber que há passageiros sem lugar (Mensagem DEN)
# SC- definir estação terminal X metros depois da última estação


#IMEPLEMENTAR: parâmetro stoped na obd_2_i para enviar na mensagem CA quando BUS para.

