#!/bin/bash
gunicorn -w 1 -b 0.0.0.0:8010  -k uvicorn.workers.UvicornWorker --timeout 120 --graceful-timeout 30 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 main:app