#favor的勾选
#position必须是数字的规范化
#停盘的记为灰色
#Favor列表移动
#分类添加Favor列表
#分类进行智能提取并标注颜色


import datetime
from ftplib import FTP
import pandas
import pandas as pd
import efinance
import glob
from joblib import Parallel,delayed

import ZBaseFunc
import Zfinance
import ZfinanceCfg
from ZfinanceCfg import TableColor
import ZFavorEditor
import ZDataClean
from time import sleep
import pathlib
import time

import PySide2.QtWidgets ,PySide2.QtWidgets ,PySide2.QtGui
from PySide2.QtWidgets import QApplication, QMessageBox,QFileDialog,QCheckBox
from PySide2.QtWidgets import QButtonGroup,QSlider,QLabel,QRadioButton,QTableWidget,QHeaderView
from PySide2.QtUiTools  import QUiLoader
from PySide2.QtGui import QFont
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
import datetime

import json
import os
import  threading
from threading import Thread



DownloadAbortFlag = True
Process = 0
ProcessLen = 100
TableInitFlag = False
GlobalMainUIx = 1
CfgDict = dict()
TableWidgetChannel = None
DownloadProcessBarChannel = None
VPN = None

TempColorYellow = 1
TempColorRed = 2
TempColorGreen = 3
TempColorGray = 4

ScrollBarPosition = 0

