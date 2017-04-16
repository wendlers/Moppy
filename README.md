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
