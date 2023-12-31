import numpy as np
import utils.envs, utils.seed, utils.buffers, utils.torch, utils.common
import torch
import tqdm
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# Deep Q Learning

# Constants
SEEDS = [1,2,3]
t = utils.torch.TorchHelper()
DEVICE = t.device
WINDOW = 50
STRIDE = 10
OBS_N = WINDOW*9               # State space size
ACT_N = 10               # Action space size
MINIBATCH_SIZE = 10     # How many examples to sample per train step
GAMMA = 0.99            # Discount factor in episodic reward objective
LEARNING_RATE = 5e-4    # Learning rate for Adam optimizer
TRAIN_AFTER_EPISODES = 10   # Just collect episodes for these many episodes
TRAIN_EPOCHS = 5        # Train for these many epochs every time
BUFSIZE = 10000         # Replay buffer size
EPISODES = 10000          # Total number of episodes to learn over
TEST_EPISODES = 1       # Test episodes after every train episode
HIDDEN = 512            # Hidden nodes
TARGET_UPDATE_FREQ = 10 # Target network update frequency
STARTING_EPSILON = 1.0  # Starting epsilon
STEPS_MAX = 10000       # Gradually reduce epsilon over these many steps
EPSILON_END = 0.01      # At the end, keep epsilon at this value

def chunking():
    global WINDOW, STRIDE, OBS_N
    w, s = WINDOW, STRIDE
    OBS_N = WINDOW*9
    print('Window', w, 'Stride', s)
    # read data
    modes = ['circle-cw', 'circle-ccw', 'swipe-r', 'swipe-l', 'swipe-u', 'swipe-d', 'swipe-f', 'swipe-b', 'ok', 'stop']
    data_raw = {}
    for mode in modes:
        filename = 'data/' + mode + '.npy'
        data_raw[mode] = np.load(filename, allow_pickle=True)
    len(data_raw)
    # chunk
    label, sequence, chunks, next_chunks = [], [], [], []
    for m in range(len(modes)):
        mode = modes[m]
        for d in range(len(data_raw[mode])):
            datum = np.array(data_raw[mode][d])
            i = 0
            datum = (datum - datum.mean(0))/datum.std(0)
            while (i+1)*s+w < len(datum):
                chunk = datum[i*s: i*s+w]
                next_chunk = datum[(i+1)*s: (i+1)*s+w]
                label.append(m)
                sequence.append(d)
                chunks.append(np.array(chunk).reshape(w*9,))
                next_chunks.append(np.array(next_chunk).reshape(w*9,))
                i += 1
    label, sequence, chunks, next_chunks = np.array(label), np.array(sequence), np.array(chunks), np.array(next_chunks)
    # save
    np.save('label', label, allow_pickle=True)
    np.save('sequence', sequence, allow_pickle=True)
    np.save('chunks', chunks, allow_pickle=True)
    np.save('next_chunks', next_chunks, allow_pickle=True)
# Global variables
EPSILON = STARTING_EPSILON
Q = None

# Create environment
# Create replay buffer
# Create network for Q(s, a)
# Create target network
# Create optimizer
def create_everything(seed):

    utils.seed.seed(seed)
    env = utils.envs.Env()
    env.seed(seed)
    test_env = utils.envs.Env()
    test_env.seed(10+seed)
    buf = utils.buffers.ReplayBuffer(BUFSIZE)
    Q = torch.nn.Sequential(
        torch.nn.Linear(OBS_N, HIDDEN), torch.nn.ReLU(),
        torch.nn.Linear(HIDDEN, HIDDEN), torch.nn.ReLU(),
        torch.nn.Linear(HIDDEN, ACT_N)
    ).to(DEVICE)
    Qt = torch.nn.Sequential(
        torch.nn.Linear(OBS_N, HIDDEN), torch.nn.ReLU(),
        torch.nn.Linear(HIDDEN, HIDDEN), torch.nn.ReLU(),
        torch.nn.Linear(HIDDEN, ACT_N)
    ).to(DEVICE)
    OPT = torch.optim.Adam(Q.parameters(), lr = LEARNING_RATE)
    return env, test_env, buf, Q, Qt, OPT

# Update a target network using a source network
def update(target, source):
    for tp, p in zip(target.parameters(), source.parameters()):
        tp.data.copy_(p.data)

