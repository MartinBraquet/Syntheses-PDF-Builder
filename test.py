#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sat Feb  3 12:54:54 2018

@author: martin
"""

import subprocess
import os
import re
import pipes
import fnmatch
import argparse

try:
    from subprocess import DEVNULL  # py3k
except ImportError:
     DEVNULL = open(os.devnull, 'wb')

basename = 'elec-FSAB1201-exam-2015-Janvier-All.tex'
dirname = '/home/martin/Documents/Syntheses/src/q1/elec-FSAB1201/exam/2015/Janvier/All'

sub_build_command = 'latexmk -pdf -pdflatex="pdflatex -jobname={} -output-directory {} -shell-escape -enable-write18 \
                            {}" -use-make {}'
        #translated_properties.update('buildCommandnotsol')
x = sub_build_command.format(
            pipes.quote('new'),
            pipes.quote('/home/martin/Desktop'),
            pipes.quote('\def\Sol{false} \input{%S}'),
            pipes.quote(basename)
            )
        
subprocess.call(x, shell=True, cwd=dirname, stdout=DEVNULL)

cmd = ['pdflatex', '-interaction', 'nonstopmode', 'elec-FSAB1201-exam-2015-Janvier-All.tex']
proc = subprocess.Popen(cmd)
proc.communicate()