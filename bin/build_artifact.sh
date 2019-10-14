#!/bin/bash

OUTFILE=$1

set +e
set +x

pipenv install
mkdir target

pipenv --venv 2>&1

VENV=$(pipenv --venv 2>&1)
echo "Virtual env is $VENV"

LIB_PATH="$VENV/lib/*/site-packages"
echo "Lib Path: $LIB_PATH"

cp maxmind.py $LIB_PATH
chmod 644 $LIB_PATH/maxmind.py

cd $LIB_PATH
zip -q -r ${OUTFILE} . -x ${OUTFILE}
openssl dgst -sha256 -binary ${OUTFILE} | openssl enc -base64 > ${OUTFILE}.base64sha256
