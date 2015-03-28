import errno
import os
import sqlite3

import appdirs
import polytaxis

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


def init_db(conn):
    conn.execute('CREATE TABLE files (id INTEGER PRIMARY KEY, parent INT, segment TEXT NOT NULL, tags TEXT)')
    conn.execute('CREATE TABLE tags (tag TEXT NOT NULL, file INT NOT NULL)')

def open_db():
    root = appdirs.user_data_dir('ptmonitor', 'zarbosoft')
    mkdir_p(root)

    db_path = os.path.join(root, 'db.sqlite3')
    do_init_db = False
    if not os.path.exists(db_path):
        print(u'Initializing db at [{}]'.format(db_path))
        do_init_db = True
    conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    conn = conn.cursor()
    if do_init_db:
        init_db(conn)
    return conn

def parse_query(args):
    includes = set()
    excludes = set()
    columns = []
    sort = []
    for item in args:
        col = shifttext(item, 'col:')
        if col:
            columns.append(col)
            continue
        sort_asc = shifttext(item, 'sort+:')
        if sort_asc:
            columns.append(sort_asc)
            sort.append(('asc', sort_asc))
            continue
        sort_desc = shifttext(item, 'sort-:')
        if sort_desc:
            columns.append(sort_desc)
            sort.append(('desc', sort_desc))
            continue
        exclude = shifftest(item, '-')
        if exclude:
            excludes.append(polytaxis.decode_tag(exclude))
            continue
        includes.append(polytaxis.decode_tag(item))
        self.query_changed.emit(includes, excludes, columns, sort)
    return includes, excludes, sort, columns

class QueryDB(object):
    def __init__(self):
        self.conn = open_db()

    def query(self, include, exclude):
        primary_tags = []
        primary_include = []
        primary_exclude = []
        primary_args = {
        }
        primary_limit = 3
        primary_index = 0
        for key, value in include:
            primary_include.append(
                'SELECT file FROM tags WHERE tag = :tag{}'.format(
                    primary_index
                )
            )
            primary_args['tag{}'.format(primary_index)] = (
                polytaxis.encode_tag(key, value)
            )
            primary_index += 1
            if primary_index >= primary_limit:
                break
        for key, value in exclude:
            primary_exclude.append(
                'SELECT file FROM tags WHERE tag != :tag{}'.format(
                    primary_index
                )
            )
            primary_args['tag{}'.format(primary_index)] = (
                polytaxis.encode_tag(key, value)
            )
            primary_index += 1
            if primary_index >= primary_limit:
                break
        if primary_index == 0:
            primary_select = 'SELECT id FROM files WHERE tags is not NULL LIMIT :offset, :size'
        else:
            if primary_include:
                primary_exclude.insert(0, ' INTERSECT '.join(primary_include))
            primary_select = (
                ' EXCEPT '.join(primary_exclude) + ' LIMIT :offset, :size'
            )
        batch_size = 100
        batch_index = 0
        while True:
            primary_args['offset'] = batch_index
            primary_args['size'] = batch_size
            batch = set(
                self.conn.execute(primary_select, primary_args).fetchall()
            )
            batch_index += 1
            for (fid,) in batch:
                segment, tags = self.conn.execute(
                    'SELECT segment, tags FROM files WHERE id = :fid LIMIT 1',
                    {
                        'fid': fid,
                    },
                ).fetchone()
                tags = polytaxis.decode_tags(tags)
                def manual_filter():
                    for key, value in include:
                        found_values = tags.get(key)
                        if found_values is None:
                            return False
                        if not value in found_values:
                            return False
                    for key, value in exclude:
                        found_values = tags.get(key)
                        if found_values is None:
                            continue
                        if value in found_values:
                            return False
                    return True
                if not manual_filter():
                    continue
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
            fid, segment = self.conn.execute(
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
                batch = self.conn.execute(
                    'SELECT DISTINCT tag FROM tags WHERE tag LIKE :arg ORDER BY tag ASC LIMIT :offset, :size',
                    {
                        'arg': arg + '%',
                        'offset': batch_index,
                        'size': batch_size,
                    },
                ).fetchall()
            elif method == 'anywhere':
                batch = self.conn.execute(
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

def sort(sort_info, rows):
    def cmp(x, y):
        for direction, column in sort_info:
            x_val = x['tags'][column]
            y_val = y['tags'][column]
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
    return sorted(rows, cmp)

