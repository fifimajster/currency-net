from currency_net import *
import socket
import pickle
import sys
import time
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random
from _thread import *

HOST = ''  # Symbolic name, meaning all available interfaces
PORT = 1620  # Arbitrary non-privileged port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created')

# Bind socket to local host and port
try:
    s.bind((HOST, PORT))
except socket.error as msg:
    print('Bind failed. Error Code : ', msg)
    sys.exit()

print('Socket bind complete')

# Start listening on socket
s.listen(10)
print('Socket now listening')


G = nx.Graph()
G = G.to_directed()



# Function for handling connections. This will be used to create threads
def clientthread(conn, addr):
    # Sending message to connected client
    conn.sendall(b'Welcome to the server. Type something and hit enter\n')  # send only takes string
    clients_public_key = 0

    # infinite loop so that function do not terminate and thread do not end.
    while True:

        # Receiving from client
        raw_received_message = conn.recv(1024)
        if not raw_received_message:
            break
        # unpack
        raw_received_message = pickle.loads(raw_received_message)
        signature = raw_received_message[0]
        raw_received_message = raw_received_message[1]
        received_message = pickle.loads(raw_received_message)

        if received_message[1] == 'r':
            # register
            # message has form:    timestamp r name public_key
            clients_public_key = received_message[3]
        elif received_message[1] == 'l':
            # login
            # message has form:    timestamp l name
            try:
                logged_name = received_message[2]
                clients_public_key = G.nodes[logged_name]['public_key']
            except:
                conn.sendall(b'such name is not registered')
                continue


        # verify message
        if not clients_public_key:
            conn.sendall(b'you have to login or register first')
            continue
        hash = SHA256.new(raw_received_message).digest()
        is_verified = clients_public_key.verify(hash, signature)

        if not is_verified:
            clients_public_key = 0 # because the received key was signed incorrectly
            conn.sendall(b'signature incorrect')
            continue


        # now we are verified

        if received_message[1] == 'r':
            # message is verified so we can register a new node
            name = received_message[2]
            try:
                # check if this person already is registered
                G[name]
                conn.sendall(b'this name is already registered')
                clients_public_key = 0
                continue
            except:
                G.add_node(name)
                G.nodes[name]['public_key'] = clients_public_key
                G.add_edge(name, name)
                G[name][name]['trust'] = 1  # you must trust yourself completely
                G[name][name]['amount'] = 20000  # use only integers !!
                logged_name = name
                conn.sendall(b'registered succesfully')
                continue
        elif received_message[1] == 'l':
            # message is verified so we can login
            # message has form:    timestamp l name
            conn.sendall(b'login succesfull')
            continue
        elif received_message[1] == 'trust':
            # message has form:     timestamp trust new_trust_lvl name
            try:
                new_trust_lvl = float(received_message[2])
            except:
                conn.sendall(b'trust level must be a number')
                continue
            name = received_message[3]
            if new_trust_lvl > 1 or new_trust_lvl < 0:
                conn.sendall(b'trust level must be between 0 and 1')
                continue
            try:
                G[name]
            except:
                conn.sendall(b'given name is not registered')
                continue
            try:
                G[logged_name][name]['potential_trust'] = new_trust_lvl
            except:
                # there is no such edge so create it
                G.add_edge(logged_name, name)
                G.add_edge(name, logged_name)
                G[logged_name][name]['trust'] = 0
                G[name][logged_name]['trust'] = 0
                G[logged_name][name]['amount'] = 0
                G[name][logged_name]['amount'] = 0
                G[logged_name][name]['potential_trust'] = new_trust_lvl
                G[name][logged_name]['potential_trust'] = 0
                update_smells(G)
            min_potential_trust = min(new_trust_lvl, G[name][logged_name]['potential_trust'])
            if min_potential_trust > G[logged_name][name]['trust']:
                # we can make the trust lvl higher
                G[logged_name][name]['trust'] = min_potential_trust
                G[name][logged_name]['trust'] = min_potential_trust
                to_send = 'changed trust level to ' + str(min_potential_trust)
                conn.sendall(to_send.encode())
                continue
            conn.sendall(b'changed potential trust level')
            continue
        elif received_message[1] == 'b':
            balance = total_tokens(G, logged_name)
            to_send = 'your balance is ' + str(balance)
            conn.sendall(to_send.encode())
            continue
        elif received_message[1] == 't':
            # make a transaction
            # message has form:     timestamp t amount name
            try:
                amount = int(received_message[2])
            except:
                conn.sendall(b'amount to transfer must be a number')
                continue
            try:
                name = received_message[3]
            except:
                conn.sendall(b'you must say where to transfer')
                continue
            try:
                G[name]
            except:
                conn.sendall(b'given name is not registered')
                continue
            max_possible_amount, list_of_direct_transfers = transfer(G, logged_name, name, amount)
            if max_possible_amount != amount:
                # it means that transfer failed
                to_send = 'transfer failed, maximum possible amount you can transfer is '
                to_send += str(max_possible_amount)
                conn.sendall(to_send.encode())
                continue
            conn.sendall(b'transfer succesfull')
            continue

        conn.sendall(b'didnt understand, type h for help')

    # came out of loop
    conn.close()
    print('Disconnected with ' + addr[0] + ':' + str(addr[1]))


# now keep talking with the client
while 1:
    # wait to accept a connection - blocking call
    conn, addr = s.accept()
    print('Connected with ' + addr[0] + ':' + str(addr[1]))

    start_new_thread(clientthread, (conn, addr))

s.close()