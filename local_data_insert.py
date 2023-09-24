# -*- coding: utf-8 -*-
import sqlite3

from core.gui.helpers import database_init

# SQLite 데이터베이스에 연결
conn = sqlite3.connect('app/local.db')

# SQLite 데이터베이스 생성 (초기화)
database_init()

try:
    # 커서 생성
    cursor = conn.cursor()

    # SQL 파일을 읽어옴
    with open('app/data.sql', 'r', encoding='utf-8') as sql_file:
        sql_queries = sql_file.read()

    # SQL 파일 내의 모든 쿼리 실행
    cursor.executescript(sql_queries)

    # 변경사항을 커밋
    conn.commit()

except sqlite3.Error as e:
    print("SQLite 오류:", e)

finally:
    # 연결 종료
    conn.close()
