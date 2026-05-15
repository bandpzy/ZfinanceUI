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
from joblib import Parallel, delayed

import ZBaseFunc
import Zfinance
import ZfinanceCfg
from ZfinanceCfg import TableColor
import ZFavorEditor
import ZDataClean
from time import sleep
import pathlib
import time

import PySide2.QtWidgets
import PySide2.QtGui
from PySide2.QtWidgets import QApplication, QMessageBox, QFileDialog, QCheckBox
from PySide2.QtWidgets import QButtonGroup, QSlider, QLabel, QRadioButton, QTableWidget, QHeaderView, QMenu, QCursor, QPoint
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QFont
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
import json
import os
import threading
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
GlobalDLUI = None
GlobalMainUI = None


class DownloadUIProc:
    def __init__(self, GlobalUI, APP, GlobalFavorEditorUI):
        global GlobalMainUI, CfgDict, TableWidgetChannel, DownloadProcessBarChannel, GlobalDLUI, GlobalAPP
        self.GlobalMainUI = GlobalUI
        GlobalAPP = APP
        GlobalMainUI = GlobalUI
        self.DownloadCfgUI = QUiLoader().load('UIDesign/DownloadConfig.ui')

        self.DataCleanUIx = ZDataClean.DataCleanUIProc(GlobalAPP)
        GlobalDLUI = self.DownloadCfgUI
        
        TableWidgetChannel = SignalThreadChannel()
        DownloadProcessBarChannel = SignalThreadChannel()

        TableWidgetChannel.TableSignal.connect(UpdateTableWidget)
        DownloadProcessBarChannel.PBarSignal.connect(UpdateDownloadProcessBarWidget)

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
        self.PeriodDictList = []

    def FavorListChechboxSelectMenu(self):
        popMenu = QMenu()
        if self.DownloadCfgUI.FavorList.currentItem() is not None:
            if self.DownloadCfgUI.FavorList.currentItem().parent() == None:
                SelectAll = popMenu.addAction('全选')
                CancelAll = popMenu.addAction("取消全选")

                CancelAll.triggered.connect(self.CancelAllChildrenInFavorList)
                SelectAll.triggered.connect(self.SelectAllChildrenInFavorList)
        popMenu.exec_(QCursor.pos())
        return

    def CancelAllChildrenInFavorList(self):
        self.DownloadCfgUI.FavorList.currentItem().setCheckState(0, PySide2.QtCore.Qt.CheckState.Unchecked)
        cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.FavorList.currentItem())
        ChildCnt = cursor.value().childCount()
        cursor = cursor.__iadd__(1)

        for i in range(ChildCnt):
            cursor.value().setCheckState(0, PySide2.QtCore.Qt.CheckState.Unchecked)
            cursor = cursor.__iadd__(1)

    def SelectAllChildrenInFavorList(self):
        self.DownloadCfgUI.FavorList.currentItem().setCheckState(0, PySide2.QtCore.Qt.CheckState.Checked)
        cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.FavorList.currentItem())
        ChildCnt = cursor.value().childCount()
        cursor = cursor.__iadd__(1)

        for i in range(ChildCnt):
            cursor.value().setCheckState(0, PySide2.QtCore.Qt.CheckState.Checked)
            cursor = cursor.__iadd__(1)

    def handleDataCleanUI(self):
        print('Data Clean UI')

    def HandleUpdateTickerList(self):
        global GlobalAPP
        self.DownloadCfgUI.SymbolsListProgressBar.setValue(0)
        try:
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
            ZBaseFunc.Log2LogBox('股票列表更新完成')
        except Exception as e:
            ZBaseFunc.Log2LogBox('更新股票列表失败: ' + str(e))

    def HandleDownloadPeriod(self):
        try:
            DownloadPeriod_x = self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()]
            self.DownloadCfgUI.ShowPeriod.setText(DownloadPeriod_x)
        except:
            pass

    def HandleDownloadConfig(self):
        try:
            ZFavorEditor.LoadFavorListCfg(self.DownloadCfgUI.FavorList, CheckBox=True)
        except:
            pass

        self.DownloadCfgUI.show()
        self.PeriodDictList = []
        for key, value in ZfinanceCfg.Period2DayLenthDict.items():
            self.PeriodDictList.append(key)

        self.DownloadCfgUI.DownloadPeriod.setMaximum(len(self.PeriodDictList) - 1)
        self.DownloadCfgUI.DownloadPeriod.setMinimum(0)
        self.DownloadCfgUI.DownloadPeriod.setTickInterval(1)
        self.DownloadCfgUI.ShowPeriod.setText(self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()])
        
        if not self.DLUIInit:
            self.DownloadCfgUI.MulitThreadDL.addItems(ZfinanceCfg.MulitThreadList_c)
            self.DownloadCfgUI.SkipPeriod.addItems(ZfinanceCfg.SkipPeriodList_c)
            self.DownloadCfgUI.ReConnect.addItems(ZfinanceCfg.ReConnectList_c)
            self.DownloadCfgUI.TimeOut.addItems(ZfinanceCfg.TimeOutList_c)
            self.DownloadCfgUI.DownloadAPI.addItems(ZfinanceCfg.DownloadAPIList_c)

            self.HandleOpenDLConfig(Default=True)
            self.DLUIInit = True

    def HandleConfirmDownload(self):
        global CfgDict
        try:
            cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.MarketSelector)
            while cursor.value():
                Temp = cursor.value()
                if Temp.checkState(0):
                    CfgDict['EX_' + Temp.text(0) + '_x'] = True
                else:
                    CfgDict['EX_' + Temp.text(0) + '_x'] = False
                cursor = cursor.__iadd__(1)
            
            CfgDict['List_Favor_x'] = CfgDict.get('EX_FAVOR_x', True)
            CfgDict['Intervial_1Day_x'] = self.DownloadCfgUI.Intervial_1Day.isChecked()
            CfgDict['Intervial_1h_x'] = self.DownloadCfgUI.Intervial_1h.isChecked()
            CfgDict['Intervial_30min_x'] = self.DownloadCfgUI.Intervial_30min.isChecked()
            CfgDict['Intervial_15min_x'] = self.DownloadCfgUI.Intervial_15min.isChecked()
            CfgDict['Intervial_5min_x'] = self.DownloadCfgUI.Intervial_5min.isChecked()
            CfgDict['Intervial_1min_x'] = self.DownloadCfgUI.Intervial_1min.isChecked()

            CfgDict['FunAna_Info_x'] = self.DownloadCfgUI.FunAna_Info.isChecked()
            CfgDict['FunAna_Financials_x'] = self.DownloadCfgUI.FunAna_Financials.isChecked()
            CfgDict['FunAna_Balancesheet_x'] = self.DownloadCfgUI.FunAna_Balancesheet.isChecked()
            CfgDict['FunAna_Cashflow_x'] = self.DownloadCfgUI.FunAna_Cashflow.isChecked()
            CfgDict['FunAna_Dividends_x'] = self.DownloadCfgUI.FunAna_Dividends.isChecked()
            CfgDict['FunAna_Splits_x'] = self.DownloadCfgUI.FunAna_Splits.isChecked()

            CfgDict['DownloadPeriod_x'] = self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()]
            CfgDict['MulitThreadDL_x'] = int(self.DownloadCfgUI.MulitThreadDL.currentText())
            CfgDict['ReConnectCnt_x'] = int(self.DownloadCfgUI.ReConnect.currentText())
            CfgDict['TimeOut_x'] = int(self.DownloadCfgUI.TimeOut.currentText())

            CfgDict['DownloadAPI_x'] = self.DownloadCfgUI.DownloadAPI.currentText()
            CfgDict['ProxyEnable_x'] = self.DownloadCfgUI.ProxyEnable.isChecked()
            CfgDict['ProxyIP_x'] = self.DownloadCfgUI.ProxyIP.text()
            CfgDict['ProxyPort_x'] = self.DownloadCfgUI.ProxyPort.text()

            CfgDict['SkipNG_x'] = self.DownloadCfgUI.SkipNG.isChecked()
            CfgDict['SkipPeriod_x'] = int(self.DownloadCfgUI.SkipPeriod.currentText())

            self.DownloadCfgUI.close()
        except Exception as e:
            ZBaseFunc.Log2LogBox('确认下载配置失败: ' + str(e))

    def HandleSaveDLConfig(self):
        global CfgDict
        try:
            cursor = QTreeWidgetItemIterator(self.DownloadCfgUI.MarketSelector)
            while cursor.value():
                Temp = cursor.value()
                if Temp.checkState(0):
                    CfgDict['EX_' + Temp.text(0) + '_x'] = True
                else:
                    CfgDict['EX_' + Temp.text(0) + '_x'] = False
                cursor = cursor.__iadd__(1)

            CfgDict['List_Favor_x'] = CfgDict.get('EX_FAVOR_x', True)
            CfgDict['Intervial_1Day_x'] = self.DownloadCfgUI.Intervial_1Day.isChecked()
            CfgDict['Intervial_1h_x'] = self.DownloadCfgUI.Intervial_1h.isChecked()
            CfgDict['Intervial_30min_x'] = self.DownloadCfgUI.Intervial_30min.isChecked()
            CfgDict['Intervial_15min_x'] = self.DownloadCfgUI.Intervial_15min.isChecked()
            CfgDict['Intervial_5min_x'] = self.DownloadCfgUI.Intervial_5min.isChecked()
            CfgDict['Intervial_1min_x'] = self.DownloadCfgUI.Intervial_1min.isChecked()

            CfgDict['FunAna_Info_x'] = self.DownloadCfgUI.FunAna_Info.isChecked()
            CfgDict['FunAna_Financials_x'] = self.DownloadCfgUI.FunAna_Financials.isChecked()
            CfgDict['FunAna_Balancesheet_x'] = self.DownloadCfgUI.FunAna_Balancesheet.isChecked()
            CfgDict['FunAna_Cashflow_x'] = self.DownloadCfgUI.FunAna_Cashflow.isChecked()
            CfgDict['FunAna_Dividends_x'] = self.DownloadCfgUI.FunAna_Dividends.isChecked()
            CfgDict['FunAna_Splits_x'] = self.DownloadCfgUI.FunAna_Splits.isChecked()

            CfgDict['DownloadPeriod_x'] = self.PeriodDictList[self.DownloadCfgUI.DownloadPeriod.value()]
            CfgDict['MulitThreadDL_x'] = int(self.DownloadCfgUI.MulitThreadDL.currentText())
            CfgDict['ReConnectCnt_x'] = int(self.DownloadCfgUI.ReConnect.currentText())
            CfgDict['TimeOut_x'] = int(self.DownloadCfgUI.TimeOut.currentText())

            CfgDict['DownloadAPI_x'] = self.DownloadCfgUI.DownloadAPI.currentText()
            CfgDict['ProxyEnable_x'] = self.DownloadCfgUI.ProxyEnable.isChecked()
            CfgDict['ProxyIP_x'] = self.DownloadCfgUI.ProxyIP.text()
            CfgDict['ProxyPort_x'] = self.DownloadCfgUI.ProxyPort.text()

            CfgDict['SkipPeriod_x'] = int(self.DownloadCfgUI.SkipPeriod.currentText())
            CfgDict['SkipNG_x'] = self.DownloadCfgUI.SkipNG.isChecked()

            ConfigFilePathName, ok = QFileDialog.getSaveFileName(None, "配置文件保存", 'Data/00_Config', 'ZfinanceDownloadCfg (*.ZFdl)')

            if ConfigFilePathName == "":
                return

            with open(ConfigFilePathName, "w") as f:
                json.dump(CfgDict, f, indent=1)
            ZBaseFunc.Log2LogBox('配置文件保存成功')
        except Exception as e:
            ZBaseFunc.Log2LogBox('保存配置文件失败: ' + str(e))

    def HandleOpenDLConfig(self, Default=False):
        global CfgDict
        try:
            if Default:
                ConfigFilePathName = 'Data/00_Config/DefaultDownload.ZFdl'
                if not os.path.exists(ConfigFilePathName):
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
                ConfigFilePathName, ok = QFileDialog.getOpenFileName(None, "选择配置文件", 'Data/00_Config', 'ZfinanceDownloadCfg (*.ZFdl)')
                if ConfigFilePathName == "":
                    return

            with open(ConfigFilePathName, 'r') as load_f:
                CfgDict = json.load(load_f)

            self.DownloadCfgUI.Intervial_1Day.setChecked(CfgDict.get('Intervial_1Day_x', True))
            self.DownloadCfgUI.Intervial_1h.setChecked(CfgDict.get('Intervial_1h_x', True))
            self.DownloadCfgUI.Intervial_30min.setChecked(CfgDict.get('Intervial_30min_x', True))
            self.DownloadCfgUI.Intervial_15min.setChecked(CfgDict.get('Intervial_15min_x', True))
            self.DownloadCfgUI.Intervial_5min.setChecked(CfgDict.get('Intervial_5min_x', True))
            self.DownloadCfgUI.Intervial_1min.setChecked(CfgDict.get('Intervial_1min_x', True))

            self.DownloadCfgUI.FunAna_Info.setChecked(CfgDict.get('FunAna_Info_x', True))
            self.DownloadCfgUI.FunAna_Financials.setChecked(CfgDict.get('FunAna_Financials_x', True))
            self.DownloadCfgUI.FunAna_Balancesheet.setChecked(CfgDict.get('FunAna_Balancesheet_x', True))
            self.DownloadCfgUI.FunAna_Cashflow.setChecked(CfgDict.get('FunAna_Cashflow_x', True))
            self.DownloadCfgUI.FunAna_Dividends.setChecked(CfgDict.get('FunAna_Dividends_x', True))
            self.DownloadCfgUI.FunAna_Splits.setChecked(CfgDict.get('FunAna_Splits_x', True))

            period_str = CfgDict.get('DownloadPeriod_x', '1 Day')
            if period_str in self.PeriodDictList:
                self.DownloadCfgUI.DownloadPeriod.setValue(self.PeriodDictList.index(period_str))

            self.DownloadCfgUI.MulitThreadDL.setCurrentIndex(max(0, ZfinanceCfg.MulitThreadList_c.index(str(CfgDict.get('MulitThreadDL_x', 5)))))
            self.DownloadCfgUI.ReConnect.setCurrentIndex(max(0, ZfinanceCfg.ReConnectList_c.index(str(CfgDict.get('ReConnectCnt_x', 2)))))
            self.DownloadCfgUI.TimeOut.setCurrentIndex(max(0, ZfinanceCfg.TimeOutList_c.index(str(CfgDict.get('TimeOut_x', 10)))))

            self.DownloadCfgUI.DownloadAPI.setCurrentIndex(max(0, ZfinanceCfg.DownloadAPIList_c.index(CfgDict.get('DownloadAPI_x', 'AutoSelect'))))

            self.DownloadCfgUI.ProxyEnable.setChecked(CfgDict.get('ProxyEnable_x', False))
            self.DownloadCfgUI.ProxyIP.setText(CfgDict.get('ProxyIP_x', '127.0.0.1'))
            self.DownloadCfgUI.ProxyPort.setText(CfgDict.get('ProxyPort_x', '10808'))

            self.DownloadCfgUI.SkipPeriod.setCurrentIndex(max(0, ZfinanceCfg.SkipPeriodList_c.index(str(CfgDict.get('SkipPeriod_x', 0)))))
            self.DownloadCfgUI.SkipNG.setChecked(CfgDict.get('SkipNG_x', True))

            self.DownloadCfgUI.MarketSelector.setColumnCount(2)
            self.DownloadCfgUI.MarketSelector.setHeaderLabels(('Market', 'Comment', 'Rule'))

            for Key, Value in ZfinanceCfg.ExchargeMarket.items():
                root = QTreeWidgetItem(self.DownloadCfgUI.MarketSelector)
                root.setText(0, Key)
                root.setText(1, Value[0])
                root.setText(2, Value[1])
                if CfgDict.get('EX_' + Key + '_x', False):
                    root.setCheckState(0, Qt.Checked)
                else:
                    root.setCheckState(0, Qt.Unchecked)
            self.DownloadCfgUI.MarketSelector.addTopLevelItem(root)
            self.DownloadCfgUI.MarketSelector.setCurrentItem((self.DownloadCfgUI.MarketSelector.topLevelItem(0)))

            ZBaseFunc.Log2LogBox('配置文件加载成功')
        except Exception as e:
            ZBaseFunc.Log2LogBox('加载配置文件失败: ' + str(e))

    def CloseDownloadCfgUI(self):
        self.DownloadCfgUI.close()


