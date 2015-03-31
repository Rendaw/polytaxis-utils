import os
import ntpath
import argparse
import signal
import time

import watchdog
import watchdog.events
import watchdog.observers
import appdirs
import polytaxis

from polytaxis_monitor import common

verbose = False

die = False
def signal_handler(signal, frame):
    global die
    die = True
signal.signal(signal.SIGINT, signal_handler)

def os_path_split_asunder(path, windows):
    # Thanks http://stackoverflow.com/questions/4579908/cross-platform-splitting-of-path-in-python/4580931#4580931
    # Mod for windows paths on linux
    parts = []
    while True:
        newpath, tail = (ntpath.split if windows else os.path.split)(path)
        if newpath == path:
            assert not tail
            if path: parts.append(path)
            break
        parts.append(tail)
        path = newpath
    parts.reverse()
    return parts

def split_abs_path(path):
    windows = False
    out = []
    if len(path) > 1 and path[1] == ':':
        windows = True
        drive, path = ntpath.splitdrive(path)
        out.append(drive)
    extend = os_path_split_asunder(path, windows)
    if windows:
        extend.pop(0)
    out.extend(extend)
    return out

def get_fid_and_raw_tags(parent, segment):
    got = cursor.execute(
        'SELECT id, tags FROM files WHERE parent is :parent AND segment = :segment LIMIT 1', 
        {
            'parent': parent, 
            'segment': segment.encode('utf-8'),
        },
    ).fetchone()
    if got is None:
        return None, None
    return got[0], got[1]

def get_fid(parent, segment):
    got = cursor.execute(
        'SELECT id FROM files WHERE parent is :parent AND segment = :segment LIMIT 1', 
        {
            'parent': parent, 
            'segment': segment.encode('utf-8'),
        },
    ).fetchone()
    if got is None:
        return None
    return got[0]

def create_file(filename, tags):
    fid = None
    splits = split_abs_path(filename)
    last_index = len(splits) - 1
    for index, split in enumerate(splits):
        next_fid = get_fid(fid, split)
        if next_fid is None:
            cursor.execute(
                'INSERT INTO files (id, parent, segment, tags) VALUES (NULL, :parent, :segment, :tags)',
                {
                    'parent': fid,
                    'segment': split.encode('utf-8'),
                    'tags': polytaxis.encode_tags(tags) if index == last_index else None,
                },
            )
            next_fid = cursor.lastrowid
        fid = next_fid
    return fid

def delete_file(fid):
    parent = True
    while fid is not None:
        (parent,) = cursor.execute(
            'SELECT parent FROM files WHERE id is :id',
            {
                'id': fid,
            }
        ).fetchone()
        cursor.execute('DELETE FROM files WHERE id is :id', {'id': fid})
        if cursor.execute(
                'SELECT count(1) FROM files WHERE parent is :id',
                {
                    'id': fid,
                },
                ).fetchone()[0] > 0:
            break
        fid = parent

def add_tags(fid, tags):
    if not tags:
        cursor.execute('INSERT INTO tags (tag, file) VALUES (:tag, :fid)',
            {
                'tag': 'untagged'.encode('utf-8'),
                'fid': fid,
            }
        )
        return

    for key, values in tags.items():
        for value in values:
            cursor.execute('INSERT INTO tags (tag, file) VALUES (:tag, :fid)',
                {
                    'tag': polytaxis.encode_tag(key, value),
                    'fid': fid,
                }
            )

def remove_tags(fid):
    cursor.execute('DELETE FROM tags WHERE file = :fid', {'fid': fid})

def process(filename):
    filename = os.path.abspath(filename)
    is_file = os.path.isfile(filename)
    tags = polytaxis.get_tags(filename) if is_file else None
    fid = None
    splits = split_abs_path(filename)
    last_split = splits.pop()
    for split in splits:
        fid = get_fid(fid, split)
        if fid is None:
            break
    fid, old_tags = get_fid_and_raw_tags(fid, last_split)
    if tags is None and fid is None:
        pass
    elif tags is not None and fid is None:
        fid = create_file(filename, tags)
        add_tags(fid, tags)
    elif tags is not None and fid is not None:
        old_tags = polytaxis.decode_tags(old_tags)
        if tags != old_tags:
            remove_tags(fid)
            add_tags(fid, tags)
    elif is_file and tags is None and fid is not None:
        remove_tags(fid)
        delete_file(fid)

def move_file(source, dest):
    sparent = None
    sfid = None
    for split in split_abs_path(source):
        sparent = sfid
        sfid = get_fid(sparent, split)
        if sfid is None:
            return
    dparent = None
    dfid = None
    dsplits = split_abs_path(source)
    new_name = dsplits[-1]
    dsplits = dsplits[:-1]
    for split in dsplits:
        dparent = dfid
        dfid = get_fid(dparent, split)
        if dfid is None:
            return
    cursor.execute(
        'UPDATE files SET parent = :parent, segment = :segment WHERE id = :id',
        {
            'parent': dfid,
            'segment': new_name.encode('utf-8'),
            'id': sfid,
        },
    )

class MonitorHandler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        process(event.src_path)
        conn.commit()

    def on_deleted(self, event):
        process(event.src_path)
        conn.commit()

    def on_modified(self, event):
        process(event.src_path)
        conn.commit()

    def on_moved(self, event):
        move_file(event.src_path, event.dest_path)
        conn.commit()

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
        '-s',
        '--scan',
        action='store_true',
        help='Walk directories for missed file changes before monitoring.',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Enable verbose output.',
    )
    args = parser.parse_args()

    if args.verbose:
        common.verbose = True
        global verbose
        verbose = True
    
    global cursor
    global conn
    conn, cursor = common.open_db()

    if args.scan:
        print('Looking for deleted files...')
        stack = [(False, None, '')]
        parts = []
        last_parent = None
        while stack:
            scanned, fid, segment = stack.pop()
            if not scanned:
                stack.append((True, fid, segment))
                parts.append(segment)
                for next_segment, next_id in cursor.execute(
                        'SELECT segment, id FROM files WHERE parent is :parent',
                        {
                            'parent': fid,
                        }):
                    stack.append((False, next_id, next_segment.decode('utf-8')))
            else:
                joined = '/' + os.path.join(*parts)
                if verbose:
                    print('Checking [{}]'.format(joined))
                if joined and not os.path.exists(joined):
                    print('[{}] no longer exists, removing'.format(joined))
                    remove_tags(fid)
                    delete_file(fid)
                parts.pop()

        for path in args.directory:
            print('Scanning [{}]...'.format(path))
            for base, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    abs_filename = os.path.join(base, filename)
                    if verbose:
                        print('Scanning file [{}]'.format(abs_filename))
                    process(abs_filename)

    conn.commit()

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
