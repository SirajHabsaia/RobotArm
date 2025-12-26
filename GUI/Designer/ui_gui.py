# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gui.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QPushButton, QSizePolicy, QSlider,
    QSpacerItem, QStackedWidget, QVBoxLayout, QWidget)
import Designer.resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1000, 600)
        MainWindow.setMinimumSize(QSize(1000, 600))
        MainWindow.setStyleSheet(u"background-color: rgb(51, 51, 51);")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_3 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.icon_only_widget = QWidget(self.centralwidget)
        self.icon_only_widget.setObjectName(u"icon_only_widget")
        self.icon_only_widget.setMinimumSize(QSize(50, 0))
        self.icon_only_widget.setMaximumSize(QSize(50, 16777215))
        self.icon_only_widget.setStyleSheet(u"QWidget{\n"
"	background-color: rgb(33, 100, 33);\n"
"}\n"
"QPushButton{\n"
"	border: none;\n"
"}\n"
"QPushButton:checked{\n"
"	background-color: rgb(51, 51, 51);\n"
"}\n"
"QPushButton:hover{\n"
"	background-color: rgb(102, 102, 102);\n"
"}")
        self.verticalLayout = QVBoxLayout(self.icon_only_widget)
        self.verticalLayout.setSpacing(25)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 10, 0, 10)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_2 = QSpacerItem(13, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.label = QLabel(self.icon_only_widget)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(40, 40))
        self.label.setMaximumSize(QSize(40, 40))
        self.label.setPixmap(QPixmap(u":/images/sidebar/icon.png"))
        self.label.setScaledContents(True)

        self.horizontalLayout_2.addWidget(self.label)

        self.horizontalSpacer_3 = QSpacerItem(13, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.verticalSpacer_3 = QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer_3)

        self.HomeBtn1 = QPushButton(self.icon_only_widget)
        self.HomeBtn1.setObjectName(u"HomeBtn1")
        self.HomeBtn1.setMinimumSize(QSize(40, 40))
        self.HomeBtn1.setMaximumSize(QSize(100, 40))
        icon = QIcon()
        icon.addFile(u":/images/sidebar/home_white.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.HomeBtn1.setIcon(icon)
        self.HomeBtn1.setIconSize(QSize(30, 30))
        self.HomeBtn1.setCheckable(True)
        self.HomeBtn1.setAutoExclusive(True)

        self.verticalLayout.addWidget(self.HomeBtn1)

        self.ManipBtn1 = QPushButton(self.icon_only_widget)
        self.ManipBtn1.setObjectName(u"ManipBtn1")
        self.ManipBtn1.setMinimumSize(QSize(40, 40))
        self.ManipBtn1.setMaximumSize(QSize(100, 40))
        icon1 = QIcon()
        icon1.addFile(u":/images/sidebar/manip.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ManipBtn1.setIcon(icon1)
        self.ManipBtn1.setIconSize(QSize(30, 30))
        self.ManipBtn1.setCheckable(True)
        self.ManipBtn1.setAutoExclusive(True)

        self.verticalLayout.addWidget(self.ManipBtn1)

        self.ProgramBtn1 = QPushButton(self.icon_only_widget)
        self.ProgramBtn1.setObjectName(u"ProgramBtn1")
        self.ProgramBtn1.setMinimumSize(QSize(40, 40))
        self.ProgramBtn1.setMaximumSize(QSize(100, 40))
        icon2 = QIcon()
        icon2.addFile(u":/images/sidebar/program.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ProgramBtn1.setIcon(icon2)
        self.ProgramBtn1.setIconSize(QSize(30, 30))
        self.ProgramBtn1.setCheckable(True)
        self.ProgramBtn1.setAutoExclusive(True)

        self.verticalLayout.addWidget(self.ProgramBtn1)

        self.DrawBtn1 = QPushButton(self.icon_only_widget)
        self.DrawBtn1.setObjectName(u"DrawBtn1")
        self.DrawBtn1.setMinimumSize(QSize(40, 40))
        self.DrawBtn1.setMaximumSize(QSize(100, 40))
        icon3 = QIcon()
        icon3.addFile(u":/images/sidebar/draw.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.DrawBtn1.setIcon(icon3)
        self.DrawBtn1.setIconSize(QSize(30, 30))
        self.DrawBtn1.setCheckable(True)
        self.DrawBtn1.setAutoExclusive(True)

        self.verticalLayout.addWidget(self.DrawBtn1)

        self.ChessBtn1 = QPushButton(self.icon_only_widget)
        self.ChessBtn1.setObjectName(u"ChessBtn1")
        self.ChessBtn1.setMinimumSize(QSize(40, 40))
        self.ChessBtn1.setMaximumSize(QSize(100, 40))
        icon4 = QIcon()
        icon4.addFile(u":/images/sidebar/chess.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.ChessBtn1.setIcon(icon4)
        self.ChessBtn1.setIconSize(QSize(30, 30))
        self.ChessBtn1.setCheckable(True)
        self.ChessBtn1.setAutoExclusive(True)

        self.verticalLayout.addWidget(self.ChessBtn1)

        self.verticalSpacer = QSpacerItem(20, 64, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.GithubBtn1 = QPushButton(self.icon_only_widget)
        self.GithubBtn1.setObjectName(u"GithubBtn1")
        self.GithubBtn1.setMinimumSize(QSize(40, 40))
        self.GithubBtn1.setMaximumSize(QSize(100, 40))
        icon5 = QIcon()
        icon5.addFile(u":/images/sidebar/github_white.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.GithubBtn1.setIcon(icon5)
        self.GithubBtn1.setIconSize(QSize(30, 30))

        self.verticalLayout.addWidget(self.GithubBtn1)


        self.horizontalLayout_3.addWidget(self.icon_only_widget)

        self.icon_name_widget = QWidget(self.centralwidget)
        self.icon_name_widget.setObjectName(u"icon_name_widget")
        self.icon_name_widget.setMinimumSize(QSize(140, 0))
        self.icon_name_widget.setMaximumSize(QSize(150, 16777215))
        self.icon_name_widget.setStyleSheet(u"QWidget{\n"
"	background-color: rgb(33, 100, 33);\n"
"}\n"
"QPushButton{\n"
"	color: rgb(255, 255, 255);\n"
"	text-align: left;\n"
"	border: none;\n"
"	padding-left: 10px;    /* moves the ICON + TEXT to the right */\n"
"}\n"
"QPushButton:checked{\n"
"	background-color: rgb(51, 51, 51);\n"
"	font-weight: bold;\n"
"}\n"
"QPushButton:hover{\n"
"	background-color: rgb(102, 102, 102);\n"
"}")
        self.verticalLayout_2 = QVBoxLayout(self.icon_name_widget)
        self.verticalLayout_2.setSpacing(25)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 10, 0, 10)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_4 = QSpacerItem(13, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_4)

        self.label_2 = QLabel(self.icon_name_widget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(40, 40))
        self.label_2.setMaximumSize(QSize(40, 40))
        self.label_2.setPixmap(QPixmap(u":/images/sidebar/icon.png"))
        self.label_2.setScaledContents(True)

        self.horizontalLayout.addWidget(self.label_2)

        self.label_3 = QLabel(self.icon_name_widget)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(90, 0))
        font = QFont()
        font.setPointSize(15)
        font.setBold(True)
        self.label_3.setFont(font)
        self.label_3.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout.addWidget(self.label_3)

        self.horizontalSpacer_5 = QSpacerItem(13, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_5)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.verticalSpacer_4 = QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_2.addItem(self.verticalSpacer_4)

        self.HomeBtn2 = QPushButton(self.icon_name_widget)
        self.HomeBtn2.setObjectName(u"HomeBtn2")
        self.HomeBtn2.setMinimumSize(QSize(40, 40))
        self.HomeBtn2.setMaximumSize(QSize(200, 40))
        font1 = QFont()
        font1.setPointSize(15)
        font1.setBold(False)
        self.HomeBtn2.setFont(font1)
        self.HomeBtn2.setIcon(icon)
        self.HomeBtn2.setIconSize(QSize(30, 30))
        self.HomeBtn2.setCheckable(True)
        self.HomeBtn2.setAutoExclusive(True)

        self.verticalLayout_2.addWidget(self.HomeBtn2)

        self.ManipBtn2 = QPushButton(self.icon_name_widget)
        self.ManipBtn2.setObjectName(u"ManipBtn2")
        self.ManipBtn2.setMinimumSize(QSize(40, 40))
        self.ManipBtn2.setMaximumSize(QSize(200, 40))
        self.ManipBtn2.setFont(font1)
        self.ManipBtn2.setIcon(icon1)
        self.ManipBtn2.setIconSize(QSize(30, 30))
        self.ManipBtn2.setCheckable(True)
        self.ManipBtn2.setAutoExclusive(True)

        self.verticalLayout_2.addWidget(self.ManipBtn2)

        self.ProgramBtn2 = QPushButton(self.icon_name_widget)
        self.ProgramBtn2.setObjectName(u"ProgramBtn2")
        self.ProgramBtn2.setMinimumSize(QSize(40, 40))
        self.ProgramBtn2.setMaximumSize(QSize(200, 40))
        self.ProgramBtn2.setFont(font1)
        self.ProgramBtn2.setIcon(icon2)
        self.ProgramBtn2.setIconSize(QSize(30, 30))
        self.ProgramBtn2.setCheckable(True)
        self.ProgramBtn2.setAutoExclusive(True)

        self.verticalLayout_2.addWidget(self.ProgramBtn2)

        self.DrawBtn2 = QPushButton(self.icon_name_widget)
        self.DrawBtn2.setObjectName(u"DrawBtn2")
        self.DrawBtn2.setMinimumSize(QSize(40, 40))
        self.DrawBtn2.setMaximumSize(QSize(200, 40))
        self.DrawBtn2.setFont(font1)
        self.DrawBtn2.setIcon(icon3)
        self.DrawBtn2.setIconSize(QSize(30, 30))
        self.DrawBtn2.setCheckable(True)
        self.DrawBtn2.setAutoExclusive(True)

        self.verticalLayout_2.addWidget(self.DrawBtn2)

        self.ChessBtn2 = QPushButton(self.icon_name_widget)
        self.ChessBtn2.setObjectName(u"ChessBtn2")
        self.ChessBtn2.setMinimumSize(QSize(40, 40))
        self.ChessBtn2.setMaximumSize(QSize(200, 40))
        self.ChessBtn2.setFont(font1)
        self.ChessBtn2.setIcon(icon4)
        self.ChessBtn2.setIconSize(QSize(30, 30))
        self.ChessBtn2.setCheckable(True)
        self.ChessBtn2.setAutoExclusive(True)

        self.verticalLayout_2.addWidget(self.ChessBtn2)

        self.verticalSpacer_2 = QSpacerItem(20, 64, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.GithubBtn2 = QPushButton(self.icon_name_widget)
        self.GithubBtn2.setObjectName(u"GithubBtn2")
        self.GithubBtn2.setMinimumSize(QSize(40, 40))
        self.GithubBtn2.setMaximumSize(QSize(200, 40))
        self.GithubBtn2.setFont(font1)
        self.GithubBtn2.setIcon(icon5)
        self.GithubBtn2.setIconSize(QSize(30, 30))

        self.verticalLayout_2.addWidget(self.GithubBtn2)


        self.horizontalLayout_3.addWidget(self.icon_name_widget)

        self.central_widget = QWidget(self.centralwidget)
        self.central_widget.setObjectName(u"central_widget")
        self.verticalLayout_3 = QVBoxLayout(self.central_widget)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.title_widget = QWidget(self.central_widget)
        self.title_widget.setObjectName(u"title_widget")
        self.title_widget.setMinimumSize(QSize(0, 32))
        self.title_widget.setMaximumSize(QSize(16777215, 32))
        self.title_widget.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"}\n"
"QPushButton:hover{\n"
"	\n"
"	background-color: rgb(85, 85, 85);\n"
"}")
        self.horizontalLayout_4 = QHBoxLayout(self.title_widget)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(-1, 0, -1, 0)
        self.SidebarBtn = QPushButton(self.title_widget)
        self.SidebarBtn.setObjectName(u"SidebarBtn")
        icon6 = QIcon()
        icon6.addFile(u":/images/menu.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.SidebarBtn.setIcon(icon6)
        self.SidebarBtn.setIconSize(QSize(32, 32))
        self.SidebarBtn.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.SidebarBtn)

        self.horizontalSpacer_6 = QSpacerItem(303, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_6)

        self.label_4 = QLabel(self.title_widget)
        self.label_4.setObjectName(u"label_4")
        font2 = QFont()
        font2.setFamilies([u"Ruda"])
        font2.setPointSize(12)
        self.label_4.setFont(font2)

        self.horizontalLayout_4.addWidget(self.label_4)

        self.horizontalSpacer = QSpacerItem(303, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.MinimizeBtn = QPushButton(self.title_widget)
        self.MinimizeBtn.setObjectName(u"MinimizeBtn")
        self.MinimizeBtn.setMinimumSize(QSize(32, 32))
        icon7 = QIcon()
        icon7.addFile(u":/images/minimize.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MinimizeBtn.setIcon(icon7)
        self.MinimizeBtn.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.MinimizeBtn)

        self.MaximizeBtn = QPushButton(self.title_widget)
        self.MaximizeBtn.setObjectName(u"MaximizeBtn")
        self.MaximizeBtn.setMinimumSize(QSize(32, 32))
        icon8 = QIcon()
        icon8.addFile(u":/images/maximize.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MaximizeBtn.setIcon(icon8)
        self.MaximizeBtn.setIconSize(QSize(20, 20))
        self.MaximizeBtn.setCheckable(True)

        self.horizontalLayout_4.addWidget(self.MaximizeBtn)

        self.CloseBtn = QPushButton(self.title_widget)
        self.CloseBtn.setObjectName(u"CloseBtn")
        self.CloseBtn.setMinimumSize(QSize(32, 32))
        icon9 = QIcon()
        icon9.addFile(u":/images/close.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.CloseBtn.setIcon(icon9)
        self.CloseBtn.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.CloseBtn)


        self.verticalLayout_3.addWidget(self.title_widget)

        self.line = QFrame(self.central_widget)
        self.line.setObjectName(u"line")
        self.line.setMaximumSize(QSize(16777215, 1))
        font3 = QFont()
        font3.setStrikeOut(False)
        self.line.setFont(font3)
        self.line.setStyleSheet(u"background-color: rgb(255, 255, 255);")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_3.addWidget(self.line)

        self.stackedWidget = QStackedWidget(self.central_widget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.stackedWidget.setStyleSheet(u"background-color: transparent;")
        self.page_home = QWidget()
        self.page_home.setObjectName(u"page_home")
        self.gridLayout_2 = QGridLayout(self.page_home)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setSpacing(50)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.widget_2 = QWidget(self.page_home)
        self.widget_2.setObjectName(u"widget_2")
        self.widget_2.setMinimumSize(QSize(0, 140))
        self.widget_2.setMaximumSize(QSize(16777215, 140))
        self.horizontalLayout_10 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_10.setSpacing(50)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(-1, 30, -1, -1)
        self.label_7 = QLabel(self.widget_2)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setMinimumSize(QSize(150, 100))
        self.label_7.setMaximumSize(QSize(150, 100))
        self.label_7.setPixmap(QPixmap(u":/images/home/um6p.png"))
        self.label_7.setScaledContents(True)

        self.horizontalLayout_10.addWidget(self.label_7)

        self.label_15 = QLabel(self.widget_2)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setMinimumSize(QSize(150, 100))
        self.label_15.setMaximumSize(QSize(150, 100))
        self.label_15.setPixmap(QPixmap(u":/images/home/emines.png"))
        self.label_15.setScaledContents(True)

        self.horizontalLayout_10.addWidget(self.label_15)


        self.verticalLayout_7.addWidget(self.widget_2)

        self.verticalSpacer_8 = QSpacerItem(20, 100, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_8)

        self.comWidget = QWidget(self.page_home)
        self.comWidget.setObjectName(u"comWidget")
        self.comWidget.setMinimumSize(QSize(450, 0))
        self.comWidget.setMaximumSize(QSize(450, 16777215))
        self.comWidget.setStyleSheet(u"QWidget#comWidget{\n"
"	border: 1px solid gray;\n"
"	border-radius: 10px;\n"
"}\n"
"QWidget{\n"
"	background-color: transparent;\n"
"}")
        self.gridLayout = QGridLayout(self.comWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.label_11 = QLabel(self.comWidget)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setStyleSheet(u"QLabel {\n"
"    color: #d4d7dc;\n"
"    font-size: 15px;\n"
"    font-weight: bold;\n"
"    padding: 4px;\n"
"}\n"
"")
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_5.addWidget(self.label_11)

        self.listCOM = QListWidget(self.comWidget)
        self.listCOM.setObjectName(u"listCOM")
        self.listCOM.setMinimumSize(QSize(300, 200))
        self.listCOM.setMaximumSize(QSize(300, 16777215))
        self.listCOM.setStyleSheet(u"QListWidget {\n"
"    background: #2b2d31;\n"
"    border: 1px solid #3a3c3f;\n"
"    border-radius: 6px;\n"
"    padding: 4px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QListWidget::item {\n"
"    background: #34363b;\n"
"    color: white;\n"
"    padding: 12px;          /* makes items bigger */\n"
"    margin: 4px;            /* spacing between items */\n"
"    border-radius: 6px;     /* rounded corners */\n"
"}\n"
"\n"
"QListWidget::item:hover {\n"
"    background: #3f4250;\n"
"}\n"
"\n"
"QListWidget::item:selected {\n"
"    background: #4b6ea7;    /* selection color */\n"
"    color: white;\n"
"}\n"
"\n"
"QListWidget::item:selected:!active {\n"
"    background: #4b6ea7;\n"
"}\n"
"\n"
"QListWidget::item:pressed {\n"
"    background: #2b3143;\n"
"}\n"
"")
        self.listCOM.setFrameShape(QFrame.Shape.StyledPanel)
        self.listCOM.setLineWidth(1)

        self.verticalLayout_5.addWidget(self.listCOM)


        self.horizontalLayout_5.addLayout(self.verticalLayout_5)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setSpacing(20)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_5)

        self.verticalSpacer_7 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_7)

        self.connectBtn = QPushButton(self.comWidget)
        self.connectBtn.setObjectName(u"connectBtn")
        self.connectBtn.setMinimumSize(QSize(120, 35))
        self.connectBtn.setMaximumSize(QSize(120, 16777215))
        font4 = QFont()
        font4.setFamilies([u"Verdana"])
        font4.setBold(False)
        self.connectBtn.setFont(font4)
        self.connectBtn.setStyleSheet(u"QPushButton {\n"
"    background-color: #2d2f33;\n"
"    color: white;\n"
"    border: 2px solid #444;\n"
"    border-radius: 6px;\n"
"    padding: 6px 12px;\n"
"    font-size: 16px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #3b3e42;\n"
"    border: 1px solid #5a5d60;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #1f2022;\n"
"    border: 1px solid #3a3c3f;\n"
"}\n"
"\n"
"QPushButton:disabled {\n"
"    background-color: #555;\n"
"    color: #aaa;\n"
"    border: 1px solid #666;\n"
"}\n"
"")

        self.verticalLayout_4.addWidget(self.connectBtn)

        self.disconnectBtn = QPushButton(self.comWidget)
        self.disconnectBtn.setObjectName(u"disconnectBtn")
        self.disconnectBtn.setMinimumSize(QSize(120, 35))
        self.disconnectBtn.setMaximumSize(QSize(120, 16777215))
        self.disconnectBtn.setFont(font4)
        self.disconnectBtn.setStyleSheet(u"QPushButton {\n"
"    background-color: #2d2f33;\n"
"    color: white;\n"
"    border: 2px solid #444;\n"
"    border-radius: 6px;\n"
"    padding: 6px 12px;\n"
"    font-size: 16px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #3b3e42;\n"
"    border: 1px solid #5a5d60;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #1f2022;\n"
"    border: 1px solid #3a3c3f;\n"
"}\n"
"\n"
"QPushButton:disabled {\n"
"    background-color: #555;\n"
"    color: #aaa;\n"
"    border: 1px solid #666;\n"
"}\n"
"")

        self.verticalLayout_4.addWidget(self.disconnectBtn)

        self.refreshBtn = QPushButton(self.comWidget)
        self.refreshBtn.setObjectName(u"refreshBtn")
        self.refreshBtn.setMinimumSize(QSize(120, 35))
        self.refreshBtn.setMaximumSize(QSize(120, 16777215))
        self.refreshBtn.setFont(font4)
        self.refreshBtn.setStyleSheet(u"QPushButton {\n"
"    background-color: #2d2f33;\n"
"    color: white;\n"
"    border: 2px solid #444;\n"
"    border-radius: 6px;\n"
"    padding: 6px 12px;\n"
"    font-size: 16px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #3b3e42;\n"
"    border: 1px solid #5a5d60;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #1f2022;\n"
"    border: 1px solid #3a3c3f;\n"
"}\n"
"\n"
"QPushButton:disabled {\n"
"    background-color: #555;\n"
"    color: #aaa;\n"
"    border: 1px solid #666;\n"
"}\n"
"")

        self.verticalLayout_4.addWidget(self.refreshBtn)

        self.quitBtn = QPushButton(self.comWidget)
        self.quitBtn.setObjectName(u"quitBtn")
        self.quitBtn.setMinimumSize(QSize(120, 35))
        self.quitBtn.setMaximumSize(QSize(120, 16777215))
        self.quitBtn.setFont(font4)
        self.quitBtn.setStyleSheet(u"QPushButton {\n"
"    background-color: #2d2f33;\n"
"    color: white;\n"
"    border: 2px solid #444;\n"
"    border-radius: 6px;\n"
"    padding: 6px 12px;\n"
"    font-size: 16px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #3b3e42;\n"
"    border: 1px solid #5a5d60;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #1f2022;\n"
"    border: 1px solid #3a3c3f;\n"
"}\n"
"\n"
"QPushButton:disabled {\n"
"    background-color: #555;\n"
"    color: #aaa;\n"
"    border: 1px solid #666;\n"
"}\n"
"")

        self.verticalLayout_4.addWidget(self.quitBtn)

        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_6)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")

        self.verticalLayout_4.addLayout(self.verticalLayout_6)


        self.horizontalLayout_5.addLayout(self.verticalLayout_4)


        self.gridLayout.addLayout(self.horizontalLayout_5, 0, 0, 1, 1)


        self.verticalLayout_7.addWidget(self.comWidget)


        self.horizontalLayout_6.addLayout(self.verticalLayout_7)

        self.renderLabel = QLabel(self.page_home)
        self.renderLabel.setObjectName(u"renderLabel")
        self.renderLabel.setPixmap(QPixmap(u":/images/render.png"))
        self.renderLabel.setScaledContents(True)
        self.renderLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_6.addWidget(self.renderLabel)


        self.gridLayout_2.addLayout(self.horizontalLayout_6, 0, 0, 1, 1)

        self.stackedWidget.addWidget(self.page_home)
        self.page_manip = QWidget()
        self.page_manip.setObjectName(u"page_manip")
        self.page_manip.setStyleSheet(u"")
        self.horizontalLayout_7 = QHBoxLayout(self.page_manip)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.manipWidget = QWidget(self.page_manip)
        self.manipWidget.setObjectName(u"manipWidget")
        self.manipWidget.setMinimumSize(QSize(220, 0))
        self.manipWidget.setMaximumSize(QSize(220, 16777215))
        self.manipWidget.setStyleSheet(u"QWidget#manipWidget{\n"
"	border: 1px solid gray;\n"
"	border-radius: 10px;\n"
"}\n"
"QWidget{\n"
"	background-color: transparent;\n"
"}")
        self.verticalLayout_8 = QVBoxLayout(self.manipWidget)
        self.verticalLayout_8.setSpacing(0)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 10)
        self.label_12 = QLabel(self.manipWidget)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setMinimumSize(QSize(0, 30))
        self.label_12.setMaximumSize(QSize(16777215, 30))
        font5 = QFont()
        font5.setBold(True)
        font5.setKerning(True)
        self.label_12.setFont(font5)
        self.label_12.setStyleSheet(u"QLabel {\n"
"    color: #d4d7dc;\n"
"    font-size: 15px;\n"
"    font-weight: bold;\n"
"    padding: 4px;\n"
"	\n"
"	background-color: transparent;\n"
"}\n"
"")
        self.label_12.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_8.addWidget(self.label_12)

        self.cartesianWidget = QWidget(self.manipWidget)
        self.cartesianWidget.setObjectName(u"cartesianWidget")
        self.cartesianWidget.setMinimumSize(QSize(0, 260))
        self.cartesianWidget.setStyleSheet(u"QLineEdit{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}\n"
"QSlider::groove:horizontal {\n"
"    border: none;\n"
"    height: 4px;\n"
"    background: #d0d0d0;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background:  #d0d0d0;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background: #d0d0d0;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: #ffffff;\n"
"    border: 2px solid  rgb(33, 100, 33);\n"
"    width: 5px;\n"
"    height: 5px;\n"
"    margin: -7px 0;       /* centers the handle */\n"
"    border-radius: 9px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background: #e9f1ff;\n"
"    border-color: #1a73e8;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background: #cfe0ff;\n"
"    border-color: #1a73e8;\n"
"}")
        self.verticalLayout_15 = QVBoxLayout(self.cartesianWidget)
        self.verticalLayout_15.setSpacing(0)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.xWidget = QWidget(self.cartesianWidget)
        self.xWidget.setObjectName(u"xWidget")
        self.verticalLayout_9 = QVBoxLayout(self.xWidget)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(-1, 5, -1, 5)
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalSpacer_8 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_8)

        self.label_8 = QLabel(self.xWidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setMinimumSize(QSize(0, 20))
        font6 = QFont()
        font6.setPointSize(12)
        font6.setBold(True)
        self.label_8.setFont(font6)

        self.horizontalLayout_9.addWidget(self.label_8)

        self.xlineEdit = QLineEdit(self.xWidget)
        self.xlineEdit.setObjectName(u"xlineEdit")
        self.xlineEdit.setMinimumSize(QSize(40, 0))
        self.xlineEdit.setMaximumSize(QSize(50, 16777215))

        self.horizontalLayout_9.addWidget(self.xlineEdit)

        self.xBtn = QPushButton(self.xWidget)
        self.xBtn.setObjectName(u"xBtn")
        self.xBtn.setMinimumSize(QSize(16, 6))
        self.xBtn.setMaximumSize(QSize(16, 16))
        self.xBtn.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}")
        icon10 = QIcon()
        icon10.addFile(u":/images/send.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.xBtn.setIcon(icon10)
        self.xBtn.setIconSize(QSize(16, 16))

        self.horizontalLayout_9.addWidget(self.xBtn)

        self.xLabel = QLabel(self.xWidget)
        self.xLabel.setObjectName(u"xLabel")
        self.xLabel.setMinimumSize(QSize(40, 0))
        self.xLabel.setStyleSheet(u"QLabel{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}")

        self.horizontalLayout_9.addWidget(self.xLabel)

        self.horizontalSpacer_7 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_7)


        self.verticalLayout_9.addLayout(self.horizontalLayout_9)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.xminLabel = QLabel(self.xWidget)
        self.xminLabel.setObjectName(u"xminLabel")
        self.xminLabel.setMaximumSize(QSize(35, 16777215))
        font7 = QFont()
        font7.setPointSize(12)
        font7.setBold(False)
        self.xminLabel.setFont(font7)

        self.horizontalLayout_8.addWidget(self.xminLabel)

        self.xSlider = QSlider(self.xWidget)
        self.xSlider.setObjectName(u"xSlider")
        self.xSlider.setStyleSheet(u"")
        self.xSlider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_8.addWidget(self.xSlider)

        self.xmaxLabel = QLabel(self.xWidget)
        self.xmaxLabel.setObjectName(u"xmaxLabel")
        self.xmaxLabel.setMaximumSize(QSize(35, 16777215))
        self.xmaxLabel.setFont(font7)

        self.horizontalLayout_8.addWidget(self.xmaxLabel)


        self.verticalLayout_9.addLayout(self.horizontalLayout_8)


        self.verticalLayout_15.addWidget(self.xWidget)

        self.yWidget = QWidget(self.cartesianWidget)
        self.yWidget.setObjectName(u"yWidget")
        self.verticalLayout_10 = QVBoxLayout(self.yWidget)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(-1, 5, -1, 5)
        self.horizontalLayout_20 = QHBoxLayout()
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.horizontalSpacer_19 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_19)

        self.label_31 = QLabel(self.yWidget)
        self.label_31.setObjectName(u"label_31")
        self.label_31.setMinimumSize(QSize(0, 20))
        self.label_31.setFont(font6)

        self.horizontalLayout_20.addWidget(self.label_31)

        self.ylineEdit = QLineEdit(self.yWidget)
        self.ylineEdit.setObjectName(u"ylineEdit")
        self.ylineEdit.setMinimumSize(QSize(40, 0))
        self.ylineEdit.setMaximumSize(QSize(50, 16777215))

        self.horizontalLayout_20.addWidget(self.ylineEdit)

        self.yBtn = QPushButton(self.yWidget)
        self.yBtn.setObjectName(u"yBtn")
        self.yBtn.setMinimumSize(QSize(16, 6))
        self.yBtn.setMaximumSize(QSize(16, 16))
        self.yBtn.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}")
        self.yBtn.setIcon(icon10)
        self.yBtn.setIconSize(QSize(16, 16))

        self.horizontalLayout_20.addWidget(self.yBtn)

        self.yLabel = QLabel(self.yWidget)
        self.yLabel.setObjectName(u"yLabel")
        self.yLabel.setMinimumSize(QSize(40, 0))
        self.yLabel.setStyleSheet(u"QLabel{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}")

        self.horizontalLayout_20.addWidget(self.yLabel)

        self.horizontalSpacer_20 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_20)


        self.verticalLayout_10.addLayout(self.horizontalLayout_20)

        self.horizontalLayout_21 = QHBoxLayout()
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.yminLabel = QLabel(self.yWidget)
        self.yminLabel.setObjectName(u"yminLabel")
        self.yminLabel.setMaximumSize(QSize(35, 16777215))
        self.yminLabel.setFont(font7)

        self.horizontalLayout_21.addWidget(self.yminLabel)

        self.ySlider = QSlider(self.yWidget)
        self.ySlider.setObjectName(u"ySlider")
        self.ySlider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_21.addWidget(self.ySlider)

        self.ymaxLabel = QLabel(self.yWidget)
        self.ymaxLabel.setObjectName(u"ymaxLabel")
        self.ymaxLabel.setMaximumSize(QSize(35, 16777215))
        self.ymaxLabel.setFont(font7)

        self.horizontalLayout_21.addWidget(self.ymaxLabel)


        self.verticalLayout_10.addLayout(self.horizontalLayout_21)


        self.verticalLayout_15.addWidget(self.yWidget)

        self.zWidget = QWidget(self.cartesianWidget)
        self.zWidget.setObjectName(u"zWidget")
        self.verticalLayout_13 = QVBoxLayout(self.zWidget)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(-1, 5, -1, 5)
        self.horizontalLayout_22 = QHBoxLayout()
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.horizontalSpacer_21 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_22.addItem(self.horizontalSpacer_21)

        self.label_34 = QLabel(self.zWidget)
        self.label_34.setObjectName(u"label_34")
        self.label_34.setMinimumSize(QSize(0, 20))
        self.label_34.setFont(font6)

        self.horizontalLayout_22.addWidget(self.label_34)

        self.zlineEdit = QLineEdit(self.zWidget)
        self.zlineEdit.setObjectName(u"zlineEdit")
        self.zlineEdit.setMinimumSize(QSize(40, 0))
        self.zlineEdit.setMaximumSize(QSize(50, 16777215))

        self.horizontalLayout_22.addWidget(self.zlineEdit)

        self.zBtn = QPushButton(self.zWidget)
        self.zBtn.setObjectName(u"zBtn")
        self.zBtn.setMinimumSize(QSize(16, 6))
        self.zBtn.setMaximumSize(QSize(16, 16))
        self.zBtn.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}")
        self.zBtn.setIcon(icon10)
        self.zBtn.setIconSize(QSize(16, 16))

        self.horizontalLayout_22.addWidget(self.zBtn)

        self.zLabel = QLabel(self.zWidget)
        self.zLabel.setObjectName(u"zLabel")
        self.zLabel.setMinimumSize(QSize(40, 0))
        self.zLabel.setStyleSheet(u"QLabel{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}")

        self.horizontalLayout_22.addWidget(self.zLabel)

        self.horizontalSpacer_22 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_22.addItem(self.horizontalSpacer_22)


        self.verticalLayout_13.addLayout(self.horizontalLayout_22)

        self.horizontalLayout_23 = QHBoxLayout()
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.zminLabel = QLabel(self.zWidget)
        self.zminLabel.setObjectName(u"zminLabel")
        self.zminLabel.setMaximumSize(QSize(35, 16777215))
        self.zminLabel.setFont(font7)

        self.horizontalLayout_23.addWidget(self.zminLabel)

        self.zSlider = QSlider(self.zWidget)
        self.zSlider.setObjectName(u"zSlider")
        self.zSlider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_23.addWidget(self.zSlider)

        self.zmaxLabel = QLabel(self.zWidget)
        self.zmaxLabel.setObjectName(u"zmaxLabel")
        self.zmaxLabel.setMaximumSize(QSize(35, 16777215))
        self.zmaxLabel.setFont(font7)

        self.horizontalLayout_23.addWidget(self.zmaxLabel)


        self.verticalLayout_13.addLayout(self.horizontalLayout_23)


        self.verticalLayout_15.addWidget(self.zWidget)

        self.muWidget = QWidget(self.cartesianWidget)
        self.muWidget.setObjectName(u"muWidget")
        self.verticalLayout_14 = QVBoxLayout(self.muWidget)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(-1, 5, -1, 5)
        self.horizontalLayout_24 = QHBoxLayout()
        self.horizontalLayout_24.setObjectName(u"horizontalLayout_24")
        self.horizontalSpacer_23 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_24.addItem(self.horizontalSpacer_23)

        self.label_37 = QLabel(self.muWidget)
        self.label_37.setObjectName(u"label_37")
        self.label_37.setMinimumSize(QSize(0, 20))
        self.label_37.setFont(font6)

        self.horizontalLayout_24.addWidget(self.label_37)

        self.mulineEdit = QLineEdit(self.muWidget)
        self.mulineEdit.setObjectName(u"mulineEdit")
        self.mulineEdit.setMinimumSize(QSize(40, 0))
        self.mulineEdit.setMaximumSize(QSize(50, 16777215))

        self.horizontalLayout_24.addWidget(self.mulineEdit)

        self.muBtn = QPushButton(self.muWidget)
        self.muBtn.setObjectName(u"muBtn")
        self.muBtn.setMinimumSize(QSize(16, 6))
        self.muBtn.setMaximumSize(QSize(16, 16))
        self.muBtn.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}")
        self.muBtn.setIcon(icon10)
        self.muBtn.setIconSize(QSize(16, 16))

        self.horizontalLayout_24.addWidget(self.muBtn)

        self.muLabel = QLabel(self.muWidget)
        self.muLabel.setObjectName(u"muLabel")
        self.muLabel.setMinimumSize(QSize(40, 0))
        self.muLabel.setStyleSheet(u"QLabel{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}")

        self.horizontalLayout_24.addWidget(self.muLabel)

        self.horizontalSpacer_24 = QSpacerItem(50, 17, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_24.addItem(self.horizontalSpacer_24)


        self.verticalLayout_14.addLayout(self.horizontalLayout_24)

        self.horizontalLayout_25 = QHBoxLayout()
        self.horizontalLayout_25.setObjectName(u"horizontalLayout_25")
        self.muminLabel = QLabel(self.muWidget)
        self.muminLabel.setObjectName(u"muminLabel")
        self.muminLabel.setMaximumSize(QSize(35, 16777215))
        self.muminLabel.setFont(font7)

        self.horizontalLayout_25.addWidget(self.muminLabel)

        self.muSlider = QSlider(self.muWidget)
        self.muSlider.setObjectName(u"muSlider")
        self.muSlider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_25.addWidget(self.muSlider)

        self.mumaxLabel = QLabel(self.muWidget)
        self.mumaxLabel.setObjectName(u"mumaxLabel")
        self.mumaxLabel.setMaximumSize(QSize(35, 16777215))
        self.mumaxLabel.setFont(font7)

        self.horizontalLayout_25.addWidget(self.mumaxLabel)


        self.verticalLayout_14.addLayout(self.horizontalLayout_25)


        self.verticalLayout_15.addWidget(self.muWidget)

        self.sendallWidget = QWidget(self.cartesianWidget)
        self.sendallWidget.setObjectName(u"sendallWidget")
        self.horizontalLayout_19 = QHBoxLayout(self.sendallWidget)
        self.horizontalLayout_19.setSpacing(0)
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.horizontalSpacer_16 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_19.addItem(self.horizontalSpacer_16)

        self.sendallBtn = QPushButton(self.sendallWidget)
        self.sendallBtn.setObjectName(u"sendallBtn")
        self.sendallBtn.setMinimumSize(QSize(0, 30))
        self.sendallBtn.setMaximumSize(QSize(16777215, 30))
        self.sendallBtn.setStyleSheet(u"QPushButton {\n"
"    background-color: transparent;\n"
"    color: #e6e6e6;\n"
"\n"
"    border: 2px solid #6a6a6a;   /* visible gray frame */\n"
"    border-radius: 6px;\n"
"\n"
"    padding: 6px 14px;\n"
"    font-size: 14px;\n"
"}\n"
"\n"
"/* Hover: brighter frame + subtle overlay */\n"
"QPushButton:hover {\n"
"    border-color: #9a9a9a;\n"
"    background-color: rgba(255, 255, 255, 0.04);\n"
"}\n"
"\n"
"/* Pressed: darker frame + stronger overlay */\n"
"QPushButton:pressed {\n"
"    border-color: #b0b0b0;\n"
"    background-color: rgba(0, 0, 0, 0.25);\n"
"    padding-top: 7px;   /* subtle pressed effect */\n"
"    padding-bottom: 5px;\n"
"}\n"
"\n"
"/* Focus (keyboard navigation) */\n"
"QPushButton:focus {\n"
"    border-color: #bfbfbf;\n"
"}\n"
"\n"
"/* Disabled */\n"
"QPushButton:disabled {\n"
"    color: #777777;\n"
"    border-color: #444444;\n"
"    background-color: transparent;\n"
"}\n"
"")

        self.horizontalLayout_19.addWidget(self.sendallBtn)

        self.horizontalSpacer_15 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_19.addItem(self.horizontalSpacer_15)


        self.verticalLayout_15.addWidget(self.sendallWidget)


        self.verticalLayout_8.addWidget(self.cartesianWidget)

        self.label_13 = QLabel(self.manipWidget)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setMinimumSize(QSize(0, 30))
        self.label_13.setMaximumSize(QSize(16777215, 30))
        self.label_13.setStyleSheet(u"QLabel {\n"
"    color: #d4d7dc;\n"
"    font-size: 15px;\n"
"    font-weight: bold;\n"
"    padding: 4px;\n"
"}\n"
"")
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_8.addWidget(self.label_13)

        self.polarWidget = QWidget(self.manipWidget)
        self.polarWidget.setObjectName(u"polarWidget")
        self.polarWidget.setMinimumSize(QSize(0, 180))
        self.polarWidget.setMaximumSize(QSize(16777215, 16777215))
        self.polarWidget.setToolTipDuration(46)
        self.polarWidget.setStyleSheet(u"")
        self.gridLayout_3 = QGridLayout(self.polarWidget)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(-1, 0, -1, 0)
        self.thetaWidget = QWidget(self.polarWidget)
        self.thetaWidget.setObjectName(u"thetaWidget")
        self.thetaWidget.setMinimumSize(QSize(80, 80))
        self.thetaWidget.setMaximumSize(QSize(80, 80))
        self.thetaWidget.setStyleSheet(u"")

        self.gridLayout_3.addWidget(self.thetaWidget, 0, 0, 1, 1)

        self.alphaWidget = QWidget(self.polarWidget)
        self.alphaWidget.setObjectName(u"alphaWidget")
        self.alphaWidget.setMinimumSize(QSize(80, 80))
        self.alphaWidget.setMaximumSize(QSize(80, 80))
        self.alphaWidget.setStyleSheet(u"")

        self.gridLayout_3.addWidget(self.alphaWidget, 0, 1, 1, 1)

        self.betaWidget = QWidget(self.polarWidget)
        self.betaWidget.setObjectName(u"betaWidget")
        self.betaWidget.setMinimumSize(QSize(80, 80))
        self.betaWidget.setMaximumSize(QSize(80, 80))
        self.betaWidget.setStyleSheet(u"")

        self.gridLayout_3.addWidget(self.betaWidget, 1, 0, 1, 1)

        self.gammaWidget = QWidget(self.polarWidget)
        self.gammaWidget.setObjectName(u"gammaWidget")
        self.gammaWidget.setMinimumSize(QSize(80, 80))
        self.gammaWidget.setMaximumSize(QSize(80, 80))
        self.gammaWidget.setStyleSheet(u"")

        self.gridLayout_3.addWidget(self.gammaWidget, 1, 1, 1, 1)


        self.verticalLayout_8.addWidget(self.polarWidget)

        self.label_14 = QLabel(self.manipWidget)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setMinimumSize(QSize(0, 30))
        self.label_14.setMaximumSize(QSize(16777215, 30))
        self.label_14.setStyleSheet(u"QLabel {\n"
"    color: #d4d7dc;\n"
"    font-size: 15px;\n"
"    font-weight: bold;\n"
"    padding: 4px;\n"
"}\n"
"")
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_8.addWidget(self.label_14)

        self.griperSlider = QSlider(self.manipWidget)
        self.griperSlider.setObjectName(u"griperSlider")
        self.griperSlider.setOrientation(Qt.Orientation.Horizontal)

        self.verticalLayout_8.addWidget(self.griperSlider)


        self.horizontalLayout_7.addWidget(self.manipWidget)

        self.ThreeDWidget1 = QWidget(self.page_manip)
        self.ThreeDWidget1.setObjectName(u"ThreeDWidget1")
        self.ThreeDWidget1.setStyleSheet(u"QWidget#ThreeDWidget1{\n"
"	border: 1px solid gray;\n"
"	border-radius: 10px;\n"
"}")

        self.horizontalLayout_7.addWidget(self.ThreeDWidget1)

        self.stackedWidget.addWidget(self.page_manip)
        self.page_program = QWidget()
        self.page_program.setObjectName(u"page_program")
        self.horizontalLayout_11 = QHBoxLayout(self.page_program)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.programWidget = QWidget(self.page_program)
        self.programWidget.setObjectName(u"programWidget")
        self.programWidget.setMinimumSize(QSize(220, 0))
        self.programWidget.setMaximumSize(QSize(220, 16777215))
        self.programWidget.setStyleSheet(u"QWidget#programWidget{\n"
"	border: 1px solid gray;\n"
"	border-radius: 10px;\n"
"}\n"
"QWidget{\n"
"	background-color: transparent;\n"
"}")
        self.verticalLayout_16 = QVBoxLayout(self.programWidget)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.modeWidget = QWidget(self.programWidget)
        self.modeWidget.setObjectName(u"modeWidget")
        self.modeWidget.setMinimumSize(QSize(0, 25))
        self.modeWidget.setMaximumSize(QSize(16777215, 25))
        self.modeWidget.setStyleSheet(u"")
        self.horizontalLayout_12 = QHBoxLayout(self.modeWidget)
        self.horizontalLayout_12.setSpacing(10)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(-1, 0, -1, 0)
        self.label_10 = QLabel(self.modeWidget)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setMaximumSize(QSize(45, 16777215))
        font8 = QFont()
        font8.setFamilies([u"Consolas"])
        font8.setPointSize(12)
        font8.setBold(True)
        self.label_10.setFont(font8)

        self.horizontalLayout_12.addWidget(self.label_10)

        self.recordBtn = QPushButton(self.modeWidget)
        self.recordBtn.setObjectName(u"recordBtn")
        font9 = QFont()
        font9.setPointSize(10)
        self.recordBtn.setFont(font9)
        self.recordBtn.setStyleSheet(u"QPushButton {\n"
"	background-color: transparent;\n"
"	border: 1px solid #cccccc;\n"
"	border-radius: 8px;\n"
"	padding: 0px\n"
"}\n"
"\n"
"QPushButton:checked {\n"
"	background-color: rgb(33, 100, 33);\n"
"	color: white;\n"
"	border: 1px solid #cccccc;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"	background-color: #666666;\n"
"	color: white;\n"
"	border: 1px solid #cccccc;\n"
"}")
        self.recordBtn.setCheckable(True)
        self.recordBtn.setChecked(True)
        self.recordBtn.setAutoExclusive(True)

        self.horizontalLayout_12.addWidget(self.recordBtn)

        self.execBtn = QPushButton(self.modeWidget)
        self.execBtn.setObjectName(u"execBtn")
        self.execBtn.setFont(font9)
        self.execBtn.setStyleSheet(u"QPushButton {\n"
"	background-color: transparent;\n"
"	border: 1px solid #cccccc;\n"
"	border-radius: 8px;\n"
"	padding: 0px\n"
"}\n"
"\n"
"QPushButton:checked {\n"
"	background-color: rgb(33, 100, 33);\n"
"	color: white;\n"
"	border: 1px solid #cccccc;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"	background-color: #666666;\n"
"	color: white;\n"
"	border: 1px solid #cccccc;\n"
"}")
        self.execBtn.setCheckable(True)
        self.execBtn.setAutoExclusive(True)

        self.horizontalLayout_12.addWidget(self.execBtn)


        self.verticalLayout_16.addWidget(self.modeWidget)

        self.label_16 = QLabel(self.programWidget)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setMinimumSize(QSize(0, 25))
        self.label_16.setMaximumSize(QSize(16777215, 25))
        self.label_16.setStyleSheet(u"QLabel {\n"
"    color: #d4d7dc;\n"
"    font-size: 15px;\n"
"    font-weight: bold;\n"
"    padding: 4px;\n"
"}\n"
"")
        self.label_16.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_16.addWidget(self.label_16)

        self.verticalLayout_12 = QVBoxLayout()
        self.verticalLayout_12.setSpacing(2)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.horizontalLayout_18 = QHBoxLayout()
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.xyControl = QWidget(self.programWidget)
        self.xyControl.setObjectName(u"xyControl")
        self.xyControl.setMinimumSize(QSize(160, 160))
        self.xyControl.setMaximumSize(QSize(160, 160))
        self.xyControl.setStyleSheet(u"background-color: rgb(80, 80, 80);")

        self.horizontalLayout_18.addWidget(self.xyControl)

        self.zControlWidget = QWidget(self.programWidget)
        self.zControlWidget.setObjectName(u"zControlWidget")
        self.zControlWidget.setMinimumSize(QSize(35, 0))
        self.zControlWidget.setMaximumSize(QSize(35, 16777215))
        self.zControlWidget.setStyleSheet(u"")
        self.verticalLayout_11 = QVBoxLayout(self.zControlWidget)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.zLineEditProgram = QLineEdit(self.zControlWidget)
        self.zLineEditProgram.setObjectName(u"zLineEditProgram")
        self.zLineEditProgram.setStyleSheet(u"QLineEdit{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}")

        self.verticalLayout_11.addWidget(self.zLineEditProgram)

        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalSpacer_9 = QSpacerItem(13, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_9)

        self.zSliderProgram = QSlider(self.zControlWidget)
        self.zSliderProgram.setObjectName(u"zSliderProgram")
        self.zSliderProgram.setOrientation(Qt.Orientation.Vertical)

        self.horizontalLayout_15.addWidget(self.zSliderProgram)

        self.horizontalSpacer_10 = QSpacerItem(13, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_10)


        self.verticalLayout_11.addLayout(self.horizontalLayout_15)

        self.label_35 = QLabel(self.zControlWidget)
        self.label_35.setObjectName(u"label_35")
        self.label_35.setMinimumSize(QSize(0, 20))
        self.label_35.setFont(font6)
        self.label_35.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_11.addWidget(self.label_35)


        self.horizontalLayout_18.addWidget(self.zControlWidget)


        self.verticalLayout_12.addLayout(self.horizontalLayout_18)

        self.muControlWidget = QWidget(self.programWidget)
        self.muControlWidget.setObjectName(u"muControlWidget")
        self.muControlWidget.setMinimumSize(QSize(0, 22))
        self.muControlWidget.setMaximumSize(QSize(16777215, 22))
        self.muControlWidget.setStyleSheet(u"")
        self.horizontalLayout_16 = QHBoxLayout(self.muControlWidget)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.horizontalLayout_16.setContentsMargins(-1, 1, -1, 1)
        self.muLineEditProgram = QLineEdit(self.muControlWidget)
        self.muLineEditProgram.setObjectName(u"muLineEditProgram")
        self.muLineEditProgram.setMinimumSize(QSize(35, 20))
        self.muLineEditProgram.setMaximumSize(QSize(35, 20))
        self.muLineEditProgram.setStyleSheet(u"QLineEdit{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}")

        self.horizontalLayout_16.addWidget(self.muLineEditProgram)

        self.muSliderProgram = QSlider(self.muControlWidget)
        self.muSliderProgram.setObjectName(u"muSliderProgram")
        self.muSliderProgram.setStyleSheet(u"")
        self.muSliderProgram.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_16.addWidget(self.muSliderProgram)

        self.label_36 = QLabel(self.muControlWidget)
        self.label_36.setObjectName(u"label_36")
        self.label_36.setMinimumSize(QSize(0, 20))
        self.label_36.setFont(font6)
        self.label_36.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_16.addWidget(self.label_36)


        self.verticalLayout_12.addWidget(self.muControlWidget)

        self.gripperControlWidget = QWidget(self.programWidget)
        self.gripperControlWidget.setObjectName(u"gripperControlWidget")
        self.gripperControlWidget.setMinimumSize(QSize(0, 22))
        self.gripperControlWidget.setMaximumSize(QSize(16777215, 22))
        self.gripperControlWidget.setStyleSheet(u"")
        self.horizontalLayout_17 = QHBoxLayout(self.gripperControlWidget)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.horizontalLayout_17.setContentsMargins(-1, 1, -1, 1)
        self.gripperLineEditProgram = QLineEdit(self.gripperControlWidget)
        self.gripperLineEditProgram.setObjectName(u"gripperLineEditProgram")
        self.gripperLineEditProgram.setMinimumSize(QSize(35, 20))
        self.gripperLineEditProgram.setMaximumSize(QSize(35, 20))
        self.gripperLineEditProgram.setStyleSheet(u"QLineEdit{\n"
"	color: white;\n"
"	font-size: 9pt;\n"
"	background: transparent;\n"
"	border: 1px solid gray;\n"
"}")

        self.horizontalLayout_17.addWidget(self.gripperLineEditProgram)

        self.gripperSliderProgram = QSlider(self.gripperControlWidget)
        self.gripperSliderProgram.setObjectName(u"gripperSliderProgram")
        self.gripperSliderProgram.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_17.addWidget(self.gripperSliderProgram)

        self.label_38 = QLabel(self.gripperControlWidget)
        self.label_38.setObjectName(u"label_38")
        self.label_38.setMinimumSize(QSize(0, 20))
        self.label_38.setFont(font6)
        self.label_38.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_17.addWidget(self.label_38)


        self.verticalLayout_12.addWidget(self.gripperControlWidget)


        self.verticalLayout_16.addLayout(self.verticalLayout_12)

        self.recordWidget = QWidget(self.programWidget)
        self.recordWidget.setObjectName(u"recordWidget")
        self.recordWidget.setMinimumSize(QSize(0, 32))
        self.recordWidget.setMaximumSize(QSize(16777215, 32))
        self.recordWidget.setStyleSheet(u"")
        self.horizontalLayout_13 = QHBoxLayout(self.recordWidget)
        self.horizontalLayout_13.setSpacing(6)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_12 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_13.addItem(self.horizontalSpacer_12)

        self.deleteRecording = QPushButton(self.recordWidget)
        self.deleteRecording.setObjectName(u"deleteRecording")
        self.deleteRecording.setMinimumSize(QSize(32, 32))
        self.deleteRecording.setMaximumSize(QSize(32, 32))
        self.deleteRecording.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        icon11 = QIcon()
        icon11.addFile(u":/images/media/minus.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.deleteRecording.setIcon(icon11)
        self.deleteRecording.setIconSize(QSize(32, 32))

        self.horizontalLayout_13.addWidget(self.deleteRecording)

        self.startRecording = QPushButton(self.recordWidget)
        self.startRecording.setObjectName(u"startRecording")
        self.startRecording.setMinimumSize(QSize(32, 32))
        self.startRecording.setMaximumSize(QSize(32, 32))
        self.startRecording.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        icon12 = QIcon()
        icon12.addFile(u":/images/media/play2.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.startRecording.setIcon(icon12)
        self.startRecording.setIconSize(QSize(32, 32))

        self.horizontalLayout_13.addWidget(self.startRecording)

        self.pauseRecording = QPushButton(self.recordWidget)
        self.pauseRecording.setObjectName(u"pauseRecording")
        self.pauseRecording.setMinimumSize(QSize(32, 32))
        self.pauseRecording.setMaximumSize(QSize(32, 32))
        self.pauseRecording.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        icon13 = QIcon()
        icon13.addFile(u":/images/media/pause2.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.pauseRecording.setIcon(icon13)
        self.pauseRecording.setIconSize(QSize(32, 32))

        self.horizontalLayout_13.addWidget(self.pauseRecording)

        self.stopRecording = QPushButton(self.recordWidget)
        self.stopRecording.setObjectName(u"stopRecording")
        self.stopRecording.setMinimumSize(QSize(32, 32))
        self.stopRecording.setMaximumSize(QSize(32, 32))
        self.stopRecording.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        icon14 = QIcon()
        icon14.addFile(u":/images/media/stop2.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.stopRecording.setIcon(icon14)
        self.stopRecording.setIconSize(QSize(32, 32))

        self.horizontalLayout_13.addWidget(self.stopRecording)

        self.addRecording = QPushButton(self.recordWidget)
        self.addRecording.setObjectName(u"addRecording")
        self.addRecording.setMinimumSize(QSize(32, 32))
        self.addRecording.setMaximumSize(QSize(32, 32))
        self.addRecording.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        icon15 = QIcon()
        icon15.addFile(u":/images/media/plus.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.addRecording.setIcon(icon15)
        self.addRecording.setIconSize(QSize(32, 32))

        self.horizontalLayout_13.addWidget(self.addRecording)

        self.horizontalSpacer_11 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_13.addItem(self.horizontalSpacer_11)


        self.verticalLayout_16.addWidget(self.recordWidget)

        self.execWidget = QWidget(self.programWidget)
        self.execWidget.setObjectName(u"execWidget")
        self.execWidget.setMinimumSize(QSize(0, 32))
        self.execWidget.setMaximumSize(QSize(16777215, 32))
        self.execWidget.setStyleSheet(u"")
        self.horizontalLayout_14 = QHBoxLayout(self.execWidget)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_14 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_14)

        self.previousExec = QPushButton(self.execWidget)
        self.previousExec.setObjectName(u"previousExec")
        self.previousExec.setMinimumSize(QSize(32, 32))
        self.previousExec.setMaximumSize(QSize(32, 32))
        self.previousExec.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        icon16 = QIcon()
        icon16.addFile(u":/images/media/backward.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.previousExec.setIcon(icon16)
        self.previousExec.setIconSize(QSize(32, 32))

        self.horizontalLayout_14.addWidget(self.previousExec)

        self.playExec = QPushButton(self.execWidget)
        self.playExec.setObjectName(u"playExec")
        self.playExec.setMinimumSize(QSize(32, 32))
        self.playExec.setMaximumSize(QSize(32, 32))
        self.playExec.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        self.playExec.setIcon(icon12)
        self.playExec.setIconSize(QSize(32, 32))

        self.horizontalLayout_14.addWidget(self.playExec)

        self.pauseExec = QPushButton(self.execWidget)
        self.pauseExec.setObjectName(u"pauseExec")
        self.pauseExec.setMinimumSize(QSize(32, 32))
        self.pauseExec.setMaximumSize(QSize(32, 32))
        self.pauseExec.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        self.pauseExec.setIcon(icon13)
        self.pauseExec.setIconSize(QSize(32, 32))

        self.horizontalLayout_14.addWidget(self.pauseExec)

        self.stopExec = QPushButton(self.execWidget)
        self.stopExec.setObjectName(u"stopExec")
        self.stopExec.setMinimumSize(QSize(32, 32))
        self.stopExec.setMaximumSize(QSize(32, 32))
        self.stopExec.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        self.stopExec.setIcon(icon14)
        self.stopExec.setIconSize(QSize(32, 32))

        self.horizontalLayout_14.addWidget(self.stopExec)

        self.nextExec = QPushButton(self.execWidget)
        self.nextExec.setObjectName(u"nextExec")
        self.nextExec.setMinimumSize(QSize(32, 32))
        self.nextExec.setMaximumSize(QSize(32, 32))
        self.nextExec.setStyleSheet(u"QPushButton{\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: #444444;\n"
"	color: white;\n"
"	border: 1px solid #555555;\n"
"}\n"
"QPushButton:pressed {\n"
"	background-color: transparent;\n"
"	color: white;\n"
"	border: 1px solid #444444;\n"
"}")
        icon17 = QIcon()
        icon17.addFile(u":/images/media/forward.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.nextExec.setIcon(icon17)
        self.nextExec.setIconSize(QSize(32, 32))

        self.horizontalLayout_14.addWidget(self.nextExec)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_13)


        self.verticalLayout_16.addWidget(self.execWidget)

        self.fileWidget = QHBoxLayout()
        self.fileWidget.setSpacing(10)
        self.fileWidget.setObjectName(u"fileWidget")
        self.fileWidget.setContentsMargins(4, -1, 4, -1)
        self.importBtn = QPushButton(self.programWidget)
        self.importBtn.setObjectName(u"importBtn")
        self.importBtn.setMinimumSize(QSize(80, 30))
        self.importBtn.setMaximumSize(QSize(80, 30))
        font10 = QFont()
        font10.setPointSize(11)
        self.importBtn.setFont(font10)
        self.importBtn.setStyleSheet(u"QPushButton {\n"
"	background-color: transparent;\n"
"	border: 1px solid #cccccc;\n"
"	border-radius: 8px;\n"
"	padding: 0px\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"	background-color: #666666;\n"
"	color: white;\n"
"	border: 1px solid #cccccc;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"	background-color: rgb(33, 100, 33);\n"
"	color: white;\n"
"	border: 1px solid #cccccc;\n"
"}\n"
"")
        icon18 = QIcon()
        icon18.addFile(u":/images/media/import.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.importBtn.setIcon(icon18)
        self.importBtn.setIconSize(QSize(22, 22))

        self.fileWidget.addWidget(self.importBtn)

        self.fileLabel = QLabel(self.programWidget)
        self.fileLabel.setObjectName(u"fileLabel")
        self.fileLabel.setMinimumSize(QSize(0, 30))
        self.fileLabel.setMaximumSize(QSize(16777215, 30))
        self.fileLabel.setFont(font10)
        self.fileLabel.setStyleSheet(u"QLabel{\n"
"	background-color: transparent;\n"
"	border: 1px solid #cccccc;\n"
"	border-radius: 8px;\n"
"}")

        self.fileWidget.addWidget(self.fileLabel)


        self.verticalLayout_16.addLayout(self.fileWidget)

        self.label_17 = QLabel(self.programWidget)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setMinimumSize(QSize(0, 25))
        self.label_17.setMaximumSize(QSize(16777215, 25))
        self.label_17.setStyleSheet(u"QLabel {\n"
"    color: #d4d7dc;\n"
"    font-size: 15px;\n"
"    font-weight: bold;\n"
"    padding: 4px;\n"
"}\n"
"")
        self.label_17.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_16.addWidget(self.label_17)

        self.positionlistWidget = QListWidget(self.programWidget)
        self.positionlistWidget.setObjectName(u"positionlistWidget")
        self.positionlistWidget.setStyleSheet(u"QListWidget {\n"
"    background: #2b2d31;\n"
"    border: 1px solid #3a3c3f;\n"
"    border-radius: 6px;\n"
"    padding: 4px;\n"
"    outline: none;\n"
"}\n"
"\n"
"QListWidget::item {\n"
"    background: #34363b;\n"
"    color: white;\n"
"    padding: 12px;          /* makes items bigger */\n"
"    margin: 4px;            /* spacing between items */\n"
"    border-radius: 6px;     /* rounded corners */\n"
"}\n"
"\n"
"QListWidget::item:hover {\n"
"    background: #3f4250;\n"
"}\n"
"\n"
"QListWidget::item:selected {\n"
"    background: #4b6ea7;    /* selection color */\n"
"    color: white;\n"
"}\n"
"\n"
"QListWidget::item:selected:!active {\n"
"    background: #4b6ea7;\n"
"}\n"
"\n"
"QListWidget::item:pressed {\n"
"    background: #2b3143;\n"
"}\n"
"")

        self.verticalLayout_16.addWidget(self.positionlistWidget)


        self.horizontalLayout_11.addWidget(self.programWidget)

        self.ThreeDWidget2 = QWidget(self.page_program)
        self.ThreeDWidget2.setObjectName(u"ThreeDWidget2")
        self.ThreeDWidget2.setStyleSheet(u"")

        self.horizontalLayout_11.addWidget(self.ThreeDWidget2)

        self.stackedWidget.addWidget(self.page_program)
        self.page_draw = QWidget()
        self.page_draw.setObjectName(u"page_draw")
        self.label_6 = QLabel(self.page_draw)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setGeometry(QRect(240, 240, 151, 71))
        font11 = QFont()
        font11.setPointSize(40)
        self.label_6.setFont(font11)
        self.stackedWidget.addWidget(self.page_draw)
        self.page_chess = QWidget()
        self.page_chess.setObjectName(u"page_chess")
        self.label_5 = QLabel(self.page_chess)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(230, 250, 151, 71))
        self.label_5.setFont(font11)
        self.stackedWidget.addWidget(self.page_chess)

        self.verticalLayout_3.addWidget(self.stackedWidget)


        self.horizontalLayout_3.addWidget(self.central_widget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.SidebarBtn.toggled.connect(self.icon_only_widget.setHidden)
        self.SidebarBtn.toggled.connect(self.icon_name_widget.setVisible)
        self.ChessBtn1.toggled.connect(self.ChessBtn2.setChecked)
        self.DrawBtn1.toggled.connect(self.DrawBtn2.setChecked)
        self.ProgramBtn1.toggled.connect(self.ProgramBtn2.setChecked)
        self.ManipBtn1.toggled.connect(self.ManipBtn2.setChecked)
        self.HomeBtn1.toggled.connect(self.HomeBtn2.setChecked)
        self.HomeBtn2.toggled.connect(self.HomeBtn1.setChecked)
        self.ManipBtn2.toggled.connect(self.ManipBtn1.setChecked)
        self.ProgramBtn2.toggled.connect(self.ProgramBtn1.setChecked)
        self.DrawBtn2.toggled.connect(self.DrawBtn1.setChecked)
        self.ChessBtn2.toggled.connect(self.ChessBtn1.setChecked)
        self.MinimizeBtn.clicked.connect(MainWindow.showMinimized)
        self.CloseBtn.clicked.connect(MainWindow.close)
        self.recordBtn.toggled.connect(self.fileLabel.setHidden)
        self.recordBtn.toggled.connect(self.execWidget.setHidden)
        self.execBtn.toggled.connect(self.recordWidget.setHidden)
        self.execBtn.toggled.connect(self.execWidget.setVisible)
        self.recordBtn.toggled.connect(self.importBtn.setHidden)
        self.execBtn.toggled.connect(self.fileLabel.setVisible)
        self.execBtn.toggled.connect(self.importBtn.setVisible)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label.setText("")
        self.HomeBtn1.setText("")
        self.ManipBtn1.setText("")
        self.ProgramBtn1.setText("")
        self.DrawBtn1.setText("")
        self.ChessBtn1.setText("")
        self.GithubBtn1.setText("")
        self.label_2.setText("")
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Menu", None))
        self.HomeBtn2.setText(QCoreApplication.translate("MainWindow", u"    Home", None))
        self.ManipBtn2.setText(QCoreApplication.translate("MainWindow", u"    Manip", None))
        self.ProgramBtn2.setText(QCoreApplication.translate("MainWindow", u"  Program", None))
        self.DrawBtn2.setText(QCoreApplication.translate("MainWindow", u"    Draw", None))
        self.ChessBtn2.setText(QCoreApplication.translate("MainWindow", u"  Chess AI", None))
        self.GithubBtn2.setText(QCoreApplication.translate("MainWindow", u"  Github", None))
        self.SidebarBtn.setText("")
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Graphical Interface - Projet 3", None))
        self.MinimizeBtn.setText("")
        self.MaximizeBtn.setText("")
        self.CloseBtn.setText("")
        self.label_7.setText("")
        self.label_15.setText("")
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"COM Ports", None))
        self.connectBtn.setText(QCoreApplication.translate("MainWindow", u"Connect", None))
        self.disconnectBtn.setText(QCoreApplication.translate("MainWindow", u"Disconnect", None))
        self.refreshBtn.setText(QCoreApplication.translate("MainWindow", u"Refresh", None))
        self.quitBtn.setText(QCoreApplication.translate("MainWindow", u"Quit", None))
        self.renderLabel.setText("")
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"\u2013\u2013\u2013\u2013\u2013\u2013  Cartesian Coordinates  \u2013\u2013\u2013\u2013\u2013\u2013", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"X :", None))
        self.xlineEdit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.xBtn.setText("")
        self.xLabel.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.xminLabel.setText(QCoreApplication.translate("MainWindow", u"-200", None))
        self.xmaxLabel.setText(QCoreApplication.translate("MainWindow", u"200", None))
        self.label_31.setText(QCoreApplication.translate("MainWindow", u"Y :", None))
        self.ylineEdit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.yBtn.setText("")
        self.yLabel.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.yminLabel.setText(QCoreApplication.translate("MainWindow", u"-200", None))
        self.ymaxLabel.setText(QCoreApplication.translate("MainWindow", u"200", None))
        self.label_34.setText(QCoreApplication.translate("MainWindow", u"Z :", None))
        self.zlineEdit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.zBtn.setText("")
        self.zLabel.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.zminLabel.setText(QCoreApplication.translate("MainWindow", u"-200", None))
        self.zmaxLabel.setText(QCoreApplication.translate("MainWindow", u"200", None))
        self.label_37.setText(QCoreApplication.translate("MainWindow", u"\u03bc :", None))
        self.mulineEdit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.muBtn.setText("")
        self.muLabel.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.muminLabel.setText(QCoreApplication.translate("MainWindow", u"-200", None))
        self.mumaxLabel.setText(QCoreApplication.translate("MainWindow", u"200", None))
        self.sendallBtn.setText(QCoreApplication.translate("MainWindow", u"Send all coordinates", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013  Joint Angles  \u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013", None))
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"\u2013\u2013\u2013\u2013\u2013\u2013\u2013  Gripper Activation  \u2013\u2013\u2013\u2013\u2013\u2013\u2013", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Mode:", None))
        self.recordBtn.setText(QCoreApplication.translate("MainWindow", u"Record", None))
        self.execBtn.setText(QCoreApplication.translate("MainWindow", u"Execute", None))
        self.label_16.setText(QCoreApplication.translate("MainWindow", u"\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013  Controls  \u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013", None))
        self.zLineEditProgram.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.label_35.setText(QCoreApplication.translate("MainWindow", u"Z", None))
        self.muLineEditProgram.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.label_36.setText(QCoreApplication.translate("MainWindow", u"\u03bc", None))
        self.gripperLineEditProgram.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.label_38.setText(QCoreApplication.translate("MainWindow", u"G", None))
        self.deleteRecording.setText("")
        self.startRecording.setText("")
        self.pauseRecording.setText("")
        self.stopRecording.setText("")
        self.addRecording.setText("")
        self.previousExec.setText("")
        self.playExec.setText("")
        self.pauseExec.setText("")
        self.stopExec.setText("")
        self.nextExec.setText("")
        self.importBtn.setText(QCoreApplication.translate("MainWindow", u" Import", None))
        self.fileLabel.setText(QCoreApplication.translate("MainWindow", u"No file selected", None))
        self.label_17.setText(QCoreApplication.translate("MainWindow", u"\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013  Position List  \u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013\u2013", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Draw", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Chess", None))
    # retranslateUi

