#!/usr/bin/python
from currency_net import *
import socket
import sys
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random
from _thread import *

HOST = ''  # Symbolic name, meaning all available interfaces
PORT = 1622  # Arbitrary non-privileged port

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
s.listen(30)
print('Socket now listening')


try:
    with open('network_backup.pickle', 'rb') as handle:
        N = pickle.load(handle)
except Exception as e:
    N = NetworkKeeper()
    print(e)



# Function for handling connections. This will be used to create threads
def clientthread(conn, addr):
    # Sending message to connected client
    conn.sendall(b'Welcome to the server. Type something and hit enter\n')  # send only takes string
    clients_public_key = 0

    # infinite loop so that function do not terminate and thread do not end.
    while True:
        # try:    # in case that the message from the client is invalid
            # Receiving from client
            packed_message = conn.recv(1024)
            if not packed_message:
                break
            # unpack
            signature, raw_received_message = pickle.loads(packed_message)
            full_message = pickle.loads(raw_received_message)
            timestamp = full_message[0]
            command = full_message[1]
            message = full_message[2:]

            if command == 'r':      # register
                name, clients_public_key = message
            elif command == 'l':        # login
                logged_name = message[0]
                if logged_name in N:
                    clients_public_key = N.nodes[logged_name]['public_key']
                else:
                    conn.sendall(b'such name is not registered')
                    continue

            # verify message
            if not clients_public_key:
                conn.sendall(b'you have to login or register first')
                continue
            hash = SHA256.new(raw_received_message).digest()
            if not clients_public_key.verify(hash, signature):
                # didn't pass verification
                clients_public_key = 0 # because the received key was signed incorrectly
                conn.sendall(b'signature incorrect')
                continue

            # now we are verified

            if command == 'r':
                try:
                    N.register_node(name, public_key=clients_public_key)
                    N.make_backup()
                    logged_name = name
                    conn.sendall(b'registered succesfully')
                except RuntimeError:
                    # it means that node already is registered
                    clients_public_key = 0
                    conn.sendall(b'this name is already registered')
            elif command == 'l':
                conn.sendall(b'login succesfull')
            elif command == 'trust':
                name, new_potential_trust = message
                new_potential_trust = float(new_potential_trust)
                if new_potential_trust > 1 or new_potential_trust < 0:
                    conn.sendall(b'trust level must be between 0 and 1')
                    continue
                if name not in N:
                    conn.sendall(b'given name is not registered')
                    continue
                if (logged_name, name) not in N.edges:
                    # edge doesn't exist so create it
                    N.create_edge(logged_name, name)
                    N.update_smells()
                N[logged_name][name]['potential_trust'] = new_potential_trust
                new_lvl = N.update_trust(logged_name, name)
                N.make_backup()
                to_send = 'changed trust level to ' + str(new_lvl)
                conn.sendall(to_send.encode())
            elif command == 't':        # make a transaction
                name, amount = message
                amount = int(amount)
                if name not in N:
                    conn.sendall(b'given name is not registered')
                    continue
                max_possible_amount, list_of_direct_transfers = N.transfer(logged_name, name, amount)
                if max_possible_amount != amount:
                    # it means that transfer failed
                    to_send = 'transfer failed, maximum possible amount you can transfer is '
                    to_send += str(max_possible_amount)
                    conn.sendall(to_send.encode())
                    continue
                N.make_backup()
                conn.sendall(b'transfer succesfull')
            elif command == 'b':
                balance = N.total_tokens(logged_name)
                to_send = 'your balance is ' + str(balance)
                conn.sendall(to_send.encode())
            elif command == 'c':    # get connections, their trust level and amount of their tokens
                connections = N.get_connections(logged_name)
                to_send = ''
                for c in connections:
                    to_send += c[0] + ' \t' + str(c[1]) + ' \t' + str(c[2]) + '\n'
                conn.sendall(to_send.encode())
            else:
                conn.sendall(b'didnt understand, type h for help')
        # except:
        #     conn.sendall(b'invalid message, type h for help')

    # came out of loop
    conn.close()
    print('Disconnected with ' + addr[0] + ':' + str(addr[1]))


# now keep talking with the client
try:
    while 1:
        # wait to accept a connection - blocking call
        conn, addr = s.accept()
        print('Connected with ' + addr[0] + ':' + str(addr[1]))

        start_new_thread(clientthread, (conn, addr))
finally:
    s.close()