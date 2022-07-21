
"""
@author: juanbeta

TODO:
! FIX SAMPLE PATHS
! Check Q parameter
! Check HOLDING COST (TIMING)
! Backlogs not functioning under stochastic parameters


FUTURE WORK - Not completely developed:
- Instance_file uploading
- Continuous time horizon
- historical_file uploading
- Instance_file exporting

"""

################################## Modules ##################################
### Basic Librarires
import numpy as np; from copy import copy, deepcopy; import matplotlib.pyplot as plt
import networkx as nx; import sys; import pandas as pd; import math; import numpy as np
import time; from termcolor import colored
from random import random, seed, randint, shuffle

### Optimizer
import gurobipy as gu

### Renderizing
import imageio

### Gym & OR-Gym
import gym; #from gym import spaces
from or_gym import utils

################################ Description ################################
'''
State (S_t): The state according to Powell (three components): 
    - Physical State (R_t):
        state:  Current available inventory (!*): (dict)  Inventory of product k \in K of age o \in O_k
                When backlogs are activated, will appear under age 'B'
    - Other deterministic info (Z_t):
        p: Prices: (dict) Price of product k \in K at supplier i \in M
        q: Available quantities: (dict) Available quantity of product k \in K at supplier i \in M
        h: Holding cost: (dict) Holding cost of product k \in K
        historical_data: (dict) historical log of information (optional)
    - Belief State (B_t):
        sample_paths: Simulated sample paths (optional)

Action (X_t): The action can be seen as a three level-decision. These are the three layers:
    1. Routes to visit the selected suppliers
    2. Quantities to purchase on each supplier
    3. Demand compliance plan, dispatch decision
    4. (Optional) Backlogs compliance
    
    Accordingly, the action will be a list composed as follows:
    X = [routes, purchase, demand_compliance, backorders]
        - routes: (list) list of lists, each with the nodes visited on the route (including departure and arriving to the depot)
        - purchase: (dict) Units to purchase of product k \in K at supplier i \in M
        - demand_compliance: (dict) Units of product k in K of age o \in O_k used to satisfy the demand 
        - backlogs_compliance: (dict) Units of product k in K of age o \in O_k used to satisfy the backlogs


Exogenous information (W): The stochastic factors considered on the environment:
    Demand (dict) (*): Key k 
    Prices (dict) (*): Keys (i,k)
    Available quantities (dict) (*): Keys (i,k)
    Holding cost (dict) (*): Key k

(!*) Available inventory at the decision time. Never age 0 inventory.       
(*) Varying the stochastic factors might be of interest. Therefore, the deterministic factors
    will be under Z_t and stochastic factors will be generated and presented in the W_t
'''

################################## Steroid IRP class ##################################

