#!/usr/bin/env bash

NPM=npm
GRUNT=node_modules/grunt-cli/bin/grunt
TSC=node_modules/typescript/bin/tsc

FULL_LINE=$(printf '\033[1m''=%.0s''\033[0m' $(seq 1 $(tput cols)))

echo
echo -e '\033[1m''\033[33m'"Updating NPM..."'\033[0m'
$NPM install --no-optional || exit -1

echo
echo -e $FULL_LINE
echo -e '\033[1m''\033[33m'"Copying config file..."'\033[0m'
cp -v src/configs/config.review.js src/config.js || exit -1

echo
echo -e $FULL_LINE
echo -e '\033[1m''\033[33m'"Starting Servers..."'\033[0m'
npm run server || exit -1