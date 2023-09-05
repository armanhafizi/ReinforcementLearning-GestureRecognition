import gym
import numpy as np
import random
from copy import deepcopy

# Play an episode according to a given policy
# env: environment
# policy: function(env, state)
# render: whether to render the episode or not (default - False)
def play_episode(env, policy, render = False):
    states, actions, rewards = [], [], []
    states.append(env.reset())
    done = False
    if render: env.render()
    while not done:
        action = policy(env, states[-1])
        actions.append(action)
        obs, reward, done = env.step(action)
        if render: env.render()
        states.append(obs)
        rewards.append(reward)
    return states, actions, rewards

# Play an episode according to a given policy and add 
# to a replay buffer
# env: environment
# policy: function(env, state)
def play_episode_rb(env, policy, buf):
    states, actions, rewards = [], [], []
    states.append(env.reset())
    done = False
    while not done:
        action = policy(env, states[-1])
        actions.append(action)
        obs, reward, done = env.step(action)
        buf.add(states[-1], action, reward, obs, done)
        states.append(obs)
        rewards.append(reward)
    return states, actions, rewards


class Env:
    def __init__(self) -> None:
        self.labels = np.load('label.npy')
        self.windows = np.load('chunks.npy')
        self.seq_num = np.load('sequence.npy')

        self.s_l, self.s_s, self.mask = None, None, None
        self.selected_seq, self.selected_l = None, None
        self.i = 0
    
    def seed(self, seed):
        self.rng = np.random.RandomState(seed)

    def reset(self):
        self.s_l = self.rng.randint(0, 9)
        temp = self.labels == self.s_l
        n_seq = self.seq_num[temp].max()
        self.s_s = self.rng.randint(0, n_seq-1)

        self.mask = (self.seq_num == self.s_s) & (temp)
        self.selected_seq = self.windows[self.mask]
        self.selected_l = self.labels[self.mask]
        self.i = 0

        return self.selected_seq[0]

    def step(self, action):
        reward = -1
        if action == self.selected_l[self.i]:
            reward = +1
        
        self.i += 1
        done = 1
        if self.i + 1 < len(self.selected_seq):
            done = 0

        
        return self.selected_seq[self.i], reward, done


