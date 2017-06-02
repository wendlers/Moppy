#!/bin/env python3

import os
import pty
import serial
import socket
import select
import struct
import logging
import binascii
import argparse
import time

from moppy import version


class SerialReader:

    def __init__(self, port, timeout=0.5):

        self.logger = logging.getLogger('serialr')

        self.timeout = timeout
        self.serial = serial.Serial(port=port, baudrate=9600,
                                    timeout=self.timeout)

        self.logger.info("created (%s)" % port)

    def read_msg(self, timeout=1.0):

        msg = bytearray()

        while len(msg) != 3:

            c = self.serial.read(1)

            if c == '':
                break
            else:
                msg += c

        return msg

    def __str__(self):
        return 'serialr'


class SerialWriter:

    def __init__(self, port):

        self.logger = logging.getLogger('serialw')

        self.serial = serial.Serial(port=port, baudrate=9600)

        self.logger.info("created (%s)" % port)

    def write_msg(self, msg):

        self.serial.write(msg)

    def __str__(self):
        return 'serialw'


class PtyReader:

    def __init__(self, file_path='/tmp/.moppy_proxy_pty', timeout=0.5):

        self.logger = logging.getLogger('ptyr')

        self.file_path = file_path
        self.timeout = timeout
        self.master, self.slave = pty.openpty()
        self.created = False

        if os.system('ln -s "%s" "%s"' % (self.pty_name, self.file_path)):
            self.logger.error("file exists: %s" % self.file_path)
            raise RuntimeError("Already running proxy? File exists: %s" %
                               self.file_path)

        self.logger.info("created (%s, %s)" % (self.pty_name, self.file_path))
        self.created = True

    def __del__(self):

        if self.created:
            os.system('rm "%s"' % self.file_path)

    @property
    def pty_name(self):
        return os.ttyname(self.slave)

    def read_msg(self):

        msg = bytearray()

        while len(msg) != 3:

            try:

                r, _, _ = select.select([self.master], [], [], self.timeout)

                if not len(r):
                    break
                elif self.master in r:
                    msg += os.read(self.master, 1)

            except KeyboardInterrupt as e:
                exit(0)

        return msg

    def __str__(self):
        return 'ptyr'


class UdpReader:

    def __init__(self, host, port, timeout=0.5):

        self.logger = logging.getLogger('udpr')

        self.timeout = timeout

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))

        self.logger.info("created (%s, %d)" % (host, port))

    def read_msg(self):

        msg = bytearray()

        r, _, _ = select.select([self.socket], [], [], self.timeout)

        if len(r):
            msg = self.socket.recv(1024)

        return msg

    def __str__(self):
        return 'udpr'


class UdpWriter:

    def __init__(self, host, port):

        self.logger = logging.getLogger('udpw')

        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.logger.info("created (%s, %d)" % (host, port))

    def write_msg(self, msg):

        self.socket.sendto(msg, (self.host, self.port))

    def __str__(self):
        return 'udpw'


class SysfsWriter:

    def __init__(self, file_path="/sys/kernel/moppy/"):

        self.logger = logging.getLogger('sysfsw')

        self.file_path = file_path

        self.logger.info("created")

    def write_msg(self, msg):

        pin, value = struct.unpack("!BH", msg)

        if pin == 100 and (pin == 0 or pin > 4):
            with open(self.file_path + "ctrl", "w") as f:
                f.write("reset")
        else:
            with open(self.file_path + "ticks", "w") as f:
                f.write("%d, %d" % ((pin - 2) / 2, value))

    def __str__(self):
        return 'sysfsw'


class FileWriter:

    def __init__(self, file_path):

        self.logger = logging.getLogger('filew')

        self.timstamp = None
        self.file = open(file_path, "w")

        self.logger.info("created (%s)" % file_path)

    def __del__(self):

        if self.file is not None:
            self.file.close()

    def write_msg(self, msg):

        pin, value = struct.unpack("!BH", msg)

        if self.timstamp is None or pin == 100:
            t = 0
        else:
            t = time.time() - self.timstamp

        self.timstamp = time.time()

        self.file.write("%f, %d, %d\n" % (t, pin, value))

    def __str__(self):
        return 'filew'


