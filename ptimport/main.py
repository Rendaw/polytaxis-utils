import argparse
import os
import sys
import traceback
import pprint

import exifread
import taglib
import magic
import polytaxis

def main():
    parser = argparse.ArgumentParser(
        description='Create polytaxis tags from other formats.',
    )
    parser.add_argument(
        'file',
        help='File to convert.',
    )
    parser.add_argument(
        '-o',
        '--overwrite',
        help='Overwrite polytaxis header if it already exists',
        action='store_true',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='Display verbose import information.',
        action='store_true',
    )
    parser.add_argument(
        '-t',
        '--type',
        help='Don\'t try to detect the file type. Instead, use this type.',
        choices=['audio', 'image'],
    )
    args = parser.parse_args()

    if os.path.isdir(args.file):
        parser.error(
            'File [{}] must be a regular file, but it is a directory.'.format(
                args.file,
            )
        )

    overwrite = False
    if polytaxis.get_tags(args.file) is not None:
        overwrite = True
        if not args.overwrite:
            raise RuntimeError(
                'File [{}] already has a polytaxis header.'
                ' Use -o/--overwrite to re-import tags.'
            )

    ftype = args.type
    if not ftype:
        try:
            mime = magic.Magic(mime=True)
            ftype = mime.from_file(args.file).decode('ascii').split('/', 1)[0]
        except:
            if args.verbose:
                sys.stderr.write(
                    'Error while determining file type of [{}]: {}\n'.format(
                        args.file,
                        traceback.format_exc(),
                    )
                )
            pass
    if ftype:
        if args.verbose:
            print('File type of [{}] is {}'.format(args.file, ftype))
    else:
        raise RuntimeError(
            'File type of [{}] could not be determined. Aborting.'.format(
                args.file,
            )
        )

    tags = None
    try:
        if ftype == 'audio':
            if overwrite:
                raise RuntimeError(
                    'File type of [{}] doesn\'t currently support overwriting.'
                    .format(
                        args.file,
                    ),
                )
            tags = {
                key: set(value) 
                for key, value in taglib.File(args.file).tags.items()
            } 
        elif ftype == 'image':
            with polytaxis.open_unwrap(args.file, 'r') as file:
                tags = { 
                    key: set([str(value)])
                    for key, value in exifread.process_file(file).items()
                    if key not in (
                        'JPEGThumbnail', 
                        'TIFFThumbnail', 
                        'Filename', 
                        'EXIF MakerNote'
                    )
                } 
    except:
        if args.verbose:
            sys.stderr.write('Error while reading tags from [{}]: {}\n'.format(
                args.file,
                traceback.format_exc(),
            ))
    if tags is None:
        raise RuntimeError(
            'Could not read tags from file [{}].'
            ' Filetype may not be supported.'
            .format(
                args.file
            ),
        )
    if args.verbose:
        print('Imported tags: {}'.format(pprint.pformat(tags)))
    polytaxis.set_tags(args.file, tags)

if __name__ == '__main__':
    main()
