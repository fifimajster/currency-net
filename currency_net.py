from graph_smell import *

# quick explanation:
# G[a][b]['amount'] means amount of b tokens that a has
# G[a][b]['trust'] means how many percent of a's total tokens can be b tokens
# can be less but cannot be more than that


def total_tokens(G, node):
    return sum([G[node][neighbor]['amount']
                for neighbor in G.neighbors(node)])


def max_possible_direct_transfer(G, sender, receiver):
    # maximum possible transfer assuming G[sender][sender]['amount'] = inf
    # how many sender tokens receiver can accept
    result = G[receiver][sender]['trust'] * total_tokens(G, receiver)
    # minus sender's tokens he already has
    result -= G[receiver][sender]['amount']
    # check if the sender has this much sender tokens
    result = min(result, G[sender][sender]['amount'])
    # plus receiver tokens that the sender possesses
    result += G[sender][receiver]['amount']
    return result


def direct_transfer(G, sender, receiver, amount):
    if amount > max_possible_direct_transfer(G, sender, receiver):
        raise RuntimeError('impossible to transfer this amount')
    # first try to pay only with receiver tokens
    if amount <= G[sender][receiver]['amount']:
        G[sender][receiver]['amount'] -= amount
        G[receiver][receiver]['amount'] += amount
    # if you can't use also receivers trust
    else:
        receiver_tokens = G[sender][receiver]['amount']
        G[sender][receiver]['amount'] -= receiver_tokens
        G[receiver][receiver]['amount'] += receiver_tokens
        G[sender][sender]['amount'] -= (amount - receiver_tokens)
        G[receiver][sender]['amount'] += (amount - receiver_tokens)


def try_to_transfer_with_only_one_branch(G, sender, receiver, amount, max_nodes_you_can_visit=30):
    # record visited nodes so we don't visit them again so we don't make loops
    visited_nodes = [sender]
    # branch we will grow and use for transfer
    branch = [sender]

    def step_back():
        del branch[-1]
        if branch == []:
            # we deleted even the sender node
            raise RuntimeError('couldnt find a single branch for transfer')

    while branch[-1] != receiver and len(visited_nodes) <= max_nodes_you_can_visit:
        try:
            candidate = smelling_policy(G, branch[-1], receiver, cursed_nodes=visited_nodes)
        except RuntimeError:
            # this exception was raised if path finder was stuck in dead end, so we have to step back
            step_back()
            continue
        visited_nodes.append(candidate)
        # if smell_distance(G, candidate, receiver) > smell_distance(G, branch[-1], receiver):
        #     # candidate node is further away from the receiver, so instead of following him, just step back
        #     step_back()
        #     continue
        if amount <= max_possible_direct_transfer(G, branch[-1], candidate):
            branch.append(candidate)

    if branch[-1] != receiver:
        raise RuntimeError('exceeded maximum number of nodes to visit')

    print('transfer possible, visited nodes: ', len(visited_nodes),
                                '   branch length: ', len(branch),
                                '   amount: ', amount)

    # translate the branch into a list of direct transfers
    list_of_direct_transfers = []
    for n in range(len(branch) - 1):
        list_of_direct_transfers.append([branch[n], branch[n+1], amount])
    print(list_of_direct_transfers)
    execute_transfers(G, list_of_direct_transfers)


def try_to_transfer_with_recursive_branches(G, sender, receiver, amount, max_recursion_lvl=5):
    if total_tokens(G, sender) < amount:
        raise RuntimeError('not enough tokens to send this amount')
    try:
        try_to_transfer_with_only_one_branch(G, sender, receiver, amount)
    except RuntimeError:
        if max_recursion_lvl == 0:
            raise RuntimeError('reached maximum recursion level and failed to transfer')
        try_to_transfer_with_recursive_branches(G, sender, receiver, amount / 2,
                                                max_recursion_lvl=max_recursion_lvl - 1)
        try_to_transfer_with_recursive_branches(G, sender, receiver, amount / 2,
                                                max_recursion_lvl=max_recursion_lvl - 1)


# def find_a_way_to_transfer_with_recursive_branches(G, sender, receiver, amount, max_recursion_lvl=5):
#     # ! doesnt actually transfer, it just collects the list of direct transfers needed
#     if total_tokens(G, sender) < amount:
#         raise RuntimeError('not enough tokens to send this amount')
#     list_of_direct_transfers = []
#     try:
#         list_of_direct_transfers += find_a_way_to_transfer_with_only_one_branch(G, sender, receiver, amount)
#     except RuntimeError:
#         if max_recursion_lvl == 0:
#             raise RuntimeError('reached maximum recursion level and failed to transfer')
#         list_of_direct_transfers += \
#             find_a_way_to_transfer_with_recursive_branches(G, sender, receiver, amount / 2,
#                                                            max_recursion_lvl=max_recursion_lvl - 1)
#         list_of_direct_transfers += \
#             find_a_way_to_transfer_with_recursive_branches(G, sender, receiver, amount / 2,
#                                                            max_recursion_lvl=max_recursion_lvl - 1)
#     return list_of_direct_transfers


def execute_transfers(G, list_of_direct_transfers):
    for transfer in list_of_direct_transfers:
        direct_transfer(G, transfer[0], transfer[1], transfer[2])


def make_random_transfers(G, transfer_method, amount, iterations):
    for i in range(iterations):
        node1 = np.random.choice(G.nodes)
        node2 = np.random.choice(G.nodes)
        transfer_method(G, node1, node2, amount)


if __name__ == "__main__":
    # generate a scale-free graph which resembles a social network
    G = nx.connected_watts_strogatz_graph(1000, 30, 0.1)
    G = G.to_directed()
    initialize_smells(G, dimensions=300)

    # dissipate smells
    for i in range(15):
        dissipate_smells(G, change_rate=0.1)
        # make tests
        test_random_paths(G, 10)

    # set default trust level for every connection
    nx.set_edge_attributes(G, 0.1, 'trust')
    # amount of somebody's tokens is initially 0
    nx.set_edge_attributes(G, 0, 'amount')

    for node in G.nodes:
        G.add_edge(node, node)
        G[node][node]['trust'] = 1  # use must trust yourself completely
        G[node][node]['amount'] = 1000