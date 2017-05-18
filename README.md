# Kernel Moppy

This is a fork of the great Moppy project from [SammyIAm](https://github.com/SammyIAm/Moppy). The goals of this fork a mainly:

* to provide a Linux Kernel module which allows driving floppies directly e.g.
	from a Raspberry Pi
* to provide a Python3 library which easily allows playing MIDI files through the
	floppies

This is work in progress and it is likely that things are changing a lot in future. Also documentation at the moment is very sparse.

![FloppyOrgel](./docs/images/raspi_floppyorgel_2.jpg "Raspberry Pi FloppyOrgel")

Or to see a very early prototype in action see this [video](https://youtu.be/JAqpbqwstrw)

## Current state

The following is currently in a more or less working state:

* Kernel Module to drive the floppies, currently only tested with a Raspberry Pi
	and eight floppy drives
* Python3 library for playing MIDI files
* Some Python3 tools like:
	* Curses based player
	* Web based player
	* Proxy to allow Java based MoppyDesk player to use Moppy Kernel module for
		playback
	* Special version of MoppyDesk which detects the proxy

## Things to do

* Write documentation
* Make the Web based player a configurable daemon
* Testing

## Connect the Hardware

For a Moppy Pi setup you will need the following hardware:

* 1 x Raspberry Pi 3 with Raspian on SD card already configured
* 1 to 8 3.5 floppy drives
* 1 power supply (e.g. old AT power supply)
* Some wires

GND of all Floppies needs to be connected to GND of the Pi. Each floppy needs to have a jumper between pin 12 (drive b) and the pin below (GND). Now, connect step (ST) signal (pin 20) and direction (DI) signal (pin 18) from the floppies to the Pi header as shown below:

	Pin Flp.   Pin  Flp.
	Pi         Pi
	----------------------
	 2, "ST#0",  3, "DI#0"
	17, "ST#1", 27, "DI#1"
	22, "ST#2", 23, "DI#2"
	10, "ST#3",  9, "DI#3"
	11, "ST#4",  8, "DI#4"
	 5, "ST#5",  6, "DI#5"
	13, "ST#6", 19, "DI#6"
	26, "ST#7", 20, "DI#7"

For flopy pin-out see [this](http://pinouts.ru/HD/InternalDisk_pinout.shtml)

## Building and Installing the Raspberry Pi Kernel Module

### Prerequisites

The build tools are 32 bit, thus make sure you have 32 bit libs installed
even when on a 64 bit Linux. For Ubuntu they are most likely already installed.
For Debian, the following commands would install them:

	sudo dpkg --add-architecture i386
	sudo apt-get update
	sudo apt-get install build-essential gcc-multilib rpm libstdc++6:i386 libgcc1:i386 zlib1g:i386 libncurses5:i386

### Cross-Compile the Kernel and the Moppy Modules

The Makefile will download the Kernel sources from git, as well as the build tools.

On your host computer (not the Pi), first configure the environment to point to the right compiler:

	cd moppy-kmod
	source setenv.sh

Next, start the build:

	make

This will take a while, but at the end, the archive ``rpi-moppy-kernel.tar.bz2`` should have been created under the main directory.

Copy the archive to your Pi. Now on the Pi execute the following command to install the new Kernel:

	sudo tar -jxvf todo -C /

### Install the new Kernel on the Pi

You could ignore the complaints about file permissions (they are because the boot directory is on a FAT partition and tar is not able to set Linux permissions here). Next, reboot the Pi.

### Load the Moppy Kernel Module
sudo apt-get install python-pip python3-pip
Again on the Pi, load the Moppy module:

	modprobe moppy

You could get some information about the loading with:

	dmesg

## Install the Python Midi Player on the Pi

On the host computer, from within the main directory, copy the whole directory (with all subdirectories) to the Pi. Now set the players up on the Pi:

	sudo apt-get install python3-pip

Instal the Python3 dependencies:

	sudo pip3 install Flask
	sudo pip3 install mido
	sudo pip3 install pyserial # if not already present

To access the kernel module via sysfs, the user pi needs to be added to the group ``root``:

	sudo adduser pi root

Please note, that the group settings apply after the next login only.

Finally install the players by chingin into the ``moppy-python`` directory and execute:

	sudo python3 setup.py install

## Start the Web-Based Player on the Pi

Now, the web server for the web based player could be started on the Pi with:

	moppy-server

With a browser, you now could access the player with the following URL:

	http://<ip-of-your-pi>:8088/
