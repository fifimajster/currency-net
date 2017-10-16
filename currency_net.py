from graph_smell import *
import math

# quick explanation:
# G[a][b]['amount'] means amount of b tokens that a has
# G[a][b]['trust'] means how many percent of a's total tokens can be b tokens
# can be less but cannot be more than that


def total_tokens(G, node):
    return sum([G[node][neighbor]['amount']
                for neighbor in G.neighbors(node)])


def max_possible_direct_transfer(G, sender, receiver):
    # how many sender tokens receiver can accept
    sender_tokens = G[receiver][sender]['trust'] * total_tokens(G, receiver)
    # money should always be int so none is lost due to precision
    sender_tokens = int(sender_tokens)
    # minus sender's tokens he already has
    sender_tokens -= G[receiver][sender]['amount']
    # check if the sender has this much sender tokens
    sender_tokens = min(sender_tokens, G[sender][sender]['amount'])
    # receiver tokens that the sender possesses
    receiver_tokens = G[sender][receiver]['amount']
    # returns amount of sender tokens and receiver tokens needed to make maximum transfer
    return sender_tokens, receiver_tokens


def direct_transfer(G, sender, receiver, amount, which_tokens, force=False):
    st_max, rt_max = max_possible_direct_transfer(G, sender, receiver)
    if which_tokens == 'sender':
        if amount > st_max and not force:
            raise Exception('incorrect direct transfer')
        G[sender][sender]['amount'] -= amount
        G[receiver][sender]['amount'] += amount
    elif which_tokens == 'receiver':
        if amount > rt_max and not force:
            raise Exception('incorrect direct transfer')
        G[sender][receiver]['amount'] -= amount
        G[receiver][receiver]['amount'] += amount
    else:
        raise Exception('incorrect token name')


def try_to_transfer_with_only_one_branch(G, sender, receiver, amount, max_nodes_you_can_visit=50):
    # branch we will grow and use for transfer
    branch = [sender]
    nodes_visited_from = {sender: []}
    counter = 0
    def step_back():
        del branch[-1]
        if branch == []:
            # we deleted even the sender node
            raise RuntimeError('couldnt find a single branch for transfer')
    while branch[-1] != receiver and counter <= max_nodes_you_can_visit:
        try:
            candidate = smelling_policy(G, branch[-1], receiver,
                                        cursed_nodes=nodes_visited_from[branch[-1]] + branch)
        except RuntimeError:
            # this exception was raised if path finder was stuck in dead end, so we have to step back
            step_back()
            continue
        nodes_visited_from[branch[-1]].append(candidate)
        counter += 1
        if amount <= sum(max_possible_direct_transfer(G, branch[-1], candidate)):
            branch.append(candidate)
            try:
                nodes_visited_from[candidate]
            except:
                # it doesn't exist so create it
                nodes_visited_from[candidate] = []
    if branch[-1] != receiver:
        raise RuntimeError('exceeded maximum number of nodes to visit')
    # translate the branch into a list of direct transfers
    list_of_direct_transfers = []
    for n in range(len(branch) - 1):
        sender_tokens, receiver_tokens = max_possible_direct_transfer(G, branch[n], branch[n+1])
        if amount > receiver_tokens:
            sender_tokens = amount - receiver_tokens
        else:
            sender_tokens = 0
            receiver_tokens = amount
        list_of_direct_transfers.append([branch[n], branch[n+1], sender_tokens, receiver_tokens])
    # execute only after we are sure it's possible
    execute_transfers(G, list_of_direct_transfers)
    return list_of_direct_transfers


def transfer(G, sender, receiver, amount, test=False):
    if amount == 'all':
        amount = total_tokens(G, sender)
    amount_so_far = [0]  # it's wrapped into a list so it can be passed by reference
    list_of_direct_transfers = []
    def transfer_recursively(G, sender, receiver, amount,
                             amount_so_far, list_of_direct_transfers, max_recursion_lvl=10):
        try:
            list_of_direct_transfers += try_to_transfer_with_only_one_branch(G, sender, receiver, amount)
            amount_so_far[0] += amount
        except RuntimeError:
            if max_recursion_lvl == 0:
                raise RuntimeError('reached maximum recursion level and failed to transfer fully')
            transfer_recursively(G, sender, receiver, math.ceil(amount/2),
                                 amount_so_far, list_of_direct_transfers,
                                 max_recursion_lvl=max_recursion_lvl-1)
            transfer_recursively(G, sender, receiver, math.floor(amount / 2),
                                 amount_so_far, list_of_direct_transfers,
                                 max_recursion_lvl=max_recursion_lvl - 1)
    try:
        transfer_recursively(G, sender, receiver, amount,
                             amount_so_far, list_of_direct_transfers)
        if test:
            execute_transfers(G, list_of_direct_transfers, reverse=True)
    except:
        print("could't find a way to transfer ", amount)
        print('maximum possible amount you can transfer is: ', amount_so_far[0])
        # rollback
        execute_transfers(G, list_of_direct_transfers, reverse=True)
    return list_of_direct_transfers


def execute_transfers(G, list_of_direct_transfers, reverse=False):
    if reverse:
        for transfer in reversed(list_of_direct_transfers):
            direct_transfer(G, transfer[1], transfer[0], transfer[2], 'receiver')
            direct_transfer(G, transfer[1], transfer[0], transfer[3], 'sender', force=True)
    else:
        for transfer in list_of_direct_transfers:
            direct_transfer(G, transfer[0], transfer[1], transfer[2], 'sender')
            direct_transfer(G, transfer[0], transfer[1], transfer[3], 'receiver')


# for running simulations
def make_random_transfers(G, transfer_method, amount, iterations):
    for i in range(iterations):
        node1 = np.random.choice(G.nodes)
        node2 = np.random.choice(G.nodes)
        transfer_method(G, node1, node2, amount)


if __name__ == "__main__":
    # generate a scale-free graph which resembles a social network
    G = nx.connected_watts_strogatz_graph(1000, 30, 0.3)
    #G = nx.barabasi_albert_graph(5000, 10)
    G = G.to_directed()
    initialize_smells(G, dimensions=300)

    # dissipate smells
    for i in range(30):
        dissipate_smells(G, change_rate=0.1)
        # make tests
        test_random_paths(G, 10)

    # set default trust level for every connection
    nx.set_edge_attributes(G, 0.2, 'trust')
    # amount of somebody's tokens is initially 0
    nx.set_edge_attributes(G, 0, 'amount')

    for node in G.nodes:
        G.add_edge(node, node)
        G[node][node]['trust'] = 1  # you must trust yourself completely
        G[node][node]['amount'] = 1000  # use only integers !!