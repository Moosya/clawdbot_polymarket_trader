#!/bin/bash

# start.sh

# Start the Flask application with Gunicorn
gunicorn -b 0.0.0.0:8000 app:app