class steroid_IRP(gym.Env): 
    '''
    Stochastic-Dynamic Inventory-Routing-Problem with Perishable Products environment
    
    INITIALIZATION
    Time Horizon: Two time horizon types (horizon_type = 'episodic')
    1. 'episodic': Every episode (simulation) has a finite number of time steps
        Related parameters:
            - T: Decision periods (time-steps)
    2. !!!NOT DEVELOPED!!! 'continuous': Never-ending episodes
        Related parameters: 
            - gamma: Discount factor
    (For internal environment's processes: 1 for episodic, 0 for continuous)
    
    Look-ahead approximation: Generation of sample paths (look_ahead = ['d']):
    1. List of parameters to be forecasted on the look-ahead approximation ['d', 'p', ...]
    2. List with '*' to generate foreecasts for all parameters
    3. False for no sample path generation
    Related parameters:
        - S: Number of sample paths
        - LA_horizon: Number of look-ahead periods
            
    historical data: Generation or usage of historical data (historical_data = ['d'])   
    Three historical data options:
    1.  ['d', 'p', ...]: List with the parameters the historical info will be generated for
    2.  ['*']: historical info generated for all parameters
    3.  !!!NOT DEVELOPED!!! path: File path to be processed by upload_historical_data() 
    4.  False: No historical data will be used
    Related parameter:
        - hist_window: Initial log size (time periods)
    
    Backorders: Catch unsatisfied demand (backorders = False):
    1. 'backorders': Demand may be not fully satisfied. Non-complied orders will be automatically fullfilled at an extra-cost
    2. 'backlogs': Demand may be not fully satisfied. Non-complied orders will be registered and kept track of on age 'B'
    3. False: All demand must be fullfilled
    Related parameter:
        - back_o_cost = 20
        - back_l_cost = 20 
    
    PARAMETERS
    env_init = 'episodic': Time horizon type {episodic, continouos} 
    look_ahead = ['d']: Generate sample paths for look-ahead approximation
    historical_data = ['d']: Use of historicalal data
    backorders = False: Backorders
    rd_seed = 0: Seed for random number generation
    wd = True: Working directory path
    file_name = True: File name when uploading instances from .txt
    **kwargs: 
        M = 10: Number of suppliers
        K = 10: Number of Products
        F = 2:  Number of vehicles on the fleet
        T = 6:  Number of decision periods
        
        wh_cap = 1e9: Warehouse capacity
        min/max_sprice: Max and min selling prices (per m and k)
        min/max_hprice: Max and min holding cost (per k)
        penalization_cost: Penalization costs for RL
        
        S = 4:  Number of sample paths 
        LA_horizon = 5: Number of look-ahead periods
        lambda1 = 0.5: Controls demand, assures feasibility
        
    Two main functions:
    -   reset(return_state = False)
    -   step(action)
    '''
    
    # Initialization method
    def __init__(self, horizon_type = 'episodic', look_ahead = ['*'], historical_data = ['*'], backorders = False,
                 stochastic_parameters = [], rd_seed = 0, wd = True, file_name = True, **kwargs):

        seed(rd_seed)
        
        ### Main parameters ###
        self.M = 10                                     # Suppliers
        self.K = 10                                     # Products
        self.F = 4                                      # Fleet
        
        ### Other parameters ### 
        self.wh_cap = 1e9                               # Warehouse capacity
        self.min_sprice = 1;  self.max_sprice = 500
        self.min_hprice = 1;  self.max_hprice = 500
        self.penalization_cost = 1e9
        self.lambda1 = 0.5

        self.Q = 100 #!!!!!!!!
        self.stochastic_parameters = stochastic_parameters
        
        self.hor_typ = horizon_type == 'episodic'
        if self.hor_typ:    self.T = 6
        
        ### Look-ahead parameters ###
        if look_ahead:    
            self.S = 4              # Number of sample paths
            self.LA_horizon = 5     # Look-ahead time window's size
        
        ### historical log parameters ###
        if type(historical_data) == list:        
            self.hist_window = 40       # historical window

        ### Backorders parameters ###
        if backorders == 'backorders':
            self.back_o_cost = 20
        elif backorders == 'backlogs':
            self.back_l_cost = 20

        ### Custom configurations ###
        if file_name:
            utils.assign_env_config(self, kwargs)
            self.gen_sets()

        ### State space ###
        # Physical state
        self.state = {}     # Inventory
        
        ### Extra information ###
        self.others = {'look_ahead':look_ahead, 'historical': historical_data, 'wd': wd, 'file_name': file_name, 
                        'backorders': backorders}


    # Reseting the environment
    def reset(self, return_state = False):
        '''
        Reseting the environment. Genrate or upload the instance.
        PARAMETER:
        return_state: Indicates whether the state is returned
         
        '''   
        # Environment generated data
        if self.others['file_name']:  
            # General parameters
            self.gen_det_params()
            self.Ages = {k: range(1,self.O_k[k] + 1) for k in self.Products}
            self.gen_instance_data()
            
            # Episodic horizon
            if self.hor_typ:
                # Cuerrent time-step
                self.t = 0

            ## State ##
            self.state = {(k,o):0   for k in self.Products for o in self.Ages[k]}
            if self.others['backorders'] == 'backlogs':
                for k in self.Products:
                    self.state[k,'B'] = 0

            if self.hor_typ:
                self.p = {(i,k): self.p_t[i,k,self.t] for i in self.Suppliers for k in self.Products}
                self.q = {(i,k): self.q_t[i,k,self.t] for i in self.Suppliers for k in self.Products}
                self.h = {k: self.h_t[k,self.t] for k in self.Products}
                self.d = {k: self.d_t[k,self.t] for k in self.Products}
            else:
                self.gen_realization()

            # Look-ahead, sample paths
            if self.others['look_ahead']:
                self.sample_path_window_size = copy(self.LA_horizon)
                self.gen_sample_paths()                        
            
        # TODO! Data file upload 
        else:
            # Cuerrent time-step
            self.t = 0
            
            # Upload parameters from file
            self.O_k, self.c, self.Q, self.h_t, self.M_kt, self.K_it, self.q_t, self.p_t, 
            self.d_t, inventory = self.upload_instance(self.file_name, self.wd)
            
            # State
            self.state = inventory
        
        if return_state:    
            # EXTRA INFORMATION TO BE RETURNED
            _ = {'p': self.p, 'q': self.q, 'h': self.h, 'd': self.d}
            if self.others['historical']:
                _['historical_info'] = self.historical_data
            if self.others['look_ahead']:
                _['sample_paths'] = self.sample_paths
            return self.state, _
        
    
    # Step 
    def step(self, action, validate_action = False, warnings = True):
        if validate_action:
            self.action_validity(action)

        # Exogenous information realization 
        W = self.gen_exog_info_W()
        real_action = self.get_real_actions(action, W)

        # Inventory dynamics
        s_tprime, reward = self.transition_function(real_action, W, warnings)

        # Reward
        transport_cost, purchase_cost, holding_cost, backorders_cost = self.compute_costs(real_action, s_tprime)
        reward += transport_cost + purchase_cost + holding_cost + backorders_cost

        # Time step update and termination check
        self.t += 1
        done = self.check_termination(s_tprime)
        _ = {}

        # State update
        if not done:
            self.update_state(s_tprime)
    
            # EXTRA INFORMATION TO BE RETURNED
            _ = {'p': self.p, 'q': self.q, 'h': self.h, 'd': self.d}
            if self.others['historical']:
                _['historical_info'] = self.historical_data
            if self.others['look_ahead']:
                _['sample_paths'] = self.sample_paths
            
        return self.state, reward, done, _
    
    
    def action_validity(self, action):
        routes, purchase, demand_compliance = action[:3]
        if self.others['backorders'] == 'backlogs':   back_o_compliance = action[3]
        valid = True
        error_msg = ''
        
        # Routing check
        assert not len(routes) > self.F, 'The number of routes exceedes the number of vehicles'

        for route in routes:
            assert not (route[0] != 0 or route[-1] != 0), \
                'Routes not valid, must start and end at the depot'

            route_capacity = sum(purchase[node,k] for k in self.Products for node in route[1:-2])
            assert not route_capacity > self.Q, \
                "Purchased items exceed vehicle's capacity"

            assert not len(set(route)) != len(route) - 1, \
                'Suppliers can only be visited once by a route'

            for i in range(len(route)):
                assert not route[i] not in self.V, \
                    'Route must be composed of existing suppliers' 
            
        # Purchase
        for i in self.Suppliers:
            for k in self.Products:
                assert not purchase[i,k] > self.q[i,k], \
                    f"Purchased quantities exceed suppliers' available quantities  ({i},{k})"
        
        # Demand_compliance
        for k in self.Products:
            assert not (self.others['backorders'] != 'backlogs' and demand_compliance[k,0] > sum(purchase[i,k] for i in self.Suppliers)), \
                f'Demand compliance with purchased items of product {k} exceed the purchase'

            assert not (self.others['backorders'] == 'backlogs' and demand_compliance[k,0] + back_o_compliance[k,0] > sum(purchase[i,k] for i in self.Suppliers)), \
                f'Demand/backlogs compliance with purchased items of product {k} exceed the purchase'

            assert not sum(demand_compliance[k,o] for o in range(self.O_k[k] + 1)) > self.d[k], \
                f'Trying to comply a non-existing demand of product {k}' 
            
            for o in range(1, self.O_k[k] + 1):
                assert not (self.others['backorders'] != 'backlogs' and demand_compliance[k,o] > self.state[k,o]), \
                    f'Demand compliance with inventory items exceed the stored items  ({k},{o})' 
                
                assert not (self.others['backorders'] == 'backlogs' and demand_compliance[k,o] + back_o_compliance[k,o] > self.state[k,o]), \
                    f'Demand/Backlogs compliance with inventory items exceed the stored items ({k},{o})'

        # backlogs
        if self.others['backorders'] == 'backlogs':
            for k in self.Products:
                assert not sum(back_o_compliance[k,o] for o in range(self.O_k[k])) > self.state[k,'B'], \
                    f'Trying to comply a non-existing backlog of product {k}'
        
        elif self.others['backorders'] == False:
            for k in self.Products:
                assert not sum(demand_compliance[k,o] for o in range(self.O_k[k] + 1)) < self.d[k], \
                    f'Demand of product {k} was not fullfiled'


    def get_real_actions(self, action, W):
        purchase, demand_compliance = action[:3]

        '''
        Demand compliance must take into account the realized demand, take out the latest inventory
        '''

        real_purchase = {(i,k): min(purchase[i,k], W['q'][i,k]) for i in self.Suppliers for k in self.Products}
        real_demand_compliance = {(k,o): min(demand_compliance[k,0], real_purchase[k,o]) for k in self.Suppliers for o in range(self.O_k[k] + 1)}

        real_action = [action[0], real_purchase, real_demand_compliance]

        return real_action


    # Compute costs of a given procurement plan for a given day
    def compute_costs(self, action, s_tprime):
        routes, purchase, demand_compliance = action[:3]
        if self.others['backorders'] == 'backlogs':   back_o_compliance = action[3]

        transport_cost = 0
        for route in routes:
            transport_cost += sum(self.c[route[i], route[i + 1]] for i in range(len(route) - 1))
        
        purchase_cost = sum(purchase[i,k] * self.p[i,k]   for i in self.Suppliers for k in self.Products)
        
        # TODO!!!!!
        holding_cost = sum(sum(s_tprime[k,o] for o in range(1, self.O_k[k] + 1)) * self.h[k] for k in self.Products)

        backorders_cost = 0
        if self.others['backorders'] == 'backorders':
            backorders = round(sum(max(self.d[k] - sum(demand_compliance[k,o] for o in range(self.O_k[k]+1)),0) for k in self.Products),1)
            print(f'backorders: {backorders}')
            backorders_cost = backorders * self.back_o_cost
        
        elif self.others['backorders'] == 'backlogs':
            backorders_cost = sum(s_tprime[k,'B'] for k in self.Products) * self.back_l_cost

        return transport_cost, purchase_cost, holding_cost, backorders_cost
            
    
    # Inventory dynamics of the environment
    def transition_function(self, real_action, W, warnings):
        purchase, demand_compliance = real_action[1:3]
        # backlogs
        if self.others['backorders'] == 'backlogs':
            back_o_compliance = real_action[3]
        inventory = deepcopy(self.state)
        reward  = 0

        # Inventory update
        for k in self.Products:
            inventory[k,1] = round(sum(purchase[i,k] for i in self.Suppliers) - demand_compliance[k,0],1)

            max_age = self.O_k[k]
            if max_age > 1:
                for o in range(2, max_age + 1):
                        inventory[k,o] = round(self.state[k,o - 1] - demand_compliance[k,o - 1],1)
            
            if self.others['backorders'] == 'backlogs':
                new_backlogs = round(max(self.W['d'][k] - sum(demand_compliance[k,o] for o in range(self.O_k[k] + 1)),0),1)
                inventory[k,'B'] = round(self.state[k,'B'] + new_backlogs - sum(back_o_compliance[k,o] for o in range(self.O_k[k]+1)),1)

            # Factibility checks         
            if warnings:
                if self.state[k, max_age] - demand_compliance[k,max_age] > 0:
                    reward += self.penalization_cost
                    print(colored(f'Warning! {self.state[k, max_age] - demand_compliance[k,max_age]} units of {k} were lost due to perishability','yellow'))
    

                if sum(demand_compliance[k,o] for o in range(self.O_k[k] + 1)) < W['d'][k]:
                    print(colored(f'Warning! Demand of product {k} was not fullfiled', 'yellow'))

            # if sum(inventory[k,o] for k in self.Products for o in range(self.O_k[k] + 1)) > self.wh_cap:
            #     reward += self.penalization_cost
            #     print(f'Warning! Capacity of the whareouse exceeded')

        return inventory, reward


    # Checking for episode's termination
    def check_termination(self, s_tprime):
        done = False

        # Time-step limit
        if self.hor_typ:
            done = self.t >= self.T
         
        # # Exceedes wharehouse capacitiy
        # if sum(s_tprime[k,o] for k in self.Products for o in range(1, self.O_k[k] + 1)) >= self.wh_cap:
        #     done = True

        return done

    def update_state(self, s_tprime):
        # Update historicalals
        for k in self.Products:
            for i in self.Suppliers:
                if 'p' in self.others['historical']  or '*' in self.others['historical']:
                    self.historical_data['p'][i,k].append(self.p[i,k])
                if 'q' in self.others['historical']  or '*' in self.others['historical']:
                    self.historical_data['q'][i,k].append(self.q[i,k])
            if 'h' in self.others['historical']  or '*' in self.others['historical']:
                self.historical_data['h'][k].append(self.h[k])
            if 'd' in self.others['historical']  or '*' in self.others['historical']:
                self.historical_data['d'][k].append(self.d[k])

        # Update state
        if self.hor_typ:
            self.p = {(i,k): self.p_t[i,k,self.t] for i in self.Suppliers for k in self.Products}
            self.q = {(i,k): self.q_t[i,k,self.t] for i in self.Suppliers for k in self.Products}
            self.h = {k: self.h_t[k,self.t] for k in self.Products}
            self.d = {k: self.d_t[k,self.t] for k in self.Products}
        else:
            self.gen_realization()

        self.state = s_tprime

        # Update sample-paths
        self.gen_sample_paths()
     
        
    # Generates exogenous information vector W (stochastic realizations for each random variable)
    def gen_exog_info_W(self):
        W = {}
        tprime = self.t + 1

        if 'h' in self.stochastic_parameters:
            W['h'] = {k:randint(self.min_hprice, self.max_hprice) for k in self.Products}
        else:
            W['h'] = {k:self.h_t[k,self.h[tprime]] for k in self.Products}
        
        M_k = {}
        for k in self.Products:
            sup = randint(1, self.M)
            M_k[k] = list(self.Suppliers)
            for ss in range(self.M - sup):
                a = int(randint(0, len(M_k[k])-1))
                del M_k[k][a]
        
        K_it = {i:[k for k in self.Products if i in M_k[k]] for i in self.Suppliers}
        
        if 'q' in self.stochastic_parameters:
            W['q'] = {(i,k):randint(1,15) if i in self.M_k[k] else 0 for i in self.Suppliers for k in self.Products}
        else:
            W['q'] = {(i,k):self.q_t[i,k,tprime] for i in self.Suppliers for k in self.Products}

        if 'p' in self.stochastic_parameters:
            W['p'] = {(i,k):randint(1,500) if i in M_k[k] else 1000 for i in self.Suppliers for k in self.Products}
        else:
            W['p'] = {(i,k):self.p_t[i,k,tprime] for i in self.Suppliers for k in self.Products}

        if 'd' in self.stochastic_parameters:
            W['d'] = {k:round((self.lambda1 * max([W['q'][i,k] for i in self.Suppliers]) + (1-self.lambda1)*sum([W['q'][i,k] for i in self.Suppliers])),1) for k in self.Products} 
        else:
            W['d'] = {k:self.d_t[k,tprime] for k in self.Products}

        return W
    

    # Auxiliary method: Generate iterables of sets
    def gen_sets(self):
    
        self.Suppliers = range(1,self.M);  self.V = range(self.M)
        self.Products = range(self.K)
        self.Vehicles = range(self.F)
        self.Samples = range(self.S)
        self.Horizon = range(self.T)
        self.TW = range(-self.hist_window, self.T)
        self.historical = range(-self.hist_window, 0)
            

    # Generate deterministic parameters 
    def gen_det_params(self):
        ''' 
        Rolling horizon model parameters generation function
        Generates:
            - O_k: (dict) maximum days that k \in K can be held in inventory
            - c: (dict) transportation cost between nodes i \in V and j \in V
        '''
        # Maximum days that product k can be held in inventory before rotting
        self.O_k = {k:randint(1, self.T) for k in self.Products}
        
        # Suppliers locations in grid
        size_grid = 1000
        coor = {i:(randint(0, size_grid), randint(0, size_grid)) for i in self.V}
        # Transportation cost between nodes i and j, estimated using euclidean distance
        self.c = {(i,j):round(np.sqrt((coor[i][0]-coor[j][0])**2 + (coor[i][1]-coor[j][1])**2)) for i in self.V for j in self.V if i!=j} 
    
    
    # Auxiliary function to manage historical and simulated data 
    def gen_instance_data(self):
        if type(self.others['historical']) == list: 
            self.gen_simulated_data()
   
        elif type(self.others['historical']) == str:  
            self.upload_historical_data()
        
        else:
            raise ValueError('historical information parameter value not valid')
                  
    
    # Generate historical and simulated stochastic parameters based on the requirement
    def gen_simulated_data(self):
        ''' 
        Simulated historicalal and sumulated data generator for quantities, prices and demand of products in each period.
        Generates:
            - h_t: (dict) holding cost of k \in K on t \in T
            - M_kt: (dict) subset of suppliers that offer k \in K on t \in T
            - K_it: (dict) subset of products offered by i \in M on t \in T
            - q_t: (dict) quantity of k \in K offered by supplier i \in M on t \in T
            - p_t: (dict) price of k \in K offered by supplier i \in M on t \in T
            - d_t: (dict) demand of k \in K on t \in T
            - historical_data: (dict) with generated historical values
        '''
        self.historical_data = {}
        # Random holding cost of product k on t
        if 'h' in self.others['historical'] or  '*' in self.others['historical']:   
            self.historical_data['h'] = {k: [randint(self.min_hprice, self.max_hprice) for t in self.historical] for k in self.Products}
        self.h_t = {(k,t):randint(self.min_hprice, self.max_hprice) for k in self.Products for t in self.Horizon}
    
        self.M_kt = {}
        # In each time period, for each product
        for k in self.Products:
            for t in self.TW:
                # Random number of suppliers that offer k in t
                sup = randint(1, self.M)
                self.M_kt[k,t] = list(self.Suppliers)
                # Random suppliers are removed from subset, regarding {sup}
                for ss in range(self.M - sup):
                    a = int(randint(0, len(self.M_kt[k,t])-1))
                    del self.M_kt[k,t][a]
        
        # Products offered by each supplier on each time period, based on M_kt
        self.K_it = {(i,t):[k for k in self.Products if i in self.M_kt[k,t]] for i in self.Suppliers for t in self.TW}
        
        # Random quantity of available product k, provided by supplier i on t
        if 'q' in self.others['historical'] or  '*' in self.others['historical']:
            self.historical_data['q']= {(i,k): [randint(1,15) if i in self.M_kt[k,t] else 0 for t in self.historical] for i in self.Suppliers for k in self.Products}
        self.q_t = {(i,k,t):randint(1,15) if i in self.M_kt[k,t] else 0 for i in self.Suppliers for k in self.Products for t in self.Horizon}

        # Random price of available product k, provided by supplier i on t
        if 'p' in self.others['historical'] or  '*' in self.others['historical']:
            self.historical_data['p'] = {(i,k): [randint(1,500) if i in self.M_kt[k,t] else 1000 for t in self.historical] for i in self.Suppliers for k in self.Products for t in self.historical}
        self.p_t = {(i,k,t):randint(1,500) if i in self.M_kt[k,t] else 1000 for i in self.Suppliers for k in self.Products for t in self.Horizon}

        # Demand estimation based on quantities - ensuring feasibility, no backlogs
        if 'd' in self.others['historical'] or  '*' in self.others['historical']:
            self.historical_data['d'] = {(k):[(self.lambda1 * max([self.historical_data['q'][i,k][t] for i in self.Suppliers]) + (1-self.lambda1)*sum([self.historical_data['q'][i,k][t] for i in self.Suppliers])) for t in self.historical] for k in self.Products}
        self.d_t = {(k,t):round((self.lambda1 * max([self.q_t[i,k,t] for i in self.Suppliers]) + (1-self.lambda1)*sum([self.q_t[i,k,t] for i in self.Suppliers])),1) for k in self.Products for t in self.Horizon}
    
   
    # Auxuliary sample value generator function
    def sim(self, hist):
        ''' 
        Sample value generator function.
        Returns a generated random number using acceptance-rejection method.
        Parameters:
        - hist: (list) historicalal dataset that is used as an empirical distribution for
                the random number generation
        '''
        Te = len(hist)
        sorted_data = sorted(hist)    
        
        prob, value = [], []
        for t in range(Te):
            prob.append((t+1)/Te)
            value.append(sorted_data[t])
        
        # Generates uniform random value for acceptance-rejection testing
        U = random()
        # Tests if the uniform random falls under the empirical distribution
        test = [i>U for i in prob]    
        # Takes the first accepted value
        sample = value[test.index(True)]
        
        return sample
    
    
    # Sample paths generator function
    def gen_sample_paths(self):
        ''' 
        Sample paths generator function.
        Returns:
            - Q_s: (float) feasible vehicle capacity to use in rolling horizon model in sample path s \in Sam
            - M_kts: (dict) subset of suppliers that offer k \in K on t \in T in sample path s \in Sam
            - K_its: (dict) subset of products offered by i \in M on t \in T in sample path s \in Sam
            - q_s: (dict) quantity of k \in K offered by supplier i \in M on t \in T in sample path s \in Sam
            - p_s: (dict) price of k \in K offered by supplier i \in M on t \in T in sample path s \in Sam
            - dem_s: (dict) demand of k \in K on t \in T in sample path s \in Sam
            - 
            - F_s: (iter) set of vehicles in sample path s \in Sam
        Parameters:
            - hist_T: (int) number of periods that the historicalal datasets have information of
            - today: (int) current time period
        '''

        if self.hor_typ and self.t + self.LA_horizon > self.T:
                self.sample_path_window_size = self.T - self.t

        self.sample_paths = {}
        
        for s in self.Samples:
            # For each product, on each period chooses a random subset of suppliers that the product has had
            self.sample_paths[('M_k',s)] = {(k,t): [self.M_kt[k,tt] for tt in range(-self.hist_window + 1, self.t)][randint(-self.hist_window + 1, self.t - 1)] for k in self.Products for t in range(1, self.sample_path_window_size)}
            for k in self.Products:
                self.sample_paths[('M_k',s)][(k,0)] = self.M_kt[k, self.t]
            
            # Products offered by each supplier on each time period, based on M_kts
            self.sample_paths[('K_i',s)] = {(i,t): [k for k in self.Products if i in self.sample_paths[('M_k',s)][(k,t)]] \
                for i in self.Suppliers for t in range(1, self.sample_path_window_size)}
            for i in self.Suppliers:
               self.sample_paths[('K_i',s)][(k,0)] = self.K_it[i, self.t]
            

            # For each supplier and product, on each period chooses a quantity to offer using the sample value generator function
            #if 'q' in self.others['look_ahead']:
            self.sample_paths[('q',s)] = {(i,k,t): self.sim(self.historical_data['q'][i,k]) if i in self.sample_paths[('M_k',s)][(k,t)] else 0 \
                for i in self.Suppliers for k in self.Products for t in range(1, self.sample_path_window_size)}
            for i in self.Suppliers:
                for k in self.Products:
                    self.sample_paths[('q',s)][(i,k,0)] = self.q[i,k]
            
            # For each supplier and product, on each period chooses a price using the sample value generator function
            if 'p' in self.others['look_ahead'] or '*' in self.others['look_ahead']:
                self.sample_paths[('p',s)] = {(i,k,t): self.sim(self.historical_data['p'][i,k]) if i in self.sample_paths[('M_k',s)][(k,t)] else 1000 \
                    for i in self.Suppliers for k in self.Products for t in range(1, self.sample_path_window_size)}
                for i in self.Suppliers:
                    for k in self.Products:
                        self.sample_paths[('p',s)][i,k,0] = self.p[i,k]
            
            if 'h' in self.others['look_ahead'] or '*' in self.others['look_ahead']:
                self.sample_paths[('h',s)] = {(k,t): self.sim(self.historical_data['h'][k]) for k in self.Products for t in range(1, self.sample_path_window_size)}
                for k in self.Products:
                    self.sample_paths[('h',s)][k,0] = self.h[k]
            
            # Estimates demand for each product, on each period, based on q_s
            if 'd' in self.others['look_ahead'] or '*' in self.others['look_ahead']:
                self.sample_paths[('d',s)] = {(k,t): (self.lambda1 * max([self.sample_paths[('q',s)][(i,k,t)] for i in self.Suppliers]) + (1 - self.lambda1) * sum([self.sample_paths[('q',s)][(i,k,t)] \
                    for i in  self.Suppliers])) for k in self.Products for t in range(1, self.sample_path_window_size)}
                for k in self.Products:
                    self.sample_paths[('d',s)][k,0] = self.d[k]
            
            # Vehicle capacity estimation
            # if 'Q' in self.others['look_ahead'] or '*' in self.others['look_ahead']:
            #     self.sample_paths[('Q',s)] = 1.2 * self.gen_Q()
            
            # Set of vehicles, based on estimated required vehicles
            # if 'F' in self.others['look_ahead'] or '*' in self.others['look_ahead']:
            #     self.sample_paths[('F',s)] = int(sum(self.sample_paths[('d',s)].values())/self.sample_paths[('Q',s)]+1)


    # TODO! Generate a realization of random variables for continuous time-horizon
    def gen_realization(self):
        pass

    
    # Load parameters from a .txt file
    def upload_instance(self, nombre, path = ''):
        
        #sys.path.insert(1, path)
        with open(nombre, "r") as f:
            
            linea1 = [x for x in next(f).split()];  linea1 = [x for x in next(f).split()] 
            Vertex = int(linea1[1])
            linea1 = [x for x in next(f).split()];  Products = int(linea1[1])
            linea1 = [x for x in next(f).split()];  Periods = int(linea1[1])
            linea1 = [x for x in next(f).split()];  linea1 = [x for x in next(f).split()] 
            Q = int(linea1[1])   
            linea1 = [x for x in next(f).split()]
            coor = {}
            for k in range(Vertex):
                linea1= [int(x) for x in next(f).split()];  coor[linea1[0]] = (linea1[1], linea1[2])   
            linea1 = [x for x in next(f).split()]  
            h = {}
            for k in range(Products):
                linea1= [int(x) for x in next(f).split()]
                for t in range(len(linea1)):  h[k,t] = linea1[t]    
            linea1 = [x for x in next(f).split()]
            d = {}
            for k in range(Products):
                linea1= [int(x) for x in next(f).split()]
                for t in range(len(linea1)):  d[k,t] = linea1[t]
            linea1 = [x for x in next(f).split()] 
            O_k = {}
            for k in range(Products):
                linea1= [int(x) for x in next(f).split()];  O_k[k] = linea1[1] 
            linea1 = [x for x in next(f).split()]
            Mk = {};  Km = {};  q = {};  p = {} 
            for t in range(Periods):
                for k in range(Products):
                    Mk[k,t] = []    
                linea1 = [x for x in next(f).split()] 
                for i in range(1, Vertex):
                    Km[i,t] = [];   linea = [int(x) for x in next(f).split()]  
                    KeyM = linea[0];   prod = linea[1];   con = 2 
                    while con < prod*3+2:
                        Mk[linea[con], t].append(KeyM);   p[(KeyM, linea[con],t)]=linea[con+1]
                        q[(KeyM, linea[con],t)]=linea[con+2];  Km[i,t].append(linea[con]);   con = con + 3
        
        self.M = Vertex;   self.Suppliers = range(1, self.M);   self.V = range(self.M)
        self.P = Products; self.Products = range(self.P)
        self.T = Periods;  self.Horizon = range(self.T)
 
        self.F, I_0, c  = self.extra_processing(coor)
        self.Vehicles = range(self.F)
        
        return O_k, c, Q, h, Mk, Km, q, p, d, I_0


    # Auxiliary method: Processing data from txt file 
    def extra_processing(self, coor):
        
        F = int(np.ceil(sum(self.d.values())/self.Q)); self.Vehicles = range(self.F)
        I_0 = {(k,o):0 for k in self.Products for o in range(1, self.O_k[k] + 1)} # Initial inventory level with an old > 1 
        
        # Travel cost between (i,j). It is the same for all time t
        c = {(i,j,t,v):round(np.sqrt(((coor[i][0]-coor[j][0])**2)+((coor[i][1]-coor[j][1])**2)),0) for v in self.Vehicles for t in self.Horizon for i in self.V for j in self.V if i!=j }
        
        return F, I_0, c


    # TODO! Uploading historical data  
    def upload_historical_data(self):  
        '''
        Method uploads information from file     
        
        '''
        file = self.others['historical']
        print('Method must be coded')

        '''
        self.h_t =
        self.q_t =
        self.p_t =
        self.d_t =
        '''

    # Simple function to visualize the inventory
    def print_inventory(self):
        max_O = max([self.O_k[k] for k in self.Products])
        listamax = [[self.state[k,o] for o in self.Ages[k]] for k in self.Products]
        df = pd.DataFrame(listamax, index=pd.Index([str(k) for k in self.Products], name='Products'),
        columns=pd.Index([str(o) for o in range(1, max_O + 1)], name='Ages'))

        return df


    # Printing a representation of the environment (repr(env))
    def __repr__(self):
        return f'Stochastic-Dynamic Inventory-Routing-Problem with Perishable Products instance. V = {self.M}; K = {self.K}; F = {self.F}'

        