import argparse
import os
import shutil
import sys
import appdirs

import polytaxis

def main():
    parser = argparse.ArgumentParser(
        description='Perform common cleanup on polytaxis tags.',
    )
    subparsers = parser.add_subparsers(help='Cleanup actions', dest='action')
    subparsers_list = []
    def add_sub(*pargs, **kwargs):
        out = subparsers.add_parser(*pargs, **kwargs)
        subparsers_list.append(out)
        return out
    parser_lowercase = add_sub(
        'lowercase',
        description='Convert tag keys to lowercase.',
    )
    parser_uppercase = add_sub(
        'uppercase',
        description='Convert tag keys to uppercase.',
    )
    parser_replace_key = add_sub(
        'replacekey',
        description='Replace keys.',
    )
    parser_replace_key.add_argument(
        'match',
        help='Key to match',
    )
    parser_replace_key.add_argument(
        'replacement',
        help='Replacement',
    )
    parser_extract = add_sub(
        'extract',
        description='Export polytaxis header-less versions of files.',
    )
    parser_extract.add_argument(
        'directory',
        help='Expored files will be placed in this directory.',
    )
    for sub in subparsers_list:
        sub.add_argument(
            'files',
            help='Files to convert.',
            nargs='+',
        )
        sub.add_argument(
            '-n',
            '--dryrun',
            help='Print result tags but don\'t save them.',
            action='store_true',
        )
        sub.add_argument(
            '-v',
            '--verbose',
            help='Display verbose cleanup information.',
            action='store_true',
        )
    args = parser.parse_args()

    if args.action == 'extract':
        unwrap_root = os.path.join(
            appdirs.user_data_dir('polytaxis-unwrap', 'zarbosoft'),
            'mount',
        )
        if not os.path.isdir(unwrap_root):
            raise RuntimeError('polytaxis-unwrap mount directory doesn\'t exist. To extract files, make sure polytaxis-unwrap is running.')

    modify_headers = [
        'lowercase',
        'uppercase',
        'replacekey',
    ]

    for filename in args.files:
        if os.path.isdir(filename):
            sys.stderr.write(
                'File [{}] must be a regular file, but it is a directory. Skipping.\n'.format(
                    filename,
                )
            )

        tags = polytaxis.get_tags(filename)
        if not tags:
            sys.stderr.write(
                'File [{}] doesn\'t have a polytaxis header. Skipping.\n'.format(
                    filename
                )
            )
            return

        if args.action in modify_headers:
            if args.action == 'lowercase':
                temp = {
                    key.lower(): values for key, values in tags.items()
                }
                tags = temp
            elif args.action == 'uppercase':
                temp = {
                    key.upper(): values for key, values in tags.items()
                }
                tags = temp
            elif args.action == 'replacekey':
                temp = {
                    args.replacement if key == args.match else key: values
                    for key, values in tags.items()
                }
                tags = temp

            if args.dryrun or args.verbose:
                print('Final tags for [{}]:'.format(filename))
                print(polytaxis.encode_tags(tags).decode('utf-8'))

            if not args.dryrun:
                polytaxis.set_tags(filename, tags)

        elif args.action == 'extract':
            new_name = filename
            if new_name.endswith('.p'):
                new_name = new_name[:-2]
            if not args.directory.endswith(os.path.sep):
                args.directory += os.path.sep
            from_path = os.path.join(
                unwrap_root,
                os.path.abspath(filename)[1:],
            )
            to_path = os.path.join(args.directory, new_name)
            if args.dryrun or args.verbose:
                print('Extracting [{}] to [{}]...'.format(from_path, to_path))
            if not args.dryrun:
                shutil.copy(from_path, to_path)

if __name__ == '__main__':
    main()
