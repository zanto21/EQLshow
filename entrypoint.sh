#!/bin/bash
source ${ROS_PATH}/setup.bash
source ${ROS_WS}/install/setup.bash 2>/dev/null || true

exec "$@"