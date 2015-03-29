# Installation

Run `pip2 install git+https://github.com/Rendaw/ptutils`.

# Utilities

## ptmonitor

`ptmonitor` monitors directories for polytaxis file additions/modifications/deletions and indexes their tags.

Files with no tags will be categorized with the tag 'untagged'.

For usage, run `ptmonitor -h`.

## ptq

`ptq` is a command line tool to query the `ptmonitor` database. `ptq` can search for files by tag as well as search available tags.

For information on flags and other arguments, run `ptq -h`.

#### File Queries
File queries are written as a list of terms. A term can be a tag ('tag' or 
'tag=value', matched in full), an exclusion ('-tag' or '-tag=value'), or a 
special term. Terms should be escaped if there are non-syntax special 
characters (equal signs, spaces, newlines, etc.) in the text.

Special terms:
sort+:COLUMN    Sort output, ascending, by COLUMN.
sort-:COLUMN    Sort output, descending, by COLUMN.
col:COLUMN      Include COLUMN in the output. If no columns are specified,
                show the filename.

Sorts are specified in higher to lower pecedence.
Currently, columns cannot be selected (only the filename is displayed).

Example:
ptq 'album=polytaxis official soundtrack' sort+:discnumber sort+:tracknumber

#### Tag Queries
Tag queries take a single string. The string is used as a query parameter
based on the query modifier ('prefix' or 'anywhere').

Example:
ptq -t prefix album=        Lists all albums.

## ptimport

`ptimport` is a command line tool to convert a file with existing filetype-specific tags into a polytaxis header.

For usage, run `ptimport -h`.

