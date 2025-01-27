#%%##########################################       Modules       ###########################################
# MODULES
import sys
from time import process_time
import numpy as np;from numpy import random

import verbose_module as verb

sys.path.append('../../.')
import pIRPgym


###########################################  Instance Generator  ##########################################
# Instance Generator

### pIRP model's parameters
# Stochasticity
stochastic_params = ['d','q']
look_ahead = ['d','q']


# Historical data
historical_data = ['*']


# Other parameters
backorders = 'backorders'

env_config = {'M':15,'K':13,'T':7,'Q':750,
              'S':6,'LA_horizon':4,
             'd_max':2500,'hist_window':60}
env_config['F'] = env_config['M']

# Creating instance generator object
inst_gen = pIRPgym.instance_generator(look_ahead,stochastic_params,
                              historical_data,backorders,env_config=env_config)

##########################################    Random Instance    ##########################################
# Random Instance
q_params = {'dist': 'c_uniform', 'r_f_params': (6,20)}          # Offer
p_params = {'dist': 'd_uniform', 'r_f_params': (20,61)}

d_params = {'dist': 'log-normal', 'r_f_params': (3,1)}          # Demand

h_params = {'dist': 'd_uniform', 'r_f_params': (20,61)}         # Holding costs

stoch_rd_seed = 1       # Random seeds
det_rd_seed = 1

disc = ("strong","conc")


# Creating instance generator object
inst_gen = pIRPgym.instance_generator(look_ahead,stochastic_params,
                              historical_data,backorders,env_config=env_config)

inst_gen.generate_basic_random_instance(det_rd_seed,stoch_rd_seed,q_params=q_params,
                                        p_params=p_params,d_params=d_params,h_params=h_params,discount=disc)


# Environment
# Creating environment object
routing = True
inventory = True
perishability = 'ages'
env = pIRPgym.steroid_IRP(routing,inventory,perishability)
state = env.reset(inst_gen,return_state=True)


# [purchase,demand_compliance], la_dec = pIRPgym.Inventory.Stochastic_Rolling_Horizon(state,env,inst_gen)    
purchase = pIRPgym.Purchasing.avg_purchase_all(inst_gen,env)
demand_compliance = pIRPgym.Inventory.det_FIFO(purchase,inst_gen,env)
pending_suppliers,requirements = pIRPgym.Routing.consolidate_purchase(purchase,inst_gen,env.t)

#%%



# GA_routes,GA_obj,GA_info,GA_time,_ = pIRPgym.Routing.GeneticAlgorithm(purchase,inst_gen,env.t,return_top=False,
#                                                                       rd_seed=0,time_limit=30,verbose=True)    # Genetic Algorithm
# print(f'GA objective: {GA_obj}')


# transport_cost = pIRPgym.Routing_management.price_routes(inst_gen,GA_routes,purchase)
# feasible,objective,(distances,loads)=pIRPgym.Routing_management.evaluate_routes(inst_gen,GA_routes,requirements)
# total_missing,reactive_missing,extra_cost=pIRPgym.Routing_management.evaluate_solution_dynamic_potential(inst_gen,env,GA_routes,purchase)


# #%%

















CG_routes,CG_obj,CG_info,CG_time,CG_cols = pIRPgym.Routing.ColumnGeneration(purchase,inst_gen,env.t,time_limit=600,
                                                                            verbose=False,heuristic_initialization=5,
                                                                            return_num_cols=True,RCL_alpha=0.6) 
inverse_routes = [[i for i in route[::-1]] for route in CG_routes]

nn_routes,nn_obj,nn_info,nn_time = pIRPgym.Routing.NearestNeighbor(purchase,inst_gen,env.t)
print(f'CG objective: {CG_obj}')
total_missing,reactive_missing,extra_cost = pIRPgym.Routing_management.evaluate_solution_dynamic_potential(inst_gen,env,CG_routes,purchase)

