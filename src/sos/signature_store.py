#!/usr/bin/env python3
#
# Copyright (c) Bo Peng and the University of Texas MD Anderson Cancer Center
# Distributed under the terms of the 3-clause BSD License.

from collections import namedtuple
import os
import sqlite3
import fasteners

class SignatureStore:
    TargetSig = namedtuple('TargetSig', 'mtime size md5')

    def __init__(self):
        self.db_file = os.path.join(os.path.expanduser('~'), '.sos', 'signatures.db')
        self.lock_file=self.db_file + '_'
        self._conn = None
        self._pid = None

        with fasteners.InterProcessLock(self.lock_file):
            if not os.path.isfile(self.db_file):
                conn = sqlite3.connect(self.db_file, timeout=20)
                conn.execute('''CREATE TABLE SIGNATURE (
                    target text PRIMARY KEY,
                    mtime FLOAT,
                    size INTEGER,
                    md5 text NOT NULL
                )''')
                conn.commit()
                conn.close()

    def _get_conn(self):
        # there is a possibility that the _conn is copied with a process
        # and we would better have a fresh conn
        if self._conn is None or self._pid != os.getpid():
            self._conn = sqlite3.connect(self.db_file, timeout=20)
            self._pid = os.getpid()
        return self._conn

    conn = property(_get_conn)

    def _list_all(self):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM SIGNATURE;')
        for rec in cur.fetchall():
            print(self.TargetSig._make(rec))

    def get(self, target):
        cur = self.conn.cursor()
        cur.execute(
            'SELECT mtime, size, md5 FROM SIGNATURE WHERE target=? ', (target.target_name(),))
        res = cur.fetchone()
        return self.TargetSig._make(res) if res else None

    def set(self, target, mtime:float, size:str, md5: str):
        #with fasteners.InterProcessLock(self.lock_file):
        self.conn.cursor().execute(
            'INSERT OR REPLACE INTO SIGNATURE VALUES (?, ?, ?, ?)',
            (target.target_name(), mtime, size, md5))
        self.conn.commit()

    def remove(self, target):
        #with fasteners.InterProcessLock(self.lock_file):
        cur=self.conn.cursor()
        cur.execute(
                'DELETE FROM SIGNATURE WHERE target=?', (target.target_name(),))
        self.conn.commit()

    def clear(self):
        cur=self.conn.cursor()
        cur.execute('DELETE FROM SIGNATURE')
        self.conn.commit()
        cur.execute('VACUUM')
        self.conn.commit()

sig_store = SignatureStore()
