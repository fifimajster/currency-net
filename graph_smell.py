import numpy as np
import networkx as nx
#import matplotlib.pyplot as plt


class SmellyGraph(nx.DiGraph):

    def __init__(self):
        nx.DiGraph.__init__(self)

    def load_graph_structure(self, g):
        self.add_nodes_from(g)
        self.add_edges_from(g.edges)

    def initialize_random_smells(self, dimensions, nodes=None):
        if nodes is None:
            # by default take all nodes
            nodes = self.nodes
        for node in nodes:
            self.nodes[node]['smell'] = np.random.uniform(-1, 1, dimensions)

    def dissipate_smells(self, change_rate, nodes=None):
        if nodes is None:
            # by default take all nodes
            nodes = self.nodes
        for node in nodes:
            neighbor_smells = [self.nodes[neighbor]['smell'] for neighbor in self.neighbors(node)]
            # take average of neighbouring smells
            neighbor_avg_smell = np.mean(neighbor_smells, axis=0)
            current_smell = self.nodes[node]['smell']
            # normalize
            neighbor_avg_smell /= np.sqrt(np.mean(neighbor_avg_smell**2))
            self.nodes[node]['smell'] = change_rate*neighbor_avg_smell + (1-change_rate)*current_smell

    def smell_distance(self, node1, node2):
        smell1 = self.nodes[node1]['smell']
        smell2 = self.nodes[node2]['smell']
        return np.sum((smell1 - smell2)**2)

    def smelling_policy(self, node, end_node, cursed_nodes=[]):
        smell_distances = [[self.smell_distance(neighbor, end_node), neighbor]
                                for neighbor in self.neighbors(node)
                                if neighbor not in cursed_nodes]
        if smell_distances == []:
            raise RuntimeError('path stuck in dead end')
        return min(smell_distances)[1]

    def update_smells(self):
        self.initialize_random_smells(300)
        for i in range(30):
            self.dissipate_smells(change_rate=0.1)



def test_random_paths(G, iterations):
    def find_path(G, node1, node2):
        path = [node1]
        current_node = node1
        while current_node != node2:
            current_node = G.smelling_policy(current_node, node2, cursed_nodes=path)
            path.append(current_node)
        return path
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
    # nx.watts_strogatz_graph(1000, 10, 0.1)
    # or nx.barabasi_albert_graph(1000, 10)
    g = nx.watts_strogatz_graph(10000, 30, 0.3)
    g = g.to_directed()
    G = SmellyGraph()
    G.load_graph_structure(g)

    G.initialize_random_smells(dimensions=300)

    for i in range(30):
        G.dissipate_smells(change_rate=0.1)
        # make tests
        test_random_paths(G, 10)

    test_random_paths(G, 5000)

    # nx.draw(self)
    # plt.show()