def HandleDownloadAbort():
    global DownloadAbortFlag, GlobalMainUI, GlobalAPP
    DownloadAbortFlag = True
    if GlobalMainUI:
        GlobalMainUI.SymbolsDownloadAbort.setDisabled(True)
        GlobalAPP.processEvents()


def HandleDownloadStart():
    global DownloadAbortFlag, GlobalDLUI, GlobalProcessCnt
    global Process, ProcessLen, GlobalMainUI, TableInitFlag, CfgDict, VPN, ScrollBarPosition
    
    DownloadAbortFlag = False
    Process = 0
    PeriodLimitlList = []
    KlineIntervialAndPeriodDictList = []
    BaseInfoList = []
    GlobalMainUI.SymbolsDownloadStart.setDisabled(True)
    GlobalAPP.processEvents()

    if CfgDict == dict():
        ConfigFilePathName = 'Data/00_Config/DefaultDownload.ZFdl'
        if os.path.exists(ConfigFilePathName):
            with open(ConfigFilePathName, 'r') as load_f:
                CfgDict = json.load(load_f)
        else:
            ZBaseFunc.Log2LogBox('请先配置下载参数')
            GlobalMainUI.SymbolsDownloadStart.setDisabled(False)
            return

    DownloadPeriod = CfgDict.get('DownloadPeriod_x', '1 Day')
    DayLenth = ZfinanceCfg.Period2DayLenthDict.get(DownloadPeriod, 1)
    
    if CfgDict.get('Intervial_1Day_x', True):
        KlineIntervialAndPeriodDictList.append({'Interval': '1d', 'Period': DayLenth})
    if CfgDict.get('Intervial_1h_x', True):
        KlineIntervialAndPeriodDictList.append({'Interval': '60m', 'Period': DayLenth})
    if CfgDict.get('Intervial_30min_x', True):
        KlineIntervialAndPeriodDictList.append({'Interval': '30m', 'Period': DayLenth})
    if CfgDict.get('Intervial_15min_x', True):
        KlineIntervialAndPeriodDictList.append({'Interval': '15m', 'Period': DayLenth})
    if CfgDict.get('Intervial_5min_x', True):
        KlineIntervialAndPeriodDictList.append({'Interval': '5m', 'Period': DayLenth})
    if CfgDict.get('Intervial_1min_x', True):
        KlineIntervialAndPeriodDictList.append({'Interval': '1m', 'Period': DayLenth})

    if CfgDict.get('FunAna_Info_x', True):
        BaseInfoList.append('inf')
    if CfgDict.get('FunAna_Financials_x', True):
        BaseInfoList.append('fin')
    if CfgDict.get('FunAna_Balancesheet_x', True):
        BaseInfoList.append('bal')
    if CfgDict.get('FunAna_Cashflow_x', True):
        BaseInfoList.append('cas')
    if CfgDict.get('FunAna_Dividends_x', True):
        BaseInfoList.append('div')
    if CfgDict.get('FunAna_Splits_x', True):
        BaseInfoList.append('spl')

    ReConnectCnt = CfgDict.get('ReConnectCnt_x', 2)

    if CfgDict.get('ProxyEnable_x', False):
        ProxyIP = CfgDict.get('ProxyIP_x', '127.0.0.1')
        ProxyPort = CfgDict.get('ProxyPort_x', '10808')
        VPN = 'socks5://' + ProxyIP + ':' + ProxyPort
        ZBaseFunc.SetDLAPIPara(key='PROXY', value=VPN)
    else:
        VPN = None
        ZBaseFunc.SetDLAPIPara(key='PROXY', value=None)

    SymbolsList = []
    try:
        CNTickerList = pd.read_csv('Data\\00_Config\\CNTickerList.csv', sep=',', dtype={'股票代码': str})
        HKTickerList = pd.read_csv('Data\\00_Config\\HKTickerList.csv', sep=',', dtype={'股票代码': str})
        USTickerList = pd.read_csv('Data\\00_Config\\USTickerList.csv', sep=',', dtype={'股票代码': str})
    except Exception as e:
        ZBaseFunc.Log2LogBox('读取股票列表失败: ' + str(e))
        GlobalMainUI.SymbolsDownloadStart.setDisabled(False)
        return

    if CfgDict.get('EX_CN-SHH_x', False):
        Temp = CNTickerList.loc[CNTickerList['市场类型'].isin(['沪A'])]
        SymbolsList.extend([str(i) + '.ss' for i in Temp['股票代码'].tolist()])

    if CfgDict.get('EX_CN-SHZ_x', False):
        Temp = CNTickerList.loc[CNTickerList['市场类型'].isin(['深A'])]
        SymbolsList.extend([str(i) + '.sz' for i in Temp['股票代码'].tolist()])

    ProcessLen = len(SymbolsList)
    ZBaseFunc.Log2LogBox('SymbolsList count=' + str(ProcessLen))
    GlobalMainUI.SymbolsDownloadProgressBar.setValue(0)
    ScrollBarPosition = 0

    TableInitFlag = True
    GlobalMainUI.SymbolsDownloadTable.clear()
    GlobalMainUI.SymbolsDownloadTable.setRowCount(0)
    GlobalMainUI.SymbolsDownloadTable.setColumnCount(len(KlineIntervialAndPeriodDictList) + len(BaseInfoList) + 1)
    GlobalMainUI.SymbolsDownloadTable.setRowCount(ProcessLen)
    GlobalMainUI.SymbolsDownloadTable.verticalHeader().setVisible(False)
    GlobalMainUI.SymbolsDownloadTable.horizontalHeader().setDefaultAlignment(PySide2.QtCore.Qt.AlignLeft)
    GlobalMainUI.SymbolsDownloadTable.setFont(QFont('song', 7))
    GlobalMainUI.SymbolsDownloadTable.horizontalHeader().setFont(QFont('song', 7))
    GlobalMainUI.SymbolsDownloadTable.verticalScrollBar().setValue(0)
    
    Row = 0
    for i in SymbolsList:
        SymbolsInTable = PySide2.QtWidgets.QTableWidgetItem(i)
        GlobalMainUI.SymbolsDownloadTable.setRowHeight(Row, 6)
        GlobalMainUI.SymbolsDownloadTable.setItem(Row, 0, SymbolsInTable)
        Row = Row + 1

    GlobalMainUI.SymbolsDownloadTable.setColumnWidth(0, 55)

    Col = 1
    for i in range(len(KlineIntervialAndPeriodDictList) + len(BaseInfoList)):
        GlobalMainUI.SymbolsDownloadTable.setColumnWidth(Col, 25)
        Col = Col + 1
    
    Temp = ['SYM']
    for i in KlineIntervialAndPeriodDictList:
        Temp.append(i['Interval'])
    for i in BaseInfoList:
        Temp.append(i)
    GlobalMainUI.SymbolsDownloadTable.setHorizontalHeaderLabels(Temp)
    GlobalAPP.processEvents()
    
    ThreadNum = CfgDict.get('MulitThreadDL_x', 5)

    try:
        SYM = ZBaseFunc.StockSymbolData(Platfrom=CfgDict.get('DownloadAPI_x', 'AutoSelect'), Symbol='AAPL')
        Result = SYM.DownloadSymbolHistoryData(Period=30, Interval='1d')
        if Result['Success']:
            NewFileEndTime = int(datetime.datetime.fromtimestamp(Result['TimeStamp']).strftime("%Y%m%d"))
        else:
            ZBaseFunc.Log2LogBox('Can not start Download, please check Network!')
            GlobalMainUI.SymbolsDownloadStart.setDisabled(False)
            return
    except Exception as e:
        ZBaseFunc.Log2LogBox('初始化下载失败: ' + str(e))
        GlobalMainUI.SymbolsDownloadStart.setDisabled(False)
        return

    thread = Thread(target=ThreadingOfDownload, args=(ThreadNum,
                                                      SymbolsList,
                                                      CfgDict.get('DownloadAPI_x', 'AutoSelect'), 5, NewFileEndTime,
                                                      KlineIntervialAndPeriodDictList,
                                                      BaseInfoList,
                                                      CfgDict.get('ReConnectCnt_x', 2),
                                                      CfgDict.get('SkipPeriod_x', 0),
                                                      CfgDict.get('SkipNG_x', True),
                                                      DownloadProcessBarChannel))

    thread.start()


