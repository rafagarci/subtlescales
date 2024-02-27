#!/usr/bin/python3
'''
SubtleScales: A simple and encrypted version of Netcat written in vanilla Python.
'''
from subprocess import Popen
from select import select
import argparse
import socket
import ssl
import sys
import pty
import os

def regular_mode(main_socket: ssl.SSLSocket, read_only: bool, write_only: bool, max_bytes: int):
    '''
    Send and/or received data through an encrypted channel.

    Parameters:
    - main_socket: ssl.SSLSocket
        TLS socket to use for sending and receiving data.

    - read_only: bool
        read-only mode, don't send any data through the connection socket

    - write_only: bool
        write-only mode, ignore data obtained from the connection socket

    - max_bytes: int
        maximum number of bytes to process at once

    Returns:
    None
    '''
    # Invalid case
    if read_only and write_only:
        raise Exception('read-only and write-only modes both selected')

    # Queue variables
    to_send_queue = []
    received_queue = []

    # Main loop
    while True:
        try:
            # Wait for data to be received either through socket or STDIN depending on the mode
            ready_for_reading, _, _ = select((main_socket, sys.stdin.buffer), (), ())
            # Terminate data if 0 bytes are received or attempted to be sent
            terminate = False
            for obj in ready_for_reading:
                # Data received
                if obj is main_socket:
                    if received := obj.recv(max_bytes):
                        if not write_only: received_queue.append(received)
                    else:
                        terminate = True
                # Data is to be sent
                elif obj is sys.stdin.buffer:
                    if obtained_stdin:= obj.readline(max_bytes):
                        if not read_only: to_send_queue.append(obtained_stdin)
                    else:
                        terminate = True
            # Handle data in the queues
            while received_queue:
                sys.stdout.buffer.write(received_queue.pop(0))
                sys.stdout.buffer.flush()
            while to_send_queue:
                main_socket.sendall(to_send_queue.pop(0))
            if terminate:
                break
        except KeyboardInterrupt:
            break

def execute_command_mode(main_socket: ssl.SSLSocket, command: str, write_only: bool, max_bytes: int):
    '''
    Execute a command locally while sending and receiving input over an encrypted channel.

    Parameters:
    - main_socket: ssl.SSLSocket
        TLS socket to use for sending and receiving data.

    - command: str
        command to execute

    - write_only: bool
        write-only mode, don't use command input from the main socket

    - max_bytes: int
        maximum number of bytes to process at once

    Returns:
    int
        Command exit code
    '''
    # Generate master/slave pty pair
    master_fd, slave_fd = pty.openpty()

    # Instantiate subprocess running the provided command
    p = Popen(command.split(), stdin=slave_fd, stdout=slave_fd, stderr=slave_fd)

    # Queues
    input_queue = []
    output_queue = []

    # Select system call timeout
    timeout = 0.1

    # Main loop
    while True:
        try:
            # Exit if subprocess finished
            if p.poll() is not None:
                break
            # Wait for data to be received either through socket or program
            ready_for_reading, _, _ = select((main_socket, master_fd), (), (), timeout)
            # Terminate data if 0 bytes are obtained
            terminate = False
            for obj in ready_for_reading:
                # Data received
                if obj is main_socket:
                    if (received := obj.recv(max_bytes)) and p.poll() is None:
                        if not write_only: input_queue.append(received)
                    else:
                        terminate = True
                # Program output received
                elif obj is master_fd:
                    if read := os.read(master_fd, max_bytes):
                        output_queue.append(read)
            # Handle data in the queues
            while input_queue:
                os.write(master_fd, input_queue.pop(0))
            while output_queue:
                main_socket.sendall(output_queue.pop(0))
            if terminate:
                break
        except KeyboardInterrupt:
            p.kill()
            break

    # Wait for process to exit
    p.terminate()
    p.wait()

    return p.poll()

if __name__ == '__main__':
    '''
    Main execution function.
    '''
    parser = argparse.ArgumentParser(prog='subtlescales.py', description='A simple and encrypted version of Netcat written in vanilla Python.')
    parser.add_argument('-a', '--address', help="listener's IP address, ignored when -l is specified", metavar='ADDRESS')
    parser.add_argument('-b', '--max-bytes', type=int, help='maximum number of bytes to process at once, defaults to 1024', default=1024)
    parser.add_argument('-e', '--execute', type=str, help='execute a command locally and transmit over an encrypted channel', metavar='COMMAND')
    parser.add_argument('-l', '--listen', help='listen for incoming connections', action='store_true', default=False)
    parser.add_argument('-p', '--port', type=int, help='port to connect to or listen from, defaults to 8443', metavar='PORT', default=8443)
    parser.add_argument('-r', '--read-only', help="read-only mode, only receive incoming data, invalid when -e is specified", action='store_true', default=False)
    parser.add_argument('-w', '--write-only', help="write-only mode, dont't expect incoming data", action='store_true', default=False)
    args = parser.parse_args()

    # Invalid cases
    if not args.listen and not args.address:
        raise Exception("listener's address not provided")
    if args.write_only and args.read_only:
        raise Exception('write-only and read-only flags were both specified')
    if args.execute and args.read_only:
        raise Exception('execute mode and read-only mode are incompatible')
    if args.max_bytes < 1:
        raise Exception('invalid maximum number of bytes')
    if args.port < 1:
        raise Exception('invalid port number specified')

    # TLS context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if args.listen else ssl.PROTOCOL_TLS_CLIENT)
    context.set_ciphers("AECDH-AES256-SHA:@SECLEVEL=0")
    context.check_hostname = False

    # Instantiate main socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
        # Encrypt connection using TLS
        with context.wrap_socket(sock) as ssock:
            if args.listen:
                ssock.bind(('127.0.0.1', args.port))
                ssock.listen(0)
                conn, addr = ssock.accept()
            else:
                ssock.connect((args.address, args.port))

            # Rename main socket
            main_socket = conn if args.listen else ssock

            # Run selected mode
            if args.execute:
                execute_command_mode(main_socket, args.execute, args.write_only, args.max_bytes)
            else:
                regular_mode(main_socket, args.read_only, args.write_only, args.max_bytes)
