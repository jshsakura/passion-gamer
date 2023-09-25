import math
import os
import sys
import logging
import time
import webbrowser
import qdarktheme
import subprocess
import platform
from .behavior import GuiBehavior
from PyQt5.QtCore import Qt, QObject, QEvent
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtGui import QIcon, QStandardItemModel, QPixmap, QFontDatabase, QFont, QColor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGridLayout, QPushButton,  QWidget,
                             QTableView,  QHBoxLayout, QVBoxLayout, QAbstractItemView, QMenu, QAction,
                             QAbstractScrollArea, QLabel, QLineEdit, QStackedWidget, QToolTip,
                             QFormLayout, QListWidget, QComboBox, QSizePolicy, QHeaderView, QHeaderView, QStyledItemDelegate)
from .helpers import absp, database_init, alert


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
        count = len(self.actions.all_roms_list)
        title_text = f"{self.app_name} [ 전체 롬 파일 갯수: {count} ]"
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

        headers = ['', '플랫폼', '썸네일', '파일 경로',
                   '상태 코드', '상태', '용량', '원본 파일명', '수정 파일명']
        self.table.setSizeAdjustPolicy(
            QAbstractScrollArea.AdjustToContentsOnFirstShow)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)

        # 헤더 클릭 이벤트 핸들러 설정
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
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
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 80)
        self.table.setColumnWidth(6, 80)
        self.table.setColumnWidth(7, 145)

        # 파일 경로 컬럼 숨김
        self.table.setColumnHidden(4, True)

        # '원본 파일명' 열을 오름차순으로 정렬합니다.
        self.table.sortByColumn(7, Qt.AscendingOrder)
        # 기본 sort 버튼 숨김
        self.table.horizontalHeader().setSortIndicatorShown(False)
        self.table.setSortingEnabled(False)
        # 클릭 이벤트 핸들러 연결
        self.table.clicked.connect(self.on_cell_clicked)
        # 더블클릭 이벤트 핸들러 연결
        self.table.doubleClicked.connect(self.on_item_double_clicked)

        # Add buttons to Horizontal Layout
        hbox = QHBoxLayout()
        # Bottom Buttons
        self.main.settings_btn = QPushButton(
            QIcon(absp('res/icon/settings.svg')), ' 설정')
        self.main.settings_btn.clicked.connect(lambda: self.settings.show(
        ) if not self.settings.isVisible() else self.settings.raise_())
        self.main.theme_btn = QPushButton(
            QIcon(absp('res/icon/smile.svg')), ' 드드라 테마')

        self.main.refresh_btn = QPushButton(
            QIcon(absp('res/icon/refresh-cw.svg')), ' 롬 파일 검색')
        self.main.remove_cn_btn = QPushButton(
            QIcon(absp('res/icon/alert-triangle.svg')), ' 중국 롬 검색')
        self.main.except_btn = QPushButton(
            QIcon(absp('res/icon/file-minus.svg')), ' 선택항목 제외')
        self.main.remove_btn = QPushButton(
            QIcon(absp('res/icon/trash-2.svg')), ' 선택항목 삭제')
        self.main.edit_btn = QPushButton(
            QIcon(absp('res/icon/check-square.svg')), ' 수정사항 적용')

        self.main.settings_btn.setFont(self.font)
        self.main.theme_btn.setFont(self.font)
        self.main.refresh_btn.setFont(self.font)
        self.main.remove_cn_btn.setFont(self.font)
        self.main.except_btn.setFont(self.font)
        self.main.remove_btn.setFont(self.font)
        self.main.edit_btn.setFont(self.font)

        self.main.settings_btn.setStyleSheet("color: #333333;")
        self.main.theme_btn.setStyleSheet("color: #333333;")
        self.main.refresh_btn.setStyleSheet("color: #333333;")
        self.main.remove_cn_btn.setStyleSheet("color: #333333;")
        self.main.except_btn.setStyleSheet("color: #333333;")
        self.main.remove_btn.setStyleSheet("color: #333333;")
        self.main.edit_btn.setStyleSheet("color: #333333;")

        hbox.addWidget(self.main.refresh_btn)
        hbox.addWidget(self.main.remove_cn_btn)
        hbox.addWidget(self.main.except_btn)
        hbox.addWidget(self.main.remove_btn)
        hbox.addWidget(self.main.edit_btn)

        self.main.page_label = QLabel()
        self.main.page_prev_btn = QPushButton()
        self.main.page_next_btn = QPushButton()

        # 버튼 아이콘 설정
        self.main.page_prev_btn.setIcon(
            QIcon(absp('res/icon/chevron-left.svg')))
        self.main.page_next_btn.setIcon(
            QIcon(absp('res/icon/chevron-right.svg')))

        self.main.page_label.setFont(self.font)
        self.main.page_prev_btn.setFont(self.font)
        self.main.page_next_btn.setFont(self.font)
        self.main.page_prev_btn.setEnabled(False)
        self.main.page_next_btn.setEnabled(False)
        self.main.page_prev_btn.setStyleSheet("color: #333333;")
        self.main.page_next_btn.setStyleSheet("color: #333333;")

        # 페이징 라벨 추가
        self.main.page_label.setAlignment(Qt.AlignCenter)

        # 아래에 페이지 관련 위젯을 추가
        button_container = QWidget(self.main)
        button_layout = QGridLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.main.page_prev_btn, 1, 0)
        button_layout.addWidget(self.main.page_next_btn, 1, 1)

        grid.addWidget(self.main.settings_btn, 1, 0)
        grid.addWidget(self.main.theme_btn, 1, 1)
        grid.addWidget(self.main.page_label, 1, 3)
        grid.addWidget(button_container, 1, 4)

        self.main.setWindowFlags(self.main.windowFlags()
                                 & Qt.CustomizeWindowHint)

        # Append widgets to grid
        grid.addWidget(self.table, 2, 0, 1, 5)
        grid.addLayout(hbox, 3, 0, 1, 5)
        widget.setLayout(grid)
        self.main.resize(720, 450)
        # Set size policies for the table
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 로딩 오버레이 위젯 생성
        self.main.loading_overlay = LoadingOverlay(self.main)
        # LoadingOverlay 클래스를 부모 위젯에 추가한 후 이벤트 필터를 설치
        # self.main.setCentralWidget(widget)
        self.main.installEventFilter(self.main.loading_overlay)

        # 메뉴바 생성
        # menubar = self.main.menuBar()

        # # 파일 메뉴 추가
        # file_menu = menubar.addMenu('추가작업')
        # theme_action = QAction('한글 테마 적용', self.main)
        # shortcut_action = QAction('한글 숏컷 적용', self.main)
        # file_menu.addAction(theme_action)
        # file_menu.addAction(shortcut_action)

        self.main.show()

    def main_win(self):
        self.main.theme_btn.clicked.connect(self.actions.set_theme)
        self.main.refresh_btn.clicked.connect(self.actions.roms_scan)
        self.main.remove_cn_btn.clicked.connect(self.actions.roms_unnecessary)
        self.main.except_btn.clicked.connect(self.actions.roms_except)
        self.main.remove_btn.clicked.connect(self.actions.roms_remove)
        self.main.edit_btn.clicked.connect(self.actions.roms_replace)
        # 페이지 이전/다음 버튼 클릭 시 해당 함수 연결
        self.main.page_prev_btn.clicked.connect(self.actions.prev_page)
        self.main.page_next_btn.clicked.connect(self.actions.next_page)

        self.table.setMouseTracking(True)

    # 로딩 오버레이를 활성화하는 메서드
    def show_loading_overlay(self):
        if self.main:
            self.main.loading_overlay.show()
            self.main.settings_btn.setEnabled(False)
            self.main.theme_btn.setEnabled(False)
            self.main.refresh_btn.setEnabled(False)
            self.main.except_btn.setEnabled(False)
            self.main.remove_btn.setEnabled(False)
            self.main.remove_cn_btn.setEnabled(False)
            self.main.edit_btn.setEnabled(False)
            self.main.page_prev_btn.setEnabled(False)
            self.main.page_next_btn.setEnabled(False)

    # 로딩 오버레이를 비활성화하는 메서드
    def hide_loading_overlay(self):
        if self.main:
            self.main.loading_overlay.hide()
            self.main.settings_btn.setEnabled(True)
            self.main.theme_btn.setEnabled(True)
            self.main.refresh_btn.setEnabled(True)
            self.main.except_btn.setEnabled(True)
            self.main.remove_btn.setEnabled(True)
            self.main.remove_cn_btn.setEnabled(True)
            self.main.edit_btn.setEnabled(True)
            self.main.page_prev_btn.setEnabled(True)
            self.main.page_next_btn.setEnabled(True)
            # 스크롤바 초기화
            self.table.verticalScrollBar().setValue(0)

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

        if column == 5:
            status = item.model().item(row, 4).text()

            if status == '0':
                item.model().item(row, 5).setForeground(QColor(255, 51, 51))
            elif status == '1':
                item.model().item(row, 5).setForeground(QColor(0, 204, 153))
            elif status == '2':
                item.model().item(row, 5).setForeground(QColor(0, 204, 153))
            elif status == '3':
                item.model().item(row, 5).setForeground(QColor(0, 204, 153))
            elif status == '4':
                item.model().item(row, 5).setForeground(QColor(255, 51, 51))
            elif status == '5':
                item.model().item(row, 5).setForeground(QColor(255, 153, 0))
            else:
                item.model().item(row, 5).setForeground(QColor(128, 128, 128))

        elif column == 8:  # 수정된 아이템이 있는 경우
            platform_name = item.model().item(row, 1).text()
            original_filename = item.model().item(row, 7).text()
            file_path = item.model().item(row, 3).text()
            new_filename = item.text()
            action = 'update'

            if original_filename == new_filename:
                item.setBackground(QColor(230, 255, 230))  # 이미 매칭된 경우
            elif not new_filename:  # 셀의 값이 비어 있는 경우
                item.model().item(row, 4).setText('0')
                item.model().item(row, 5).setText('사용자 입력')
                item.model().item(row, 5).setForeground(QColor(255, 51, 51))
                item.setBackground(QColor(255, 179, 179))  # 배경색을 빨간색으로 설정
                self.actions.update_row_from_all_roms_list(
                    file_path, new_filename, action)
                # self.actions.populate_table_with_roms()
            else:
                item.model().item(row, 4).setText('2')
                item.model().item(row, 5).setText('수정 대기')
                item.model().item(row, 5).setForeground(QColor(0, 204, 153))
                item.setBackground(QColor(255, 255, 255))  # 배경색을 기본으로 설정
                self.actions.update_row_from_all_roms_list(
                    file_path, new_filename, action)
                # self.actions.populate_table_with_roms()

    def on_cell_clicked(self, index):
        row = index.row()
        column = index.column()
        if column == 3:
            # 셀의 내용을 가져옵니다.
            file_path = self.table_model.item(row, column).text()
            self.open_in_explorer(file_path)

    def on_item_double_clicked(self, index):
        row = index.row()
        column = index.column()
        if column == 8 and self.table_model.item(row, 1).text() == 'ARCADE':
            alert(
                '[ARCADE] 플랫폼은 사용자가 직접 파일명을 수정할 수 없습니다.\n롬 폴더에 한글명이 사전 작업 된 바로가기 파일로 대체하는 방식으로 적용됩니다.')
        elif column == 8 and self.table_model.item(row, column).font().italic():
            alert(
                '선택하신 롬은 플랫폼 메인화면에 기본 [숏컷]으로 지정된 게임입니다.\n만약 파일명을 수정하면 설정 파일의 내용을 직접 수정해야하니 주의가 필요합니다!')

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

    def on_header_clicked(self, logical_index):
        # 헤더 클릭 시 호출되는 함수
        order = self.table.horizontalHeader().sortIndicatorOrder()

        # column 변수를 어떻게 정의했는지에 따라 정렬합니다.
        column = {1: "platform_name", 3: "file_path", 5: "status_name", 6: "file_byte_size",
                  7: "origin_filename", 8: "new_filename"}

        # 정렬 불가능한 열은 볼 것도 없음
        if not logical_index in column:
            self.table.horizontalHeader().setSortIndicatorShown(False)
            self.table.setSortingEnabled(False)
            return
        else:
            self.table.horizontalHeader().setSortIndicatorShown(True)
            self.table.setSortingEnabled(True)

        if self.actions:
            self.actions.all_roms_list.sort(key=lambda rom: (
                rom[column[logical_index]] is None, rom[column[logical_index]]), reverse=(order == Qt.DescendingOrder))

            # 현재 페이지를 다시 그립니다.
            self.actions.populate_table_with_roms()

            # 정렬 방향을 토글하며 해당 열을 소팅합니다.
            if order == Qt.AscendingOrder:
                self.table.sortByColumn(logical_index, Qt.DescendingOrder)
                self.table.horizontalHeader().setSortIndicator(logical_index, Qt.AscendingOrder)
            else:
                self.table.sortByColumn(logical_index, Qt.AscendingOrder)
                self.table.horizontalHeader().setSortIndicator(logical_index, Qt.DescendingOrder)


class LoadingOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        self.setWindowFlags(Qt.FramelessWindowHint)
        # SVG 이미지를 로딩 오버레이 위젯에 추가
        svg_widget = QSvgWidget(absp('res/icon/loading_image.svg'))
        svg_widget.setGeometry(0, 0, 100, 100)  # 중앙에 표시하려면 위치와 크기 조정이 필요합니다.
        svg_layout = QVBoxLayout(self)
        svg_layout.addWidget(svg_widget)
        svg_layout.setAlignment(Qt.AlignCenter)
        self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self.resize(parent.size())
        self.hide()

    def resizeEvent(self, event):
        # 오버레이의 지오메트리를 부모 위젯의 크기와 일치하도록 업데이트합니다.
        self.setGeometry(0, 0, self.parent().width(), self.parent().height())
