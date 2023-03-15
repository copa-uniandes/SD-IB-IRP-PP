#from SD_IB_IRP_PPenv import steroid_IRP
from InstanceGenerator import instance_generator
from Policies import policies
import matplotlib.pyplot as plt

#################################   Environment's parameters   #################################
# Random seed
d_rd_seed = 0
s_rd_seed = 0

# SD-IB-IRP-PP model's parameters
backorders = 'backorders'
stochastic_params = False

# Feature's parameters
look_ahead = ['*']
historical_data = ['*']

# Action's parameters
validate_action = False
warnings = False

# Other parameters
num_episodes = 5
env_config = { 'M': 3, 'K': 3, 'T': 7,  'F': 1, 
               'S': 2,  'LA_horizon': 3, 'back_o_cost':1e12}

# Offer
q_params = {'distribution': 'c_uniform', 'r_f_params': [6,20]}
p_params = {'distribution': 'd_uniform', 'r_f_params': [20,61]}

# Demand
d_params = {'distribution': 'log-normal', 'r_f_params': [2,0.5]}

# Holding costs
h_params = {'distribution': 'd_uniform', 'r_f_params': [20,61]}

#################################   Instance's parameters   #################################
inst = instance_generator(look_ahead, stochastic_params, historical_data, backorders, env_config = env_config)
inst.generate_instance(d_rd_seed, s_rd_seed, q_params = q_params, p_params = p_params, d_params = d_params, h_params = h_params)

# ############## Offer ##############
# t = 0
# print('QUANTITIES')
# print('Last historic values:')
# print(f'K\M \t 1 \t 2 \t 3')
# for k in inst.Products:
#     print(f'{k} \t {inst.hist_q[t][1,k][-1]} \t {inst.hist_q[t][2,k][-1]} \t {inst.hist_q[t][3,k][-1]}' )

# print('\n\nRealized values:')
# print(f'K\M \t 1 \t 2 \t 3')
# for k in inst.Products:
#     print(f'{k} \t {inst.W_q[t][1,k]} \t {inst.W_q[t][2,k]} \t {inst.W_q[t][3,k]}' )

# print('\n\nSample paths:')
# print('Sample \t (i, k) \t sample path')
# for sample in inst.Samples:
#     cont = 0
#     for i in inst.Suppliers:
#         for k in inst.Products:
#             if cont == 0:
#                 print(f'{sample} \t {i,k} \t {[inst.s_paths_q[t][day, sample][i,k] for day in range(inst.sp_window_sizes[t])]}')
#             else:
#                 print(f'\t {i,k} \t {[inst.s_paths_q[t][day, sample][i,k] for day in range(inst.sp_window_sizes[t])]}')
#             cont += 1

# print('PRICES')
# print('Last historic values:')
# print(f'K\M \t 1 \t 2 \t 3')
# for k in inst.Products:
#     print(f'{k} \t {inst.hist_p[t][1,k][-1]} \t {inst.hist_p[t][2,k][-1]} \t {inst.hist_p[t][3,k][-1]}' )

# print('\n\nRealized values:')
# print(f'K\M \t 1 \t 2 \t 3')
# for k in inst.Products:
#     print(f'{k} \t {inst.W_p[t][1,k]} \t {inst.W_p[t][2,k]} \t {inst.W_p[t][3,k]}' )

# print('\n\nSample paths:')
# print('Sample \t (i, k) \t sample path')
# for sample in inst.Samples:
#     cont = 0
#     for i in inst.Suppliers:
#         for k in inst.Products:
#             if cont == 0:
#                 print(f'{sample} \t {i,k} \t {[inst.s_paths_p[t][day, sample][i,k] for day in range(inst.sp_window_sizes[t])]}')
#             else:
#                 print(f'\t {i,k} \t {[inst.s_paths_p[t][day, sample][i,k] for day in range(inst.sp_window_sizes[t])]}')
#             cont += 1


############## Demand ##############
# t = 0
# print('Last historic values:')
# for k in inst.Products:
#     print(f'{k} \t {inst.hist_d[t][k][-1]}' )

# print('\n\nRealized values:')
# print(f'K')
# for k in inst.Products:
#     print(f'{k} \t {inst.W_d[t][k]}' )

# print('\n\nSample paths:')
# print('Sample \t (k) \t sample path')
# for sample in inst.Samples:
#     cont = 0
#     for k in inst.Products:
#         if cont == 0:
#             print(f'{sample} \t {k} \t {[inst.s_paths_d[t][day, sample][k] for day in range(inst.sp_window_sizes[t])]}')
#         else:
#             print(f'\t {k} \t {[inst.s_paths_d[t][day, sample][k] for day in range(inst.sp_window_sizes[t])]}')
#         cont += 1























# generator = instance_generator(env, rd_seed = 0)


# # Deterministic parameters
# O_k = generator.gen_ages()
# Ages = {k: range(1, O_k[k] + 1) for k in env.Products}
# c = generator.gen_routing_costs()

# # Availabilities
# M_kt, K_it = generator.gen_availabilities()

# # Stochastic parameters
# generator.gen_quantities(**q_params)
# generator.gen_demand(**d_params)

# # Other deterministic parameters
# p_t = generator.gen_p_price(**p_params)
# h_t = generator.gen_h_cost(**h_params)

# print(generator.sample_paths)








































'''
POLICY EVALUATION FUNCTION
'''
# def Policy_evaluation(num_episodes = 1000):
    
#     rewards = {}
#     states = {}
#     real_actions = {}
#     backorders = {}
#     la_decisions = {}
#     realized_dem = {}
#     q_sample = {}
#     tws = {}
#     env = steroid_IRP( look_ahead = look_ahead, 
#                        historical_data = historical_data, 
#                        backorders = backorderss,
#                        stochastic_parameters = stochastic_parameters, 
#                        env_config = env_config)

#     policy = policies()

#     for episode in range(num_episodes):

#         state, _ = env.reset(return_state = True, rd_seed = rd_seed, 
#           q_params = q_params, 
#           p_params = p_params,
#           d_params = d_params,
#           h_params = h_params)
#         done = False

#         while not done:
            
#             print(f'############################# {env.t} #############################')
#             states[episode,env.t] = state
#             action, la_dec = policy.stochastic_rolling_horizon(state, _, env)
#             print(action[0])
#             q_sample[episode,env.t] = [_["sample_paths"]["q"][0,s] for s in env.Samples]
#             state, reward, done, real_action, _,  = env.step(action, validate_action = validate_action, warnings = warnings)

#             real_actions[episode,env.t] = real_action
#             backorders[episode,env.t] = _["backorders"]
#             rewards[episode,env.t] = reward
#             la_decisions[episode,env.t] = la_dec
#             realized_dem[episode,env.t] = env.W_t["d"]
#             if done:
#                 tws[episode,env.t] = 1
#             else:
#                 tws[episode,env.t] = _["sample_path_window_size"]
            
#     iterables = (env.Suppliers, env.Products, env.Samples, env.M_kt, env.O_k, env.Horizon)
#     costs = (env.c, env.h_t, env.p_t, env.back_o_cost)

#     return rewards, states, real_actions, backorders, la_decisions, realized_dem, q_sample, tws, iterables, costs


# rewards, states, real_actions, backorders, la_decisions, realized_dem, q_sample, tws, iterables, costs = Policy_evaluation(num_episodes = num_episodes)

