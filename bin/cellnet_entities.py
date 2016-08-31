#! /usr/bin/python

"""
this module represents entities related to the cellular network
author: Geiger&Geiger
created: 29/08/16
"""

from random import choice, gauss, uniform, expovariate
from uuid import uuid4
from event_queue import Event
from config import *


class Network:
    def __init__(self, simulation):
        self.simulation = simulation
        # as stated in the doc, the simulation network contains 7 cells
        self.cells = [Cell(simulation=self.simulation, id=x) for x in range(7)]

    def pick_cell(self, call):
        return choice(self.cells)


class Cell:
    def __init__(self, simulation, id=0):
        self.id = id
        self.simulation = simulation
        # each cell contains one base station
        self.base_station = BaseStation(cell=self, simulation=self.simulation)
        self.pending_calls = []
        self.cancel_schedule = {}

    def pick_channel(self, call):
        channel = self.base_station.free_channel()
        if channel:
            return channel
        else:
            if call.state in ["incoming", "outgoing"]:
                hangup_time = INITIAL_GIVEUP_TIME
            else:
                hangup_time = HANDOFF_GIVEUP_TIME
            self.pending_calls.append(call)
            hangup_event = Event(call, call.reneg)
            self.simulation.event_q.push(hangup_time, hangup_event)
            hangup_time += self.simulation.event_q.get_time()
            self.cancel_schedule[call] = (hangup_time, hangup_event)

    def reneg(self, call):
        return self.pending_calls.remove(call)

    def channel_evaq(self):
        """
        this method is not thread-safe: if, for some reason, one
        channel evacuates but two threads are pulling calls, than
        one call will move from the head of the queue to its end
        and receive a second "grace period". however, this scenario
        won't happen for two reasons: a. we're not multithreaded,
        and b. can't see why one channel evacuates but two threads
        are called
        """
        if self.pending_calls.__len__() > 0:
            call = self.pending_calls.pop(0)
            hangup_time, hangup_event = self.cancel_schedule[call]
            self.simulation.event_q.cancel_event(hangup_time, hangup_event)
            return call.receive_channel(self.pick_channel(call=call))
        return True


class BaseStation:
    def __init__(self, cell, simulation=None):
        self.cell = cell
        if simulation is None:
            self.simulation = self.cell.simulation
        else:
            self.simulation = simulation
        # initialize 10 channels to the base station
        self.channels = [
            Channel(base_station=self, simulation=self.simulation,
                    id=(x*10)+self.cell.id) for x in range(10)
            ]

    def free_channel(self):
        free_channels = []
        for channel in self.channels:
            if channel.free:
                free_channels.append(channel)
        if free_channels.__len__() > 0:
            channel = choice(free_channels)
            channel.allocate()
            return channel
        return False

    def channel_evaq(self):
        self.cell.channel_evaq()


class Channel:
    def __init__(self, base_station, simulation=None, free=True, id=0):
        self.id = id
        self.base_station = base_station
        if simulation is not None:
            self.simulation = simulation
        else:
            self.simulation = simulation
        self.free = free

    def allocate(self):
        self.free = False
        self.simulation.log(self, self.simulation.BUSY)

    def evaq(self):
        self.free = True
        self.simulation.log(self, self.simulation.FREE)
        self.base_station.channel_evaq()

    @property
    def state(self):
        if self.free:
            return "free"
        else:
            return "busy"


class Call:
    def __init__(self, simulation):
        self.id = uuid4()  # it'll be useful when we'll analyze the log
        self.state = choice(["incoming", "outgoing"])
        self.cell = None
        self.channel = None
        self.simulation = simulation
        self.request_channel()

    def request_channel(self):
        self.cell = self.simulation.network.pick_cell(self)
        channel = self.cell.pick_channel(self)
        if channel is None:
            self.simulation.log(self, self.simulation.PENDING)
            return False
        return self.receive_channel(channel)

    def receive_channel(self, channel):
        self.channel = channel
        self.simulation.log(self, self.simulation.TALK)
        transition_time = max(gauss(TALK_MEAN, TALK_VAR), 5)
        self.simulation.event_q.push(transition_time,
                                     Event(self, self.transition))

    def transition(self):
        self.channel.evaq()
        if uniform(0, 1) <= HANDOFF_RATIO:
            self.simulation.log(self, self.simulation.HANDOFF)
            self.state = "handoff"
            self.request_channel()
        else:
            self.simulation.log(self, self.simulation.SUCCESS)

    def reneg(self):
        self.simulation.log(self, self.simulation.FAILED)
        self.cell.reneg(self)


class CallGenerator:
    def __init__(self, simulation):
        """
        initialize calling generation by setting the first call at time 0
        """
        self.simulation = simulation
        self.simulation.event_q.push(0,
                                     Event(self, self.generate))

    def generate(self):
        Call(self.simulation)
        self.simulation.event_q.push(expovariate(ARRIVE_MEAN)*ARRIVE_SCALE,  # mean: a call every 3 minutes
                                     Event(self, self.generate))


class NoFreeChannelError(Exception):
    def __init__(self, **kwargs):
        Exception.__init__(**kwargs)
