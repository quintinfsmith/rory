#!/usr/bin/env python3
# coding=utf-8

import os, sys

file_path = os.path.realpath(__file__)
os.chdir(file_path[0:file_path.rfind("/") + 1])


os.system("python -m build")
if "--local" in sys.argv:
    os.system("pip install dist/*")
elif "--publish" in sys.argv:
    os.system("python3 -m twine upload dist/*")

os.system("rm rory.egg-info -rf")
os.system("rm dist -rf")

#os.system("rm rory -rf")
