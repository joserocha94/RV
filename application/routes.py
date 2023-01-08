#!/usr/bin/env python
# ##########################################################################
## FUNCTIONS USED BY APPLICATION LAYER TO MANAGE THE ROUTE SYSTEM
# ##########################################################################


routes = [
    ([0, 1, 2, 3, 4]),
    ([0, 5, 6, 7, 8])
]

# prints all the routes from the system
def get_routes():
    
    for i in range (0, len(routes)):
        print("Route", i, ":", routes[i])
    return

# returns the next stop in the route
#   <id_route> int 
#   <current_stop> int     
def get_next_stop(id_route, current_stop):

    index = -1
    if not is_terminal_stop(id_route, current_stop):
        index = routes[id_route][current_stop+1]    
    
    return index


# check if <stop_id> is the last stop in the route <id_route>
#   <id_route> int
#   <stop_id> int
def is_terminal_stop(id_route, stop_id):

    found_index = -1
    bool = False

    for i in range (0, len(routes[id_route])):
        if (stop_id == routes[id_route][i]):
            found_index = i+1

    bool = False if found_index < len(routes[id_route]) else True
    
    return bool




