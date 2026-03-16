#!/usr/bin/env python3
"""Wrapper: delegates to todo-server-fastapi.py"""
import os, sys
os.execv(sys.executable, [sys.executable, '/home/hyfree/todo-server-fastapi.py'] + sys.argv[1:])
