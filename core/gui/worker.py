import logging
import os
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject

from core.gui.helpers import get_platform_name


class RomScannerWorkerSignals(QObject):
    romsListReady = pyqtSignal()
    changePage = pyqtSignal()
    romsRemoved = pyqtSignal()  # 삭제 작업을 알리기 위한 신호 추가
    rowsToRemove = pyqtSignal(list, str)  # 삭제완료 시그널
    showLoading = pyqtSignal()  # 로딩 오버레이 보여주기 위한 신호
    hideLoading = pyqtSignal()  # 로딩 오버레이 숨기기 위한 신호
    renameCompleted = pyqtSignal()


class RomScannerWorker(QRunnable):
    def __init__(self, gui_behavior, action='scan', rows=[]):
        super(RomScannerWorker, self).__init__()
        self.signals = RomScannerWorkerSignals()
        self.gui_behavior = gui_behavior
        self.action = action  # 작업 구분자: 'scan' 또는 'remove'
        self.rows = rows

    def run(self):
        # 로딩 오버레이
        self.signals.showLoading.emit()

        if self.action == 'scan':
            # 롬 파일 목록 얻기
            self.gui_behavior.page = 1
            self.gui_behavior.get_roms_list(action='scan')
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.signals.romsListReady.emit()
        if self.action == 'unnecessary':
            # 롬 파일 목록 얻기
            self.gui_behavior.page = 1
            self.gui_behavior.get_roms_list(action='unnecessary')
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            self.signals.romsListReady.emit()
        elif self.action == 'next':
            # 다음 페이지로 이동
            if self.gui_behavior.page < self.gui_behavior.get_total_pages():
                self.gui_behavior.page += 1
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            self.signals.changePage.emit()
        elif self.action == 'prev':
            # 이전 페이지로 이동
            if self.gui_behavior.page > 1:
                self.gui_behavior.page -= 1
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            self.signals.changePage.emit()
        elif self.action == 'update':
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.current_roms_list = self.gui_behavior.get_current_page_roms()
            self.signals.romsListReady.emit()
        elif self.action == 'remove' or self.action == 'except':
            rows_to_remove = self.rows  # 여기에서 삭제하려는 행의 인덱스 목록을 생성합니다.
            self.signals.rowsToRemove.emit(rows_to_remove, self.action)
        elif self.action == 'replace':
            # 롬 파일 목록 얻기
            roms_list = self.gui_behavior.all_roms_list

            for rom in roms_list:
                # 원본 파일명과 변경될 파일명을 비교
                if rom['origin_filename'] != rom['new_filename'] and rom['new_filename']:
                    if get_platform_name(rom['file_path']) == 'ARCADE':
                        logging.debug('아케이드 준비 중')

                    else:
                        # 단순 파일명 변경
                        old_path = rom['file_path']
                        directory, old_filename_with_ext = os.path.split(
                            old_path)
                        new_filename_with_ext = str(rom['new_filename']).replace('\n', '') + \
                            os.path.splitext(old_filename_with_ext)[-1]
                        new_path = os.path.join(
                            directory, new_filename_with_ext)
                        os.rename(old_path, new_path)

            # 롬 파일 목록 얻기
            remove_roms_list = self.gui_behavior.remove_roms_list
            for file_path in remove_roms_list:
                try:
                    os.remove(file_path)
                    logging.debug(f"{file_path} 파일이 삭제되었습니다.")
                except OSError as e:
                    logging.debug(f"{file_path} 파일을 삭제하는 중 오류 발생: {e}")

            self.signals.renameCompleted.emit()

        # 로딩 창을 숨김
        self.signals.hideLoading.emit()
