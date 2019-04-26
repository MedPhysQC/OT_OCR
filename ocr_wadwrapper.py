#!/usr/bin/env python
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This code is an analysis module for WAD-QC 2.0: a server for automated 
# analysis of medical images for quality control.
#
# The WAD-QC Software can be found on 
# https://bitbucket.org/MedPhysNL/wadqc/wiki/Home
# 
#
# Changelog:
#   20190426: Fix for matplotlib>3
#   20161220: removed class variables; removed testing stuff
#   20160901: first version, combination of TdW, JG, AS
#
# mkdir -p TestSet/StudyCurve
# mkdir -p TestSet/Config
# cp ~/Downloads/1/us_philips_*.xml TestSet/Config/
# ln -s /home/nol/WAD/pyWADdemodata/US/US_AirReverberations/dicom_curve/ TestSet/StudyCurve/
# ./ocr_wadwrapper.py -d TestSet/StudyEpiqCurve/ -c Config/ocr_philips_epiq.json -r results_epiq.json
#
from __future__ import print_function

__version__ = '20190426'
__author__ = 'aschilham'

import os
# this will fail unless wad_qc is already installed
from wad_qc.module import pyWADinput
from wad_qc.modulelibs import wadwrapper_lib

import numpy as np
if not 'MPLCONFIGDIR' in os.environ:
    import pkg_resources
    try:
        #only for matplotlib < 3 should we use the tmp work around, but it should be applied before importing matplotlib
        matplotlib_version = [int(v) for v in pkg_resources.get_distribution("matplotlib").version.split('.')]
        if matplotlib_version[0]<3:
            os.environ['MPLCONFIGDIR'] = "/tmp/.matplotlib" # if this folder already exists it must be accessible by the owner of WAD_Processor 
    except:
        os.environ['MPLCONFIGDIR'] = "/tmp/.matplotlib" # if this folder already exists it must be accessible by the owner of WAD_Processor 

import matplotlib
matplotlib.use('Agg') # Force matplotlib to not use any Xwindows backend.

import ocr_lib

def logTag():
    return "[OCR_wadwrapper] "

# MODULE EXPECTS PYQTGRAPH DATA: X AND Y ARE TRANSPOSED!

def OCR(data, results, action):
    """
    Use pyOCR which for OCR
    """
    try:
        params = action['params']
    except KeyError:
        params = {}

    inputfile = data.series_filelist[0]  # give me a [filename]
    dcmInfile, pixeldataIn, dicomMode = wadwrapper_lib.prepareInput(inputfile, headers_only=False, logTag=logTag())

    # solve ocr params
    regions = {}
    for k,v in params.items():
        #'OCR_TissueIndex:xywh' = 'x;y;w;h'
        #'OCR_TissueIndex:prefix' = 'prefix'
        #'OCR_TissueIndex:suffix' = 'suffix'
        if k.startswith('OCR_'):
            split = k.find(':')
            name = k[:split]
            stuff = k[split+1:]
            if not name in regions:
                regions[name] = {'prefix':'', 'suffix':''}
            if stuff == 'xywh':
                regions[name]['xywh'] = [int(p) for p in v.split(';')]
            elif stuff == 'prefix':
                regions[name]['prefix'] = v
            elif stuff == 'suffix':
                regions[name]['suffix'] = v
            elif stuff == 'type':
                regions[name]['type'] = v

    for name, region in regions.items():
        txt, part = ocr_lib.OCR(pixeldataIn, region['xywh'])
        if region['type'] == 'object':
            import scipy
            im = scipy.misc.toimage(part) 
            fn = '%s.jpg'%name
            im.save(fn)
            results.addObject(name, fn)
            
        else:
            value = ocr_lib.txt2type(txt, region['type'], region['prefix'],region['suffix'])
            if region['type'] == 'float':
                results.addFloat(name, value)
            elif region['type'] == 'string':
                results.addString(name, value)
            elif region['type'] == 'bool':
                results.addBool(name, value)

def acqdatetime_series(data, results, action):
    """
    Read acqdatetime from dicomheaders and write to IQC database

    Workflow:
        1. Read only headers
    """
    try:
        import pydicom as dicom
    except ImportError:
        import dicom
    try:
        params = action['params']
    except KeyError:
        params = {}

    ## 1. read only headers
    dcmInfile = dicom.read_file(data.series_filelist[0][0], stop_before_pixels=True)

    dt = wadwrapper_lib.acqdatetime_series(dcmInfile)

    results.addDateTime('AcquisitionDateTime', dt) 

if __name__ == "__main__":
    data, results, config = pyWADinput()

    # read runtime parameters for module
    for name,action in config['actions'].items():
        if name == 'acqdatetime':
            acqdatetime_series(data, results, action)
        elif name == 'qc_series':
            OCR(data, results, action)

    #results.limits["minlowhighmax"]["mydynamicresult"] = [1,2,3,4]

    results.write()
