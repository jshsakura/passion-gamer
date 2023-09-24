import os
import logging
from pathlib import Path
from .frogtool import zxx_ext

from PyQt5.QtCore import Qt, QThreadPool, QSize
from PyQt5.QtGui import QColor
from core.gui.worker import RomScannerWorker
from .helpers import *
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QStandardItem, QImage, QIcon, QPixmap
from PyQt5.QtWidgets import QApplication


class GuiBehavior:
    def __init__(self, gui):
        self.worker_thread = QThreadPool()
        self.worker_thread.setMaxThreadCount(1)
        self.process_workers = []
        self.gui = gui
        self.settings = None
        self.all_roms_list = []
        self.page = 1  # 현재 페이지 번호
        self.page_size = 500  # 한 페이지에 표시할 아이템 수
        self.current_roms_list = []  # 현재 페이지의 롬 목록
        self.remove_roms_list = []  # 삭제할 롬 목록
        self.except_roms_list = []  # 삭제할 롬 목록

    def get_current_page_roms(self):
        # 현재 페이지에 해당하는 롬 목록을 반환
        start_idx = (self.page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.all_roms_list[start_idx:end_idx]

    def next_page(self):
        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='next')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.changePage.connect(self.populate_table_with_roms)
        self.worker_thread.start(worker)

    def prev_page(self):
        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='prev')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.changePage.connect(self.populate_table_with_roms)
        self.worker_thread.start(worker)

    def get_total_pages(self):
        # 전체 페이지 수 계산
        return math.ceil(len(self.all_roms_list) / self.page_size)

    def handle_init(self):
        '''
        Load settings.
        Create file in case it doesn't exist.
        '''
        settings = []
        default_dir = get_settings('directory')
        if default_dir:
            self.gui.dl_directory_input.setText(default_dir)
            settings.append(default_dir)
        else:
            settings.append(None)

        default_device = get_settings('device')
        if default_device:
            self.gui.device_select.setCurrentIndex(int(default_device))
            settings.append(int(default_device))
        else:
            settings.append(0)

        default_thread = get_settings('thread')
        if default_thread:
            self.worker_thread.setMaxThreadCount(int(default_thread))
            settings.append(int(default_thread))
        else:
            self.worker_thread.setMaxThreadCount(1)
            settings.append(1)
        self.settings = settings

    def get_roms_list(self, action):

        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        roms_folder = get_settings('directory')
        # if roms_folder and not roms_folder in 'ROMS':
        #     roms_folder = os.path.normpath(roms_folder+'/ROMS')
        roms_list = []
        # 검색할 platform_name 값들
        target_platforms = ['ARCADE', 'FC', 'GB', 'GBA', 'GBC',
                            'MD', 'SFC']  # 'ARCADE'는 zfb 교체

        if roms_folder:
            for root, dirs, files in os.walk(roms_folder):
                for file in files:
                    rom_path = os.path.normpath(os.path.join(root, file))
                    file_extension = os.path.splitext(file)[-1].lower()

                    origin_filename = get_file_name_without_extension(rom_path)
                    platform_name = get_platform_name(rom_path)

                    new_filename = get_db_game_name(
                        platform_name, origin_filename)

                    status = '0'  # 사용자 입력
                    # status = '1' # DB 일치
                    # status = '2' # 수정 대기
                    # status = '4' # 삭제 대기
                    # status = '5' # 제외 됨
                    if not new_filename:
                        status = '0'
                    elif origin_filename != new_filename and new_filename:
                        status = '1'
                    elif origin_filename == new_filename:
                        status = '3'
                    else:
                        status = '2'

                    # logging.debug('file_extension: '+str(file_extension))
                    if '.z' in file_extension and platform_name in target_platforms and ((action == 'unnecessary' and '(CN)' in origin_filename) or action == 'scan'):
                        # 썸네일 설정
                        thumbnail = self.get_thumbnail(
                            platform_name, rom_path, True)

                        # 콘솔 아이콘 설정
                        platform_icon = self.get_platform_icon(platform_name)

                        # 원본 파일명 설정
                        file_size = self.get_filesize(
                            os.path.getsize(rom_path))

                        file_byte_size = os.path.getsize(rom_path)

                        if status == '0':
                            status_name = "파일명 누락"
                        elif status == '1':
                            status_name = "DB 존재"
                        elif status == '2':
                            status_name = "수정 대기"
                        elif status == '3':
                            status_name = "수정 완료"
                        elif status == '4':
                            status_name = "삭제 대기"
                        elif status == '5':
                            status_name = "제외 됨"

                        roms_list.append({"file_path": rom_path, "platform_name": platform_name, "origin_filename": origin_filename,
                                         "new_filename": new_filename, "status": status, "status_name": status_name, "file_size": file_size, "file_byte_size": file_byte_size, "thumbnail": thumbnail, "platform_icon": platform_icon})
        else:
            alert('설정하신 롬 파일 경로가 없습니다.')

        self.all_roms_list = roms_list

    def populate_table_with_roms(self):
        roms_list = self.get_current_page_roms()

        for row, rom in enumerate(roms_list):
            # 행 높이 수정, 아이콘 사이즈 수정
            self.gui.table.setRowHeight(row, 58)
            self.gui.table.setIconSize(QSize(50, 58))

            # logging.debug(rom)
            platform_name = rom['platform_name']
            platform_icon = rom['platform_icon']
            file_path = rom['file_path']
            thumbnail = rom['thumbnail']
            file_size = rom['file_size']
            status = rom['status']

            status_name = rom['status_name']
            if file_path in self.remove_roms_list:
                status = '4'
            elif file_path in self.except_roms_list:
                status = '5'

            origin_filename = rom['origin_filename']
            new_filename = rom['new_filename']

            # 플랫폼 아이콘 설정
            if platform_icon:
                platform_icon_item = QStandardItem()
                platform_icon_item.setIcon(platform_icon)
                platform_icon_item.setFlags(platform_icon_item.flags(
                ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                platform_icon_item.setTextAlignment(
                    Qt.AlignVCenter | Qt.AlignCenter)
                self.gui.table_model.setItem(row, 0, platform_icon_item)

            # 플랫폼 설정
            platform_name_item = QStandardItem()
            platform_name_item.setText(platform_name)
            # 텍스트 좌측 정렬
            platform_name_item.setTextAlignment(
                Qt.AlignVCenter | Qt.AlignCenter)

            platform_name_item.setFlags(platform_name_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 1, platform_name_item)

            # 썸네일 설정
            if thumbnail:
                thumbnail_item = QStandardItem()
                thumbnail_item.setIcon(thumbnail)

                thumbnail_item.setFlags(thumbnail_item.flags(
                ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.gui.table_model.setItem(row, 2, thumbnail_item)

            # 파일 경로 설정
            file_path_item = QStandardItem()
            file_path_item.setTextAlignment(
                Qt.AlignLeft | Qt.AlignVCenter)  # 텍스트를 왼쪽 정렬
            file_path_item.setData(
                Qt.ElideRight, Qt.DisplayRole)  # 텍스트 오버플로우 설정
            file_path_item.setSizeHint(
                QSize(file_path_item.sizeHint().width(), 5))
            file_path_item.setText(file_path)

            file_path_item.setFlags(file_path_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 3, file_path_item)
            # self.gui.table.setColumnHidden(3, True)

            # 원본 파일 용량 설정
            status_item = QStandardItem(status)
            status_item.setFlags(status_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            status_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.gui.table_model.setItem(row, 4, status_item)

            # 상태 설정
            # status_name = "수정 대기" if origin_filename != new_filename and new_filename else "DB 일치"
            status_name_item = QStandardItem(status_name)

            if status == '0':  # 입력 필요
                status_name_item.setForeground(QColor(255, 51, 51))  # 폰트 색상 설정
            elif status == '1':  # DB 일치
                status_name_item.setForeground(
                    QColor(128, 128, 128))  # 폰트 색상 설정
            elif status == '2':  # 수정 대기
                status_name_item.setForeground(QColor(0, 204, 153))  # 폰트 색상 설정
            elif status == '4':
                status_name_item.setForeground(QColor(255, 51, 51))  # 삭제 대기
                status_name_item.setText('삭제 대기')
            elif status == '5':
                status_name_item.setForeground(QColor(255, 153, 0))  # 목록 제외
                status_name_item.setText('제외 됨')

            status_name_item.setTextAlignment(Qt.AlignCenter)

            status_name_item.setFlags(status_name_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 5, status_name_item)

            # 원본 파일 용량 설정
            filesize_item = QStandardItem(file_size)
            filesize_item.setFlags(filesize_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            filesize_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.gui.table_model.setItem(row, 6, filesize_item)

            # 원본 파일명 설정
            origin_filename_item = QStandardItem(origin_filename)
            origin_filename_item.setFlags(origin_filename_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 7, origin_filename_item)

            # 변경될 파일명 설정
            new_filename_item = QStandardItem(new_filename)
            self.gui.table_model.setItem(row, 8, new_filename_item)
            if platform_name == 'ARCADE':
                new_filename_item.setFlags(origin_filename_item.flags(
                ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                new_filename_item.setForeground(QColor(26, 26, 26))
                italic_font = self.gui.font
                italic_font.setItalic(True)
                new_filename_item.setFont(italic_font)

            # 행 높이 수정, 아이콘 사이즈 수정
            self.gui.table.setRowHeight(row, 58)
            self.gui.table.setIconSize(QSize(50, 58))

        # 페이지 정보 업데이트 (예: "페이지 1 / 3")
        if self.get_total_pages() > 0:
            self.gui.main.page_label.setText(
                f"페이지 {self.page} / {self.get_total_pages()}")

    def roms_scan(self):
        # 삭제,제외 대상 초기화
        self.remove_roms_list = []
        self.except_roms_list = []
        self.all_roms_list = []
        self.current_roms_list = []

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='scan')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.romsListReady.connect(self.populate_table_with_roms)
        self.worker_thread.start(worker)

    def roms_unnecessary(self):
        # 삭제,제외 대상 초기화
        self.remove_roms_list = []
        self.except_roms_list = []
        self.all_roms_list = []
        self.current_roms_list = []

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='unnecessary')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.romsListReady.connect(self.populate_table_with_roms)
        self.worker_thread.start(worker)

    def roms_replace(self):
        # 테이블이 비었는지 확인
        if self.gui.table_model.rowCount() == 0:
            alert('현재 화면의 수정 목록이 비어 있습니다.\n먼저 설정에서 롬 폴더를 지정하고 롬 파일을 검색해야합니다.')
            return

        if not self.confirm_bulk_rename():
            return

        worker = RomScannerWorker(self, action='replace')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.renameCompleted.connect(
            self.show_rename_completed_alert)
        self.worker_thread.start(worker)

    def show_rename_completed_alert(self):
        alert('롬 파일의 이름이 모두 변경되었습니다.\n목록을 새로 고칩니다.')
        self.roms_scan()

    def confirm_bulk_rename(self):
        message = ''
        if len(self.remove_roms_list) > 0:
            message = f"삭제 대상인 {len(self.remove_roms_list)} 건을 실제 롬 폴더에서 삭제하니 주의하세요.\n수정 파일명이 존재하는 파일들의 이름을 변경하시겠습니까?"
        else:
            message = "수정 파일명이 존재하는 파일들의 이름을 변경하시겠습니까?"
        reply = QMessageBox.question(None, '파일명 일괄 변경 확인', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def ask_for_delete_confirmation(self, action):
        # 선택된 행의 개수를 가져옵니다.
        selected_rows_count = len(
            self.gui.table.selectionModel().selectedRows())

        # 선택된 행이 없으면, 함수를 종료합니다.
        if selected_rows_count == 0:
            return False

        # 확인 메시지 박스 생성
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)

        action_name = ''
        if action == 'except':
            msg_box.setText(
                f"선택하신 {selected_rows_count}개의 행을 정말로 수정사항에서 제외하시겠습니까?")
        else:
            msg_box.setText(
                f"선택하신 {selected_rows_count}개의 행을 삭제대상으로 등록합니다.\n수정사항 적용 버튼을 눌러야만 실제 롬 폴더에도 반영됩니다.")

        msg_box.setWindowTitle("목록에서 제외")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # 사용자 응답 반환
        return msg_box.exec_() == QMessageBox.Yes

    def roms_except(self):
        # 현재 선택된 행(ROMs)의 인덱스를 가져옵니다.
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            # 선택된 행이 없으면 경고 메시지를 표시하고 반환합니다.
            alert('목록에서 제외할 롬 파일을 선택하세요.')
            return

        if self.ask_for_delete_confirmation('except'):
            # 사용자가 '예'를 클릭한 경우, 행 삭제 작업을 진행합니다.
            worker = RomScannerWorker(
                self, action='except', rows=selected_rows)
            worker.signals.rowsToRemove.connect(
                self.remove_rows_from_table)  # 연결
            worker.signals.showLoading.connect(self.gui.show_loading_overlay)
            worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
            self.worker_thread.start(worker)
            pass
        # 목록 새로고침
        self.populate_table_with_roms()

    def roms_remove(self):
        # 현재 선택된 행(ROMs)의 인덱스를 가져옵니다.
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            # 선택된 행이 없으면 경고 메시지를 표시하고 반환합니다.
            alert('목록에서 삭제할 롬 파일을 선택하세요.')
            return

        if self.ask_for_delete_confirmation('remove'):
            # 사용자가 '예'를 클릭한 경우, 행 삭제 작업을 진행합니다.
            worker = RomScannerWorker(
                self, action='remove', rows=selected_rows)
            worker.signals.rowsToRemove.connect(
                self.remove_rows_from_table)  # 연결
            worker.signals.showLoading.connect(self.gui.show_loading_overlay)
            worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
            self.worker_thread.start(worker)
            pass
        # 목록 새로고침
        self.populate_table_with_roms()

    def remove_rows_from_table(self, rows, action):
        for row in sorted(rows, reverse=True):  # 높은 인덱스부터 작업
            # 해당 행의 데이터 가져오기
            item_list = []
            for column in range(self.gui.table_model.columnCount()):
                item = self.gui.table_model.item(row, column)

                if column == 5:
                    new_text = "삭제 대기" if action == 'remove' else '제외 됨'
                    font_color = QColor(255, 51, 51) if action == 'remove' else QColor(
                        255, 153, 0)
                    status_code = '4' if action == 'remove' else '5'
                    item.setText(new_text)
                    item.setForeground(font_color)  # 폰

                if column == 4:
                    status_code = '4' if action == 'remove' else '5'
                    item.setText(status_code)

                if item:
                    item_list.append(item.text())
                else:
                    item_list.append(None)

            # 플랫폼 이름과 원본 파일명 가져오기
            # platform_name = item_list[1]  # 1은 플랫폼 열의 인덱스
            # original_filename = item_list[5]  # 5는 원본 파일명 열의 인덱스

            # 파일경로를 사실상 키로 사용해도 무관
            file_path = item_list[3]
            new_filename = item_list[8]

            if action == 'remove':
                # 플랫폼 이름과 원본 파일명 가져오기
                self.remove_roms_list.append(item_list[3])  # 3은 파일 경로
            else:
                self.except_roms_list.append(item_list[3])  # 3은 파일 경로

            self.update_row_from_all_roms_list(file_path, new_filename, action)

            # self.all_roms_list에서 해당 행 삭제
            # self.remove_row_from_all_roms_list(
            #     platform_name, original_filename)

            # 행 삭제
            # self.gui.table_model.removeRow(row)

    def update_row_from_all_roms_list(self, file_path, new_filename, action):
        work_flag = False
        for index, rom in enumerate(self.all_roms_list):
            if rom['file_path'] == file_path:
                # 조건에 해당하는 항목을 찾았으므로 삭제합니다.
                if action == 'remove':
                    self.all_roms_list[index]['status'] = '4'
                elif action == 'except':
                    self.all_roms_list[index]['status'] = '5'
                elif action == 'update':
                    # 파일명 업데이트
                    self.all_roms_list[index]['new_filename'] = new_filename
                    if not new_filename:
                        self.all_roms_list[index]['status'] = '0'
                        self.all_roms_list[index]['status_name'] = '0'
                        work_flag = True

                break  # 해당 항목을 찾았으면 반복문 종료

    # def remove_row_from_all_roms_list(self, platform_name, original_filename):
    #     for rom in self.all_roms_list:
    #         if rom['platform_name'] == platform_name and rom['origin_filename'] == original_filename:
    #             # 조건에 해당하는 항목을 찾았으므로 삭제합니다.
    #             self.all_roms_list.remove(rom)
    #             break  # 해당 항목을 찾았으면 반복문 종료

    def get_selected_rows(self):
        # table_view는 QTableView의 인스턴스 이름입니다. 이를 적절하게 수정해야 합니다.
        selection_model = self.gui.table.selectionModel()
        selected_rows = selection_model.selectedRows()
        return [index.row() for index in selected_rows]

    def set_dl_directory(self):
        file_dialog = QFileDialog(self.gui.settings)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.exec_()
        self.gui.dl_directory_input.setText(file_dialog.selectedFiles()[0])

    def change_device(self, device=None):
        '''
        Change app palette (theme).
        0 = SF2000
        1 = Miyoo Mini
        '''
        if device:
            self.gui.device_select.setCurrentIndex(device)

    def save_settings(self):
        settings = []
        if self.gui.dl_directory_input.text():
            set_settings('directory',
                         self.gui.dl_directory_input.text())
            logging.debug('save_settings directory:' +
                          self.gui.dl_directory_input.text())
            settings.append(self.gui.dl_directory_input.text())
        else:
            settings.append(None)

        if self.gui.device_select.currentIndex():
            set_settings('device',
                         self.gui.device_select.currentIndex())
            logging.debug('save_settings device:' +
                          str(self.gui.device_select.currentIndex()))
            settings.append(self.gui.device_select.currentIndex())
        else:
            set_settings('device',
                         self.gui.device_select.currentIndex())
            settings.append(0)

        set_settings('thread',
                     self.worker_thread.maxThreadCount())
        logging.debug('save_settings thread:' +
                      str(self.worker_thread.maxThreadCount()))
        settings.append(1)

        self.settings = settings
        self.gui.settings.hide()

    def select_settings(self):
        selection = self.gui.settings_list.selectedIndexes()[0].row()
        self.gui.stacked_settings.setCurrentIndex(selection)

    def handle_exit(self):
        # 종료시 동작 기술
        os._exit(1)

    def get_filesize(self, filesize):
        humanReadableFileSize = "ERROR"
        if filesize > 1024*1024:  # More than 1 Megabyte
            humanReadableFileSize = f"{round(filesize/(1024*1024),2)} MB"
        elif filesize > 1024:  # More than 1 Kilobyte
            humanReadableFileSize = f"{round(filesize/1024,2)} KB"
        else:  # Less than 1 Kilobyte
            humanReadableFileSize = f"filesize Bytes"
        return humanReadableFileSize

    def get_thumbnail(self, platform, filepath, is_scale):
        thumbnail = None
        extension = get_file_extension(filepath)
        sys_zxx_ext = '.' + zxx_ext[platform]

        if extension == sys_zxx_ext:
            original_width = 144
            original_height = 208

            with open(filepath, "rb") as rom_file:
                rom_content = bytearray(rom_file.read(
                    original_width * original_height * 2))

            img = QImage(rom_content, original_width,
                         original_height, QImage.Format_RGB16)

            # Scale down the image
            if is_scale:
                pimg = QPixmap.fromImage(img).scaled(
                    72, 104, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                pimg = QPixmap.fromImage(img).scaled(
                    original_width, original_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon = QIcon(pimg)
            return icon

        return thumbnail

    def get_platform_icon(self, platform):
        icon_path = absp(f'res/icon/{platform}.png')
        # 파일이 존재하는지 확인
        if os.path.exists(icon_path):
            size = QSize(32, 32)
            icon = QIcon(icon_path)
            pixmap = icon.pixmap(size)
            return QIcon(pixmap)
        else:
            return None  # 또는 기본 아이콘을 반환할 수 있습니다.

    def sort_all_roms_list(self, column, order):
        # self.all_roms_list를 정렬합니다.
        self.all_roms_list.sort(
            key=lambda rom: rom[column], reverse=(order == Qt.DescendingOrder))

        # 현재 페이지를 다시 그립니다.
        self.populate_table_with_roms()
