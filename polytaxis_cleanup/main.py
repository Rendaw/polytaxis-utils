import argparse
import os

import polytaxis

def main():
    parser = argparse.ArgumentParser(
        description='Perform common cleanup on polytaxis tags.',
    )
    subparsers = parser.add_subparsers(help='Cleanup actions', dest='action')
    parser_lowercase = subparsers.add_parser('lowercase')
    parser_uppercase = subparsers.add_parser('uppercase')
    parser_replace_key = subparsers.add_parser('replacekey')
    parser_replace_key.add_argument(
        'match',
        help='Key to match',
    )
    parser_replace_key.add_argument(
        'replacement',
        help='Replacement',
    )
    parser.add_argument(
        'file',
        help='File to convert.',
    )
    parser.add_argument(
        '-n',
        '--dryrun',
        help='Print result tags but don\'t save them.',
        action='store_true',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='Display verbose cleanup information.',
        action='store_true',
    )
    args = parser.parse_args()

    if os.path.isdir(args.file):
        parser.error(
            'File [{}] must be a regular file, but it is a directory.'.format(
                args.file,
            )
        )

    tags = polytaxis.get_tags(args.file)
    if not tags:
        raise RuntimeError(
            'File [{}] doesn\'t have a polytaxis header. Aborting.'.format(
                args.file
            )
        )
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
        print('Final tags for [{}]:'.format(args.file))
        print(polytaxis.encode_tags(tags).decode('utf-8'))

    if not args.dryrun:
        polytaxis.set_tags(args.file, tags)

if __name__ == '__main__':
    main()
