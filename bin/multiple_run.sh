#! /usr/bin/time /bin/bash

# make sure the file is right
headerline="handoff_fail_rate,initiated_fail_rate,channel_utilization,handoff_avg_pending,initiated_avg_pending"
csvfile="../cellnet_simulation.csv"
if [ "$1" == "" ]
then
    times=10
else
    times=$1
fi
if ! [ -f $csvfile ] || [ "`head -1 $csvfile`" != $headerline ]
then
    echo $headerline > $csvfile
fi
i=0
while [ $i -lt $times ]
do
    /usr/bin/python2.7 ./cellnet_simulation.py >> $csvfile
    i=$(($i+1))
done
