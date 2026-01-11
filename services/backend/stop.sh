#!/bin/bash

# 进入 backend_server 目录
cd "$(dirname "$0")"

sudo kill -9 $(sudo lsof -t -i:8006)