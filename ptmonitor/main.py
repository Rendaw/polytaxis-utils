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

import common


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

def create_file(filename, tags):
    fid = None
    splits = split_abs_path(filename)
    last_index = len(splits) - 1
    for index, split in enumerate(splits):
        next_fid = get_fid(fid, split)
        if next_fid is None:
            conn.execute(
                'INSERT INTO files (id, parent, segment, tags) VALUES (NULL, :parent, :segment, :tags)',
                {
                    'parent': fid,
                    'segment': split,
                    'tags': polytaxis.encode_tags(tags) if index == last_index else None,
                },
            )
            next_fid = conn.lastrowid
        fid = next_fid
    return fid

def delete_file(fid):
    parent = True
    while fid is not None:
        (parent,) = conn.execute(
            'SELECT parent FROM files WHERE id is :id',
            {
                'id': fid,
            }
        ).fetchone()
        conn.execute('DELETE FROM files WHERE id is :id', {'id': fid})
        if conn.execute(
                'SELECT count(1) FROM files WHERE parent is :id',
                {
                    'id': fid,
                },
                ).fetchone()[0] > 0:
            break
        fid = parent

def add_tags(fid, tags):
    if not tags:
        conn.execute('INSERT INTO tags (tag, file) VALUES (:tag, :fid)',
            {
                'tag': 'untagged',
                'fid': fid,
            }
        )
        return

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
    filename = os.path.abspath(filename)
    is_file = os.path.isfile(filename)
    tags = polytaxis.get_tags(filename) if is_file else None
    fid = None
    for split in split_abs_path(filename):
        fid = get_fid(fid, split)
        if fid is None:
            break
    if tags is None and fid is None:
        pass
    elif tags is not None and fid is None:
        fid = create_file(filename, tags)
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
    
    global conn
    conn = common.open_db()

    if args.check:
        print(u'Checking...')
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
                print(u'Checking [{}]'.format(joined)) # DEBUG
                if joined and not os.path.exists(joined):
                    print(u'[{}] no longer exists, removing'.format(joined))
                    remove_tags(fid)
                    delete_file(fid)
                parts.pop()

    if args.scan:
        for path in args.directory:
            print(u'Scanning [{}]...'.format(path))
            for base, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    process(os.path.join(base, filename))

    observer = watchdog.observers.Observer()
    handler = MonitorHandler()
    for path in args.directory:
        print(u'Starting watch on [{}]'.format(path))
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
