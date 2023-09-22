import logging
import math
import os
import sqlite3
import sys
import logging
import os
import time
from PyQt5.QtWidgets import QMessageBox
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


def alert(text):
    '''
    Create and show QMessageBox Alert.
    '''
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle('안내')
    msg.setText(text)
    msg.exec_()


def check_selection(table):
    '''
    Get selected rows from table.
    Returns list: [Rows]
    '''
    selection = []
    for index in table.selectionModel().selectedRows():
        selection.append(index.row())
    if not selection:
        alert('다운로드 목록에서 먼저 파일을 선택해주세요.')
    else:
        return selection


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


def get_db_game_name(platform_name, origin_filename):
    category = 'gamelists'
    conn = sqlite3.connect('app/local.db')
    c = conn.cursor()
    c.execute("SELECT kr_filename FROM gamelists WHERE platform_name=? AND UPPER(REPLACE(REPLACE(origin_filename,'.',''),' ','')) = UPPER(REPLACE(REPLACE(?,'.',''),' ','')) OR kr_filename = ?",
              (platform_name, origin_filename, origin_filename))
    result = c.fetchone()
    conn.close()
    if result:
        return str(result[0])
    return None


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