nn_routes,nn_obj,nn_info,nn_time = pIRPgym.Routing.NearestNeighbor(purchase,inst_gen,env.t)
print(f'NN objective: {nn_obj}')


RCL_obj,RCL_veh,RCL_time,(RCL_median,RCL_std,RCL_min,RCL_max) = pIRPgym.Routing.\
                                                            evaluate_randomized_policy( pIRPgym.Routing.RCL_Heuristic,
                                                                                        purchase,inst_gen,env,n=15,
                                                                                        averages=True,dynamic_p=False,
                                                                                        time_limit=20,RCL_alphas=[0.05,0.1,0.25,0.4],
                                                                                        adaptative=True)
print(f'RCL objective light: {RCL_obj}')
print(RCL_median,RCL_min,RCL_max)

# RCL_obj,RCL_veh,RCL_time,(RCL_median,RCL_std,RCL_min,RCL_max) = pIRPgym.Routing.\
#                                                             evaluate_stochastic_policy( pIRPgym.Routing.RCL_Heuristic,
#                                                                                         purchase,inst_gen,env,n=15,
#                                                                                         averages=True,dynamic_p=False,
#                                                                                         time_limit=60,RCL_alphas=[0.05,0.1,0.25,0.4],
#                                                                                         adaptative=True)
# print(f'RCL objective hard: {RCL_obj}')
# print(RCL_median,RCL_min,RCL_max)


GA_routes,GA_obj,GA_info,GA_time,_ = pIRPgym.Routing.GeneticAlgorithm(purchase,inst_gen,env.t,return_top=False,
                                                                      rd_seed=0,time_limit=30,verbose=True)    # Genetic Algorithm
print(f'GA objective: {GA_obj}')




#%%


RCL_obj,RCL_veh,RCL_time,(RCL_median,RCL_std,RCL_min,RCL_max) = pIRPgym.Routing.\
                                                            multiprocess_eval_stoch_policy( pIRPgym.Routing.RCL_Heuristic,
                                                                                        purchase,inst_gen,env,n=15,
                                                                                        averages=True,dynamic_p=False,
                                                                                        time_limit=15,RCL_alphas=[0.05,0.1,0.25,0.4],
                                                                                        adaptative=True)





