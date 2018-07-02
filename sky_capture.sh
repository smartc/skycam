#!/bin/bash

cd "$(dirname "$0")"

source ./venv/bin/activate
python sky_capture.py
