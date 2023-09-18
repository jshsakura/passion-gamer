import os
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject


class RomScannerWorkerSignals(QObject):
    romsListReady = pyqtSignal(list)
    romsRemoved = pyqtSignal()  # 삭제 작업을 알리기 위한 신호 추가
    rowsToRemove = pyqtSignal(list)  # 삭제완료 시그널
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
            roms_list = self.gui_behavior.get_roms_list()
            # 롬 목록이 준비되면 메인 스레드에 알리기
            self.signals.romsListReady.emit(roms_list)
        elif self.action == 'remove':
            rows_to_remove = self.rows  # 여기에서 삭제하려는 행의 인덱스 목록을 생성합니다.
            self.signals.rowsToRemove.emit(rows_to_remove)
        elif self.action == 'replace':
            # 롬 파일 목록 얻기
            roms_list = self.gui_behavior.get_roms_list()

            for rom in roms_list:
                # 원본 파일명과 변경될 파일명을 비교
                if rom['origin_filename'] != rom['new_filename'] and rom['new_filename']:
                    # 파일명 변경
                    old_path = rom['file_path']
                    directory, old_filename_with_ext = os.path.split(old_path)
                    new_filename_with_ext = rom['new_filename'] + \
                        os.path.splitext(old_filename_with_ext)[-1]
                    new_path = os.path.join(directory, new_filename_with_ext)
                    os.rename(old_path, new_path)

            self.signals.renameCompleted.emit()

        # 로딩 오버레이를 숨깁니다.
        self.signals.hideLoading.emit()
