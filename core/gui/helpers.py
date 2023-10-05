import logging
import math
import os
import re
import sqlite3
import sys
import logging
import os
import time
from PyQt5.QtWidgets import QMessageBox, QApplication
import tkinter as tk

FIRST_RUN = True
PLATFORM = os.name


def convert_size(size_bytes: int) -> str:
    '''
    Convert from bytes to human readable sizes (str).
    '''
    # https://stackoverflow.com/a/14822210
    if size_bytes == 0:
        return '0 B'
    size_name = ('B', 'KB', 'MB', 'GB', 'TB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '%s %s' % (s, size_name[i])


def absp(path):
    '''
    Get absolute path.
    '''
    if getattr(sys, "frozen", False):
        # Pyinstaller 컴파일 이후 경로
        resolved_path = resource_path(path)
    else:
        # Python 파일 실행시 경로
        relative_path = os.path.join(os.path.dirname(__file__), '.')
        resolved_path = os.path.join(os.path.abspath(relative_path), path)

    return resolved_path


def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(
        os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def abs_config(path):
    # 프로그램 실행 경로로 고정
    resolved_path = os.path.abspath(path)
    return resolved_path


def create_file(f):
    '''
    Create empty file.
    [note] Used to create app/settings and app/cache.
    '''
    f = abs_config(f)
    logging.debug(f'Attempting to create file: {f}...')
    os.makedirs(os.path.dirname(f), exist_ok=True)
    f = open(f, 'x')
    f.close()


def getClipboardText():
    root = tk.Tk()
    # keep the window from showing
    root.withdraw()
    return root.clipboard_get()


def database_init():
    conn = sqlite3.connect('app/local.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY not null,
        value TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS gamelists (
        platform_name TEXT not null,
        origin_filename TEXT not null,
        kr_filename TEXT,
        shortcut_link TEXT,
        CONSTRAINT gamelists_pk PRIMARY KEY (platform_name,origin_filename)
    )
    ''')

    conn.commit()
    conn.close()


def get_settings(key):
    conn = sqlite3.connect('app/local.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0]
    return None


# DB에서 모든 게임의 정보를 가져오는 함수
def get_all_db_game_names(platforms):
    conn = sqlite3.connect('app/local.db')
    cursor = conn.cursor()
    db_results = {}

    for platform in platforms:
        print(
            f"SELECT origin_filename,kr_filename, shortcut_link, platform_name FROM gamelists WHERE platform_name = '{platform}'")
        cursor.execute(
            f"SELECT origin_filename,kr_filename, shortcut_link, platform_name FROM gamelists WHERE platform_name = '{platform}'")
        results = cursor.fetchall()

        for result in results:
            # 오리지널 명칭 조회
            db_results[(platform, result[0])] = {"origin_filename": result[0],
                                                 "kr_filename": result[1], "shortcut_link": result[2], "platform_name": result[3]}
            # 한글로 변환된 명칭 조회
            db_results[(platform, result[1])] = {"origin_filename": result[1],
                                                 "kr_filename": result[1], "shortcut_link": result[2], "platform_name": result[3]}

    conn.close()

    return db_results


def get_db_game_name(platform_name, origin_filename):
    category = 'gamelists'
    conn = sqlite3.connect('app/local.db')
    c = conn.cursor()
    c.execute("SELECT kr_filename,shortcut_link FROM gamelists WHERE platform_name=? AND UPPER(REPLACE(REPLACE(origin_filename,'.',''),' ','')) = UPPER(REPLACE(REPLACE(?,'.',''),' ','')) OR kr_filename = ?",
              (platform_name, origin_filename, origin_filename))
    result = c.fetchone()
    conn.close()
    if result:
        return {"kr_filename": result[0], "shortcut_link": result[1]}
    return {"kr_filename": '', "shortcut_link": ''}


def get_db_shortcut_game_name():
    category = 'gamelists'
    conn = sqlite3.connect('app/local.db')
    c = conn.cursor()
    c.execute(
        "SELECT kr_filename FROM gamelists WHERE shortcut_link IS NOT NULL AND shortcut_link != ''")
    # 모든 레코드 가져오기
    results = c.fetchall()
    # 연결 종료
    conn.close()
    # 결과 반환
    return [row[0] for row in results] if results else []


def set_settings(key, value):
    category = 'settings'
    conn = sqlite3.connect('app/local.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings VALUES (?,?)",
              (key, value))
    conn.commit()
    conn.close()


def get_file_name(file_path: str) -> str:
    return os.path.basename(file_path)


def get_file_extension(file_path: str) -> str:
    _, extension = os.path.splitext(file_path)
    return extension


def get_file_name_without_extension(file_path):
    # 파일의 기본 이름을 가져옵니다 (디렉토리를 제외).
    base_name = os.path.basename(file_path)

    # 파일명과 확장자를 분리합니다.
    file_name, _ = os.path.splitext(base_name)

    return file_name


def get_platform_name(file_path):
    # 경로를 디렉토리와 파일로 분리
    directory, filename = os.path.split(file_path)

    # 디렉토리 경로를 분리하여 리스트로 만듭니다
    directories = directory.split(os.path.sep)

    # 마지막 폴더 이름을 추출하여 반환
    last_folder = directories[-1]

    return last_folder


def alert(text):
    '''
    Create and show QMessageBox Alert.
    '''
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle('안내')
    # 화면 중앙 좌표 계산
    screen_geo = QApplication.primaryScreen().geometry()
    screen_center = screen_geo.center()

    # 메시지 박스의 크기를 설정
    msg_box_width = 300  # 메시지 박스의 너비
    msg_box_height = 200  # 메시지 박스의 높이

    # 메시지 박스를 화면 중앙으로 이동
    msg.setGeometry(
        screen_center.x() - msg_box_width // 2,
        screen_center.y() - msg_box_height // 2,
        msg_box_width,
        msg_box_height
    )

    msg.setText(text)
    msg.exec_()


def replace_shortcut_link(origin_name, modify_name):
    shortcut_file_path = os.path.normpath(
        absp(f'res/data/Resources/xfgle.hgp'))

    # 파일을 열어 읽기 모드로 가져옵니다.
    with open(shortcut_file_path, 'r') as file:
        text = file.readlines()

    # 파일을 다시 열어 쓰기 모드로 가져옵니다.
    with open(shortcut_file_path, 'w') as file:
        for line in text:
            # 정규식 패턴을 사용하여 중간 문구를 추출합니다.
            pattern = r"(\d+)\s+(.+)\..+$"
            match = re.match(pattern, line)
            if match:
                prefix, middle_text, extension = match.groups()

                # 파일명이 수정되었다면 중간 문구를 수정합니다.
                if origin_name != modify_name and origin_name == middle_text:
                    modified_line = f'{prefix} {modify_name}.{extension}\n'
                else:
                    modified_line = line
                file.write(modified_line)
            else:
                # 정규식과 일치하지 않는 라인은 그대로 유지합니다.
                file.write(line)
