import time
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
import sys
import picoscope_main_gui_101022
from colorama import Fore, Style


from numba import jit,njit
import glob
import pyqtgraph as pg
import random

import h5py
import os




import ctypes
import platform

from datetime import datetime

import math
from picosdk.ps5000a import ps5000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc


def make_dpi_aware():
    if int(platform.release()) >= 8:
        ctypes.windll.shcore.SetProcessDpiAwareness(True)

make_dpi_aware()


chandle = ctypes.c_int16()
status = {}


''' A function to initialize the picoscope mesurements'''
def StartPSScope():
    resolution =ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]
    # Returns handle to chandle for use in future API functions
    status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(chandle), None, resolution)
    # print(status)

    try:
        assert_pico_ok(status["openunit"])
    except: # PicoNotOkError:

        powerStatus = status["openunit"]

        if powerStatus == 286:
            status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
        elif powerStatus == 282:
            status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
        else:0==0
            # raise

            # assert_pico_ok(status["changePowerSource"])
    if status["openunit"] == 0:
        # Set up channel A
        # handle = chandle
        channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        # enabled = 1
        coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
        chARange = ps.PS5000A_RANGE["PS5000A_2V"]
        # analogue offset = 0 V
        status["setChA"] = ps.ps5000aSetChannel(chandle, channel, 1, coupling_type, chARange, 0)
        assert_pico_ok(status["setChA"])

        # Set up channel B
        # handle = chandle
        channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
        # enabled = 1
        # coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
        chBRange = ps.PS5000A_RANGE["PS5000A_2V"]
        # analogue offset = 0 V
        status["setChB"] = ps.ps5000aSetChannel(chandle, channel, 1, coupling_type, chBRange, 0)
        assert_pico_ok(status["setChB"])

        # find maximum ADC count value
        # handle = chandle
        # pointer to value = ctypes.byref(maxADC)
        maxADC = ctypes.c_int16()
        status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
        assert_pico_ok(status["maximumValue"])

        # Set up single trigger
        # handle = chandle
        # enabled = 1
        source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
        threshold = int(mV2adc(1000,chARange, maxADC))
        # direction = PS5000A_RISING = 2
        # delay = 0 s
        # auto Trigger = 1000 ms
        status["trigger"] = ps.ps5000aSetSimpleTrigger(chandle, 1, source, threshold, 2, 0, 1000)
        assert_pico_ok(status["trigger"])

    return status, chandle


def StopPSScope(stauts,chandle):
    status["stop"] = ps.ps5000aStop(chandle)
    # assert_pico_ok(status["stop"])

    # Close unit Disconnect the scope
    # handle = chandle
    status["close"]=ps.ps5000aCloseUnit(chandle)
    # assert_pico_ok(status["close"])


