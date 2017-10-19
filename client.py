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
    print('trust name new_trust_lvl  -  say what trust level to someone do you want')
    print('t name amount             -  transfer amount to someone')
    print('c                         -  print people connected to you, amount of their tokens you have and trust level between you')

HOST = ''
PORT = 1622

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket created')

# Bind socket to local host and port
try:
    s.connect((HOST, PORT))
except socket.error as msg:
    print('Connect failed. Error Code : ', msg)
    sys.exit(1)

print('Socket connection complete')
received_message = s.recv(1024)
print(received_message.decode())

key = 0
# now keep talking with the client
while 1:
    try:
        to_send = input('>>> ')
        to_send = to_send.split()
        command = to_send[0]

        if command == 'r':      # register
            name = to_send[1]
            filename = name + '.pickle'
            if os.path.isfile(filename):
                print('you already have a key for ', name, ' so just log in')
                continue
            # make a key
            random_generator = Random.new().read
            key = RSA.generate(1024, random_generator)
            public_key = key.publickey()
            # send public key to the server
            to_send.append(public_key)
            # save key to a a file
            with open(filename, 'wb') as handle:
                pickle.dump(key, handle, protocol=pickle.HIGHEST_PROTOCOL)
        elif command == 'l':     # login
            name = to_send[1]
            filename = name + '.pickle'
            try:
                with open(filename, 'rb') as handle:
                    key = pickle.load(handle)
            except:
                print('you have no key for ', name)
                continue
        elif command == 'h':
            print_help()
            continue

        # make a time stamp and pack it
        to_send = [time.time()] + to_send
        to_send = pickle.dumps(to_send)
        # sign the message you're trying to send
        if not key:
            print('log in or register first')
            print_help()
            continue
        hash = SHA256.new(to_send).digest()
        signature = key.sign(hash, '')
        # attach signature at the beginning and pack
        to_send = [signature, to_send]
        to_send = pickle.dumps(to_send)
        s.sendall(to_send)

        received_message = s.recv(1024)
        if not received_message:
            break
        print(received_message.decode())
    except Exception as e:
        print(e)
        print_help()
s.close()