def ThreadingOfDownload(ThreadNum, SymbolsList, Platfrom, Timeout, NewFileEndTime,
                       KlineIntervialAndPeriodDictList, BaseInfoList, ReConnectCnt,
                       SkipLenth, SkipNG, PrgressSignal):
    global GlobalProcessCnt

    GlobalProcessCnt = 0
    Parallel(n_jobs=ThreadNum, backend='threading')(delayed(DownloadThread)(
        Symbol=Symbol,
        Platfrom=Platfrom,
        Timeout=Timeout,
        NewFileEndTime=NewFileEndTime,
        CurrRow=SymbolsList.index(Symbol),
        KlineIntervialAndPeriodDictList=KlineIntervialAndPeriodDictList,
        BaseInfoList=BaseInfoList,
        ReConnectCnt=ReConnectCnt,
        SkipLenth=SkipLenth,
        SkipNG=SkipNG,
        PrgressSignal=PrgressSignal) for Symbol in SymbolsList)

    GlobalMainUI.SymbolsDownloadStart.setDisabled(False)
    GlobalMainUI.SymbolsDownloadAbort.setDisabled(False)


def DeleteUselessOKNG(FolderPath):
    try:
        for i in glob.glob(FolderPath + '/TAG_*'):
            try:
                os.remove(i)
            except:
                pass
    except:
        pass


