import os
import sys
import logging
import webbrowser
import qdarktheme
import subprocess
import platform
from .behavior import GuiBehavior
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtGui import QIcon, QStandardItemModel, QPixmap, QFontDatabase, QFont, QColor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGridLayout, QPushButton,  QWidget,
                             QTableView,  QHBoxLayout, QVBoxLayout, QAbstractItemView,
                             QAbstractScrollArea, QLabel, QLineEdit, QStackedWidget, QToolTip,
                             QFormLayout, QListWidget, QComboBox, QSizePolicy, QHeaderView, QHeaderView, QStyledItemDelegate)
from .helpers import absp, database_init


class Gui:
    def __init__(self):
        # Init GuiBehavior()
        self.app_name = 'Retro Passion gamer'
        self.font = None
        self.table_model = None

        # Init DB
        database_init()

        # Create App
        qdarktheme.enable_hi_dpi()
        app = QApplication(sys.argv)
        qdarktheme.setup_theme("light")

        font_database = QFontDatabase()
        font_id = font_database.addApplicationFont(
            absp("res/fonts/NanumGothic.ttf"))
        if font_id == -1:
            logging.debug("Font load failed!")
        else:
            font_families = font_database.applicationFontFamilies(font_id)
            self.font = QFont(font_families[0], 10)

        app.setWindowIcon(QIcon(absp('res/icon/ico.ico')))
        app.setStyle('Fusion')
        self.app = app

        # Initialize self.main
        self.main_init()
        self.actions = GuiBehavior(self)
        app.aboutToQuit.connect(self.actions.handle_exit)

        # Create Windows
        self.main_win()
        self.settings_win()
        self.actions.handle_init()

        # Change App Theme to saved one (Palette)
        if self.actions.settings:
            self.actions.change_device(self.actions.settings[1])

        # 셀 편집 완료 시 이벤트 연결
        self.table_model.itemChanged.connect(self.handle_item_changed)
        # Connect the model signals to update the status bar
        self.table_model.rowsInserted.connect(self.update_titlebar)
        self.table_model.rowsRemoved.connect(self.update_titlebar)

        sys.exit(app.exec_())

    def update_titlebar(self):
        count = self.table_model.rowCount()
        title_text = f"{self.app_name} [ 현재 조회된 롬 파일 갯수: {count} ]"
        self.main.setWindowTitle(title_text)

    def main_init(self):
        # Define Main Window
        self.main = QMainWindow()
        self.main.setWindowTitle(self.app_name)
        self.main.setFont(self.font)

        widget = QWidget(self.main)
        self.main.setCentralWidget(widget)

        # Create Grid
        grid = QGridLayout()

        # Table
        self.table = QTableView()
        headers = ['', '플랫폼', '썸네일', '파일 경로', '용량', '원본 파일명', '수정 파일명']
        self.table.setSizeAdjustPolicy(
            QAbstractScrollArea.AdjustToContentsOnFirstShow)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().hide()

        # 테이블 간격 조정
        self.table_model = QStandardItemModel()
        self.table_model.setHorizontalHeaderLabels(headers)

        self.table.setModel(self.table_model)

        # 폰트 변경
        if self.font:
            self.table.setFont(self.font)

        # 컬럼 사이즈 조절
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 46)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 145)

        # '변경될 파일명' 열을 오름차순으로 정렬합니다.
        self.table.sortByColumn(0, Qt.AscendingOrder)
        self.table.clicked.connect(self.on_cell_clicked)

        # Append widgets to grid
        grid.addWidget(self.table, 1, 0, 1, 3)

        # Add buttons to Horizontal Layout
        hbox = QHBoxLayout()
        # Bottom Buttons
        settings_btn = QPushButton(
            QIcon(absp('res/icon/settings.svg')), ' 설정')
        settings_btn.clicked.connect(lambda: self.settings.show(
        ) if not self.settings.isVisible() else self.settings.raise_())

        self.main.refresh_btn = QPushButton(
            QIcon(absp('res/icon/refresh-cw.svg')), ' 롬 폴더 검색')
        self.main.remove_btn = QPushButton(
            QIcon(absp('res/icon/trash-2.svg')), ' 선택항목 제외')
        self.main.edit_btn = QPushButton(
            QIcon(absp('res/icon/edit.svg')), ' 실제 파일에 적용')

        settings_btn.setFont(self.font)
        self.main.refresh_btn.setFont(self.font)
        self.main.edit_btn.setFont(self.font)
        self.main.remove_btn.setFont(self.font)

        hbox.addWidget(settings_btn)
        hbox.addWidget(self.main.refresh_btn)
        hbox.addWidget(self.main.remove_btn)
        hbox.addWidget(self.main.edit_btn)

        self.main.setWindowFlags(self.main.windowFlags()
                                 & Qt.CustomizeWindowHint)

        grid.addLayout(hbox, 2, 0, 1, 3)
        widget.setLayout(grid)
        self.main.resize(716, 415)
        # Set size policies for the table
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 로딩 오버레이 위젯 생성
        self.main.loading_overlay = QWidget(self.main)
        self.main.loading_overlay.setGeometry(
            0, 0, self.main.width(), self.main.height())
        self.main.loading_overlay.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.6);")
        self.main.loading_overlay.setVisible(False)

        # SVG 이미지를 로딩 오버레이 위젯에 추가
        svg_widget = QSvgWidget(absp('res/icon/loading_image.svg'))
        svg_widget.setGeometry(0, 0, 100, 100)  # 중앙에 표시하려면 위치와 크기 조정이 필요합니다.
        svg_layout = QVBoxLayout(self.main.loading_overlay)
        svg_layout.addWidget(svg_widget)
        svg_layout.setAlignment(Qt.AlignCenter)

        self.hoverEventFilter = HoverEventFilter(self.table)
        self.table.viewport().installEventFilter(self.hoverEventFilter)
        self.table.setMouseTracking(True)

        self.main.show()

    def main_win(self):
        self.main.refresh_btn.clicked.connect(self.actions.roms_scan)
        self.main.remove_btn.clicked.connect(self.actions.roms_remove)
        self.main.edit_btn.clicked.connect(self.actions.roms_replace)

    # 로딩 오버레이를 활성화하는 메서드

    def show_loading_overlay(self):
        if self.main:
            self.main.loading_overlay.setVisible(True)

    # 로딩 오버레이를 비활성화하는 메서드
    def hide_loading_overlay(self):
        if self.main:
            self.main.loading_overlay.setVisible(False)

    def settings_win(self):
        # Define Settings Win
        self.settings = QMainWindow(self.main)
        self.settings.setWindowTitle('설정')

        # Create StackedWidget and Selection List
        self.stacked_settings = QStackedWidget()
        self.settings_list = QListWidget()
        self.settings_list.setFixedWidth(110)
        self.settings_list.addItems(['기본 설정', '프로그램 정보'])
        self.settings_list.clicked.connect(self.actions.select_settings)
        self.settings_list.setCurrentRow(0)

        # Central Widget
        central_widget = QWidget()
        hbox = QHBoxLayout()
        hbox.addWidget(self.settings_list)

        hbox.addWidget(self.stacked_settings)
        central_widget.setLayout(hbox)
        self.settings.setCentralWidget(central_widget)

        '''
        Child widget
        Behavior Settings
        '''

        behavior_settings = QWidget()
        self.stacked_settings.addWidget(behavior_settings)

        # Main Layouts
        vbox = QVBoxLayout()
        vbox.setAlignment(Qt.AlignTop)
        form_layout = QFormLayout()

        # 기종 선택
        form_layout.addRow(QLabel('기종 선택:'))

        self.device_select = QComboBox()
        self.device_select.addItems(['SF2000'])
        self.device_select.currentIndexChanged.connect(
            self.actions.change_device)
        if self.actions.settings is not None:
            self.device_select.setCurrentIndex(self.actions.settings[1])
        form_layout.addRow(self.device_select)

        # Change Directory
        form_layout.addRow(QLabel('롬 파일(ROMS) 경로:'))

        dl_directory_btn = QPushButton('폴더 선택..')
        dl_directory_btn.clicked.connect(self.actions.set_dl_directory)

        self.dl_directory_input = QLineEdit()
        if self.actions.settings is not None:
            self.dl_directory_input.setText(self.actions.settings[0])
            self.dl_directory_input.repaint()
        self.dl_directory_input.setReadOnly(True)

        form_layout.addRow(dl_directory_btn, self.dl_directory_input)

        # Bottom Buttons
        save_settings = QPushButton('저장')
        save_settings.clicked.connect(self.actions.save_settings)

        vbox.addLayout(form_layout)
        vbox.addStretch()
        vbox.addWidget(save_settings)
        behavior_settings.setLayout(vbox)

        '''
        Child widget
        About
        '''

        about_settings = QWidget()
        self.stacked_settings.addWidget(about_settings)

        about_layout = QGridLayout()
        about_layout.setAlignment(Qt.AlignCenter)

        logo = QLabel()
        logo.setPixmap(QPixmap(absp('res/icon/ico.svg')))
        logo.setAlignment(Qt.AlignCenter)
        logo.setMargin(20)

        text = QLabel(self.app_name)
        text.setStyleSheet('font-weight: bold; color: #4256AD')

        github_btn = QPushButton(QIcon(absp('res/icon/github.svg')), '')
        github_btn.setFixedWidth(32)
        github_btn.clicked.connect(lambda: webbrowser.open(
            'https://github.com/jshsakura/passion-gamer'))

        about_layout.addWidget(logo, 0, 0, 1, 0)
        about_layout.addWidget(github_btn, 1, 0)
        about_layout.addWidget(text, 1, 1)
        about_settings.setLayout(about_layout)

    def handle_item_changed(self, item):
        # 아이템이 속한 모델을 가져옵니다.
        # 변경된 아이템의 행과 열 번호를 얻습니다.
        row = item.row()
        column = item.column()
        # 셀의 값이 변경되면 호출되는 메서드

        if column == 6:  # 수정된 아이템이 3번 열에 있는 경우
            other_item = item.model().item(row, 5)
            if other_item.text() == item.text():
                item.setBackground(QColor(230, 255, 230))  # 이미 매칭된 경우
            elif not item.text():  # 셀의 값이 비어 있는 경우
                item.setBackground(QColor(255, 179, 179))  # 배경색을 빨간색으로 설정
            else:
                item.setBackground(QColor(255, 255, 255))  # 배경색을 기본으로 설정

    def on_cell_clicked(self, index):
        row = index.row()
        column = index.column()
        if column == 3:
            # 셀의 내용을 가져옵니다.
            file_path = self.table_model.item(row, column).text()
            self.open_in_explorer(file_path)

    def open_in_explorer(self, file_path):
        folder_path = os.path.dirname(file_path)  # 파일의 폴더 경로를 얻습니다.
        # OS에 따라 명령어를 다르게 실행합니다.
        if platform.system() == 'Windows':
            # 파일을 강조 표시하려면 /select 옵션을 사용합니다.
            subprocess.Popen(f'explorer /select,"{file_path}"')
        elif platform.system() == 'Darwin':  # macOS의 경우
            subprocess.Popen(['open', folder_path])
        elif platform.system() == 'Linux':
            subprocess.Popen(['xdg-open', folder_path])


class HoverEventFilter(QObject):
    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table

    def eventFilter(self, obj, event):
        if event.type() == QEvent.HoverMove:  # 호버 움직임 감지
            point = event.pos()  # 호버 위치 얻기
            logging.debug(point)
            index = self.table.indexAt(point)  # 호버 위치의 셀 인덱스 얻기
            if index.isValid() and index.column() == 2:  # 두 번째 컬럼이면
                # 툴팁 표시
                QToolTip.showText(event.globalPos(),
                                  "이곳을 클릭하여 탐색기를 엽니다.", self.main.table)
            else:
                QToolTip.hideText()
            return True
        return super().eventFilter(obj, event)
