from currency_net import *
import socket
import sys
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random
from _thread import *
import base64
from Crypto.Signature import PKCS1_v1_5

HOST = ''  # Symbolic name, meaning all available interfaces
PORT = 1620  # Arbitrary non-privileged port

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created')

# Bind socket to host and port
try:
    s.bind((HOST, PORT))
except socket.error as msg:
    print('Bind failed. Error Code : ', msg)
    sys.exit()

print('Socket bind complete')

# Start listening on socket
s.listen(100)
print('Socket now listening')


try:
    with open('network_backup.pickle', 'rb') as handle:
        N = pickle.load(handle)
except Exception as e:
    N = NetworkKeeper()
    print(e)




def verify_message(raw_message, public_key, signature):
    # signing doedn't work for now
    # hash = SHA256.new(raw_message.encode()).digest()
    # verifier = PKCS1_v1_5.new(public_key)
    # verifier.verify(hash, signature)
    s = "-----BEGIN RSA PUBLIC KEY-----\n" + \
        signature + \
        "\n-----END RSA PUBLIC KEY-----\n"
    sigString = RSA.importKey(s)
    return public_key == sigString


# Function for handling connections. This will be used to create threads
def clientthread(conn, addr):
    # Sending message to connected client
    conn.sendall(b'connected to server\n')  # send only takes string
    clients_public_key = None

    def send_to_client(message, sign=False):
        message += '\n'
        conn.sendall(message.encode())

    # infinite loop so that function do not terminate and thread do not end.
    while True:
        try:    # in case that the message from the client is invalid
            # Receiving from client
            unparsed_message = conn.recv(1024)
            if not unparsed_message:
                break
            unparsed_message = unparsed_message[:-1]  # because there is a new line character at the end

            full_message = unparsed_message.decode().split(" ")
            signature = full_message[0]
            timestamp = full_message[1]
            command = full_message[2]
            message = full_message[3:]

            if command == 'r':      # register
                name, public_key_string = message
                # get key from received string
                s = "-----BEGIN RSA PUBLIC KEY-----\n" + \
                    public_key_string + \
                    "\n-----END RSA PUBLIC KEY-----\n"
                clients_public_key = RSA.importKey(s)

            elif command == 'l':        # login
                logged_name = message[0]
                if logged_name in N:
                    clients_public_key = N.nodes[logged_name]['public_key']
                else:
                    send_to_client('such name is not registered')
                    continue

            # verify message
            if not clients_public_key:
                send_to_client('you have to login or register first')
                continue
            if not verify_message(" ".join(full_message[1:]), clients_public_key, signature):
                # didn't pass verification
                clients_public_key = 0 # because the received key was signed incorrectly
                send_to_client('signature incorrect')
                continue

            # now we are verified

            if command == 'r':
                try:
                    N.register_node(name, public_key=clients_public_key)
                    N.make_backup()
                    logged_name = name
                    send_to_client('registered succesfully')
                except RuntimeError:
                    # it means that node already is registered
                    clients_public_key = None
                    send_to_client('this name is already registered')
            elif command == 'l':
                send_to_client('login succesfull')
            elif command == 'trust':
                name, new_potential_trust = message
                new_potential_trust = float(new_potential_trust)
                if new_potential_trust > 1 or new_potential_trust < 0:
                    send_to_client('trust level must be between 0 and 1')
                    continue
                if name not in N:
                    send_to_client('given name is not registered')
                    continue
                if (logged_name, name) not in N.edges:
                    # edge doesn't exist so create it
                    N.create_edge(logged_name, name)
                N[logged_name][name]['potential_trust'] = new_potential_trust
                N.update_trust(logged_name, name)
                N.make_backup()
                N.nodes[logged_name]['todays_actions'].append(unparsed_message)
                send_to_client('changed trust for ' + name + ' to ' + str(new_potential_trust))
            elif command == 't':        # make a transaction
                name, amount = message
                amount = int(amount)
                if name not in N:
                    send_to_client('given name is not registered')
                    continue
                if amount <= 0:
                    send_to_client('amount to transfer must be positive ;)')
                    continue
                max_possible_amount, list_of_direct_transfers = N.transfer(logged_name, name, amount)
                if max_possible_amount != amount:
                    # it means that transfer failed
                    send_to_client('transfer failed, the most you can transfer is ' +
                                   str(max_possible_amount))
                    continue
                N.nodes[logged_name]['last_transaction'] = unparsed_message   # record clients message for proof
                N.nodes[logged_name]['todays_actions'].append(unparsed_message)
                N.nodes[name]['todays_actions'].append(unparsed_message)
                N.make_backup()
                send_to_client('transfer succesfull')
            elif command == 'b':
                balance = N.total_tokens(logged_name)
                send_to_client('balance: ' + str(balance))
            elif command == 'c':    # get connections, their trust level and amount of their tokens
                connections = N.get_connections(logged_name)
                to_send = ''
                for c in connections:
                    to_send += c[0] + ' ' + str(c[1]) + ' ' + str(c[2]) + ':'
                send_to_client('connections: ' + to_send)
            elif command == 'last: ':
                name = message
                send_to_client('last' + N.get_last_transaction(name))
            elif command == 'actions':
                name = message
                send_to_client('actions: ' + N.get_actions(name))
            else:
                send_to_client('didnt understand, type h for help')
        except Exception as e:
            send_to_client('server error: ' + str(e))

    # came out of loop
    conn.close()
    print('Disconnected with ' + addr[0] + ':' + str(addr[1]))


def network_updater(seconds_interval):
    while True:
        N.try_to_make_dayly_update()
        time.sleep(seconds_interval)


start_new_thread(network_updater, (60,))

# now keep talking with the client
while 1:
    # wait to accept a connection - blocking call
    conn, addr = s.accept()
    print('Connected with ' + addr[0] + ':' + str(addr[1]))

    start_new_thread(clientthread, (conn, addr))