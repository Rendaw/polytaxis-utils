import argparse
import sys

import ptmonitor.common

def limit(maxcount, generator):
    count = 0
    for x in generator:
        if count >= maxcount:
            break
        count += 1
        yield x

def main():
    parser = argparse.ArgumentParser(
        description='Query files and tags in ptmonitor database.',
    )
    parser.add_argument(
        'args',
        help='Query argument(s).',
        action='append',
        default=[],
    )
    parser.add_argument(
        '-t',
        '--tags',
        help='Query tags rather than files.',
        choices=['prefix', 'anywhere'],
        default='prefix',
    )
    parser.add_argument(
        '-n',
        '--limit',
        help='Limit number of results.',
        type=int,
        default=1000,
    )
    parser.add_argument(
        '-u',
        '--unwrap',
        help='Provide polytaxis-unwraped filename results.  Requires a running unwrapper.',
        action='store_true',
    )
    args = parser.parse_args()

    if args.unwrap:
        unwrap_root = os.path.join(
            appdirs.user_data_dir('ptwrapd', 'zarbosoft'),
            'mount',
        )

    db = ptmonitor.common.QueryDB()

    if args.tags:
        if len(args.args) != 1:
            parser.error(
                'When querying tags you may only specify one query argument.'
            )
        rows = [
            row for row in limit(
                args.limit, db.query_tags(args.tags, args.args[0])
            )
        ]
        for row in rows:
            print(row)
    else:
        includes, excludes, sort, columns = ptmonitor.common.parse_query(args.args)
        rows = [row for row in limit(args.limit, db.query(includes, excludes))]
        ptmonitor.common.sort(sort, rows)
        for row in rows:
            path = db.query_path(row['fid'])
            if args.unwrap:
                path = os.path.join(unwrap_root, path)
            print(path)
    if len(rows) == args.limit:
        sys.stderr.write('Stoped at {} results.\n'.format(args.limit))

if __name__ == '__main__':
    main()