def DownloadThread(Symbol, Platfrom, Timeout, NewFileEndTime=None, CurrRow=0,
                  KlineIntervialAndPeriodDictList=[], BaseInfoList=[], ReConnectCnt=1,
                  SkipLenth=0, SkipNG=True, PrgressSignal=None):
    global GlobalMainUI, DownloadAbortFlag, ScrollBarPosition
    global TempColorGreen, TempColorYellow, TempColorRed

    if CurrRow > ScrollBarPosition:
        ScrollBarPosition = CurrRow
        if ScrollBarPosition > 5:
            GlobalMainUI.SymbolsDownloadTable.verticalScrollBar().setValue(ScrollBarPosition - 4)

    TimeStamp = str(int(time.time()))
    RootDir = 'Data/01_TickerDatabase/'
    if DownloadAbortFlag:
        PrgressSignal.PBarSignal.emit(CurrRow + 1)
        return
    
    TempFolderPath = RootDir + Symbol
    if not os.path.exists(TempFolderPath):
        try:
            os.mkdir(TempFolderPath)
        except:
            ZBaseFunc.Log2LogBox('Creat Folder [' + TempFolderPath + '] Failed')
    
    OKFilePath = TempFolderPath + '/TAG_OK_' + TimeStamp
    NGFilePath = TempFolderPath + '/TAG_NG_' + TimeStamp
    TempCol = 0
    OKFLAG = True
    DeleteUselessOKNG(TempFolderPath)

    for KlineIntervialAndPeriod in KlineIntervialAndPeriodDictList:
        TempCol += 1
        TempIntervial = KlineIntervialAndPeriod['Interval']
        TempPeriod = KlineIntervialAndPeriod['Period']
        TableWidgetChannel.TableSignal.emit(CurrRow, TempCol, TempColorYellow)

        for ReConnectCnt_i in range(ReConnectCnt):
            if TempPeriod == 0:
                NewFileStartTime = 19000101
            else:
                NewFileStartTime = int((datetime.datetime.now() - datetime.timedelta(days=TempPeriod)).strftime("%Y%m%d"))

            LastFileName = ZBaseFunc.GetCompleteFileName(Path=TempFolderPath + '/' + Symbol + "_" + TempIntervial)
            Tempdf_Exist = pd.DataFrame()
            
            if LastFileName is not None:
                ExistFileStartTime = int(LastFileName.split('_')[2])
                ExistFileEndTime = int(LastFileName.split('_')[3])
                
                if (ExistFileStartTime <= NewFileStartTime) and (ExistFileEndTime >= NewFileEndTime):
                    TableWidgetChannel.TableSignal.emit(CurrRow, TempCol, TempColorGreen)
                    break
                try:
                    Tempdf_Exist = pd.read_csv(TempFolderPath + '/' + LastFileName, sep=',', index_col='DateTime')
                except:
                    pass

            try:
                SYMBOL = ZBaseFunc.StockSymbolData(Symbol=Symbol, Platfrom=Platfrom)
                HistorydfDict = SYMBOL.DownloadSymbolHistoryData(Period=TempPeriod, Interval=TempIntervial, timeout=Timeout)
                
                if HistorydfDict['Success']:
                    Tempdf = Tempdf_Exist.append(HistorydfDict['DataFrame'])
                    Tempdf = Tempdf[~Tempdf.index.duplicated(keep='last')]

                    NewFileStartTimeStr = Tempdf.index[0][:10].replace('-', '')
                    NewFileEndTimeStr = Tempdf.index[-1][:10].replace('-', '')

                    TempPeriodStr = 'max' if TempPeriod == 0 else str(TempPeriod) + 'd'
                    TempSYMFileName = TempFolderPath + '/' + Symbol + "_" + str(TempIntervial) + "_" + \
                                      NewFileStartTimeStr + '_' + NewFileEndTimeStr + '_' + TempPeriodStr + '.csv'
                    try:
                        if LastFileName:
                            os.remove(TempFolderPath + '/' + LastFileName)
                    except:
                        pass
                    
                    Tempdf.to_csv(TempSYMFileName, sep=',', index_label='DateTime')
                    TableWidgetChannel.TableSignal.emit(CurrRow, TempCol, TempColorGreen)
                    break
                else:
                    TableWidgetChannel.TableSignal.emit(CurrRow, TempCol, TempColorRed)
                    if ReConnectCnt_i == ReConnectCnt - 1:
                        OKFLAG = False
            except Exception as e:
                TableWidgetChannel.TableSignal.emit(CurrRow, TempCol, TempColorRed)
                if ReConnectCnt_i == ReConnectCnt - 1:
                    OKFLAG = False

    if OKFLAG:
        FlagPath = OKFilePath
    else:
        FlagPath = NGFilePath
    
    try:
        open(FlagPath, 'w').close()
    except:
        pass

    PrgressSignal.PBarSignal.emit(CurrRow + 1)
    return


