from graph_smell import *


#def send_tokens(G, _from, _to, amount):
    


if __name__ == "__main__":
    # generate a scale-free graph which resembles a social network
    G = nx.barabasi_albert_graph(100, 10)
    G = G.to_directed()
    initialize_smells(G, dimensions=20)

    # dissipate smells
    for i in range(3, 100):
        dissipate_smells(G, change_rate=1/i)
        # make tests
        test_random_paths(G, 10)

    # set default trust level for every connection
    nx.set_edge_attributes(G, 0.2, 'trust')
    # amount of somebody's tokens is initially 0
    nx.set_edge_attributes(G, 0, 'amount')

    for node in G.nodes:
        G.add_edge(node, node)
        G[node][node]['trust'] = 1  # use must trust yourself completely
        G[node][node]['amount'] = 1000