class GuiThread(QtWidgets.QMainWindow, picoscope_main_gui_101022.Ui_MainWindow):



     data_transfer_to_worker = pyqtSignal(object)


     def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)



        ''' Initialize sampling value'''
        self.TimingSampleNumberSpinBox.setRange(0,1000000)
        self.TimingSampleNumberSpinBox.setValue(5000)
        self.psSamplingNumber  = self.TimingSampleNumberSpinBox.value()



        self.psCollectedData = np.zeros((5,self.psSamplingNumber))

        self.psCollectedData[0,:] = np.linspace(-5,5,num = self.psSamplingNumber)
        self.psCollectedData[1,:] = np.sin(10*self.psCollectedData[0,:])/self.psCollectedData[0,:]+np.random.normal(0,0.05,self.psSamplingNumber)
        self.psCollectedData[2,:] = np.sin(5*self.psCollectedData[0,:])+np.random.normal(0,0.05,self.psSamplingNumber)
        self.psCollectedData[3,:] = np.sin(0.5*self.psCollectedData[0,:])+np.random.normal(0,0.05,self.psSamplingNumber)
        self.psCollectedData[4,:] = 1*np.sin(2.*self.psCollectedData[0,:])+np.random.normal(0,0.05,self.psSamplingNumber)


        # pg.setConfigOption('background', 'w')
        # pg.setConfigOption('foreground', 'k')
        self.psDataPlot = pg.PlotWidget()
        # self.psDataPlot.setMouseMode(self.psDataPlot.vb.RectMode)
        self.psDataPlot.plotItem.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        # self.psDataPlot.setMouseMode(self.psDataPlot.RectMode)
        self.psDataPlot.setObjectName('psDataPlot')
        self.psDataLayout.addWidget(self.psDataPlot)
        # self.psTextLabel = pg.TextItem("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>,   <span style='color: green'>y2=%0.1f</span>" % (1,2,3),anchor=(1, 1), color= (255,0,0))
        # self.psDataPlot.addItem(self.psTextLabel)

        self.label = pg.TextItem('blablalba', anchor = (0,0), color = (0,0,255))
        self.psDataPlot.addItem(self.label)






        self.psDataPlot.plot(self.psCollectedData[0,:],self.psCollectedData[1,:],pen=(255,0,0))
        self.psDataPlot.plot(self.psCollectedData[0,:],self.psCollectedData[2,:],pen=(0,0,255))
        self.psDataPlot.plot(self.psCollectedData[0,:],self.psCollectedData[3,:],pen=(0,255,0))
        self.psDataPlot.plot(self.psCollectedData[0,:],self.psCollectedData[4,:],pen=(255,200,0))



        " Scan window"


        self.ScanColors = [(0,0,255,100),(255,0,0,100),(0,255,0,100),(0,255,255,100),(255,0,255,100),(255,0,127,100),(255,127,0,100)]
        self.ScanColors1 = [(0,0,255),(255,0,0),(0,255,0),(0,255,255),(255,0,255),(255,0,127),(255,127,0)]

        self.psScanPlot1 = pg.PlotWidget()
        self.psScanPlot2 = pg.PlotWidget()

        self.psScanPlot1.plotItem.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.psScanPlot2.plotItem.getViewBox().setMouseMode(pg.ViewBox.RectMode)


        self.psScanPlot1.setObjectName('psScanPlot1')
        self.psScanPlot2.setObjectName('psScanPlot2')
        self.psScanLayout1.addWidget(self.psScanPlot1)
        self.psScanLayout2.addWidget(self.psScanPlot2)


        # self.vLine = pg.InfiniteLine(angle=90, movable=True)
        # self.hLine = pg.InfiniteLine(angle=90, movable=True)
        self.ScanRegion1 = pg.LinearRegionItem(orientation = 'vertical', movable = True,brush = self.ScanColors[0])
        self.ScanRegion2 = pg.LinearRegionItem(orientation = 'vertical', movable = True, brush =self.ScanColors[1])
        self.ScanRegion3 = pg.LinearRegionItem(orientation = 'vertical', movable = True, brush =self.ScanColors[2])
        self.ScanRegion4 = pg.LinearRegionItem(orientation = 'vertical', movable = True, brush =self.ScanColors[3])
        self.ScanRegion5 = pg.LinearRegionItem(orientation = 'vertical', movable = True, brush =self.ScanColors[4])
        self.ScanRegion6 = pg.LinearRegionItem(orientation = 'vertical', movable = True, brush =self.ScanColors[5])
        self.ScanRegion7 = pg.LinearRegionItem(orientation = 'vertical', movable = True, brush =self.ScanColors[6])
        # self.ScanRegion8 = pg.LinearRegionItem(orientation = 'vertical', movable = True, brush =(255,0,0,100))

        self.psScanPlot1.plot(self.psCollectedData[0,:],self.psCollectedData[1,:],pen=(255,0,0))
        self.psScanPlot1.plot(self.psCollectedData[0,:],self.psCollectedData[2,:],pen=(0,0,255))
        self.psScanPlot1.plot(self.psCollectedData[0,:],self.psCollectedData[3,:],pen=(0,255,0))
        self.psScanPlot1.plot(self.psCollectedData[0,:],self.psCollectedData[4,:],pen=(255,200,0))
        # self.psScanPlot1.addItem(self.ScanRegion1, ignoreBounds=True)
        # self.psScanPlot1.addItem(self.ScanRegion2, ignoreBounds=True)
        # self.psScanPlot1.addItem(self.ScanRegion3, ignoreBounds=True)
        # self.psScanPlot1.addItem(self.ScanRegion4, ignoreBounds=True)
        # self.psScanPlot1.addItem(self.ScanRegion5, ignoreBounds=True)
        # self.psScanPlot1.addItem(self.ScanRegion6, ignoreBounds=True)
        # self.psScanPlot1.addItem(self.ScanRegion7, ignoreBounds=True)
        # print(self.ScanRegion1.getRegion())
        self.psScanCount = 0
        self.psScanActive = 'Off'
        # print(self.ScanGatecheckBox1)
        # print(self.psScanPlot1)


        self.ScanGateState1 = 'Off'
        self.ScanGateState2 = 'Off'
        self.ScanGateState3 = 'Off'
        self.ScanGateState4 = 'Off'
        self.ScanGateState5 = 'Off'
        self.ScanGateState6 = 'Off'
        self.ScanGateState7 = 'Off'

        self.ScanGatecheckBox1.stateChanged.connect(lambda: self.ScanGateCheckBoxFunc(self.ScanGatecheckBox1,self.ScanRegion1))
        self.ScanGatecheckBox2.stateChanged.connect(lambda: self.ScanGateCheckBoxFunc(self.ScanGatecheckBox2,self.ScanRegion2))
        self.ScanGatecheckBox3.stateChanged.connect(lambda: self.ScanGateCheckBoxFunc(self.ScanGatecheckBox3,self.ScanRegion3))
        self.ScanGatecheckBox4.stateChanged.connect(lambda: self.ScanGateCheckBoxFunc(self.ScanGatecheckBox4,self.ScanRegion4))
        self.ScanGatecheckBox5.stateChanged.connect(lambda: self.ScanGateCheckBoxFunc(self.ScanGatecheckBox5,self.ScanRegion5))
        self.ScanGatecheckBox6.stateChanged.connect(lambda: self.ScanGateCheckBoxFunc(self.ScanGatecheckBox6,self.ScanRegion6))
        self.ScanGatecheckBox7.stateChanged.connect(lambda: self.ScanGateCheckBoxFunc(self.ScanGatecheckBox7,self.ScanRegion7))
        # self.ScanGatecheckBox1.stateChanged.connect(functools.partial( self.ScanGateCheckBoxFunc,self.ScanGatecheckBox1,self.psScanPlot1))

        self.ScanGateButton.clicked.connect(self.ScanButtonFunc)


        ''' Binning '''
        self.BinAvgState = 'Off'
        self.BinningN = self.NBinsSpinBox.value()
        self.BinAvgN = self.NAvgSpinBox.value()

        self.BinAvgCount = 0

        self.BinAvgPlot = pg.PlotWidget()
        self.BinAvgPlot.plotItem.getViewBox().setMouseMode(pg.ViewBox.RectMode)
        self.BinAvgPlot.setObjectName('BinPlot')
        self.BinAvgLayout.addWidget(self.BinAvgPlot)







        ''' Readout trigger settings'''
        self.TriggerMode = self.TriggerModeComboBox.currentText()
        self.TriggerSlope = self.TriggerSlopeComboBox.currentText()
        self.TriggerChannel = self.TriggerChannelComboBox.currentText()
        self.TriggerLevel = self.TriggerLevelSpinBox.value()


        ''' Readout Timing settings '''
        self.TimingDivision = self.TimingTimeDivisionSpinBox.value()
        self.TimingDivisionComboBoxValue = self.TimingTimeDivisionComboBox.currentText()
        self.TimingOffset = self.TimingTimeOffsetSpinBox.value()
        self.TimingOffsetComboBoxValue = self.TimingTimeOffsetComboBox.currentText()



        ''' Channel A Readout settings '''
        self.ChannelACoupling = self.ChannelACouplingComboBox.currentText()
        self.ChannelAOffset = self.ChannelAOffsetSpinBox.value()
        # self.ChannelAOffsetComboBoxValue = self.ChannelAOffsetComboBox.currentText()


        ''' Channel B Readout settings '''
        self.ChannelBCoupling = self.ChannelBCouplingComboBox.currentText()
        self.ChannelBOffset = self.ChannelBOffsetSpinBox.value()
        # self.ChannelBOffsetComboBoxValue = self.ChannelBOffsetComboBox.currentText()

        ''' Channel C Readout settings '''
        self.ChannelCCoupling = self.ChannelCCouplingComboBox.currentText()
        self.ChannelCOffset = self.ChannelCOffsetSpinBox.value()
        # self.ChannelCOffsetComboBoxValue = self.ChannelCOffsetComboBox.currentText()

        ''' Channel D Readout settings '''
        self.ChannelDCoupling = self.ChannelDCouplingComboBox.currentText()
        self.ChannelDOffset = self.ChannelDOffsetSpinBox.value()
        # self.ChannelDOffsetComboBoxValue = self.ChannelDOffsetComboBox.currentText()


        ''' Measurement state'''
        self.MeasurementState = 'Off'

        ''' Channel state'''
        self.ChannelAState = 'Off'
        self.ChannelBState = 'Off'
        self.ChannelCState = 'Off'
        self.ChannelDState = 'Off'


        ''' Start measurement and channel'''
        self.StartMeasurementButton.clicked.connect(self.StartMeasurementButtonFunction)
        self.ChannelAButton.clicked.connect(self.ChannelAButtonPress)
        self.ChannelBButton.clicked.connect(self.ChannelBButtonPress)
        self.ChannelCButton.clicked.connect(self.ChannelCButtonPress)
        self.ChannelDButton.clicked.connect(self.ChannelDButtonPress)


        ''' Trigger change '''
        self.TriggerModeComboBox.currentTextChanged.connect(self.TriggerSetup)
        self.TriggerSlopeComboBox.currentTextChanged.connect(self.TriggerSetup)
        self.TriggerChannelComboBox.currentTextChanged.connect(self.TriggerSetup)
        self.TriggerLevelSpinBox.valueChanged.connect(self.TriggerSetup)


        ''' Channel A change '''
        self.ChannelACouplingComboBox.currentTextChanged.connect(self.ChannelAUpdate)
        self.ChannelAOffsetSpinBox.valueChanged.connect(self.ChannelAUpdate)
        self.ChARangeBox.currentTextChanged.connect(self.ChannelAUpdate)


        ''' Channel B change '''
        self.ChannelBCouplingComboBox.currentTextChanged.connect(self.ChannelBUpdate)
        self.ChannelBOffsetSpinBox.valueChanged.connect(self.ChannelBUpdate)
        self.ChBRangeBox.currentTextChanged.connect(self.ChannelBUpdate)


        ''' Channel C change '''
        self.ChannelCCouplingComboBox.currentTextChanged.connect(self.ChannelCUpdate)
        self.ChannelCOffsetSpinBox.valueChanged.connect(self.ChannelCUpdate)
        self.ChCRangeBox.currentTextChanged.connect(self.ChannelCUpdate)


        ''' Channel D change '''
        self.ChannelDCouplingComboBox.currentTextChanged.connect(self.ChannelDUpdate)
        self.ChannelDOffsetSpinBox.valueChanged.connect(self.ChannelDUpdate)
        self.ChDRangeBox.currentTextChanged.connect(self.ChannelDUpdate)

        ''' Channel voltage ranges '''
        self.ChannelVoltageRanges = ['PS5000A_10MV','PS5000A_20MV','PS5000A_50MV','PS5000A_100MV','PS5000A_200MV','PS5000A_500MV','PS5000A_1V',
                                     'PS5000A_2V','PS5000A_5V','PS5000A_10V','PS5000A_20V','PS5000A_50V','PS5000A_MAX_RANGES']



        "Save Waveform"
        self.SaveWaveformButton.clicked.connect(self.SaveWaveformData)


        " Continuous Save Data"
        self.ContinuousSaveDataLocation = 'C:\\Users\\damjanov\\Documents\\XFEL_stuff\\Work_stuff\\Work\\Python_programs\\Picoscope\\Programs\\03062022_main_window_gui\\Data\\'
        self.save_count = 0
        self.ContinuousSaveMode = 'Off'
        self.WaveformContinousSaveFileLocation.clicked.connect(self.ContinuousSaveFolderButton)
        self.WaveformContinousSave.clicked.connect(self.ContinuousSaveButton)


        "Mouse point inital"
        self.mpoint_x = 0
        self.mpoint_y = 0



        ''' Binning start button'''

        self.StartBinningButton.clicked.connect(self.BinAvgButton)



     def StartMeasurementButtonFunction(self):
        if self.MeasurementState == 'Off':


            self.status, self.chandle = StartPSScope()
            # print(self.status['openunit'] )
            # self.label.setText('blablabla123',color = (0,0,255))

            if  self.status['openunit']==0 or self.status['openunit']==286 or self.status['openunit']==282:

                self.StartMeasurementButton.setText('Measuring')
                self.StartMeasurementButton.setStyleSheet('background-color : green')
                self.MeasurementState = 'On'

                self.ChannelAState = 'On'
                self.ChannelBState = 'On'
                self.ChannelAButtonPress()
                self.ChannelBButtonPress()
                self.ChannelAUpdate()
                self.ChannelAUpdate()
                self.ChannelBUpdate()


                # self.psMT = psMeasureThread()
                # self.psMT.start()
                # self.psMT.data_for_transfer.connect(self.UpdatePlot)


                self.thread = QThread()
                self.psMT = psMeasureThread1()
                self.psMT.moveToThread(self.thread)
                # self.psMT.start()
                self.thread.started.connect(self.psMT.StartTimer)
                self.thread.start()
                self.psMT.data_for_transfer.connect(self.UpdatePlot)
                self.data_transfer_to_worker.connect(self.psMT.DataFrom_GUI)
                self.data_transfer_to_worker.emit('abc')






            elif self.status['openunit']!=0 and self.status['openunit']!=286 and self.status['openunit']!=282:
                self.StartMeasurementButton.setText('No Picoscope')
                self.StartMeasurementButton.setStyleSheet('background-color : red')
                self.MeasurementState = 'Error'





        elif self.MeasurementState == 'On':
            self.StartMeasurementButton.setText('Start Measuring')
            self.StartMeasurementButton.setStyleSheet('background-color : light grey')
            self.MeasurementState = 'Off'


            self.ChannelAButton.setText('Off')
            self.ChannelAButton.setStyleSheet('background-color : light grey')
            self.ChannelAState = 'Off'
            self.ChannelBButton.setText('Off')
            self.ChannelBButton.setStyleSheet('background-color : light grey')
            self.ChannelBState = 'Off'
            self.ChannelCButton.setText('Off')
            self.ChannelCButton.setStyleSheet('background-color : light grey')
            self.ChannelCState = 'Off'
            self.ChannelDButton.setText('Off')
            self.ChannelDButton.setStyleSheet('background-color : light grey')
            self.ChannelDState = 'Off'

            StopPSScope(self.status,self.chandle)
            self.thread.terminate()

        elif self.MeasurementState == 'Error':
            self.StartMeasurementButton.setText('Start Measuring')
            self.StartMeasurementButton.setStyleSheet('background-color : light grey')
            self.MeasurementState = 'Off'









     '''Trigger functions '''

     def TriggerSetup(self):
         self.TriggerMode = self.TriggerModeComboBox.currentText()


         self.TriggerSlope = self.TriggerSlopeComboBox.currentText()
         if self.TriggerSlope == 'Rising': self.TriggerSlopeVal = 2
         if self.TriggerSlope == 'Falling': self.TriggerSlopeVal = 3

         self.TriggerChannel = self.TriggerChannelComboBox.currentText()
         if self.TriggerChannel == 'A': self.TriggerChannelVal = 0
         if self.TriggerChannel == 'B': self.TriggerChannelVal = 1
         if self.TriggerChannel == 'C': self.TriggerChannelVal = 2
         if self.TriggerChannel == 'D': self.TriggerChannelVal = 3
         if self.TriggerChannel == 'External': self.TriggerChannelVal = 4

         self.TriggerLevel = self.TriggerLevelSpinBox.value()
         self.chRange = 10


         if self.MeasurementState == 'On':

             self.maxADC = ctypes.c_int16()
             self.status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(self.maxADC))
             assert_pico_ok(self.status["maximumValue"])

             self.threshold = int(mV2adc(self.TriggerLevel,self.chRange, self.maxADC))
             # direction = PS5000A_RISING = 2
             # delay = 0 s
             # auto Trigger = 1000 ms
             self.status["trigger"] = ps.ps5000aSetSimpleTrigger(chandle, 1, self.TriggerChannelVal, self.threshold, self.TriggerSlopeVal, 0, 1000)
             assert_pico_ok(self.status["trigger"])








     # '''Channel Functions '''


     def ChannelAButtonPress(self):
         if self.MeasurementState == 'On':

            if self.ChannelAState == 'Off':
                self.ChannelAButton.setText('On')
                self.ChannelAButton.setStyleSheet('background-color : green')
                self.ChannelAState = 'On'
                self.ChannelAUpdate()
                self.ScanGateComboBoxFunc()

            elif self.ChannelAState == 'On':
                self.ChannelAButton.setText('Off')
                self.ChannelAButton.setStyleSheet('background-color : light grey')
                self.ChannelAState = 'Off'
                self.ChannelAUpdate()
                self.ScanGateComboBoxFunc()


     def ChannelBButtonPress(self):
         if self.MeasurementState == 'On':

            if self.ChannelBState == 'Off':
                self.ChannelBButton.setText('On')
                self.ChannelBButton.setStyleSheet('background-color : green')
                self.ChannelBState = 'On'
                self.ChannelBUpdate()
                self.ScanGateComboBoxFunc()

            elif self.ChannelBState == 'On':
                self.ChannelBButton.setText('Off')
                self.ChannelBButton.setStyleSheet('background-color : light grey')
                self.ChannelBState = 'Off'
                self.ChannelBUpdate()
                self.ScanGateComboBoxFunc()

     def ChannelCButtonPress(self):
         if self.MeasurementState == 'On':

            if self.ChannelCState == 'Off':
                self.ChannelCButton.setText('On')
                self.ChannelCButton.setStyleSheet('background-color : green')
                self.ChannelCState = 'On'
                self.ChannelCUpdate()
                self.ScanGateComboBoxFunc()

            elif self.ChannelCState == 'On':
                self.ChannelCButton.setText('Off')
                self.ChannelCButton.setStyleSheet('background-color : light grey')
                self.ChannelCState = 'Off'
                self.ChannelCUpdate()
                self.ScanGateComboBoxFunc()


     def ChannelDButtonPress(self):
         if self.MeasurementState == 'On':

            if self.ChannelDState == 'Off':
                self.ChannelDButton.setText('On')
                self.ChannelDButton.setStyleSheet('background-color : green')
                self.ChannelDState = 'On'
                self.ChannelDUpdate()
                self.ScanGateComboBoxFunc()

            elif self.ChannelDState == 'On':
                self.ChannelDButton.setText('Off')
                self.ChannelDButton.setStyleSheet('background-color : light grey')
                self.ChannelDState = 'Off'
                self.ChannelDUpdate()
                self.ScanGateComboBoxFunc()


     def ChannelAUpdate(self):

         if self.MeasurementState == 'On':

             self.channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
             self.ChACoupling = self.ChannelACouplingComboBox.currentText()
             if self.ChACoupling == 'AC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_AC"]
             elif self.ChACoupling == 'DC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]


             self.rangeIndex = self.ChARangeBox.currentIndex()
             self.chRange = ps.PS5000A_RANGE[self.ChannelVoltageRanges[self.rangeIndex]]
             self.ChannelAOffsetValue  = self.ChannelAOffsetSpinBox.value()

             print(chandle, self.channel, 1, self.ChACoupling, self.chRange, 0)
             if self.ChannelAState == 'On':
                 status["setChA"] = ps.ps5000aSetChannel(chandle, self.channel, 1, self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChA"])
             elif self.ChannelAState == 'Off':
                 status["setChA"] = ps.ps5000aSetChannel(chandle, self.channel, 0, self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChA"])


     def ChannelBUpdate(self):

         if self.MeasurementState == 'On' and self.ChannelBState == 'On':

             self.channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
             self.ChBCoupling = self.ChannelBCouplingComboBox.currentText()
             if self.ChBCoupling == 'AC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_AC"]
             elif self.ChBCoupling == 'DC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]

             self.rangeIndex = self.ChBRangeBox.currentIndex()
             self.chRange = ps.PS5000A_RANGE[self.ChannelVoltageRanges[self.rangeIndex]]
             self.ChannelBOffsetValue  = self.ChannelBOffsetSpinBox.value()

             print(chandle, self.channel, 1, self.ChBCoupling, self.chRange, 0)
             if self.ChannelAState == 'On':
                 status["setChB"] = ps.ps5000aSetChannel(chandle, self.channel, 1, self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChB"])
             elif self.ChannelBState == 'Off':
                 status["setChB"] = ps.ps5000aSetChannel(chandle, self.channel, 0, self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChB"])



     def ChannelCUpdate(self):

         if self.MeasurementState == 'On' and self.ChannelCState == 'On':

             self.channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_C"]
             self.ChCCoupling = self.ChannelCCouplingComboBox.currentText()
             if self.ChCCoupling == 'AC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_AC"]
             elif self.ChCCoupling == 'DC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]

             self.rangeIndex = self.ChCRangeBox.currentIndex()
             self.chRange = ps.PS5000A_RANGE[self.ChannelVoltageRanges[self.rangeIndex]]
             self.ChannelCOffsetValue  = self.ChannelCOffsetSpinBox.value()
             if self.ChannelAState == 'On':
                 status["setChC"] = ps.ps5000aSetChannel(chandle, self.channel, 1,self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChC"])
             elif self.ChannelCState == 'Off':
                 status["setChC"] = ps.ps5000aSetChannel(chandle, self.channel, 0,self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChC"])



     def ChannelDUpdate(self):

         if self.MeasurementState == 'On' and self.ChannelDState == 'On':

             self.channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_D"]
             self.ChDCoupling = self.ChannelDCouplingComboBox.currentText()
             if self.ChDCoupling == 'AC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_AC"]
             elif self.ChDCoupling == 'DC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]

             self.rangeIndex = self.ChDRangeBox.currentIndex()
             self.chRange = ps.PS5000A_RANGE[self.ChannelVoltageRanges[self.rangeIndex]]
             self.ChannelDOffsetValue  = self.ChannelDOffsetSpinBox.value()
             if self.ChannelDState == 'On':
                 status["setChD"] = ps.ps5000aSetChannel(chandle, self.channel, 1, self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChD"])
             elif self.ChannelDState == 'Off':
                 status["setChD"] = ps.ps5000aSetChannel(chandle, self.channel, 0, self.coupling_type, self.chRange, 0)
                 assert_pico_ok(status["setChD"])






     def mouseMoved(self,evt):
         pos = evt
         if self.psDataPlot.sceneBoundingRect().contains(pos):
             mousePoint = self.psDataPlot.plotItem.vb.mapSceneToView(pos)
             # self.mousecoordinatesdisplay.setText("<span style='font-size: 15pt'>X=%0.1f, <span style='color: black'>Y=%0.1f</span>" % (mousePoint.x(),mousePoint.y()))

         # self.psDataPlot.plotItem.vLine.setPos(mousePoint.x())
         # self.psDataPlot.plotItem.hLine.setPos(mousePoint.y())
         # print(mousePoint.x(),mousePoint.y())
         # global mpoint_x,mpoint_y
         self.mpoint_x = mousePoint.x()
         self.mpoint_y = mousePoint.y()
         # self.label = pg.TextItem('x = ' + str(mousePoint.x())+', y = ' + str(mousePoint.y()), anchor = (0,0), color = (0,0,255))
         # self.psDataPlot.addItem(self.label)
         # self.psDataPlot.LabelItem('a')
         # t_up.setPos(i + 0.5, -j + 0.5)
         # self.label.setText("<span style='font-size: 26pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>,   <span style='color: green'>y2=%0.1f</span>" % (mousePoint.x(), mousePoint.x(), mousePoint.x()))


     def UpdatePlot(self,data):

         self.data = data
         # self.vLine = pg.InfiniteLine(angle=90, movable=True)
         # self.hLine = pg.InfiniteLine(angle=0, movable=True)
         # self.psDataPlot.addItem(self.vLine, ignoreBounds=True)
         # self.psDataPlot.addItem(self.hLine, ignoreBounds=True)
         self.psDataPlot.setMouseTracking(True)

         self.psDataPlot.scene().sigMouseMoved.connect(self.mouseMoved)
         # self.label = pg.TextItem('blablalba', anchor = (0,0), color = (0,0,255))
         # self.psDataPlot.addItem(self.label)




         # self.psDataPlot.clear()

         if  self.ChannelAState == 'On':
             self.psDataPlot.plot(data[0,:],data[1,:] + float(self.ChannelAOffsetValue),pen=(0,0,255),clear = True)
             self.psScanPlot1.plot(data[0,:],data[1,:] + float(self.ChannelAOffsetValue),pen=(0,0,255),clear = True)
         if  self.ChannelBState == 'On':
             self.psDataPlot.plot(data[0,:],data[2,:]+ float(self.ChannelBOffsetValue),pen=(255,0,0))
             self.psScanPlot1.plot(data[0,:],data[2,:]+ float(self.ChannelBOffsetValue),pen=(255,0,0))
         # self.label.setPos(QtCore.QPointF(-0, 0.))
         # self.label.setText('sdfasdfasdfasdfasdfadfasd')
         self.label = pg.TextItem('x = ' + str(round(self.mpoint_x/1e6,5)) +' \u03BCs, y = ' + str(round(self.mpoint_y,2)) + 'mV', anchor = (0,0))
         self.psDataPlot.addItem(self.label)
         # self.label.updateTextPos()
         self.CheckAllGates()

         if self.ContinuousSaveMode == 'On':
             self.ContinuousSaveData()
             self.save_count+=1


         if self.psScanActive == 'On':
             0==0

             if self.psScanCount == 0:
                 self.ScanGateAvgData1 = []
                 self.ScanGateAvgData2 = []
                 self.ScanGateAvgData3 = []
                 self.ScanGateAvgData4 = []
                 self.ScanGateAvgData5 = []
                 self.ScanGateAvgData6 = []
                 self.ScanGateAvgData7 = []


             if self.ScanGateState1!='Off':
                 self.ScanGateAvgData1.append(self.ScanGateData(self.data, self.ScanRegion1, self.ScanGateCheckBoxState1))

             if self.ScanGateState2!='Off':
                 self.ScanGateAvgData2.append(self.ScanGateData(self.data, self.ScanRegion2, self.ScanGateCheckBoxState2))

             if self.ScanGateState3!='Off':
                 self.ScanGateAvgData3.append(self.ScanGateData(self.data, self.ScanRegion3, self.ScanGateCheckBoxState3))

             if self.ScanGateState4!='Off':
                 self.ScanGateAvgData4.append(self.ScanGateData(self.data, self.ScanRegion4, self.ScanGateCheckBoxState4))

             if self.ScanGateState5!='Off':
                 self.ScanGateAvgData5.append(self.ScanGateData(self.data, self.ScanRegion5, self.ScanGateCheckBoxState5))

             if self.ScanGateState6!='Off':
                 self.ScanGateAvgData6.append(self.ScanGateData(self.data, self.ScanRegion6, self.ScanGateCheckBoxState6))

             if self.ScanGateState7!='Off':
                 self.ScanGateAvgData7.append(self.ScanGateData(self.data, self.ScanRegion7, self.ScanGateCheckBoxState7))

             self.psScanCount+=1
             # print(self.psScanCount,self.ScanNAvg)


             if self.psScanCount==int(self.ScanNAvg):

                 self.psScanCount = 0

                 self.psScanPlot2.clear()

                 self.ScanGateAvgDataTotN.append(len(self.ScanGateAvgDataTotN)+1)
                 if self.ScanGateState1!='Off':
                     self.ScanGateAvgDataTot1.append(np.mean(self.ScanGateAvgData1))
                     self.ScanGateAvgDataTotError1.append(np.std(self.ScanGateAvgData1))
                     # print(self.ScanGateAvgDataTotError1)
                     self.psScanPlot2.plot(self.ScanGateAvgDataTotN,self.ScanGateAvgDataTot1,pen=self.ScanColors1[0],style = 'o')
                     self.ScanErrorbar1 = pg.ErrorBarItem(x = np.array(self.ScanGateAvgDataTotN), y= np.array(self.ScanGateAvgDataTot1), top = np.array(self.ScanGateAvgDataTotError1), bottom =np.array(self.ScanGateAvgDataTotError1),  pen=self.ScanColors1[0])
                     self.psScanPlot2.addItem( self.ScanErrorbar1)
                     print(self.ScanGateCheckBoxState1)

                 if self.ScanGateState2!='Off':
                     self.ScanGateAvgDataTot2.append(np.mean(self.ScanGateAvgData2))
                     self.ScanGateAvgDataTotError2.append(np.std(self.ScanGateAvgData2))
                     self.psScanPlot2.plot(self.ScanGateAvgDataTotN,self.ScanGateAvgDataTot2,pen=self.ScanColors1[1])
                     self.ScanErrorbar2 = pg.ErrorBarItem(x = np.array(self.ScanGateAvgDataTotN), y= np.array(self.ScanGateAvgDataTot2), top = np.array(self.ScanGateAvgDataTotError2), bottom =np.array(self.ScanGateAvgDataTotError2),  pen=self.ScanColors1[1])
                     self.psScanPlot2.addItem( self.ScanErrorbar2)


                 if self.ScanGateState3!='Off':
                     self.ScanGateAvgDataTot3.append(np.mean(self.ScanGateAvgData3))
                     self.ScanGateAvgDataTotError3.append(np.std(self.ScanGateAvgData3))
                     self.psScanPlot2.plot(self.ScanGateAvgDataTotN,self.ScanGateAvgDataTot3,pen=self.ScanColors1[2])
                     self.ScanErrorbar3 = pg.ErrorBarItem(x = np.array(self.ScanGateAvgDataTotN), y= np.array(self.ScanGateAvgDataTot3), top = np.array(self.ScanGateAvgDataTotError3), bottom =np.array(self.ScanGateAvgDataTotError3),  pen=self.ScanColors1[2])
                     self.psScanPlot2.addItem( self.ScanErrorbar3)

                 if self.ScanGateState4!='Off':
                     self.ScanGateAvgDataTot4.append(np.mean(self.ScanGateAvgData4))
                     self.ScanGateAvgDataTotError4.append(np.std(self.ScanGateAvgData4))
                     self.psScanPlot2.plot(self.ScanGateAvgDataTotN,self.ScanGateAvgDataTot4,pen=self.ScanColors1[3])
                     self.ScanErrorbar4 = pg.ErrorBarItem(x = np.array(self.ScanGateAvgDataTotN), y= np.array(self.ScanGateAvgDataTot4), top = np.array(self.ScanGateAvgDataTotError4), bottom =np.array(self.ScanGateAvgDataTotError4),  pen=self.ScanColors1[3])
                     self.psScanPlot2.addItem( self.ScanErrorbar4)

                 if self.ScanGateState5!='Off':
                     self.ScanGateAvgDataTot5.append(np.mean(self.ScanGateAvgData5))
                     self.ScanGateAvgDataTotError5.append(np.std(self.ScanGateAvgData5))
                     self.psScanPlot2.plot(self.ScanGateAvgDataTotN,self.ScanGateAvgDataTot5,pen=self.ScanColors1[4])
                     self.ScanErrorbar5 = pg.ErrorBarItem(x = np.array(self.ScanGateAvgDataTotN), y= np.array(self.ScanGateAvgDataTot5), top = np.array(self.ScanGateAvgDataTotError5), bottom =np.array(self.ScanGateAvgDataTotError5),  pen=self.ScanColors1[4])
                     self.psScanPlot2.addItem( self.ScanErrorbar5)


                 if self.ScanGateState6!='Off':
                     self.ScanGateAvgDataTot6.append(np.mean(self.ScanGateAvgData6))
                     self.ScanGateAvgDataTotError6.append(np.std(self.ScanGateAvgData6))
                     self.psScanPlot2.plot(self.ScanGateAvgDataTotN,self.ScanGateAvgDataTot6,pen=self.ScanColors1[5])
                     self.ScanErrorbar6 = pg.ErrorBarItem(x = np.array(self.ScanGateAvgDataTotN), y= np.array(self.ScanGateAvgDataTot6), top = np.array(self.ScanGateAvgDataTotError6), bottom =np.array(self.ScanGateAvgDataTotError6),  pen=self.ScanColors1[5])
                     self.psScanPlot2.addItem( self.ScanErrorbar6)

                 if self.ScanGateState7!='Off':
                     self.ScanGateAvgDataTot7.append(np.mean(self.ScanGateAvgData7))
                     self.ScanGateAvgDataTotError7.append(np.std(self.ScanGateAvgData7))
                     self.psScanPlot2.plot(self.ScanGateAvgDataTotN,self.ScanGateAvgDataTot7,pen=self.ScanColors1[6])
                     self.ScanErrorbar7 = pg.ErrorBarItem(x = np.array(self.ScanGateAvgDataTotN), y= np.array(self.ScanGateAvgDataTot7), top = np.array(self.ScanGateAvgDataTotError7), bottom =np.array(self.ScanGateAvgDataTotError7),  pen=self.ScanColors1[6])
                     self.psScanPlot2.addItem( self.ScanErrorbar7)


         if self.BinAvgState == 'On':
              if self.BinAvgCount == self.BinAvgN:
                  self.BinAvgCount = 0
                  self.BinAvgData = np.zeros(np.array(self.data.shape))


              self.BinAvgData = (self.BinAvgData*self.BinAvgCount+self.data)/(self.BinAvgCount+1)
              self.BinAvgData[0,:] = self.data[0,:]
              self.BinAvgCount += 1
              print(self.BinAvgCount)

              if  self.ChannelAState == 'On':
                  self.BinnedData = binning_function(self.BinAvgData[[0,1],:],self.BinningN)
                  self.BinAvgPlot.plot(self.BinnedData[0,:],self.BinnedData[1,:] + float(self.ChannelAOffsetValue),pen=(0,0,255),clear = True)







     def SaveWaveformData (self):

          file , check = QFileDialog.getSaveFileName(None, "QFileDialog getSaveFileName() Demo",
                                               "", "All Files (*);;HDF5 files (*.h5);;")
          if check:
              print(file)
              ch_count = 1
              hf  = h5py.File(file,'w')
              hf.create_dataset('Timings', data = self.data[0,:])

              if  self.ChannelAState == 'On':
                  hf.create_dataset('ChA_data', data = self.data[ch_count,:])
                  ch_count+=1
              if  self.ChannelBState == 'On':
                  hf.create_dataset('ChB_data', data = self.data[ch_count,:])
                  ch_count+=1
              if  self.ChannelCState == 'On':
                  hf.create_dataset('ChC_data', data = self.data[ch_count,:])
                  ch_count+=1
              if  self.ChannelDState == 'On':
                  hf.create_dataset('ChD_data', data = self.data[ch_count,:])
                  ch_count+=1

              hf.close()




     def ContinuousSaveButton(self):

         if self.MeasurementState=='On':
             if self.ContinuousSaveMode == 'Off':

                 self.save_count = 0
                 self.ContinuousSaveMode = 'On'
                 self.current_datetime = datetime.now()
                 self.folder = self.ContinuousSaveDataLocation + '/'+self.current_datetime.strftime('%d%m%Y')
                 self.folder = self.folder.replace('/','\\')
                 if os.path.exists(self.folder)==False:
                    os.makedirs(self.folder)
                 self.filename = self.current_datetime.strftime('%H%M')
                 self.WaveformContinousSave.setStyleSheet('background-color : green')


             elif self.ContinuousSaveMode == 'On':
                 self.ContinuousSaveMode = 'Off'
                 self.WaveformContinousSave.setStyleSheet('background-color : light grey')


     def ContinuousSaveFolderButton(self):

          self.ContinuousSaveDataLocation = str(QFileDialog.getExistingDirectory(self, "Select Directory"))

          # print(self.ContinuousSaveDataLocation)

     def ContinuousSaveData(self):


        ch_count = 1

        # print(self.folder+'/'+self.filename+'_'+str(self.save_count) +'.h5')
        hf  = h5py.File(self.folder+'\\'+self.filename+'_'+str(self.save_count) +'.h5','w')
        hf.create_dataset('Timings', data = self.data[0,:])

        if  self.ChannelAState == 'On':
              hf.create_dataset('ChA_data', data = self.data[ch_count,:])
              ch_count+=1
        if  self.ChannelBState == 'On':
            hf.create_dataset('ChB_data', data = self.data[ch_count,:])
            ch_count+=1
        if  self.ChannelCState == 'On':
            hf.create_dataset('ChC_data', data = self.data[ch_count,:])
            ch_count+=1
        if  self.ChannelDState == 'On':
            hf.create_dataset('ChD_data', data = self.data[ch_count,:])
            ch_count+=1

        hf.close()





     def ScanButtonFunc(self):

         if self.MeasurementState == 'On':

            if self.psScanActive == 'Off':
                self.ScanGateButton.setText('Scanning')
                self.ScanGateButton.setStyleSheet('background-color : green')
                self.psScanActive = 'On'

                self.ScanGateAvgDataTotN = []

                if self.ScanGatecheckBox1.isChecked() == True:
                    self.ScanGateCheckBoxState1 = self.ScanGatecomboBox1.currentIndex()
                    self.ScanGateState1 = 'On'
                    self.ScanGateAvgDataTot1 = []
                    self.ScanGateAvgDataTotError1 = []
                if self.ScanGatecheckBox2.isChecked() == True:
                    self.ScanGateCheckBoxState2 = self.ScanGatecomboBox2.currentIndex()
                    self.ScanGateState2 = 'On'
                    self.ScanGateAvgDataTot2 = []
                    self.ScanGateAvgDataTotError2 = []
                if self.ScanGatecheckBox3.isChecked() == True:
                    self.ScanGateCheckBoxState3 = self.ScanGatecomboBox3.currentIndex()
                    self.ScanGateState3 = 'On'
                    self.ScanGateAvgDataTot3 = []
                    self.ScanGateAvgDataTotError3 = []
                if self.ScanGatecheckBox4.isChecked() == True:
                    self.ScanGateCheckBoxState4 = self.ScanGatecomboBox4.currentIndex()
                    self.ScanGateState4 = 'On'
                    self.ScanGateAvgDataTot4 = []
                    self.ScanGateAvgDataTotError4 = []
                if self.ScanGatecheckBox5.isChecked() == True:
                    self.ScanGateCheckBoxState5 = self.ScanGatecomboBox5.currentIndex()
                    self.ScanGateState5 = 'On'
                    self.ScanGateAvgDataTot5 = []
                    self.ScanGateAvgDataTotError5 = []
                if self.ScanGatecheckBox6.isChecked() == True:
                    self.ScanGateCheckBoxState6 = self.ScanGatecomboBox6.currentIndex()
                    self.ScanGateState6 = 'On'
                    self.ScanGateAvgDataTot6 = []
                    self.ScanGateAvgDataTotError6 = []
                if self.ScanGatecheckBox7.isChecked() == True:
                    self.ScanGateCheckBoxState7 = self.ScanGatecomboBox7.currentIndex()
                    self.ScanGateState7 = 'On'
                    self.ScanGateAvgDataTot7 = []
                    self.ScanGateAvgDataTotError7 = []

                self.ScanNAvg = self.NAvgScanGatespinBox.value()
                    # print(self.data[self.ScanGateState1,:])





            elif self.psScanActive == 'On':
                self.ScanGateButton.setText('Scan')
                self.ScanGateButton.setStyleSheet('background-color : light grey')
                self.psScanActive = 'Off'

                self.ScanGateState1 = 'Off'
                self.ScanGateState2 = 'Off'
                self.ScanGateState3 = 'Off'
                self.ScanGateState4 = 'Off'
                self.ScanGateState5 = 'Off'
                self.ScanGateState6 = 'Off'
                self.ScanGateState7 = 'Off'


     # def ChannelACouplingComboBoxChange(self):

     #     if self.MeasurementState == 'On' and self.ChannelAState == 'On':
     #         self.channel = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
     #         self.ChannelACoupling = self.ChannelACouplingComboBox.currentText()
     #         if self.ChannelACoupling == 'DC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_DC"]
     #         elif self.ChannelACoupling == 'AC': self.coupling_type = ps.PS5000A_COUPLING["PS5000A_AC"]




     def ScanGateCheckBoxFunc(self, gate, ScanRegion):

         if gate.isChecked() == True:
              # ScanRegion.setRegion([self.data[0,0],self.data[0,-1]/10])
              self.psScanPlot1.addItem(ScanRegion, ignoreBounds=True)
         else:
              self.psScanPlot1.removeItem(ScanRegion)


     def CheckAllGates(self):
         self.ScanGateCheckBoxFunc(self.ScanGatecheckBox1,self.ScanRegion1)
         self.ScanGateCheckBoxFunc(self.ScanGatecheckBox2,self.ScanRegion2)
         self.ScanGateCheckBoxFunc(self.ScanGatecheckBox3,self.ScanRegion3)
         self.ScanGateCheckBoxFunc(self.ScanGatecheckBox4,self.ScanRegion4)
         self.ScanGateCheckBoxFunc(self.ScanGatecheckBox5,self.ScanRegion5)
         self.ScanGateCheckBoxFunc(self.ScanGatecheckBox6,self.ScanRegion6)
         self.ScanGateCheckBoxFunc(self.ScanGatecheckBox7,self.ScanRegion7)


     def ScanGateComboBoxFunc(self):
        self.ScanGatecomboBox1.clear()
        self.ScanGatecomboBox2.clear()
        self.ScanGatecomboBox3.clear()
        self.ScanGatecomboBox4.clear()
        self.ScanGatecomboBox5.clear()
        self.ScanGatecomboBox6.clear()
        self.ScanGatecomboBox7.clear()

        if self.ChannelAState == 'On':
             self.ScanGatecomboBox1.addItem('Ch A')
             self.ScanGatecomboBox2.addItem('Ch A')
             self.ScanGatecomboBox3.addItem('Ch A')
             self.ScanGatecomboBox4.addItem('Ch A')
             self.ScanGatecomboBox5.addItem('Ch A')
             self.ScanGatecomboBox6.addItem('Ch A')
             self.ScanGatecomboBox7.addItem('Ch A')

        if self.ChannelBState == 'On':
             self.ScanGatecomboBox1.addItem('Ch B')
             self.ScanGatecomboBox2.addItem('Ch B')
             self.ScanGatecomboBox3.addItem('Ch B')
             self.ScanGatecomboBox4.addItem('Ch B')
             self.ScanGatecomboBox5.addItem('Ch B')
             self.ScanGatecomboBox6.addItem('Ch B')
             self.ScanGatecomboBox7.addItem('Ch B')


        if self.ChannelCState == 'On':
             self.ScanGatecomboBox1.addItem('Ch C')
             self.ScanGatecomboBox2.addItem('Ch C')
             self.ScanGatecomboBox3.addItem('Ch C')
             self.ScanGatecomboBox4.addItem('Ch C')
             self.ScanGatecomboBox5.addItem('Ch C')
             self.ScanGatecomboBox6.addItem('Ch C')
             self.ScanGatecomboBox7.addItem('Ch C')

        if self.ChannelDState == 'On':
             self.ScanGatecomboBox1.addItem('Ch D')
             self.ScanGatecomboBox2.addItem('Ch D')
             self.ScanGatecomboBox3.addItem('Ch D')
             self.ScanGatecomboBox4.addItem('Ch D')
             self.ScanGatecomboBox5.addItem('Ch D')
             self.ScanGatecomboBox6.addItem('Ch D')
             self.ScanGatecomboBox7.addItem('Ch D')

     def ScanGateData(self, data, ScanRegion, ScanGateCheckBoxState):

         gate = ScanRegion.getRegion()

         # print(data[0,:])
         # print(gate[0])
         idx_down = np.searchsorted(data[0,:],gate[0])
         idx_up = np.searchsorted(data[0,:],gate[1])

         # return np.sum(data[ScanGateState1+1,idx_down:idx_up])/np.sum(data[0,idx_down:idx_up])
         return np.sum(data[ScanGateCheckBoxState+1,idx_down:idx_up])/(idx_up-idx_down)



     def BinAvgButton(self):
         0==0
         if self.MeasurementState == 'On':
             if self.BinAvgState == 'Off':
                self.StartBinningButton.setText('Binning')
                self.StartBinningButton.setStyleSheet('background-color : green')
                self.BinAvgState = 'On'
                self.BinAvgData = np.zeros(np.array(self.data).shape)
                self.BinningN = self.NBinsSpinBox.value()
                self.BinAvgN = self.NAvgSpinBox.value()


             elif self.BinAvgState == 'On':
                self.StartBinningButton.setText('Start')
                self.StartBinningButton.setStyleSheet('background-color : light grey')
                self.BinAvgState = 'Off'







class psMeasureThread1(QObject):


     data_for_transfer = pyqtSignal(object)



     def StartTimer(self):


         self.status = {}




         self._timer = QTimer(self)
         self._timer.timeout.connect(self.LoopFunc)
         self._timer.start(20)




     def LoopFunc(self):
         # self.data = np.zeros((2,1000))
         # self.data[0,:] = np.linspace(0,2*np.pi,1000)
         # self.data[1,:] = np.sin(10*self.data[0,:]+np.random.uniform(0,2*np.pi))
         #time.sleep(0.05)
         # self.data_for_transfer.emit(self.data)

         self.NTotSamples = 100000
         self.preTriggerSamples = math.floor(self.NTotSamples/10)
         self.postTriggerSamples = self.NTotSamples - self.preTriggerSamples
         self.maxSamples = self.preTriggerSamples + self.postTriggerSamples
         self.timebase = 8
         self.status["runBlock"] = ps.ps5000aRunBlock(chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, None, 0, None, None)
         assert_pico_ok(self.status["runBlock"])

         self.timeIntervalns = ctypes.c_float()
         self.returnedMaxSamples = ctypes.c_int32()
         self.status["getTimebase2"] = ps.ps5000aGetTimebase2(chandle, self.timebase, self.maxSamples, ctypes.byref(self.timeIntervalns), ctypes.byref(self.returnedMaxSamples), 0)
         assert_pico_ok(self.status["getTimebase2"])
         self.ready = ctypes.c_int16(0)
         self.check = ctypes.c_int16(0)

         self.bufferAMax = (ctypes.c_int16 * self.maxSamples)()
         self.bufferAMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example
         self.bufferBMax = (ctypes.c_int16 * self.maxSamples)()
         self.bufferBMin = (ctypes.c_int16 * self.maxSamples)() # used for downsampling which isn't in the scope of this example

         self.status["runBlock"] = ps.ps5000aRunBlock(chandle, self.preTriggerSamples, self.postTriggerSamples, self.timebase, None, 0, None, None)
         assert_pico_ok(self.status["runBlock"])




     # Create time data


         self.maxADC = ctypes.c_int16()
         self.status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(self.maxADC))
         assert_pico_ok(self.status["maximumValue"])

         self.chARange = ps.PS5000A_RANGE["PS5000A_20V"]
         self.chBRange = ps.PS5000A_RANGE["PS5000A_20V"]
         self.source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_A"]
         self.status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(chandle, self.source, ctypes.byref(self.bufferAMax), ctypes.byref(self.bufferAMin), self.maxSamples, 0, 0)
         assert_pico_ok(self.status["setDataBuffersA"])

         self.source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
         self.status["setDataBuffersB"] = ps.ps5000aSetDataBuffers(chandle, self.source, ctypes.byref(self.bufferBMax), ctypes.byref(self.bufferBMin), self.maxSamples, 0, 0)
         assert_pico_ok(self.status["setDataBuffersB"])

         self.overflow = ctypes.c_int16()
         # create converted type maxSamples
         self.cmaxSamples = ctypes.c_int32(self.maxSamples)
         self.time = np.linspace(0, (self.cmaxSamples.value - 1) * self.timeIntervalns.value, self.cmaxSamples.value)

         while self.ready.value == self.check.value:
             self.status["isReady"] = ps.ps5000aIsReady(chandle, ctypes.byref(self.ready))
         self.status["getValues"] = ps.ps5000aGetValues(chandle, 0, ctypes.byref(self.cmaxSamples), 0, 0, 0, ctypes.byref(self.overflow))
         assert_pico_ok(self.status["getValues"])

         self.adc2mVChAMax =  adc2mV(self.bufferAMax, self.chARange, self.maxADC)
         self.adc2mVChBMax =  adc2mV(self.bufferBMax, self.chBRange, self.maxADC)
         # time.sleep(0.1)
         self.data = np.vstack((self.time, self.adc2mVChAMax, self.adc2mVChBMax))
         self.data_for_transfer.emit(self.data)

     def DataFrom_GUI(self,data):
         print(data)







class psSaveData(QThread):

     def __init__(self):
        QThread.__init__(self)

class psContinuousSaveData(QThread):

     def __init__(self):
        QThread.__init__(self)

# @njit
def binning_function(data, bins):
    return_data = []
    d = 0
    for i in range(0,data.shape[1]-bins, bins):
        d=0
        for j in range(i, i+bins):
            d = d + data[1,j]
        return_data.append([data[0,i], d])
    return np.array(return_data).T/bins


def main():
    app = QtWidgets.QApplication(sys.argv)
    # QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Plastique'))
    form = GuiThread()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
#
