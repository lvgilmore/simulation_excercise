#! /usr/bin/python

"""
this is the main simulation program.
it represents the simulation itself
author: Geiger&Geiger
created: 29/08/16
"""

from numpy import mean, var
from event_queue import EventQueue
from cellnet_entities import Network, CallGenerator
from config import *


class CellnetSimulation:

    # the "enum" part of the simulation, for the log
    # Call enum
    TALK = 1
    SUCCESS = 2
    FAILED = 3
    HANDOFF = 4
    PENDING = 5
    # Channel enum
    FREE = 11
    BUSY = 12

    def __init__(self):
        # TODO: read end time from configuration file
        # we want to run the simulation for a day,
        # and we count in seconds
        self.event_q = EventQueue()
        self.generator = CallGenerator(self)
        self.network = Network(self)
        self._log = []  # matrix of the form (TIME, ENTITY, EVENT)

        # start running
        self.main()

    def log(self, entity, event):
        self._log.append([self.event_q.get_time(), str(entity.__class__),
                          entity.id, event, entity.state])

    def main(self):
        flag = True
        while flag:
            try:
                event = self.event_q.pop()
                event.subject()
            except IndexError:
                flag = False
        self.run_statistics()

    def run_statistics(self):
        def _verbose():
            print "channel stats:"
            print channel_stats["util"]
            print "*************************************"
            print "call stats:"
            for result in ["success", "failed"]:
                print result
                print call_stats[result]
            for state in ["incoming", "outgoing", "handoff"]:
                print state
                print call_stats[state]

        def _debug():
            for cellid, channel in channel_stats.iteritems():
                if isinstance(cellid, int):
                    print "*************************************"
                    print "cell: " + str(cellid)
                    for channelid, stats in channel.iteritems():
                        print "\tchannel:\t\t" + str(channelid)
                        print "\t\toverall free:\t" + str(stats["free"])
                        print "\t\toverall busy:\t" + str(stats["busy"])
                        print "\t\tutilization:\t" + str(stats["utilization"])

        def _prod():
            handoff_fail_rate = 1.0 - call_stats["handoff"]["success rate"]
            initiated_fail_rate = (call_stats["incoming"]["failed"] \
                                   + call_stats["outgoing"]["failed"]) \
                                  / (call_stats["incoming"]["total"] \
                                     + call_stats["outgoing"]["total"])
            channel_utilization   = channel_stats["util"]["avg"]
            handoff_avg_pending   = call_stats["handoff"]["total pending"] \
                                    / call_stats["handoff"]["total"]
            initiated_avg_pending = (call_stats["incoming"]["total pending"] \
                                     + call_stats["outgoing"]["total pending"]) \
                                    / (call_stats["incoming"]["total"] \
                                       + call_stats["outgoing"]["total"])
            print str(handoff_fail_rate) + "," + \
                  str(initiated_fail_rate) + "," + \
                  str(channel_utilization) + "," + \
                  str(handoff_avg_pending) + "," + \
                  str(initiated_avg_pending)

        channel_stats = self._channel_statistics()
        call_stats = self._call_statistics()

        # show overall statistics
        if DEBUG_LEVEL == 0:
            _prod()
        elif DEBUG_LEVEL == 1:
            _verbose()
        elif DEBUG_LEVEL == 2:
            _debug()

    def _channel_statistics(self):
        # initialize values
        channel_stats = {
            y: {
                x: {
                    "last state": "free",
                    "last started": 0,
                    "free": 0,
                    "busy": 0,
                } for x in range(10)
                } for y in range(7)
            }
        # analyze log
        for line in self._log:
            if str(line[1]).endswith("Channel"):
                time, classname, id, event, state = line
                # make sure state actually changed
                cellid = id % 10
                channelid = id / 10
                last_state = channel_stats[cellid][channelid]["last state"]
                if last_state != state:
                    channel_stats[cellid][channelid][last_state] += \
                        time - channel_stats[cellid][channelid]["last started"]
                else:
                    print "something fishy in log"
                channel_stats[cellid][channelid]["last state"] = state
                channel_stats[cellid][channelid]["last started"] = time
        # now we need to consider the fact that the last state
        # lasted to the end
        for cellid, channel in channel_stats.iteritems():
            for channelid, stats in channel.iteritems():
                last_state = channel_stats[cellid][channelid]["last state"]
                channel_stats[cellid][channelid][last_state] += \
                    self.event_q.get_time() - channel_stats[cellid][channelid]["last started"]
                channel_stats[cellid][channelid]["utilization"] = \
                    stats["busy"] / (stats["free"] + stats["busy"])
        # and now - let's wrap it up
        utilizations = [
            channel_stats[cellid][channelid]["utilization"]
            for cellid in range(7)
            for channelid in range(10)
            ]
        channel_stats["util"] = {
            "avg": mean(utilizations),
            "var": var(utilizations),
        }

        return channel_stats

    def _call_statistics(self):
        # internal methods
        def _parse_talk():
            if call_stats.has_key(callid) and \
                            call_stats[callid]["last pending"] > \
                            call_stats[callid]["last time"]:
                pending = time - call_stats[callid]["last pending"]
                call_stats[callid]["total pending"] += pending
                call_stats[state]["total pending"] += pending
            elif call_stats.has_key(callid):
                pass
            else:
                _initialize_call()
            call_stats[callid]["last time"] = time

        def _parse_success():
            talk = time - call_stats[callid]["last time"]
            call_stats[callid]["total talk"] += talk
            call_stats[state]["total talk"] += talk
            call_stats["success"]["count"] += 1
            call_stats["success"]["total talk"] += \
                call_stats[callid]["total talk"]
            call_stats["success"]["total pending"] += \
                call_stats[callid]["total pending"]
            call_stats[state]["success"] += 1

        def _parse_failed():
            pending = time - call_stats[callid]["last pending"]
            call_stats[callid]["total pending"] += pending
            call_stats[state]["total pending"] += pending
            call_stats["failed"]["count"] += 1
            call_stats["failed"]["total talk"] += \
                call_stats[callid]["total talk"]
            call_stats["failed"]["total pending"] += \
                call_stats[callid]["total pending"]
            call_stats[state]["failed"] += 1

        def _parse_handoff():
            if call_stats[callid]["last time"] > \
                    call_stats[callid]["last pending"]:
                talk = time - call_stats[callid]["last time"]
                call_stats[callid]["total talk"] += talk
                call_stats[state]["total talk"] += talk
            else:
                pending = time - call_stats[callid]["last pending"]
                call_stats[callid]["total pending"] += pending
                call_stats[state]["total pending"] += pending
                call_stats[callid]["last time"] = line[0]
            if state in ["incoming", "outgoing"]:
                call_stats[state]["handoff"] += 1

        def _parse_pending():
            if call_stats.has_key(callid) and \
                            call_stats[callid]["last time"] > \
                            call_stats[callid]["last pending"]:
                talk = time - call_stats[callid]["last time"]
                call_stats[callid]["total talk"] += talk
                call_stats[state]["total talk"] += talk
            elif call_stats.has_key(callid):
                pass
            else:
                _initialize_call()
            call_stats[callid]["last pending"] = time

        def _initialize_call():
            call_stats[callid] = {
                "total talk": 0,
                "total pending": 0,
                "last time": -1,
                "last pending": -1,
            }
        # initialize values
        call_stats = {
            "success": {
                "count": 0,
                "total talk": 0,
                "total pending": 0,
            },
            "failed": {
                "count": 0,
                "total talk": 0,
                "total pending": 0,
            },
            "incoming": {
                "success": 0,
                "failed": 0,
                "handoff": 0,
                "total talk": 0,
                "total pending": 0,
            },
            "outgoing": {
                "success": 0,
                "failed": 0,
                "handoff": 0,
                "total talk": 0,
                "total pending": 0,
            },
            "handoff": {
                "success": 0,
                "failed": 0,
                "handoff": 0,
                "total talk": 0,
                "total pending": 0,
            },
        }
        # analyze log
        for line in self._log:
            if str(line[1]).endswith("Call"):
                # make sure state actually changed
                time, classname, callid, event, state = line
                if event == CellnetSimulation.TALK:
                    _parse_talk()
                elif event == CellnetSimulation.SUCCESS:
                    _parse_success()
                elif event == CellnetSimulation.FAILED:
                    _parse_failed()
                elif event == CellnetSimulation.HANDOFF:
                    _parse_handoff()
                elif event == CellnetSimulation.PENDING:
                    _parse_pending()
        # compute averages
        for result in ["success", "failed"]:
            if not call_stats[result]["count"] == 0:
                call_stats[result]["avg talk"] = \
                    call_stats[result]["total talk"] / call_stats[result]["count"]
                call_stats[result]["avg pending"] = \
                    call_stats[result]["total pending"] / call_stats[result]["count"]
        for state in ["incoming", "outgoing", "handoff"]:
            count = 0
            for value in call_stats[state].values():
                count += value
            call_stats[state]["total"] = count
            call_stats[state]["success rate"] = 1.0 \
                                                - float(call_stats[state]["success"] \
                                                        + call_stats[state]["handoff"]) \
                                                  / call_stats[state]["total"]
        return call_stats


simulation = CellnetSimulation()  # there can be only one