#%%
def order_crossover_route(route1, route2):
    """
    Performs Order Crossover (OX) on two routes to produce two offspring routes.
    The first offspring route is created by copying a segment from the first route and filling
    the rest from the second route while maintaining order. The second offspring route is formed
    from the nodes not included in the first offspring route.

    Parameters:
    route1 (list): The first route (sequence of nodes).
    route2 (list): The second route (sequence of nodes).

    Returns:
    tuple of lists: The two offspring routes.
    """
    size = len(route1)
    start, end = sorted(np.random.choice(range(size), 2, replace=False))

    # Create first offspring route
    child_route1 = [None]*size
    child_route1[start:end+1] = route1[start:end+1]

    route2_filtered = [node for node in route2 if node not in child_route1[start:end+1]]
    route2_filtered_iter = iter(route2_filtered * (size // len(route2_filtered) + 1))
    child_route1 = [next(route2_filtered_iter) if node is None else node for node in child_route1]

    # Create second offspring route with remaining nodes
    child_route2 = [None]*size
    remaining_nodes = [node for node in route1 if node not in child_route1]
    child_route2[start:end+1] = remaining_nodes[:end-start+1]

    remaining_nodes = remaining_nodes[end-start+1:] + [node for node in route2 if node not in child_route1 and node not in remaining_nodes]
    child_route2 = [remaining_nodes.pop(0) if node is None else node for node in child_route2]

    return child_route1, child_route2



def _initial_crossover_and_feasibility_check(parent1,parent2,inst_gen,requirements):
    """
    Performs crossover on two individuals (sets of routes) to produce feasible offspring routes.
    It also checks for and handles duplicate nodes and infeasible routes.

    Parameters:
    parent1 (list of lists): The first individual (set of routes).
    parent2 (list of lists): The second individual (set of routes).
    inst_gen: Instance generator containing distance information.
    requirements (dict): Dictionary of load requirements for each node.

    Returns:
    tuple: A list of feasible routes and a list of missing nodes.
    """
    offspring_routes = []
    missing_nodes = []

    def is_route_feasible(route, inst_gen, requirements):
        total_distance, total_load = 0, 0
        for i in range(len(route) - 1):
            total_distance += inst_gen.c[(route[i], route[i + 1])]
            total_load += requirements[route[i]]
        return total_distance <= inst_gen.d_max and total_load <= inst_gen.Q

    def make_route_feasible(route, inst_gen, requirements):
        while not is_route_feasible(route, inst_gen, requirements):
            removed_node = random.choice(route)
            route.remove(removed_node)
            missing_nodes.append(removed_node)

    # Perform crossover and store offspring routes
    for i in range(max(len(parent1), len(parent2))):
        route1 = parent1[i % len(parent1)] if i < len(parent1) else None
        route2 = parent2[-(i % len(parent2)) - 1] if i < len(parent2) else None

        if route1 and route2:
            child_route1, child_route2 = order_crossover_route(route1, route2)
            offspring_routes.extend([child_route1, child_route2])
        elif route1 or route2:
            offspring_routes.append(route1 or route2)

    # Check for duplicate nodes and feasibility
    for route in offspring_routes:
        # Remove duplicate nodes
        seen = set()
        duplicates = [node for node in route if node in seen or seen.add(node)]
        route[:] = [node for node in route if node not in seen]
        missing_nodes.extend(duplicates)

        # Make route feasible
        make_route_feasible(route, inst_gen, requirements)

    return offspring_routes, missing_nodes


def crossover_individuals(parent1,parent2,inst_gen,requirements):
    """
    Performs crossover on two individuals (sets of routes) and produces two offspring individuals.
    Routes are assigned to the offspring based on the suitability, which is determined by the 
    uniqueness of their nodes.

    Parameters:
    parent1 (list of lists): The first individual (set of routes).
    parent2 (list of lists): The second individual (set of routes).
    inst_gen: Instance generator containing distance information.
    requirements (dict): Dictionary of load requirements for each node.

    Returns:
    tuple: Two offspring individuals (sets of routes).
    """
    offspring_routes, missing_nodes = _initial_crossover_and_feasibility_check(
        parent1, parent2, inst_gen, requirements)
    offspring1, offspring2 = [], []

    # Randomly assign the first two routes to each offspring
    random.shuffle(offspring_routes)
    offspring1.append(offspring_routes.pop(0))
    offspring2.append(offspring_routes.pop(0))

    # Function to calculate suitability of a route for an offspring
    def calculate_suitability(route, offspring):
        unique_nodes = len([node for node in route if node not in offspring])
        return unique_nodes / len(route) if route else 0

    # Assign remaining routes based on suitability
    for route in offspring_routes:
        suitability_for_offspring1 = calculate_suitability(route, offspring1)
        suitability_for_offspring2 = calculate_suitability(route, offspring2)

        if suitability_for_offspring1 > suitability_for_offspring2:
            chosen_offspring = offspring1
        else:
            chosen_offspring = offspring2

        # Remove nodes that are already in the chosen offspring
        route = [node for node in route if node not in chosen_offspring]
        chosen_offspring.append(route)

    return offspring1, offspring2



# Creating instance generator object
inst_gen = pIRPgym.instance_generator(look_ahead,stochastic_params,
                              historical_data,backorders,env_config=env_config)

inst_gen.generate_basic_random_instance(det_rd_seed,stoch_rd_seed,q_params=q_params,
                                        p_params=p_params,d_params=d_params,h_params=h_params,discount=disc)


# Environment
# Creating environment object
routing = True
inventory = True
perishability = 'ages'
env = pIRPgym.steroid_IRP(routing, inventory, perishability)
state = env.reset(inst_gen,return_state=True)

[purchase,demand_compliance], la_dec = pIRPgym.Inventory.Stochastic_Rolling_Horizon(state,env,inst_gen)    

requirements,_ = pIRPgym.Routing.consolidate_purchase(purchase,inst_gen,env.t)


routes1,_,_,_ = pIRPgym.Routing.RCL_Heuristic(purchase,inst_gen,env.t,RCL_alpha=0.8,s=0)
routes2,_,_,_ = pIRPgym.Routing.RCL_Heuristic(purchase,inst_gen,env.t,RCL_alpha=0.8,s=1)
print(f'________Generated Routes___________')
print('Ind 1: ',routes1)
print('Ind 2: ',routes2)
print('\n')

child1,child2 = crossover_individuals(routes1,routes2,inst_gen,requirements)
print(child1,child2)














#%%





#########################################      Route Pricing      ##########################################
# Creating instance generator object
inst_gen = pIRPgym.instance_generator(look_ahead,stochastic_params,
                              historical_data,backorders,env_config=env_config)

inst_gen.generate_basic_random_instance(det_rd_seed,stoch_rd_seed,q_params=q_params,
                                        p_params=p_params,d_params=d_params,h_params=h_params,discount=disc)

# Environment
# Creating environment object
routing = True
inventory = True
perishability = 'ages'
env = pIRPgym.steroid_IRP(routing, inventory, perishability)
state = env.reset(inst_gen,return_state=True)

res = {'nn':{'Reduced Cost':[0 for i in range(8)]},'RCL':{'Reduced Cost':[0 for i in range(8)]}}

done = False
while not done:
    print(f'step {env.t}')
    [purchase,demand_compliance], la_dec = pIRPgym.Inventory.Stochastic_Rolling_Horizon(state,env,inst_gen)    
    
    nn_routes,nn_obj,nn_info,nn_time,nn_r = pIRPgym.Routing.NearestNeighbor(purchase,inst_gen,env.t,price_routes=True)
    for i in range(len(nn_routes)):
        res['nn']['Reduced Cost'][i] += nn_r[i]/inst_gen.T; #print(len(nn_routes))

    RCL_routes,RCL_obj,RCL_info,RCL_time,RCL_r = pIRPgym.Routing.RCL_Heuristic(purchase,inst_gen,env.t,price_routes=True)
    for i in range(len(RCL_routes)):
        res['RCL']['Reduced Cost'][i] += RCL_r[i]/inst_gen.T; #print(len(RCL_routes))
    
    ''' Compound action'''        
    action = {'routing':nn_routes,'purchase':purchase,'demand_compliance':demand_compliance}

    state, reward, done, real_action, _,  = env.step(action,inst_gen)

pIRPgym.Visualizations.RoutingV.plot_indicator_evolution(res,'Reduced Cost',x_axis='Routes Generated')









#%%####################################### Testing pricing algorithm  ######################################## 
# Testing pricing algorithm
# Reseting the environment
state = env.reset(inst_gen,return_state=True)
done = False

res = {'nn':[0 for i in range(6)],'RCL':[0 for i in range(6)]}

while not done:
    print(f'step {env.t}')
    [purchase,demand_compliance], la_dec = pIRPgym.Inventory.Stochastic_Rolling_Horizon(state,env,inst_gen)    
    
    nn_routes,nn_obj,nn_info,nn_time,nn_r = pIRPgym.Routing.NearestNeighbor(purchase,inst_gen,env.t,price_routes=True)
    for i in range(len(nn_routes)):
        res['nn'][i] += nn_r[i]; print(len(nn_routes))

    RCL_routes,RCL_obj,RCL_info,RCL_time,RCL_r = pIRPgym.Routing.NearestNeighbor(purchase,inst_gen,env.t,price_routes=True)
    for i in range(len(RCL_routes)):
        res['RCL'][i] += RCL_r[i]; print(len(RCL_routes))

    ''' Compound action'''        
    action = {'routing':nn_routes,'purchase':purchase,'demand_compliance':demand_compliance}

    state, reward, done, real_action, _,  = env.step(action,inst_gen)
    





#%%
testing_route = nn_routes[3]
reduced_cost = pIRPgym.Routing.PriceRoute(inst_gen,testing_route,purchase,env.t,solution=CG_routes)
print(f'The reduced cost is {reduced_cost}')




#%% Comparing 













#%%####################################### Single Episode/Singe Routing Policy Simulation  ########################################
# Episode simulation
# Simulations 
''' Parameters '''
verbose = True
strategies = ['CG','NN','RCL','GA']
start = process_time()
show_gap = True
string = str()

if verbose: string = verbose_module.routing_progress.print_iteration_head(strategies,show_gap)

# Episode's and performance storage
rewards=dict();  states=dict();   real_actions=dict();   backorders=dict();   la_decisions=dict()
perished=dict(); actions=dict()

indicators = ['Obj','time','vehicles','reactive_missing','extra_cost']
routing_performance = {s:{ind:list() for ind in indicators} for s in strategies}

inst_gen.generate_basic_random_instance(det_rd_seed,stoch_rd_seed,q_params=q_params,
                                        p_params=p_params,d_params=d_params,h_params=h_params,discount=disc)

# Reseting the environment
state = env.reset(inst_gen,return_state=True)

done = False
while not done:
    # Environment transition
    states[env.t] = state

    ''' Purchase'''
    [purchase,demand_compliance], la_dec = pIRPgym.Inventory.Stochastic_Rolling_Horizon(state,env,inst_gen)

    if verbose: string = verb.routing_progress.print_step(env.t,start,purchase)
    
    ''' Routing '''
    # GA_extra_cost = env.compute_solution_real_cost(inst_gen,GA_routes,purchase)   
    if 'CG' in strategies:
        CG_routes,CG_obj,CG_info,CG_time = pIRPgym.Routing.ColumnGeneration(purchase,inst_gen,env.t,time_limit=False,verbose=False)       # Column Generation algorithm                  
        extra_cost,total_missing = pIRPgym.Routing_management.evaluate_dynamic_potential(inst_gen,env,CG_routes,purchase)
        routing_performance['CG']['Obj'].append(CG_obj)
        routing_performance['CG']['time'].append(CG_time)
        routing_performance['CG']['vehicles'].append(len(CG_routes))
        routing_performance['CG']['reactive_missing'].append(total_missing)
        routing_performance['CG']['extra_cost'].append(extra_cost)

        if verbose: string = verb.routing_progress.print_routing_update(string,CG_time,len(CG_routes),CG_obj)

    if 'NN' in strategies:
        nn_routes,nn_obj,nn_info,nn_time = pIRPgym.Routing.NearestNeighbor(purchase,inst_gen,env.t)
        extra_cost,total_missing = pIRPgym.Routing_management.evaluate_dynamic_potential(inst_gen,env,nn_routes,purchase)
        routing_performance['NN']['Obj'].append(nn_obj)
        routing_performance['NN']['time'].append(nn_time)
        routing_performance['NN']['vehicles'].append(len(nn_routes))
        routing_performance['NN']['reactive_missing'].append(total_missing)
        routing_performance['NN']['extra_cost'].append(extra_cost)                                         # Nearest Neighbor
        if verbose and show_gap:   string = verb.routing_progress.print_routing_update(string,nn_time,len(nn_routes),nn_obj,CG_obj=CG_obj)
        elif verbose and not show_gap:  string = verb.routing_progress.print_routing_update(string,nn_time,len(nn_routes),nn_obj)

    if 'RCL' in strategies:
        RCL_obj,RCL_veh,RCL_time,RCL_EC,RCL_missing = pIRPgym.Routing.evaluate_stochastic_policy(pIRPgym.Routing.RCL_Heuristic,
                                                                                           purchase,inst_gen,env,n=30,return_average=True)
        routing_performance['RCL']['Obj'].append(RCL_obj)
        routing_performance['RCL']['time'].append(RCL_time)
        routing_performance['RCL']['vehicles'].append(RCL_veh)
        routing_performance['RCL']['reactive_missing'].append(RCL_missing)
        routing_performance['RCL']['extra_cost'].append(RCL_EC)
        # RCL_routes,RCL_obj,(RCL_distances,RCL_loads),RCL_time  = pIRPgym.Routing.RCL_Heuristic(purchase,inst_gen,env.t)                                 # RCL based constructive
        if verbose and show_gap: string = verb.routing_progress.print_routing_update(string,RCL_time,RCL_veh,RCL_obj,CG_obj=CG_obj)
        elif verbose and not show_gap: string = verb.routing_progress.print_routing_update(string,RCL_time,RCL_veh,RCL_obj)

    if 'GA' in strategies:
        GA_routes,GA_obj,(GA_distances,GA_loads),GA_time,_ = pIRPgym.Routing.HybridGenticAlgorithm(purchase,inst_gen,env.t,return_top=False,rd_seed=0,time_limit=40)    # Genetic Algorithm
        extra_cost,total_missing = pIRPgym.Routing_management.evaluate_dynamic_potential(inst_gen,env,GA_routes,purchase)
        routing_performance['GA']['Obj'].append(GA_obj)
        routing_performance['GA']['time'].append(GA_time)
        routing_performance['GA']['vehicles'].append(len(GA_routes))
        routing_performance['GA']['reactive_missing'].append(total_missing)
        routing_performance['GA']['extra_cost'].append(extra_cost)
        if verbose and show_gap:  string = verb.routing_progress.print_routing_update(string,GA_time,len(GA_routes),sum(GA_distances),CG_obj=CG_obj,end=True)
        elif verbose and not show_gap: string = verb.routing_progress.print_routing_update(string,GA_time,len(GA_routes),sum(GA_distances),end=True)

    if 'HGS*' in strategies:
        HyGeSe_routes, HyGeSe_distance, HyGeSe_time  = pIRPgym.Routing.HyGeSe.HyGeSe_routing(purchase,inst_gen,env.t,time_limit=5)                                   # Hybrid Genetic Search (CVRP)
        extra_cost,total_missing = pIRPgym.Routing_management.evaluate_dynamic_potential(inst_gen,env,HyGeSe_routes,purchase)
        routing_performance['HGS*']['Obj'].append(HyGeSe_distance)
        routing_performance['HGS*']['time'].append(HyGeSe_time)
        routing_performance['HGS*']['vehicles'].append(len(HyGeSe_routes))
        routing_performance['HGS*']['reactive_missing'].append(total_missing)
        routing_performance['HGS*']['extra_cost'].append(extra_cost)
        if verbose and show_gap:  string = verb.routing_progress.print_routing_update(string,HyGeSe_time,len(HyGeSe_routes),HyGeSe_distance,CG_obj=CG_obj)
        elif verbose and not show_gap:  string = verb.routing_progress.print_routing_update(string,HyGeSe_time,len(HyGeSe_routes),HyGeSe_distance)


    ''' Compound action'''        
    action = {'routing':CG_routes,'purchase':purchase,'demand_compliance':demand_compliance}

    state, reward, done, real_action, _,  = env.step(action,inst_gen)
    if done:   states[env.t] = state
    
    # Data storage
    actions[env.t-1] = action
    real_actions[env.t-1] = real_action
    backorders[env.t-1] = _["backorders"]
    perished[env.t-1] = {k:_["perished"][k] if k in _["perished"] else 0 for k in inst_gen.Products}
    rewards[env.t] = reward 
    la_decisions[env.t-1] = la_dec

print('Finished episode!!!')

### Storing 