GlobalAPP = None
GlobalProcessCnt = 0
class DownloadUIProc:
    def __init__(self,GlobalUI,APP,GlobalFavorEditorUI):
        global GlobalMainUI,CfgDict,TableWidgetChannel,DownloadProcessBarChannel,GlobalDLUI,GlobalAPP
        self.GlobalMainUI = GlobalUI
        GlobalAPP = APP
        GlobalMainUI = GlobalUI
        self.DownloadCfgUI = QUiLoader().load('UIDesign/DownloadConfig.ui')


        self.DataCleanUIx = ZDataClean.DataCleanUIProc(GlobalAPP)
        GlobalDLUI = self.DownloadCfgUI
        ###################发射定义##############################
        TableWidgetChannel = SignalThreadChannel()
        DownloadProcessBarChannel  = SignalThreadChannel()

        TableWidgetChannel.TableSignal.connect(UpdateTableWidget)
        DownloadProcessBarChannel.PBarSignal.connect(UpdateDownloadProcessBarWidget)

        #######################################################
        GlobalMainUI.SymbolsDownloadProgressBar.setValue(0)

        self.DownloadCfgUI.SymbolsListProgressBar.setValue(0)

        self.GlobalMainUI.SymbolsDownloadConfig.clicked.connect(self.HandleDownloadConfig)
        self.DownloadCfgUI.CancelDownload.clicked.connect(self.CloseDownloadCfgUI)
        self.DownloadCfgUI.ConfirmDownload.clicked.connect(self.HandleConfirmDownload)
        self.DownloadCfgUI.OpenDLConfig.clicked.connect(self.HandleOpenDLConfig)
        self.DownloadCfgUI.SaveDLConfig.clicked.connect(self.HandleSaveDLConfig)
        self.DownloadCfgUI.EditFavorList.clicked.connect(GlobalFavorEditorUI.handleFavorEditor)

        self.DownloadCfgUI.DataClean.clicked.connect(self.handleDataCleanUI)
        self.DownloadCfgUI.DataClean.clicked.connect(self.DataCleanUIx.handleDataCleanUI)

        self.GlobalMainUI.SymbolsDownloadStart.clicked.connect(HandleDownloadStart)
        self.GlobalMainUI.SymbolsDownloadAbort.clicked.connect(HandleDownloadAbort)



        self.DownloadCfgUI.UpdateTickerList.clicked.connect(self.HandleUpdateTickerList)

        self.DownloadCfgUI.DownloadPeriod.sliderMoved.connect(self.HandleDownloadPeriod)
        self.DownloadCfgUI.DownloadPeriod.valueChanged.connect(self.HandleDownloadPeriod)

        self.DownloadCfgUI.FavorList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.DownloadCfgUI.FavorList.customContextMenuRequested[QPoint].connect(self.FavorListChechboxSelectMenu)

        self.DLUIInit = False

        # ConfigFilePathName = os.getcwd()+'\\Data\\00_Config\\Default.ZFCfg'
        # try:
        #     with open(ConfigFilePathName,'r') as load_f:
        #         CfgDict = json.load(load_f)
        #     ZBaseFunc.Log2LogBox('Load Default Download Config success!!')
        # except:
        #     ZBaseFunc.Log2LogBox('Load Default Download Config Fail!!')
        #     pass

    def FavorListChechboxSelectMenu(self):
        popMenu = QMenu()
        if self.DownloadCfgUI.FavorList.currentItem().parent() == None:
            SelectAll  = popMenu.addAction('全选')
            CancelAll  = popMenu.addAction("取消全选")

            CancelAll.triggered.connect(self.CancelAllChildrenInFavorList)
            SelectAll.triggered.connect(self.SelectAllChildrenInFavorList)
        popMenu.exec_(QCursor.pos())
        return

    def CancelAllChildrenInFavorList(self):
        self.DownloadCfgUI.FavorList.currentItem().setCheckState(0,PySide2.QtCore.Qt.CheckState.Unchecked)
        cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.FavorList.currentItem())
        ChildCnt = cursor.value().childCount()
        cursor = cursor.__iadd__(1)

        for i in range(ChildCnt):
            cursor.value().setCheckState(0,PySide2.QtCore.Qt.CheckState.Unchecked)
            cursor = cursor.__iadd__(1)
    def SelectAllChildrenInFavorList(self):
        self.DownloadCfgUI.FavorList.currentItem().setCheckState(0,PySide2.QtCore.Qt.CheckState.Checked)
        cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.FavorList.currentItem())
        ChildCnt = cursor.value().childCount()
        cursor = cursor.__iadd__(1)

        for i in range(ChildCnt):
            cursor.value().setCheckState(0,PySide2.QtCore.Qt.CheckState.Checked)
            cursor = cursor.__iadd__(1)

    def handleDataCleanUI(self):
        print('xx')

    def HandleUpdateTickerList(self):

        global GlobalAPP
        self.DownloadCfgUI.SymbolsListProgressBar.setValue(0)
        US = efinance.stock.get_realtime_quotes("美股")
        self.DownloadCfgUI.SymbolsListProgressBar.setValue(30)
        HK = efinance.stock.get_realtime_quotes("港股")
        self.DownloadCfgUI.SymbolsListProgressBar.setValue(60)
        CN = efinance.stock.get_realtime_quotes("沪深A股")
        self.DownloadCfgUI.SymbolsListProgressBar.setValue(90)

        US = US[~US['总市值'].isin(["-"])]
        HK = HK[~HK['总市值'].isin(["-"])]
        CN = CN[~CN['总市值'].isin(["-"])]

        US.to_csv("Data/00_Config/USTickerList.csv")
        HK.to_csv("Data/00_Config/HKTickerList.csv")
        CN.to_csv("Data/00_Config/CNTickerList.csv")
        self.DownloadCfgUI.SymbolsListProgressBar.setValue(100)

        #
        #
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(0)
        # self.DownloadCfgUI.UpdateTickerList.setDisabled(True)
        # GlobalAPP.processEvents()
        # ftp = FTP()
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(10)
        # ftp.connect(host='ftp.nasdaqtrader.com', port=21, timeout=10)
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(20)
        # ftp.login(user=None, passwd=None)
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(40)
        # fNasdaq = open('Data/00_Config/NasdaqTickerList.csv', 'wb')
        # fNYSEAMEX = open('Data/00_Config/NyseAmexTickerList.csv', 'wb')
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(50)
        # ftp.cwd('/Symboldirectory/')
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(60)
        # ftp.retrbinary('RETR nasdaqlisted.txt', fNasdaq.write)
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(70)
        # ftp.retrbinary('RETR otherlisted.txt', fNYSEAMEX.write)
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(80)
        # fNasdaq.close()
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(90)
        # fNYSEAMEX.close()
        # self.DownloadCfgUI.SymbolsListProgressBar.setValue(100)
        # self.DownloadCfgUI.UpdateTickerList.setDisabled(False)

    def HandleDownloadPeriod(self):
        DownloadPeriod_x = self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()]
        self.DownloadCfgUI.ShowPeriod.setText(self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()])
      #  QLabel.setText()

    def LoadSelectMarket(self,SelectList):
        SelectList.setColumnCount(2)
        SelectList.setHeaderLabels(('Market', 'Comment', 'Rule'))

        for Key, Value in ZfinanceCfg.ExchargeMarket.items():
            root = QTreeWidgetItem(SelectList)
            root.setText(0, Key)
            root.setText(1, Value[0])
            root.setText(2, Value[1])
            root.setCheckState(0, Qt.Unchecked)
        SelectList.addTopLevelItem(root)
        SelectList.setCurrentItem((SelectList.topLevelItem(0)))

    def HandleDownloadConfig(self):
        ZFavorEditor.LoadFavorListCfg(self.DownloadCfgUI.FavorList, CheckBox=True)

        self.DownloadCfgUI.show()
        self.PeriodDictList =[]
        for key,value in ZfinanceCfg.Period2DayLenthDict.items():
            self.PeriodDictList.append(key)

        self.DownloadCfgUI.DownloadPeriod.setMaximum(len(self.PeriodDictList)-1)
        self.DownloadCfgUI.DownloadPeriod.setMinimum(0)
        self.DownloadCfgUI.DownloadPeriod.setTickInterval(1)
        self.DownloadCfgUI.ShowPeriod.setText(self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()])
        if(not self.DLUIInit):
            self.DownloadCfgUI.MulitThreadDL.addItems(ZfinanceCfg.MulitThreadList_c)
            self.DownloadCfgUI.SkipPeriod.addItems(ZfinanceCfg.SkipPeriodList_c)
            self.DownloadCfgUI.ReConnect.addItems(ZfinanceCfg.ReConnectList_c)
            self.DownloadCfgUI.TimeOut.addItems(ZfinanceCfg.TimeOutList_c)
            self.DownloadCfgUI.DownloadAPI.addItems(ZfinanceCfg.DownloadAPIList_c)

            self.HandleOpenDLConfig(Default=True)
            self.DLUIInit = True




    def HandleConfirmDownload(self):

        cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.MarketSelector)     ##########刷新选择菜单
        while cursor.value():
            Temp = cursor.value()
            if Temp.checkState(0):
                CfgDict['EX_'+Temp.text(0)+'_x'] = True
            else:
                CfgDict['EX_' + Temp.text(0) + '_x'] = False
            cursor = cursor.__iadd__(1)
        CfgDict['List_Favor_x']  = CfgDict['EX_FAVOR_x']

        CfgDict['Intervial_1Day_x']     = self.DownloadCfgUI.Intervial_1Day.isChecked()
        CfgDict['Intervial_1h_x']       = self.DownloadCfgUI.Intervial_1h.isChecked()
        CfgDict['Intervial_30min_x']    = self.DownloadCfgUI.Intervial_30min.isChecked()
        CfgDict['Intervial_15min_x']    = self.DownloadCfgUI.Intervial_15min.isChecked()
        CfgDict['Intervial_5min_x']     = self.DownloadCfgUI.Intervial_5min.isChecked()
        CfgDict['Intervial_1min_x']     = self.DownloadCfgUI.Intervial_1min.isChecked()

        # Info Financials Balancesheet Cashflow Dividends Splits
        CfgDict['FunAna_Info_x']  = self.DownloadCfgUI.FunAna_Info.isChecked()
        CfgDict['FunAna_Financials_x']  = self.DownloadCfgUI.FunAna_Financials.isChecked()
        CfgDict['FunAna_Balancesheet_x']  = self.DownloadCfgUI.FunAna_Balancesheet.isChecked()
        CfgDict['FunAna_Cashflow_x']  = self.DownloadCfgUI.FunAna_Cashflow.isChecked()
        CfgDict['FunAna_Dividends_x']  = self.DownloadCfgUI.FunAna_Dividends.isChecked()
        CfgDict['FunAna_Splits_x']  = self.DownloadCfgUI.FunAna_Splits.isChecked()


        CfgDict['DownloadPeriod_x'] = self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()]

        CfgDict['MulitThreadDL_x']  = int(self.DownloadCfgUI.MulitThreadDL.currentText())
        CfgDict['ReConnectCnt_x']   = int(self.DownloadCfgUI.ReConnect.currentText())
        CfgDict['TimeOut_x']        = int(self.DownloadCfgUI.TimeOut.currentText())

        CfgDict['DownloadAPI_x'] =  self.DownloadCfgUI.DownloadAPI.currentText()
        CfgDict['ProxyEnable_x']      = self.DownloadCfgUI.ProxyEnable.isChecked()
        CfgDict['ProxyIP_x']        = self.DownloadCfgUI.ProxyIP.text()
        CfgDict['ProxyPort_x']      = self.DownloadCfgUI.ProxyPort.text()

        CfgDict['SkipNG_x']      = self.DownloadCfgUI.SkipNG.isChecked()
        CfgDict['SkipPeriod_x']  = int(self.DownloadCfgUI.SkipPeriod.currentText())

        self.DownloadCfgUI.close()

    def HandleSaveDLConfig(self):


        cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.MarketSelector)
        while cursor.value():
            Temp = cursor.value()
            if Temp.checkState(0):
                CfgDict['EX_'+Temp.text(0)+'_x'] = True
            else:
                CfgDict['EX_' + Temp.text(0) + '_x'] = False
            cursor = cursor.__iadd__(1)

        CfgDict['List_Favor_x']  = CfgDict['EX_FAVOR_x']

        CfgDict['Intervial_1Day_x']  = self.DownloadCfgUI.Intervial_1Day.isChecked()
        CfgDict['Intervial_1h_x']  = self.DownloadCfgUI.Intervial_1h.isChecked()
        CfgDict['Intervial_30min_x']  = self.DownloadCfgUI.Intervial_30min.isChecked()
        CfgDict['Intervial_15min_x']  = self.DownloadCfgUI.Intervial_15min.isChecked()
        CfgDict['Intervial_5min_x']  = self.DownloadCfgUI.Intervial_5min.isChecked()
        CfgDict['Intervial_1min_x']  = self.DownloadCfgUI.Intervial_1min.isChecked()

        CfgDict['FunAna_Info_x']  = self.DownloadCfgUI.FunAna_Info.isChecked()
        CfgDict['FunAna_Financials_x']  = self.DownloadCfgUI.FunAna_Financials.isChecked()
        CfgDict['FunAna_Balancesheet_x']  = self.DownloadCfgUI.FunAna_Balancesheet.isChecked()
        CfgDict['FunAna_Cashflow_x']  = self.DownloadCfgUI.FunAna_Cashflow.isChecked()
        CfgDict['FunAna_Dividends_x']  = self.DownloadCfgUI.FunAna_Dividends.isChecked()
        CfgDict['FunAna_Splits_x']  = self.DownloadCfgUI.FunAna_Splits.isChecked()

        CfgDict['DownloadPeriod_x'] = self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()]

        CfgDict['MulitThreadDL_x']  = int(self.DownloadCfgUI.MulitThreadDL.currentText())
        CfgDict['ReConnectCnt_x']   = int(self.DownloadCfgUI.ReConnect.currentText())
        CfgDict['TimeOut_x']        = int(self.DownloadCfgUI.TimeOut.currentText())

        CfgDict['DownloadAPI_x']    = self.DownloadCfgUI.DownloadAPI.currentText()
        CfgDict['ProxyEnable_x']      = self.DownloadCfgUI.ProxyEnable.isChecked()
        CfgDict['ProxyIP_x']        = self.DownloadCfgUI.ProxyIP.text()
        CfgDict['ProxyPort_x']      = self.DownloadCfgUI.ProxyPort.text()

        CfgDict['SkipPeriod_x']  = int(self.DownloadCfgUI.SkipPeriod.currentText())
        CfgDict['SkipNG_x']      = self.DownloadCfgUI.SkipNG.isChecked()

        ConfigFilePathName ,ok = QFileDialog.getSaveFileName(None, "配置文件保存",'Data/00_Config','ZfinanceDownloadCfg (*.ZFdl)')

        if ConfigFilePathName == "":
            return

        with open(ConfigFilePathName, "w") as f:
            json.dump(CfgDict, f,indent=1)
        return

    def HandleOpenDLConfig(self,Default = False):
        if Default:
            ConfigFilePathName = 'Data/00_Config/DefaultDownload.ZFdl'
            if(not os.path.exists(ConfigFilePathName)):

                self.DownloadCfgUI.MarketSelector.setColumnCount(2)
                self.DownloadCfgUI.MarketSelector.setHeaderLabels(('Market', 'Comment', 'Rule'))

                for Key, Value in ZfinanceCfg.ExchargeMarket.items():
                    root = QTreeWidgetItem(self.DownloadCfgUI.MarketSelector)
                    root.setText(0, Key)
                    root.setText(1, Value[0])
                    root.setText(2, Value[1])
                    root.setCheckState(0, Qt.Unchecked)
                self.DownloadCfgUI.MarketSelector.addTopLevelItem(root)
                self.DownloadCfgUI.MarketSelector.setCurrentItem((self.DownloadCfgUI.MarketSelector.topLevelItem(0)))

                return
        else:
            ConfigFilePathName ,ok= QFileDialog.getOpenFileName(None, "选择配置文件",'Data/00_Config','ZfinanceDownloadCfg (*.ZFdl)')
            if ConfigFilePathName == "":
                return

        with open(ConfigFilePathName, 'r') as load_f:
            CfgDict = json.load(load_f)
        try:

            self.DownloadCfgUI.Intervial_1Day.setChecked(CfgDict['Intervial_1Day_x'])
            self.DownloadCfgUI.Intervial_1h.setChecked(CfgDict['Intervial_1h_x'])
            self.DownloadCfgUI.Intervial_30min.setChecked(CfgDict['Intervial_30min_x'])
            self.DownloadCfgUI.Intervial_15min.setChecked(CfgDict['Intervial_15min_x'] )
            self.DownloadCfgUI.Intervial_5min.setChecked(CfgDict['Intervial_5min_x'])
            self.DownloadCfgUI.Intervial_1min.setChecked(CfgDict['Intervial_1min_x'])

            self.DownloadCfgUI.FunAna_Info.setChecked(CfgDict['FunAna_Info_x'])
            self.DownloadCfgUI.FunAna_Financials.setChecked(CfgDict['FunAna_Financials_x'])
            self.DownloadCfgUI.FunAna_Balancesheet.setChecked(CfgDict['FunAna_Balancesheet_x'])
            self.DownloadCfgUI.FunAna_Cashflow.setChecked(CfgDict['FunAna_Cashflow_x'])
            self.DownloadCfgUI.FunAna_Dividends.setChecked(CfgDict['FunAna_Dividends_x'])
            self.DownloadCfgUI.FunAna_Splits.setChecked(CfgDict['FunAna_Splits_x'])

            self.DownloadCfgUI.DownloadPeriod.setValue(self.PeriodDictList.index(CfgDict['DownloadPeriod_x']))

            self.DownloadCfgUI.MulitThreadDL.setCurrentIndex(ZfinanceCfg.MulitThreadList_c.index(str(CfgDict['MulitThreadDL_x'])))
            self.DownloadCfgUI.ReConnect.setCurrentIndex(ZfinanceCfg.ReConnectList_c.index(str(CfgDict['ReConnectCnt_x'])))
            self.DownloadCfgUI.TimeOut.setCurrentIndex(ZfinanceCfg.TimeOutList_c.index(str(CfgDict['TimeOut_x'])))

            self.DownloadCfgUI.DownloadAPI.setCurrentIndex(ZfinanceCfg.DownloadAPIList_c.index(str(CfgDict['DownloadAPI_x'])))

            self.DownloadCfgUI.ProxyEnable.setChecked(CfgDict['ProxyEnable_x'])
            self.DownloadCfgUI.ProxyIP.setText(CfgDict['ProxyIP_x'])
            self.DownloadCfgUI.ProxyPort.setText(CfgDict['ProxyPort_x'])

            self.DownloadCfgUI.SkipPeriod.setCurrentIndex(ZfinanceCfg.SkipPeriodList_c.index(str(CfgDict['SkipPeriod_x'])))
            self.DownloadCfgUI.SkipNG.setChecked(CfgDict['SkipNG_x'])


            self.DownloadCfgUI.MarketSelector.setColumnCount(2)
            self.DownloadCfgUI.MarketSelector.setHeaderLabels(('Market', 'Comment', 'Rule'))

            for Key, Value in ZfinanceCfg.ExchargeMarket.items():
                root = QTreeWidgetItem(self.DownloadCfgUI.MarketSelector)
                root.setText(0, Key)
                root.setText(1, Value[0])
                root.setText(2, Value[1])
                if CfgDict['EX_'+Key+'_x']:
                    root.setCheckState(0, Qt.Checked)
                else:
                    root.setCheckState(0, Qt.Unchecked)
            self.DownloadCfgUI.MarketSelector.addTopLevelItem(root)
            self.DownloadCfgUI.MarketSelector.setCurrentItem((self.DownloadCfgUI.MarketSelector.topLevelItem(0)))


        except:
            pass
        print(ConfigFilePathName)

        DataBasePath = os.getcwd() + '\\Data\\01_TickerDatabase'
        if (not os.path.exists(DataBasePath)):
            os.mkdir(DataBasePath)
        return

    def CloseDownloadCfgUI(self):
        self.DownloadCfgUI.close()




