import errno
import os
import sqlite3
import functools
import random

import appdirs
import polytaxis
import natsort

verbose = False

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def init_db(cursor):
    cursor.execute('CREATE TABLE files (id INTEGER PRIMARY KEY, parent INT, segment TEXT NOT NULL, tags TEXT)')
    cursor.execute('CREATE TABLE tags (tag TEXT NOT NULL, file INT NOT NULL)')

def open_db():
    root = appdirs.user_data_dir('polytaxis-monitor', 'zarbosoft')
    mkdir_p(root)

    db_path = os.path.join(root, 'db.sqlite3')
    do_init_db = False
    if not os.path.exists(db_path):
        print('Initializing db at [{}]'.format(db_path))
        do_init_db = True
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    if do_init_db:
        init_db(cursor)
    return conn, cursor

def _shifttext(source, match):
    if not source.startswith(match):
        return None
    return source[len(match):]

def parse_query(args):
    includes = set()
    excludes = set()
    columns = []
    sort = []
    for item in args:
        col = _shifttext(item, 'col:')
        if col:
            columns.append(col)
            continue
        sort_asc = _shifttext(item, 'sort+:')
        if sort_asc:
            if sort_desc not in columns:
                columns.append(sort_asc)
            sort.append(('asc', sort_asc))
            continue
        sort_desc = _shifttext(item, 'sort-:')
        if sort_desc:
            if sort_desc not in columns:
                columns.append(sort_desc)
            sort.append(('desc', sort_desc))
            continue
        exclude = _shifttext(item, '^')
        if exclude:
            excludes.add(exclude)
            continue
        includes.add(item)
    return includes, excludes, sort, columns

class QueryDB(object):
    def __init__(self):
        conn, self.cursor = open_db()

    def query(self, include, exclude):
        # Assemble includes/excludes into a sql query
        query_include = []
        query_exclude = []
        query_args = {
        }
        query_index = [0]

        def build_select(dest, item):
            if '%' in item:
                dest.append(
                    'SELECT file FROM tags WHERE tag LIKE :tag{}'.format(
                        query_index[0]
                    )
                )
            else:
                dest.append(
                    'SELECT file FROM tags WHERE tag = :tag{}'.format(
                        query_index[0]
                    )
                )
            query_args['tag{}'.format(query_index[0])] = item
            query_index[0] += 1

        for item in include:
            build_select(query_include, item)

        if len(query_include) == 0:
            query_include.append('SELECT file FROM tags')

        for item in exclude:
            build_select(query_exclude, item)

        if query_index[0] == 0:
            query_select = 'SELECT id FROM files WHERE tags is not NULL LIMIT :offset, :size'
        else:
            if query_include:
                query_exclude.insert(0, ' INTERSECT '.join(query_include))
            query_select = (
                ' EXCEPT '.join(query_exclude) + ' LIMIT :offset, :size'
            )
        
        # Perform the query in batches, and manually apply the rest of the
        # filtering.
        batch_size = 100
        batch_index = 0
        while True:
            query_args['offset'] = batch_index
            query_args['size'] = batch_size
            batch = set(
                self.cursor.execute(query_select, query_args).fetchall()
            )
            batch_index += 1
            for (fid,) in batch:
                segment, tags = self.cursor.execute(
                    'SELECT segment, tags FROM files WHERE id = :fid LIMIT 1',
                    {
                        'fid': fid,
                    },
                ).fetchone()
                tags = polytaxis.decode_tags(tags.encode('utf-8'))
                yield {
                    'fid': fid,
                    'segment': segment,
                    'tags': tags,
                }
            if len(batch) < batch_size:
                break

    def query_path(self, fid):
        segments = []
        while fid is not None:
            fid, segment = self.cursor.execute(
                'SELECT parent, segment FROM files WHERE id = :id LIMIT 1',
                {
                    'id': fid,
                },
            ).fetchone()
            segments.append(segment)
        return os.path.join(*reversed(segments))

    def query_tags(self, method, arg):
        batch_size = 100
        batch_index = 0
        while True:
            if method == 'prefix':
                batch = self.cursor.execute(
                    'SELECT DISTINCT tag FROM tags WHERE tag LIKE :arg ORDER BY tag ASC LIMIT :offset, :size',
                    {
                        'arg': arg + '%',
                        'offset': batch_index,
                        'size': batch_size,
                    },
                ).fetchall()
            elif method == 'anywhere':
                batch = self.cursor.execute(
                    'SELECT DISTINCT tag FROM tags WHERE tag LIKE :arg ORDER BY tag ASC LIMIT :offset, :size',
                    {
                        'arg': '%' + arg + '%',
                        'offset': batch_index,
                        'size': batch_size,
                    },
                ).fetchall()
            batch_index += 1 
            for (tag,) in batch:
                yield tag
            if len(batch) < batch_size:
                break

_natkey = natsort.natsort_keygen()
def sort(sort_info, rows):
    random.shuffle(rows)
    def cmp(x, y):
        for direction, column in sort_info:
            x_val = _natkey(x['tags'][column])
            y_val = _natkey(y['tags'][column])
            less = 0
            if x_val < y_val:
                less = -1
            elif x_val > y_val:
                less = 1
            if less == 0:
                continue
            if direction == 'desc':
                return less * -1
            else:
                return less
        return 0
    return sorted(rows, key=functools.cmp_to_key(cmp))

