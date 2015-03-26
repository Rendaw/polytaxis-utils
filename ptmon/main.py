import os
import argparse
import signal
import errno
import sqlite3
import time

import watchdog
import watchdog.events
import watchdog.observers
import appdirs
import polytaxis


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


die = False
def signal_handler(signal, frame):
    global die
    die = True
signal.signal(signal.SIGINT, signal_handler)

def split_path(path):
    out = []
    head = path
    while True:
        head, tail = os.path.split(head)
        if not tail:
            break
        out.append(tail)
    return reversed(out)

def get_fid(parent, segment):
    got = conn.execute(
        'SELECT id FROM files WHERE parent is :parent AND segment = :segment LIMIT 1', 
        {
            'parent': parent, 
            'segment': segment,
        },
    ).fetchone()
    if got is None:
        return None
    return got[0]

def create_file(filename):
    fid = None
    for split in split_path(filename):
        next_fid = get_fid(fid, split)
        if next_fid is None:
            conn.execute(
                'INSERT INTO files (id, parent, segment) VALUES (NULL, :parent, :segment)',
                {
                    'parent': fid,
                    'segment': split,
                },
            )
            next_fid = conn.lastrowid
        fid = next_fid
    return fid

def delete_file(fid):
    while True:
        parent = conn.execute(
            'SELECT parent FROM files WHERE id = :id',
            {
                'id': fid,
            }
        ).fetchone()[0]
        if parent is None:
            break
        conn.execute('DELETE FROM files WHERE id = :id', {'id': fid})
        if conn.execute(
                'SELECT count(1) FROM files WHERE parent is :id',
                {
                    'id': fid,
                },
                ).fetchone()[0] > 0:
            break
        fid = parent

def add_tags(fid, tags):
    for key, values in tags.items():
        for value in values:
            conn.execute('INSERT INTO tags (tag, file) VALUES (:tag, :fid)',
                {
                    'tag': polytaxis.encode_tag(key, value),
                    'fid': fid,
                }
            )

def remove_tags(fid):
    conn.execute('DELETE FROM tags WHERE file = :fid', {'fid': fid})

def process(filename):
    is_file = os.path.isfile(filename)
    tags = polytaxis.get_tags(filename) if is_file else None
    fid = None
    for split in split_path(filename):
        fid = get_fid(fid, split)
        if fid is None:
            break
    if tags is None and fid is None:
        pass
    elif tags is not None and fid is None:
        fid = create_file(filename)
        add_tags(fid, tags)
    elif tags is not None and fid is not None:
        remove_tags(fid)
        add_tags(fid, tags)
    elif is_file and tags is None and fid is not None:
        remove_tags(fid)
        delete_file(fid)

def move_file(source, dest):
    sparent = None
    sfid = None
    for split in split_path(source):
        sparent = sfid
        sfid = get_fid(sparent, split)
        if sfid is None:
            return
    dparent = None
    dfid = None
    dsplits = split_path(source)
    new_name = dsplits[-1]
    dsplits = dsplits[:-1]
    for split in dsplits:
        dparent = dfid
        dfid = get_fid(dparent, split)
        if dfid is None:
            return
    conn.execute(
        'UPDATE files SET parent = :parent, segment = :segment WHERE id = :id',
        {
            'parent': dfid,
            'segment': new_name,
            'id': sfid,
        },
    )

class MonitorHandler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        process(event.src_path)

    def on_deleted(self, event):
        process(event.src_path)

    def on_modified(self, event):
        process(event.src_path)

    def on_moved(self, event):
        move_file(event.src_path, event.dest_path)

def main():
    parser = argparse.ArgumentParser(
        description='Monitor directories, index polytaxis tags.',
    )
    parser.add_argument(
        'directory', 
        action='append', 
        help='Path to monitor.', 
        default=[],
    )
    parser.add_argument(
        '-c',
        '--check',
        action='store_true',
        help='Check known files, fix errors before monitoring.',
    )
    parser.add_argument(
        '-s',
        '--scan',
        action='store_true',
        help='Walk directories for missed files before monitoring.',
    )
    args = parser.parse_args()
    
    root = appdirs.user_data_dir('polytaxis', 'zarbosoft')
    mkdir_p(root)

    db_path = os.path.join(root, 'db.sqlite3')
    global conn
    init_db = False
    if not os.path.exists(db_path):
        print('Initializing db at [{}]'.format(db_path))
        init_db = True
    conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    conn = conn.cursor()
    if init_db:
        conn.execute('CREATE TABLE files (id INTEGER PRIMARY KEY, parent INT, segment TEXT NOT NULL)')
        conn.execute('CREATE TABLE tags (tag TEXT NOT NULL, file INT NOT NULL)')

    if args.check:
        print('Checking...')
        stack = [(False, None, '')]
        parts = []
        last_parent = None
        while stack:
            scanned, fid, segment = stack.pop()
            if not scanned:
                stack.append((True, fid, segment))
                parts.append(segment)
                for next_segment, next_id in conn.execute(
                        'SELECT segment, id FROM files WHERE parent is :parent',
                        {
                            'parent': fid,
                        }):
                    stack.append((False, next_id, next_segment))
            else:
                joined = '/' + os.path.join(*parts)
                print('Checking [{}]'.format(joined)) # DEBUG
                if joined and not os.path.exists(joined):
                    print(u'[{}] no longer exists, removing'.format(joined))
                    remove_tags(fid)
                    delete_file(fid)
                parts.pop()

    if args.scan:
        for path in args.directory:
            print('Scanning [{}]...'.format(path))
            for base, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    process(os.path.join(base, filename))

    observer = watchdog.observers.Observer()
    handler = MonitorHandler()
    for path in args.directory:
        print('Starting watch on [{}]'.format(path))
        observer.schedule(handler, path, recursive=True)
    observer.start()
    try:
        while not die:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    observer.stop()
    observer.join()

if __name__ == '__main__':
    main()
