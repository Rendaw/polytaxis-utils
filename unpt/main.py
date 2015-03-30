import argparse
import os

import appdirs

def main():
    parser = argparse.ArgumentParser(
        description='Translate a path for use with polytaxis-unwrap',
    )
    parser.add_argument(
        'path',
        help='Path to convert.',
    )
    args = parser.parse_args()

    unwrap_root = os.path.join(
        appdirs.user_data_dir('polytaxis-unwrap', 'zarbosoft'),
        'mount',
    )
    if not os.path.isdir(unwrap_root):
        raise RuntimeError('polytaxis-unwrap mount directory doesn\'t exist.')

    print(os.path.join(unwrap_root, args.path[1:]))

if __name__ == '__main__':
    main()
