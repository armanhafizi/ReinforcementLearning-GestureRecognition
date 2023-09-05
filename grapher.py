import matplotlib.pyplot as plt
import numpy as np
import ast

def plot_arrays(vars, label):
    mean = np.mean(vars, axis=0)
    std = np.std(vars, axis=0)
    plt.plot(range(len(mean)), mean, label=label)
    plt.fill_between(range(len(mean)), mean-std/2, mean+std/2, alpha=0.3)

def plot_save(basefilename, r, ylabel, title, W, S):
    fig = plt.figure()
    for s in S:
        for w in W:
            with open(basefilename + str(w) + '-' + str(s), 'r') as f:
                    data = np.array(ast.literal_eval(f.read()))
            label = 'S=' + str(s) + ', W=' + str(w)
            plot_arrays(data[:, :r], label)
    plt.legend(loc='best')
    plt.xlabel('Episode')
    plt.ylabel(ylabel)
    plt.title(title)
    fig.savefig(basefilename + '.png', dpi=320)

if __name__ == "__main__":
    W, S = [50, 75], [20, 10]
    plot_save('results/rews-', 2000, 'Average Last 25 Rewards', 'Reward by Episode', W, S)
    plot_save('results/accs-', 6000, 'Accuracy', 'Accuracy by Episode', W, S)