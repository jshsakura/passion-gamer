import os
import logging
import shutil
from .frogtool import zxx_ext, StopExecution, process_sys, systems

from PyQt5.QtCore import Qt, QThreadPool, QSize, QTimer
from PyQt5.QtGui import QColor
from core.gui.worker import RomScannerWorker
from .helpers import *
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QStandardItem, QImage, QIcon, QPixmap, QFont


class GuiBehavior:
    def __init__(self, gui):
        self.worker_thread = QThreadPool()
        self.worker_thread.setMaxThreadCount(1)
        self.process_workers = []
        self.gui = gui
        self.settings = None
        self.all_roms_list = []
        self.page = 1  # 현재 페이지 번호
        self.page_size = 1000  # 한 페이지에 표시할 아이템 수
        self.current_roms_list = []  # 현재 페이지의 롬 목록
        self.remove_roms_list = []  # 삭제할 롬 목록
        self.except_roms_list = []  # 삭제할 롬 목록
        self.msg_box = None

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
        worker.signals.changePage.connect(self.change_page_refresh)
        self.worker_thread.start(worker)

    def prev_page(self):
        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='prev')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.changePage.connect(self.change_page_refresh)
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

    def check_shortcut_files(self):
        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        roms_folder = get_settings('directory')
        roms_list = []
        # 검색할 platform_name 값들
        target_platforms = ['ARCADE', 'FC', 'GB', 'GBA', 'GBC',
                            'MD', 'SFC']  # 'ARCADE'는 zfb 교체
        target_file_extension = ['.zfb', '.zfc',
                                 '.zgb', '.zmd', '.zsf']
        # 숏컷 대상 파일
        shortcut_links = get_db_shortcut_game_name()

        if roms_folder:
            for root, dirs, files in os.walk(roms_folder):
                for file in files:
                    rom_path = os.path.normpath(os.path.join(root, file))
                    file_extension = os.path.splitext(file)[-1].lower()
                    origin_filename = get_file_name_without_extension(rom_path)
                    platform_name = get_platform_name(rom_path)

                    if file_extension in target_file_extension and platform_name in target_platforms and origin_filename in shortcut_links:
                        shortcut_links.remove(origin_filename)
                        logging.debug(
                            f'한글 숏컷 대상인 {platform_name} 플랫폼의 [ {origin_filename} ] 을 찾았습니다!')

        # 숏컷 갯수 체크
        if len(shortcut_links) == 0:
            return True
        else:
            return False

    def set_resource_install(self, action):
        # 롬 폴더 경로
        roms_folder = get_settings('directory')
        # 검색할 폴더
        target_folder = 'Resources'
        resources_path = None
        custom_resources_files = []
        # 작업명 설정
        work_name = '드드라 테마' if action == 'theme' else '한글 숏컷'

        if action == 'shortcut':
            find_shortcut = self.check_shortcut_files()
            if not find_shortcut:
                alert(
                    f'롬 폴더에 {work_name}을 설정하려면 우선 롬 파일을 한글 파일명으로 수정해야합니다.\n설정하신 파일 경로에서 한글 숏컷에 해당되는 한글 롬 파일명을 검색하지 못했습니다.\n아직 파일명을 변경하지 않았다면 먼저 파일명을 변경해주세요.')
                return

        # 리소스 폴더 검색
        if roms_folder:
            # 리소스 폴더 검색
            current_folder = roms_folder  # 현재 폴더를 설정된 경로로 초기화

            # 설정된 경로에서 상위 폴더로 이동하며 검색
            while current_folder:
                for root, dirs, files in os.walk(current_folder):
                    if target_folder in os.path.normpath(root):
                        # 리소스 폴더를 발견하면 중단!
                        resources_path = os.path.normpath(root)
                        break

                # 상위 폴더로 이동 (1단계 상위로 이동)
                current_folder = os.path.dirname(current_folder)

                # 리소스 폴더를 찾았을 때 중단
                if resources_path:
                    break

        if resources_path:
            logging.debug(f"리소스 폴더를 찾았습니다: {resources_path}")
        else:
            logging.debug("리소스 폴더를 찾을 수 없었습니다.")

        change_files = 0
        # 1. resources_path에 위치한 파일 목록 가져오기
        if resources_path:
            resources_files = os.listdir(resources_path)

            # 2. absp(f'res/data/Resources')에 위치한 파일 목록 가져오기
            custom_resources_path = os.path.normpath(
                absp(f'res/data/Resources'))
            custom_resources_files = os.listdir(custom_resources_path)

            # 수정 대상 파일
            target_resources_cnt = 0
            if action == 'theme':
                target_resources_cnt = 46
            elif action == 'shortcut':
                target_resources_cnt = 1

            # 3. 두 목록을 비교하여 수정전 파일갯수 카운트
            for custom_file in custom_resources_files:
                if custom_file in resources_files:
                    # 한글 숏컷은 제외
                    if action == 'theme' and custom_file == 'xfgle.hgp':
                        continue
                    elif action == 'shortcut' and custom_file != 'xfgle.hgp':
                        continue
                    change_files = change_files+1

            # 4. 두 목록을 비교하여 동일한 파일 교체
            if change_files == target_resources_cnt:
                for custom_file in custom_resources_files:
                    if custom_file in resources_files:
                        # 한글 숏컷은 제외
                        if action == 'theme' and custom_file == 'xfgle.hgp':
                            continue
                        elif action == 'shortcut' and custom_file != 'xfgle.hgp':
                            continue
                        # 4. 파일 덮어쓰기 (복사 및 붙여넣기)
                        custom_file_path = os.path.join(
                            custom_resources_path, custom_file)
                        resources_file_path = os.path.join(
                            resources_path, custom_file)
                        shutil.copyfile(custom_file_path,
                                        resources_file_path)
                        logging.debug(f"패치를 위해 {custom_file}를 덮어썼습니다.")

        # 5. 최종 작업 결과 알림.
        if change_files > 0 and change_files == target_resources_cnt:
            alert(
                f'Resources 폴더 안에 파일을 덮어쓰고, {work_name} 설치 작업이 완료되었습니다.')
        elif change_files > 0:
            alert(
                f'{work_name} 설치를 위해 필요한 총 {target_resources_cnt} 개의 파일 중 {change_files} 개만 검색되었습니다.\n[설정] 버튼을 눌러 선택하신 SD 카드 경로를 확인해주세요.')
        else:
            alert(
                f'Resources 폴더에 파일을 찾을 수 없어 {work_name} 설치를 진행할 수 없었습니다.\n[설정] 버튼을 눌러 선택하신 SD 카드 경로를 확인해주세요.')

    def set_bios_install(self, action):
        # 롬 폴더 경로
        roms_folder = get_settings('directory')
        # 검색할 폴더
        target_folder = 'bios'
        bios_path = None
        custom_bios_files = []
        # 작업명 설정

        if action != 'bios_install':
            logging.debug('올바른 명령이 아닙니다.')
            return

        # 리소스 폴더 검색
        if roms_folder:
            # 리소스 폴더 검색
            current_folder = roms_folder  # 현재 폴더를 설정된 경로로 초기화

            # 설정된 경로에서 상위 폴더로 이동하며 검색
            while current_folder:
                for root, dirs, files in os.walk(current_folder):
                    if target_folder in os.path.normpath(root):
                        # bios 폴더를 발견하면 중단!
                        bios_path = os.path.normpath(root)
                        break

                # 상위 폴더로 이동 (1단계 상위로 이동)
                current_folder = os.path.dirname(current_folder)

                # 리소스 폴더를 찾았을 때 중단
                if bios_path:
                    break

        change_files = 0
        # 1. bios_path에 위치한 파일 목록 가져오기
        if bios_path:
            logging.debug(f"바이오스를 설치할 폴더를 찾았습니다: {bios_path}")
            bios_files = os.listdir(bios_path)

            # 2. absp(f'res/data/Resources')에 위치한 파일 목록 가져오기
            custom_bios_path = os.path.normpath(
                absp(f'res/data/bios'))
            custom_bios_files = os.listdir(custom_bios_path)

            # 3. 두 목록을 비교하여 수정전 파일갯수 카운트
            for custom_file in custom_bios_files:
                if custom_file in bios_files:
                    # 한글 숏컷은 제외
                    change_files = change_files+1

            # 4. 두 목록을 비교하여 동일한 파일 교체
            if change_files >= 0:
                # 4. 파일 덮어쓰기 (복사 및 붙여넣기)
                custom_gba_file_path = os.path.normpath(os.path.join(
                    custom_bios_path, 'gba_bios.bin'))
                custom_sfc_fw_file_path = os.path.normpath(os.path.join(
                    custom_bios_path, 'bisrv.asd'))
                gba_bios_file = os.path.normpath(os.path.join(
                    bios_path, 'gba_bios.bin'))
                sfc_fw_file = os.path.normpath(os.path.join(
                    bios_path, 'bisrv.asd'))

                shutil.copy2(custom_gba_file_path,
                             gba_bios_file)
                shutil.copy2(custom_sfc_fw_file_path,
                             sfc_fw_file)
                logging.debug(
                    f"패치를 위해 {gba_bios_file} 파일과 {sfc_fw_file} 파일을 덮어썼습니다.")

            else:
                alert(f'bios 폴더 안에 수정할 파일이 존재하지 않습니다.')
                return

        # 5. 최종 작업 결과 알림.
        if change_files > 0:
            alert(
                f'bios 폴더 안에 파일을 복사하고 설치 완료했습니다.\n개선 펌웨어 및 바이오스 설치가 모두 완료되었습니다.')

        else:
            alert(
                f'bios 폴더를 찾을 수 없어 설치를 진행할 수 없었습니다.\n[설정] 버튼을 눌러 선택하신 SD 카드 경로를 확인해주세요.')

    def get_roms_list(self, action):

        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        roms_folder = get_settings('directory')
        roms_list = []
        # 검색할 platform_name 값들
        target_platforms = ['ARCADE', 'FC', 'GB', 'GBA', 'GBC',
                            'MD', 'SFC']  # 'ARCADE'는 zfb 교체
        target_file_extension = ['.zfb', '.zfc',
                                 '.zgb', '.zmd', '.zsf']

        if roms_folder:
            for root, dirs, files in os.walk(roms_folder):
                for file in files:
                    rom_path = os.path.normpath(os.path.join(root, file))
                    file_extension = os.path.splitext(file)[-1].lower()
                    origin_filename = get_file_name_without_extension(rom_path)
                    platform_name = get_platform_name(rom_path)
                    new_filename = ''
                    shortcut_link = ''

                    # logging.debug('file_extension: '+str(file_extension))
                    if file_extension in target_file_extension and platform_name in target_platforms:
                        db_result = get_db_game_name(
                            platform_name, origin_filename)

                        if db_result:
                            new_filename = str(db_result['kr_filename'])
                            shortcut_link = str(db_result['shortcut_link'])

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

                        # 중문롬 검색 조건일때 (CN)이 없다면 패스
                        if action == 'unnecessary' and '(CN)' not in origin_filename:
                            continue

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

                        roms_list.append({"file_path": rom_path, "platform_name": platform_name, "origin_filename": origin_filename, "shortcut_link": shortcut_link,
                                          "kr_filename": new_filename, "new_filename": new_filename, "status": status, "status_name": status_name, "file_size": file_size, "file_byte_size": file_byte_size, "thumbnail": thumbnail, "platform_icon": platform_icon})
        # else:
        #     alert('설정하신 롬 폴더 경로가 없습니다.')

        self.all_roms_list = roms_list

    # def get_roms_list(self, action):
    #     # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
    #     roms_folder = get_settings('directory')
    #     roms_list = []
    #     # 검색할 platform_name 값들
    #     target_platforms = ['ARCADE', 'FC', 'GB', 'GBA', 'GBC', 'MD', 'SFC']
    #     target_file_extension = ['.zfb', '.zfc', '.zgb', '.zmd', '.zsf']

    #     if roms_folder:
    #         for root, dirs, files in os.walk(roms_folder):
    #             for file in files:
    #                 rom_path = os.path.normpath(os.path.join(root, file))
    #                 file_extension = os.path.splitext(file)[-1].lower()
    #                 origin_filename = get_file_name_without_extension(rom_path)
    #                 platform_name = get_platform_name(rom_path)
    #                 new_filename = ''
    #                 shortcut_link = ''

    #                 if file_extension in target_file_extension and platform_name in target_platforms:

    #                     status = '0'  # 사용자 입력

    #                     # 중문롬 검색 조건일때 (CN)이 없다면 패스
    #                     if action == 'unnecessary' and '(CN)' not in origin_filename:
    #                         continue

    #                     # 썸네일 설정
    #                     thumbnail = self.get_thumbnail(
    #                         platform_name, rom_path, True)

    #                     # 콘솔 아이콘 설정
    #                     platform_icon = self.get_platform_icon(platform_name)

    #                     # 원본 파일명 설정
    #                     file_size = self.get_filesize(
    #                         os.path.getsize(rom_path))

    #                     file_byte_size = os.path.getsize(rom_path)

    #                     roms_list.append({"file_path": rom_path, "platform_name": platform_name, "origin_filename": origin_filename, "shortcut_link": shortcut_link,
    #                                       "kr_filename": new_filename, "new_filename": new_filename, "status": "0", "platform_icon": platform_icon, "thumbnail": thumbnail, "file_byte_size": file_byte_size, "file_size": file_size, "status_name": "파일명 누락"})

    #         # 한 번에 모든 게임의 정보를 DB에서 가져옵니다.
    #         db_results = get_all_db_game_names(target_platforms)

    #         # 가져온 정보를 roms_list에 업데이트합니다.
    #         for rom_info in roms_list:
    #             platform_name = rom_info["platform_name"]
    #             origin_filename = rom_info["origin_filename"]
    #             db_result = db_results.get((platform_name, origin_filename))
    #             if not db_result:
    #                 db_results.get((platform_name, new_filename))

    #                 print(db_results.get((platform_name, origin_filename)))
    #                 print(db_results.get((platform_name, new_filename)))
    #             if db_result:
    #                 new_filename = db_result["kr_filename"]
    #                 # 수정전 원본명 분리
    #                 rom_info["new_filename"] = new_filename
    #                 rom_info["kr_filename"] = new_filename
    #                 rom_info["shortcut_link"] = db_result["shortcut_link"]
    #                 status = '0'

    #                 # status = '1' # DB 일치
    #                 # status = '2' # 수정 대기
    #                 # status = '4' # 삭제 대기
    #                 # status = '5' # 제외 됨
    #                 if not new_filename:
    #                     status = '0'
    #                 elif origin_filename != new_filename and new_filename:
    #                     status = '1'
    #                 elif origin_filename == new_filename:
    #                     status = '3'
    #                 else:
    #                     status = '2'

    #                 if status == '0':
    #                     status_name = "파일명 누락"
    #                 elif status == '1':
    #                     status_name = "DB 존재"
    #                 elif status == '2':
    #                     status_name = "수정 대기"
    #                 elif status == '3':
    #                     status_name = "수정 완료"
    #                 elif status == '4':
    #                     status_name = "삭제 대기"
    #                 elif status == '5':
    #                     status_name = "제외 됨"

    #                 # 상태 업데이트
    #                 rom_info["status"] = status
    #                 rom_info["status_name"] = status_name

    #     self.all_roms_list = roms_list

    def change_page_refresh(self):
        self.populate_table_with_roms()

        # 스크롤바 초기화
        self.gui.table.verticalScrollBar().setValue(0)

    def populate_table_with_roms(self):
        roms_list = self.get_current_page_roms()
        # 테이블을 비우고 진행
        self.gui.table_model.removeRows(0, self.gui.table_model.rowCount())

        italic_font = QFont(self.gui.font)
        italic_font.setItalic(True)

        for row, rom in enumerate(roms_list):
            # 행 높이 수정, 아이콘 사이즈 수정
            self.gui.table.setRowHeight(row, 58)
            self.gui.table.setIconSize(QSize(50, 58))

            # logging.debug(rom)
            platform_name = rom['platform_name']
            platform_icon = rom.get('platform_icon', None)
            file_path = rom['file_path']
            thumbnail = rom['thumbnail']
            file_size = rom['file_size']
            status = rom['status']
            shortcut_link = rom['shortcut_link']

            status_name = rom['status_name']

            if file_path in self.remove_roms_list:
                status = '4'
            elif file_path in self.except_roms_list:
                status = '5'

            origin_filename = rom['origin_filename']
            new_filename = rom['new_filename']
            kr_filename = rom['kr_filename']

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
                status_name_item.setForeground(
                    QColor(255, 102, 102))  # 폰트 색상 설정
            elif status == '1':  # DB 일치
                status_name_item.setForeground(
                    QColor(128, 128, 128))  # 폰트 색상 설정
            elif status == '2':  # 수정 대기
                status_name_item.setForeground(QColor(0, 204, 153))  # 폰트 색상 설정
            elif status == '4':
                status_name_item.setForeground(QColor(255, 102, 102))  # 삭제 대기
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

            # 원본 DB KR 파일명 설정 (수정여부 판단)
            kr_filename_item = QStandardItem(kr_filename)
            kr_filename_item.setFlags(origin_filename_item.flags(
            ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            # kr_filename_item.setFont(bold_font)
            # kr_filename_item.setForeground(QColor(0, 0, 0))
            # kr_filename_item.setBackground(QColor(230, 255, 242))
            self.gui.table_model.setItem(row, 8, kr_filename_item)
            # self.gui.table.setColumnHidden(8, True)

            # 변경될 파일명 설정
            new_filename_item = QStandardItem(new_filename)
            self.gui.table_model.setItem(row, 9, new_filename_item)
            if platform_name == 'ARCADE':
                new_filename_item.setFlags(origin_filename_item.flags(
                ) & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                new_filename_item.setForeground(QColor(255, 128, 0))
                new_filename_item.setFont(italic_font)

            elif shortcut_link:
                new_filename_item.setForeground(QColor(255, 128, 0))
                new_filename_item.setFont(italic_font)
            elif origin_filename == new_filename:
                new_filename_item.setForeground(QColor(0, 204, 153))
            else:
                new_filename_item.setForeground(QColor(51, 173, 255))

            # 행 높이 수정, 아이콘 사이즈 수정
            self.gui.table.setRowHeight(row, 58)
            self.gui.table.setIconSize(QSize(50, 58))

        # 페이지 정보 업데이트 (예: "페이지 1 / 3")
        max_page = self.get_total_pages()
        if self.get_total_pages() > 0:
            self.gui.main.page_label.setText(
                f"페이지 {self.page} / {max_page}")

        # 페이지 버튼 활성 비활성
        if self.page == 1:
            self.gui.main.page_prev_btn.setDisabled(True)
            self.gui.main.page_next_btn.setDisabled(False)
        elif self.page == max_page:
            self.gui.main.page_prev_btn.setDisabled(False)
            self.gui.main.page_next_btn.setDisabled(True)
        else:
            self.gui.main.page_prev_btn.setDisabled(False)
            self.gui.main.page_next_btn.setDisabled(False)

        self.gui.update_titlebar()

    def set_bios(self):
        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        roms_folder = get_settings('directory')
        if not roms_folder:
            alert(
                '현재 설정에서 [bios] 폴더를 찾을 수 없습니다.\n먼저 설정 팝업에서 SD 카드 위치를 지정해야합니다.')
            return

        if not self.confirm_bios_change():
            return

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='bios_install')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.resourcesCopy.connect(
            self.set_bios_install)
        self.worker_thread.start(worker)

    def set_shortcut(self):
        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        roms_folder = get_settings('directory')
        if not roms_folder:
            alert(
                '현재 [Resource] 폴더를 찾을 수 없습니다.\n먼저 설정에서 SD 카드 위치를 지정하고 테마를 설치해야합니다.')
            return

        if not self.confirm_shortcut_change():
            return

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='shortcut_install')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.resourcesCopy.connect(
            self.set_resource_install)
        self.worker_thread.start(worker)

    def set_theme(self):
        # 롬 폴더 경로 (이미 알고 있는 경로로 설정하세요)
        roms_folder = get_settings('directory')
        if not roms_folder:
            alert(
                '현재 [Resource] 폴더를 찾을 수 없습니다.\n먼저 설정에서 SD 카드 위치를 지정하고 테마를 설치해야합니다.')
            return

        if not self.confirm_change_theme():
            return

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='theme_install')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.resourcesCopy.connect(
            self.set_resource_install)
        self.worker_thread.start(worker)

    def roms_scan(self):
        # 삭제,제외 대상 초기화
        self.remove_roms_list = []
        self.except_roms_list = []
        self.all_roms_list = []
        self.current_roms_list = []

        # 롬 폴더 경로 설정 확인
        roms_folder = get_settings('directory')
        if not roms_folder:
            alert('설정하신 롬 폴더 경로가 없습니다.')
            return

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

        # 롬 폴더 경로 설정 확인
        roms_folder = get_settings('directory')
        if not roms_folder:
            alert('설정하신 롬 폴더 경로가 없습니다.')
            return

        # 스캔 시작 버튼을 누를 때 로딩 오버레이를 표시합니다.
        worker = RomScannerWorker(self, action='unnecessary')
        worker.signals.showLoading.connect(self.gui.show_loading_overlay)
        worker.signals.hideLoading.connect(self.gui.hide_loading_overlay)
        worker.signals.romsListReady.connect(self.populate_table_with_roms)
        self.worker_thread.start(worker)

    def roms_replace(self):
        # 테이블이 비었는지 확인
        if self.gui.table_model.rowCount() == 0:
            alert(
                '현재 화면의 수정 목록이 비어 있습니다.\n먼저 설정에서 롬 폴더를 지정하고 롬 파일을 검색해야합니다.')
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
        alert('롬 파일의 수정사항이 모두 반영되었습니다.\n목록을 새로 고칩니다.')
        self.roms_scan()

    def confirm_change_theme(self):
        message = "[드드라]님이 제작하신 드드라 테마(EpicNoir)로 교체하고,\n[듀얼코어]님이 수정하신 한글 메뉴 리소스를 함께 적용합니다.\n이 작업은 Resources 폴더의 파일을 변경합니다.\n정말 적용하시겠습니까?\n\n출처: 무적풍화륜 소통카페"
        reply = QMessageBox.question(None, '테마 적용을 위한 Resources 폴더 내 파일 변경', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def confirm_bios_change(self):
        message = "GBA의 구동 성능을 개선하는 바이오스와 SFC 구동 시 느려지는 문제를 해결하는 펌웨어를 설치합니다.\n바이오스(bios) 폴더 내부의 [ bisrv.asd , gba_bios.bin ] 파일이 변경됩니다.\n부팅 시 나타나는 커스텀 부트로고는 SF2000 부트로고로 초기화됩니다.\n이 작업은 돌이킬 수 없으니 원본 파일을 먼저 백업 해두세요."
        reply = QMessageBox.question(None, '[펌웨어 및 바이오스] 적용을 위한 bios 폴더 내 파일 변경', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def confirm_shortcut_change(self):
        message = "게임 플랫폼별 화면에 4개씩 노출되는 [숏컷] 바로가기를 수정합니다.\nResources 폴더 내부의 xfgle.hgp 파일을 한글 목록으로 교체하게됩니다.\n만약 숏컷이 설정된 롬 파일을 따로 변경할 예정이라면 주의하세요."
        reply = QMessageBox.question(None, '[숏컷] 바로가기 경로 수정을 위한 Resources 폴더 내 파일 변경', message,
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

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
                    font_color = QColor(255, 102, 102) if action == 'remove' else QColor(
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