class SignalThreadChannel(QObject):
    TableSignal = Signal(int, int, int)
    PBarSignal = Signal(int)
    LPBarSignal = Signal(pd.DataFrame)


def CalcReasonablePeriod(ExistFileStartTime, ExistFileEndTime, NewFileStartTime, NewFileEndTime, TempPeriod):
    if NewFileStartTime < ExistFileStartTime:
        return TempPeriod
    else:
        TempPeriod = (datetime.datetime.strptime(str(NewFileEndTime), "%Y%m%d") - 
                      datetime.datetime.strptime(str(ExistFileEndTime), "%Y%m%d")).days
        for key, value in ZfinanceCfg.Period2DayLenthDict.items():
            if value >= TempPeriod:
                return value
        return TempPeriod


def UpdateDownloadProcessBarWidget(Process):
    global GlobalMainUI, ProcessLen, GlobalProcessCnt

    GlobalProcessCnt += 1
    if ProcessLen > 0:
        GlobalMainUI.SymbolsDownloadProgressBar.setValue(int(GlobalProcessCnt / ProcessLen * 100))


def UpdateTableWidget(row, col, color):
    global GlobalMainUI, TempColorGreen, TempColorYellow, TempColorRed
    TempColor = PySide2.QtWidgets.QTableWidgetItem('')
    TempColor.setBackgroundColor(PySide2.QtGui.QColor(0, 0, 255))
    if color == TempColorGreen:
        TempColor.setBackgroundColor(PySide2.QtGui.QColor(0, 255, 0))
    elif color == TempColorYellow:
        TempColor.setBackgroundColor(PySide2.QtGui.QColor(255, 255, 0))
    elif color == TempColorRed:
        TempColor.setBackgroundColor(PySide2.QtGui.QColor(255, 0, 0))
    elif color == TempColorGray:
        TempColor.setBackgroundColor(PySide2.QtGui.QColor(100, 100, 100))
    GlobalMainUI.SymbolsDownloadTable.setItem(row, col, TempColor)
