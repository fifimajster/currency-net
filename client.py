import socket
import pickle
import sys
import os
import time
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random

def print_help():
    print('r name                    -  to register')
    print('l name                    -  to log in')
    print('b                         -  to get your balance')
    print('trust new_trust_lvl name  -  increase your trust level to someone')
    print('t amount name             -  transfer amount to someone')

HOST = 'spongy.hopto.org'
PORT = 1620

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created')

# Bind socket to local host and port
try:
    s.connect((HOST, PORT))
except socket.error as msg:
    print('Connect failed. Error Code : ', msg)
    sys.exit(1)

print('Socket connection complete')


key = 0
# now keep talking with the client
while 1:
    received_message = s.recv(1024)
    if not received_message:
        break
    print(received_message.decode('utf-8'))
    to_send = input('>>> ')
    to_send = to_send.split()

    if to_send[0] == 'h':
        print_help()
        sys.exit(1)
    elif to_send[0] == 'r' and len(to_send) == 2:
        # making a node
        filename = to_send[1] + '.pickle'
        if os.path.isfile(filename):
            print('you already have a key for ', to_send[1], ' so just log in')
            sys.exit(1)
        # make a key
        random_generator = Random.new().read
        key = RSA.generate(1024, random_generator)
        public_key = key.publickey()
        # send public key to the server
        to_send.append(public_key)
        # save key to a a file
        with open(filename, 'wb') as handle:
            pickle.dump(key, handle, protocol=pickle.HIGHEST_PROTOCOL)
    elif to_send[0] == 'l' and len(to_send) == 2:
        # login
        filename = to_send[1] + '.pickle'
        try:
            with open(filename, 'rb') as handle:
                key = pickle.load(handle)
        except:
            print('you have no key for ', to_send[1])
            sys.exit(1)


    # make a time stamp and pack it
    to_send = [time.time()] + to_send
    to_send = pickle.dumps(to_send)

    # sign the message you're trying to send
    if not key:
        print_help()
        sys.exit(1)
    hash = SHA256.new(to_send).digest()
    signature = key.sign(hash, '')

    # attach signature at the beginning and pack
    to_send = [signature, to_send]
    to_send = pickle.dumps(to_send)

    s.sendall(to_send)
s.close()