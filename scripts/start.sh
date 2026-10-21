#!/bin/sh
set -eu
systemctl --user start ki-adler-demo.service
systemctl --user --no-pager status ki-adler-demo.service
