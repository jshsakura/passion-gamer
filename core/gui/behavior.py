import os
import logging
import PyQt5

from PyQt5.QtCore import Qt, QThreadPool
from core.gui.worker import RomScannerWorker
from .helpers import *
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem
from PyQt5.QtGui import QStandardItem, QColor


class GuiBehavior:
    def __init__(self, gui):
        self.worker_thread = QThreadPool()
        self.worker_thread.setMaxThreadCount(1)
        self.process_workers = []
        self.gui = gui
        self.settings = None

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

    def show_loading_overlay(self):
        '''
        Show the loading overlay.
        '''
        if self.gui:
            self.gui.show_loading_overlay()

    def hide_loading_overlay(self):
        '''
        Show the loading overlay.
        '''
        if self.gui:
            self.gui.hide_loading_overlay()

    def get_roms_list(self):
        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        roms_folder = get_settings('directory')
        roms_list = []
        # 검색할 platform_name 값들
        target_platforms = ['FC', 'GB', 'GBA', 'GBC', 'MD', 'SFC']

        if roms_folder:
            for root, dirs, files in os.walk(roms_folder):
                for file in files:
                    rom_path = os.path.join(root, file)
                    file_extension = os.path.splitext(file)[-1].lower()

                    origin_filename = get_file_name_without_extension(rom_path)
                    platform_name = get_platform_name(rom_path)
                    status = True

                    new_filename = get_db_game_name(
                        platform_name, origin_filename)
                    if not new_filename:
                        status = False

                    # logging.debug('file_extension: '+str(file_extension))
                    if '.z' in file_extension and platform_name in target_platforms:
                        roms_list.append({"file_path": rom_path, "platform_name": platform_name, "origin_filename": origin_filename,
                                         "new_filename": new_filename, "status": status})
        else:
            alert('설정하신 롬 파일 경로가 없습니다.')

        return roms_list

    def populate_table_with_roms(self, roms_list):
        self.gui.table_model.setRowCount(len(roms_list))

        for row, rom in enumerate(roms_list):
            # logging.debug(rom)

            # 플랫폼 설정
            platform_name_item = QStandardItem(rom['platform_name'])
            platform_name_item.setFlags(platform_name_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 0, platform_name_item)

            # 파일 경로 설정
            file_path_item = QStandardItem(rom['file_path'])
            file_path_item.setFlags(file_path_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 1, file_path_item)

            # 원본 파일명 설정
            origin_filename_item = QStandardItem(rom['origin_filename'])
            origin_filename_item.setFlags(origin_filename_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.gui.table_model.setItem(row, 2, origin_filename_item)

            # 변경될 파일명 설정
            new_filename_item = QStandardItem(rom['new_filename'])
            self.gui.table_model.setItem(row, 3, new_filename_item)
            # Check if new_filename is empty and set the row background color to red

    def roms_scan(self):
        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='scan')
        worker.signals.romsListReady.connect(self.populate_table_with_roms)
        worker.signals.showLoading.connect(self.show_loading_overlay)
        worker.signals.hideLoading.connect(self.hide_loading_overlay)
        QThreadPool.globalInstance().start(worker)

    def roms_replace(self):
        # 테이블이 비었는지 확인
        if self.gui.table_model.rowCount() == 0:
            alert('롬 목록이 비어 있습니다.')
            return

        if not self.confirm_bulk_rename():
            return

        worker = RomScannerWorker(self, action='replace')
        worker.signals.showLoading.connect(self.show_loading_overlay)
        worker.signals.hideLoading.connect(self.hide_loading_overlay)
        worker.signals.renameCompleted.connect(
            self.show_rename_completed_alert)
        QThreadPool.globalInstance().start(worker)

    def show_rename_completed_alert(self):
        alert('롬 파일의 이름이 모두 변경되었습니다.\n목록을 새로 고칩니다.')
        self.roms_scan()

    def confirm_bulk_rename(self):
        message = "수정 파일명이 존재하는 파일들의 이름을 변경하시겠습니까?"
        reply = QMessageBox.question(None, '파일명 일괄 변경 확인', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def ask_for_delete_confirmation(self):
        # 선택된 행의 개수를 가져옵니다.
        selected_rows_count = len(
            self.gui.table.selectionModel().selectedRows())

        # 선택된 행이 없으면, 함수를 종료합니다.
        if selected_rows_count == 0:
            return False

        # 확인 메시지 박스 생성
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(f"선택하신 {selected_rows_count}개의 행을 정말로 제외하시겠습니까?")
        msg_box.setWindowTitle("목록에서 제외")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        # 사용자 응답 반환
        return msg_box.exec_() == QMessageBox.Yes

    def roms_remove(self):
        # 현재 선택된 행(ROMs)의 인덱스를 가져옵니다.
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            # 선택된 행이 없으면 경고 메시지를 표시하고 반환합니다.
            alert('화면의 목록에서 제외할 롬 파일을 선택하세요.')
            return

        if self.ask_for_delete_confirmation():
            # 사용자가 '예'를 클릭한 경우, 행 삭제 작업을 진행합니다.
            worker = RomScannerWorker(
                self, action='remove', rows=selected_rows)
            worker.signals.rowsToRemove.connect(
                self.remove_rows_from_table)  # 연결
            worker.signals.showLoading.connect(self.show_loading_overlay)
            worker.signals.hideLoading.connect(self.hide_loading_overlay)
            QThreadPool.globalInstance().start(worker)
            pass

    def remove_rows_from_table(self, rows):
        for row in sorted(rows, reverse=True):  # 높은 인덱스부터 삭제
            self.gui.table_model.removeRow(row)

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
