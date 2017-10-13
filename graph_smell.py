import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


def initialize_smells(G, dimensions):
    # initialize random smells
    for node in G.nodes:
        G.nodes[node]['smell'] = np.random.uniform(-1, 1, dimensions)

def dissipate_smells(G, change_rate):
    for node in G.nodes:
        neighbor_smells = [G.nodes[neighbor]['smell'] for neighbor in G.neighbors(node)]
        # take average of neighbouring smells
        neighbor_avg_smell = np.mean(neighbor_smells, axis=0)
        current_smell = G.nodes[node]['smell']
        # normalize
        neighbor_avg_smell /= np.sqrt(np.mean(neighbor_avg_smell**2))
        G.nodes[node]['smell'] = change_rate*neighbor_avg_smell + (1-change_rate)*current_smell

def smelling_policy(G, node, end_node, cursed_nodes=[]):
    neighbour_smells = [[G.nodes[neighbour]['smell'], neighbour] for neighbour in G[node]
                                                                if neighbour not in cursed_nodes]
    end_smell = G.nodes[end_node]['smell']
    smell_distances = [[np.sum((end_smell-smell)**2), neighbour]
                       for [smell, neighbour] in neighbour_smells]
    return min(smell_distances)[1]

def find_path(G, node1, node2):
    path = [node1]
    current_node = node1
    while current_node != node2:
        current_node = smelling_policy(G, current_node, node2, cursed_nodes=path)
        path.append(current_node)
    return path

def test_random_paths(G, iterations):
    sum = 0
    max_path_len = 0
    for j in range(iterations):
        node1 = np.random.choice(G.nodes)
        node2 = np.random.choice(G.nodes)
        last_path_len = len(find_path(G, node1, node2))
        max_path_len = max(max_path_len, last_path_len)
        sum += last_path_len
    print('iterations: ', iterations,
          ' avg length: ', sum / iterations,
          ' max length: ', max_path_len)


if __name__ == "__main__":
    # generate a scale-free graph which resembles a social network
    G = nx.barabasi_albert_graph(1000000, 10)
    # G = nx.watts_strogatz_graph(1000, 10, 0.1)

    initialize_smells(G, dimensions=2000)

    for i in range(30):
        dissipate_smells(G, change_rate=0.1)
        # make tests
        test_random_paths(G, 10)

    test_random_paths(G, 5000)

    # nx.draw(G)
    # plt.show()
    # #               2/i  i=6..100  |   1/3