import sqlite3


con = sqlite3.connect('tags.db')
cur = con.cursor()

cur.execute('CREATE TABLE tags(id, name)')
