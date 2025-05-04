#!/bin/bash

./stop.sh &

# Run the first command with 8080 and device1
./start.sh 8080 device1 &

# Run the second command with 8081 and device2
./start.sh 8081 device2 &
