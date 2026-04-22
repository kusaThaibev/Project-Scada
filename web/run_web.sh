#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
echo "Starting Django Web Server..."
python3 manage.py runserver 0.0.0.0:8000
