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
        nargs='*',
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
    parser.add_argument(
        '-l',
        '--lowercase',
        help='Make all tag keys lowercase.',
        action='store_true',
    )
    args = parser.parse_args()

    ftype = args.type
    for filename in args.file:
        if os.path.isdir(filename):
            parser.error(
                'File [{}] must be a regular file, but it is a directory.'.format(
                    filename,
                )
            )

        overwrite = False
        if polytaxis.get_tags(filename) is not None:
            overwrite = True
            if not args.overwrite:
                print(
                    'File [{}] already has a polytaxis header.'
                    ' Use -o/--overwrite to re-import tags.'
                    .format(filename)
                )
                continue

        if not ftype:
            try:
                mime = magic.Magic(mime=True)
                ftype = mime.from_file(filename).decode('ascii').split('/', 1)[0]
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
                print('File type of [{}] is {}'.format(filename, ftype))
        else:
            raise RuntimeError(
                'File type of [{}] could not be determined. Aborting.'.format(
                    filename,
                )
            )

        tags = None
        try:
            if ftype == 'audio':
                if overwrite:
                    raise RuntimeError(
                        'File type of [{}] doesn\'t currently support overwriting.'
                        .format(
                            filename,
                        ),
                    )
                tags = {
                    key.lower(): set(value) 
                    for key, value in taglib.File(filename).tags.items()
                } 
            elif ftype == 'image':
                with polytaxis.open_unwrap(filename, 'rb') as file:
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
                    filename,
                    traceback.format_exc(),
                ))
        if tags is None:
            raise RuntimeError(
                'Could not read tags from file [{}].'
                ' Filetype may not be supported.'
                .format(
                    filename
                ),
            )

        if args.lowercase:
            temp = {
                key.lower(): values for key, values in tags.items()
            }
            tags = temp

        if args.verbose:
            print('Imported tags: {}'.format(pprint.pformat(tags)))
        polytaxis.set_tags(filename, tags)

if __name__ == '__main__':
    main()
