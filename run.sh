#!/usr/bin/env bash
pokebotpath=$(cd "$(dirname "$0")"; pwd)
auth=""
config=""
if [ ! -z $1 ]; then
  config=$1
else
  config="./configs/config.json"
fi
if [ ! -z $2 ]; then
  auth=$2
else
  auth="./configs/auth.json"
fi
cd $pokebotpath

sleep 2
if [ ! -f "$auth" ]; then
  echo "There's no auth file. Please use ./setup.sh -a to create one"
fi
if [ ! -f "$config" ]; then
  echo "There's no config file. Please use ./setup.sh -c to create one."
fi
while true
do
  python pokecli.py -af $auth -cf $config
  echo `date`" Pokebot "$*" Stopped."
  read -p "Press any button or wait 20 seconds to continue.
  " -r -s -n1 -t 20
done
exit 0