# Create epsilon-greedy policy
def policy(env, obs):

    global EPSILON, Q

    obs = t.f(obs).view(-1, OBS_N)  # Convert to torch tensor
    
    # With probability EPSILON, choose a random action
    # Rest of the time, choose argmax_a Q(s, a) 
    if np.random.rand() < EPSILON:
        action = np.random.randint(ACT_N)
    else:
        qvalues = Q(obs)
        action = torch.argmax(qvalues).item()
    
    # Epsilon update rule: Keep reducing a small amount over
    # STEPS_MAX number of steps, and at the end, fix to EPSILON_END
    EPSILON = max(EPSILON_END, EPSILON - (1.0 / STEPS_MAX))
    # print(EPSILON)

    return action


# Update networks
def update_networks(epi, buf, Q, Qt, OPT):
    
    # Sample a minibatch (s, a, r, s', d)
    # Each variable is a vector of corresponding values
    S, A, R, S2, D = buf.sample(MINIBATCH_SIZE, t)
    
    # Get Q(s, a) for every (s, a) in the minibatch
    qvalues = Q(S).gather(1, A.view(-1, 1)).squeeze()

    # Get max_a' Qt(s', a') for every (s') in the minibatch
    q2values = torch.max(Qt(S2), dim = 1).values

    # If done, 
    #   y = r(s, a) + GAMMA * max_a' Q(s', a') * (0)
    # If not done,
    #   y = r(s, a) + GAMMA * max_a' Q(s', a') * (1)       
    targets = R + GAMMA * q2values * (1-D)

    # Detach y since it is the target. Target values should
    # be kept fixed.
    loss = torch.nn.MSELoss()(targets.detach(), qvalues)

    # Backpropagation
    OPT.zero_grad()
    loss.backward()
    OPT.step()

    # Update target network every few steps
    if epi % TARGET_UPDATE_FREQ == 0:
        update(Qt, Q)

    return loss.item()

# Play episodes
# Training function
def train(seed):

    global EPSILON, Q
    print("Seed=%d" % seed)

    # Create environment, buffer, Q, Q target, optimizer
    env, test_env, buf, Q, Qt, OPT = create_everything(seed)
    accs, preds = [], []

    # epsilon greedy exploration
    EPSILON = STARTING_EPSILON

    testRs = []
    last25testRs = []
    print("Training:")
    pbar = tqdm.trange(EPISODES)
    for epi in pbar:

        # Play an episode and log episodic reward
        S, A, R = utils.envs.play_episode_rb(env, policy, buf)
        
        # Train after collecting sufficient experience
        if epi >= TRAIN_AFTER_EPISODES:

            # Train for TRAIN_EPOCHS
            for tri in range(TRAIN_EPOCHS): 
                update_networks(epi, buf, Q, Qt, OPT)

        # Evaluate for TEST_EPISODES number of episodes
        Rews = []
        for epj in range(TEST_EPISODES):
            S, A, R = utils.envs.play_episode(test_env, policy, render = False)
            pred_l = max(set(A), key = A.count)
            preds.append(int(pred_l == test_env.s_l))
            Rews += [sum(R)]
        testRs += [sum(Rews)/TEST_EPISODES]
        accs.append(100*sum(preds)/len(preds))
        # Update progress bar
        last25testRs += [sum(testRs[-25:])/len(testRs[-25:])]
        pbar.set_description("R25(%g)" % (last25testRs[-1]))

    # Close progress bar, environment
    pbar.close()
    print("Training finished!")
    return last25testRs, accs

# Plot mean curve and (mean-std, mean+std) curve with some transparency
# Clip the curves to be between 0, 200
def plot_arrays(vars, color, label):
    mean = np.mean(vars, axis=0)
    std = np.std(vars, axis=0)
    plt.plot(range(len(mean)), mean, color=color, label=label)
    plt.fill_between(range(len(mean)), mean-std, mean+std, color=color, alpha=0.3)
    # plt.fill_between(range(len(mean)), np.maximum(mean-std, 0), np.minimum(mean+std,200), color=color, alpha=0.3)


if __name__ == "__main__":

    W, S = [50, 75], [10, 20]
    W, S = [68], [20]
    for w in W:
        for s in S:
            WINDOW, STRIDE = w, s
            chunking()
            # Train for different seeds
            rews, accs = [], []
            for seed in SEEDS:
                rew, acc = train(seed)
                rews += [rew]
                accs += [acc]
            # Save the curves for the given seeds
            w = 75
            with open('results/rews-' + str(w) + '-' + str(s), 'w') as f:
                f.write(str(rews))
            with open('results/accs-' + str(w) + '-' + str(s), 'w') as f:
                f.write(str(accs))