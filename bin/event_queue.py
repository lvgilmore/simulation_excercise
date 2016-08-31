#! /usr/bin/python

"""
this module represents the event queue, which is the
most important module of every discrete simulation
author: Geiger&Geiger
created: 29/08/16
"""

from config import *

class EventQueue:
    def __init__(self, end_time=END_TIME):
        self.end_time = end_time
        self.simulation_time = 0
        # the schedule is a dictionary (python equivalent of hash table)
        # with key=time, and value=event
        self.schedule = {}
        # for sorting reasons, we also hold time list
        # it's not memory efficient, but it helps readability
        self.timetable = []

    def push(self, time, event):
        # we shouldn't trust our caller to know what time it is,
        # so we add it ourselves.
        time += self.simulation_time
        # ignoring events if time is out of scope
        if time > self.end_time:
            return False

        # check if we need to initialize the schedule entry
        if self.schedule.has_key(time):
            self.schedule[time].append(event)
        else:
            self.schedule[time] = [event]
        self.timetable.append(time)
        self.timetable.sort()
        return True

    def pop(self):
        # if we've reached the end, let it be known
        if (self.simulation_time >= self.end_time
            or self.timetable.__len__() == 0):
            raise IndexError

        # we need to advance the clock
        self.simulation_time = self.timetable.pop(0)
        event = self.schedule[self.simulation_time].pop(0)
        # clean the schedule if there're no events
        if self.schedule[self.simulation_time].__len__() == 0:
            self.schedule.pop(self.simulation_time)
        return event

    def get_time(self):
        return self.simulation_time

    def cancel_event(self, time, event):
        if self.schedule.has_key(time):
            assert (isinstance(self.schedule[time], list))
            try:
                self.schedule[time].remove(event)
                if self.schedule[time].__len__() == 0:
                    self.schedule.pop(time)
            except ValueError:
                return False
            self.timetable.remove(time)
            return True
        else:
            raise ValueError("time %s does not exist in schedule" % str(time))


class Event:
    def __init__(self, object, subject):
        """
        :param object: instance, whom the event happens to
        :param subject: method, what happens
        :type object: object
        :type subject: method
        """
        self.object = object
        self.subject = subject

    def __str__(self):
        return "Event: object " + str(self.object) + ", subject" + str(self.subject)

# Unit tests
if __name__ == "__main__":
    event_q = EventQueue(100)
    event_q.push(50, Event(5, 6))
    to_be_cancelled = Event(3, 4)
    event_q.push(40, to_be_cancelled)
    event_q.push(50, to_be_cancelled)
    event_q.push(60, to_be_cancelled)
    event_q.push(50, Event(1, 2))
    event_q.push(20, Event(7, 8))
    print str(event_q.pop())
    event_q.cancel_event(40, to_be_cancelled)
    event_q.cancel_event(50, to_be_cancelled)
    print str(event_q.pop())
    print str(event_q.pop())
    print str(event_q.pop())

    """
    expected output:
    Event: object 7, subject8
    Event: object 5, subject6
    Event: object 1, subject2
    Event: object 3, subject4
    """