class FileReader:

    def __init__(self, file_path):

        self.logger = logging.getLogger('filer')
        self.file = open(file_path, "r")

    def read_msg(self):

        msg = bytearray()

        line = self.file.readline().replace('\n', '').split(",")

        if len(line) == 3:

            t = float(line[0])
            pin = int(line[1])
            value = int(line[2])

            msg.append(chr(pin & 0xff))
            msg.append(chr((value >> 8) & 0xff))
            msg.append(chr(value & 0xff))

            time.sleep(t)
        else:
            raise RuntimeError("End of file")

        return msg

    def __str__(self):
        return 'filer'


class Proxy:

    def __init__(self, reader, writer):

        self.logger = logging.getLogger('proxy')

        self.reader = reader
        self.writer = writer

    def run(self):

        while True:

            msg = self.reader.read_msg()

            if len(msg):

                self.logger.debug("routing: [%s] (%s -> %s)" %
                                  (binascii.hexlify(msg), str(self.reader),
                                   str(self.writer)))

                self.writer.write_msg(msg)


def main():

    parser = argparse.ArgumentParser(description='MoppyProxy %s' %
                                     version.FULL)

    parser.add_argument("--serialport", default="/dev/ttyUSB0",
                        help="Serial port")

    parser.add_argument("--udphost", default="localhost",
                        help="UDP host")

    parser.add_argument("--udpport", default=12345, type=int,
                        help="UDP port")

    parser.add_argument("--filein", default="moppyin.mtf",
                        help="Input file")

    parser.add_argument("--fileout", default="moppyout.mtf",
                        help="Output file")

    parser.add_argument("-r", "--reader", default="pty",
                        help="Reader to use (pty, serial, udp, file)")

    parser.add_argument("-w", "--writer", default="sysfs",
                        help="Writer to use (serial, udp, sysfs, file)")

    parser.add_argument("--logfile", help="write log to file",
                        default=None)

    parser.add_argument("--loglevel",
                        help="loglevel (CRITICAL, ERROR, WARNING, INFO," +
                        " DEBUG)", default="INFO")

    args = parser.parse_args()

    if args.logfile is not None:
        logging.basicConfig(format='%(asctime)-15s %(name)-8s %(message)s',
                            filename=os.path.expanduser(args.logfile),
                            level=args.loglevel)
    else:
        logging.basicConfig(format='%(asctime)-15s %(name)-8s %(message)s',
                            level=args.loglevel)

    logging.info('ProxyServer %s' % version.FULL)

    readers = {
        "pty": PtyReader,
        "serial": SerialReader,
        "udp": UdpReader,
        "file": FileReader
    }

    if args.reader not in readers:
        print("Invalid reader: %s" % args.reader)
        exit(1)

    if args.reader == "serial":
        pr = readers[args.reader](args.serialport)
    elif args.reader == "udp":
        pr = readers[args.reader](args.udphost, args.udpport)
    elif args.reader == "file":
        pr = readers[args.reader](args.filin)
    else:
        pr = readers[args.reader]()

    writers = {
        "serial": SerialWriter,
        "udp": UdpWriter,
        "sysfs": SysfsWriter,
        "file": FileWriter
    }

    if args.writer not in writers:
        print("Invalid writer: %s" % args.writer)
        exit(1)

    if args.writer == "serial":
        pw = writers[args.writer](args.serialport)
    elif args.writer == "udp":
        pw = writers[args.writer](args.udphost, args.udpport)
    elif args.writer == "file":
        pw = writers[args.writer](args.fileout)
    else:
        pw = writers[args.writer]()

    p = Proxy(pr, pw)
    p.run()


if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
