from graph_smell import *
import math
import time
import pickle

# quick explanation:
# N[a][b]['amount'] means amount of b tokens that a has
# N[a][b]['trust'] means how many percent of a's total tokens can be b tokens
# can be less but cannot be more than that

class NetworkKeeper(SmellyGraph):

    initial_token_amount = 20000
    universal_basic_income = 1000
    
    def __init__(self):
        SmellyGraph.__init__(self)
        self.day_of_the_month_we_payed_ubi_last_time = -1

    def register_node(self, name, public_key=None, overwrite=False):
        # first check if this name is already registered
        if name in self and not overwrite:
            raise RuntimeError('this name already is registered')
        self.add_node(name)
        self.nodes[name]['public_key'] = public_key
        self.add_edge(name, name)
        self[name][name]['trust'] = 1       # you must trust yourself completely
        self[name][name]['potential_trust'] = 1       # you must trust yourself completely
        self[name][name]['amount'] = self.initial_token_amount  # use only integers !!
        np.random.seed(sum(map(ord, name)))  # because everything has to be deterministic
        self.nodes[name]['smell'] = np.random.uniform(-1, 1, self.smell_dimensions)
        self.nodes[name]['last_transaction'] = None
        self.nodes[name]['todays_actions'] = []
        self.nodes[name]['yesterdays_actions'] = []

    def create_edge(self, node1, node2):
        self.add_edge(node1, node2)
        self.add_edge(node2, node1)
        self[node1][node2]['trust'] = 0
        self[node2][node1]['trust'] = 0
        self[node1][node2]['amount'] = 0
        self[node2][node1]['amount'] = 0
        self[node1][node2]['potential_trust'] = 0
        self[node2][node1]['potential_trust'] = 0

    def update_trust(self, node1, node2):
        with self.graph_edit_lock:
            potential1 = self[node1][node2]['potential_trust']
            potential2 = self[node2][node1]['potential_trust']
            min_potential = min(potential1, potential2)
            if min_potential > self[node1][node2]['trust']:
                # we can make the trust lvl higher
                self[node1][node2]['trust'] = min_potential
                self[node2][node1]['trust'] = min_potential
                return min_potential
            ratio1 = self[node1][node2]['amount'] / self.total_tokens(node1)
            ratio2 = self[node2][node1]['amount'] / self.total_tokens(node2)
            new_lvl = max(min_potential, ratio1, ratio2)
            self[node1][node2]['trust'] = new_lvl
            self[node2][node1]['trust'] = new_lvl
            if 0 == new_lvl == potential1 == potential2:
                self.remove_edge(node1, node2)
            return new_lvl

    def get_connections(self, node):
        return [[neighbor, self[node][neighbor]['potential_trust'], self[node][neighbor]['amount']]
                for neighbor in self.neighbors(node)]

    def pay_ubi(self):
        with self.graph_edit_lock:
            for node in self.nodes:
                self[node][node]['amount'] += self.universal_basic_income
            self.day_of_the_month_we_payed_ubi_last_time = time.gmtime().tm_mday

    def total_tokens(self, node):
        return sum([self[node][neighbor]['amount']
                    for neighbor in self.neighbors(node)])
    
    def max_possible_direct_transfer(self, sender, receiver):
        # how many sender tokens receiver can accept
        sender_tokens = self[receiver][sender]['trust'] * self.total_tokens(receiver)
        # money should always be int so none is lost due to precision
        sender_tokens = int(sender_tokens)
        # minus sender's tokens he already has
        sender_tokens -= self[receiver][sender]['amount']
        # check if the sender has this much sender tokens
        sender_tokens = min(sender_tokens, self[sender][sender]['amount'])
        # receiver tokens that the sender possesses
        receiver_tokens = self[sender][receiver]['amount']
        # returns amount of sender tokens and receiver tokens needed to make maximum transfer
        return sender_tokens, receiver_tokens
    
    def direct_transfer(self, sender, receiver, amount, which_tokens, force=False):
        with self.graph_edit_lock:
            st_max, rt_max = self.max_possible_direct_transfer(sender, receiver)
            if which_tokens == 'sender':
                if amount > st_max and not force:
                    raise Exception('incorrect direct transfer')
                self[sender][sender]['amount'] -= amount
                self[receiver][sender]['amount'] += amount
            elif which_tokens == 'receiver':
                if amount > rt_max and not force:
                    raise Exception('incorrect direct transfer')
                self[sender][receiver]['amount'] -= amount
                self[receiver][receiver]['amount'] += amount
            else:
                raise RuntimeException('incorrect token name')

    def try_to_transfer_with_only_one_branch(self, sender, receiver, amount, max_nodes_you_can_visit=40):
        with self.graph_edit_lock:
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
                    candidate = self.smelling_policy(branch[-1], receiver,
                                                cursed_nodes=nodes_visited_from[branch[-1]] + branch)
                except RuntimeError:
                    # this exception was raised if path finder was stuck in dead end, so we have to step back
                    step_back()
                    continue
                nodes_visited_from[branch[-1]].append(candidate)
                counter += 1
                if amount <= sum(self.max_possible_direct_transfer(branch[-1], candidate)):
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
                sender_tokens, receiver_tokens = self.max_possible_direct_transfer(branch[n], branch[n+1])
                if amount > receiver_tokens:
                    sender_tokens = amount - receiver_tokens
                else:
                    sender_tokens = 0
                    receiver_tokens = amount
                list_of_direct_transfers.append([branch[n], branch[n+1], sender_tokens, receiver_tokens])
            # execute only after we are sure it's possible
            self.execute_direct_transfers(list_of_direct_transfers)
            return list_of_direct_transfers

    def transfer(self, sender, receiver, amount, test=False):
        # watch out for negative transfers
        with self.graph_edit_lock:
            if amount == 'all':
                amount = self.total_tokens(sender)
            amount_so_far = [0]  # it's wrapped into a list so it can be passed by reference
            list_of_direct_transfers = []
            def transfer_recursively(self, sender, receiver, amount,
                                     amount_so_far, list_of_direct_transfers, max_recursion_lvl=10):
                try:
                    list_of_direct_transfers += self.try_to_transfer_with_only_one_branch(sender, receiver, amount)
                    amount_so_far[0] += amount
                except RuntimeError:
                    if max_recursion_lvl == 0:
                        raise RuntimeError('reached maximum recursion level and failed to transfer fully')
                    transfer_recursively(self, sender, receiver, math.ceil(amount/2),
                                         amount_so_far, list_of_direct_transfers,
                                         max_recursion_lvl=max_recursion_lvl-1)
                    transfer_recursively(self, sender, receiver, math.floor(amount / 2),
                                         amount_so_far, list_of_direct_transfers,
                                         max_recursion_lvl=max_recursion_lvl - 1)
            try:
                transfer_recursively(self, sender, receiver, amount,
                                     amount_so_far, list_of_direct_transfers)
                if test:
                    self.execute_direct_transfers(list_of_direct_transfers, reverse=True)
            except RuntimeError:
                print("could't find a way to transfer ", amount)
                print('maximum possible amount you can transfer is: ', amount_so_far[0])
                # rollback
                self.execute_direct_transfers(list_of_direct_transfers, reverse=True)
            return amount_so_far[0], list_of_direct_transfers

    def execute_direct_transfers(self, list_of_direct_transfers, reverse=False):
        with self.graph_edit_lock:
            if reverse:
                for transfer in reversed(list_of_direct_transfers):
                    self.direct_transfer(transfer[1], transfer[0], transfer[2], 'receiver')
                    self.direct_transfer(transfer[1], transfer[0], transfer[3], 'sender', force=True)
            else:
                for transfer in list_of_direct_transfers:
                    self.direct_transfer(transfer[0], transfer[1], transfer[2], 'sender')
                    self.direct_transfer(transfer[0], transfer[1], transfer[3], 'receiver')

    def make_backup(self):
        with open('network_backup.pickle', 'wb') as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def try_to_make_dayly_update(self):
        if time.gmtime().tm_mday == self.day_of_the_month_we_payed_ubi_last_time:
            # we already payed so do nothing
            return
        self.pay_ubi()
        self.update_smells()
        with self.graph_edit_lock:
            for name in self.nodes:
                self.nodes[name]['yesterdays_actions'] = self.nodes[name]['todays_actions']
                self.nodes[name]['todays_actions'] = []






# for running simulations
def make_random_transfers(N, amount, iterations):
    for i in range(iterations):
        node1 = np.random.choice(N.nodes)
        node2 = np.random.choice(N.nodes)
        N.transfer(node1, node2, amount)



if __name__ == "__main__":
    # generate a scale-free graph which resembles a social network
    # nx.watts_strogatz_graph(1000, 10, 0.1)
    # or nx.barabasi_albert_graph(1000, 10)
    g = nx.watts_strogatz_graph(1000, 30, 0.3)
    g = g.to_directed()
    N = NetworkKeeper()
    N.load_graph_structure(g)

    N.initialize_random_smells(dimensions=300)

    for i in range(30):
        N.dissipate_smells(change_rate=0.1)
        # make tests
        test_random_paths(N, 10)

    # set default trust level for every connection
    nx.set_edge_attributes(N, 0.2, 'trust')
    # amount of somebody's tokens is initially 0
    nx.set_edge_attributes(N, 0, 'amount')

    for node in N.nodes:
        N.register_node(node, overwrite=True)