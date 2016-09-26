"""
An attempt at reading a WOCE sum file that conforms to chapter 3 of the woce
manual while allowing for some fuzzy.

The woce sum file is defined in section 3.3 of the woce manual. There are a few
problems with it. Perhaps the largest problem is not defining column widths
while expecting the file to be readable to most fortran programers. There are
some well defined parts which we can use to help make a reader.

Things this reader will assume about sumfiles:
* The file will have a header and body seperated by a line consiting of
  repeating ``-`` charicters, ignoring trailing whitespace. [seperation]
* The line immediately above the seperation will have column headers
* The line immediately above the seperation will contain enough information to
  know what columns are present in the file (Table 3.5) [header line]
* The lines above the header line can be ignored. (but should be printed if we
  are writing the file)
* The cast type column will only contain one of the codes in footnote 1 of
  table 3.5
* The event code column will only contain one of the codes in footnote 2 of
  table 3.5
* The Nav column will only contain one of the codes in footnote 3 of table 3.5
* The file will be strictly ASCII
* The date will be MMDDYY (yay america)
* The time will be HHMM
* The lat/lon will be "[D]DD MM.MM X", where X is N, S, E, or W, though
  allowing any number of spaces between the tokens.
* The lines after the seperator (records) will have at least once space
  seperating columns and those columns will extend the entire records section.

A note about events:
The documentation has the following:

    "*In no case should two records in the —.SUM file contain the same STNNBR
    and CASTNO on the same cruise.*"

The big take away from the above is that a "record" can span multiple lines,
and appear to usually do so. Both the parameters and comments section state
that their content "can be continued on all records associated with a given
cast." The parameters section implies that the "record" is defined also by the
event type (e.g. BE, BO, EN):

    "parameter numbers can be continued on all 3 records (BE, BO, EN)
    associated with a bottle cast."

It will be the objective of this reader to collect all the events associated
with a cast into some single "cast" output, including joining multiline comments
into a single string. For "ease" lets assume the output is JSON (though really
it will probably just be a list with some dicts)

Each cast becomes an object like this:

```
{
 "type": "ros", # Table 3.5 footnote 1
 "expocode": "",
 "woce_sect": "",
 "stnnbr": "", 
 "castno": "",
 "parameters": "", #don't really care, but lets keep it
 "comments": "",
 "events": { # keys from Table 3.5 footnote 2
    "bo": {
        "date": "", #RFC3339 dtstring
        "date_precision": 60, # or 86400
        "lat": 0, # degs north
        "lon": 0, # degs east
        "nav": "gps", # table 3.5 footnote 3
        "height": 0, # int or omit key
        "wire": 0, # int or omit key
        "max_pressure": 0, # int or omit key
        "bottles": 36 # integer or omit key
        "depth": 0 # integer or omit key
        "cdepth": 0 # integer or omit key (corrected depth)
    }
  }
}

An entire sum file is a collectino of these cast objects

Undefined Assumptions
---------------------
The following will be a list of assumptions this reader makes which are not
part of the documentation, but appear to be de facto standards due to most (or
every) sum file in the test data having the feature.

* The header labels will have at least one space seperating them. Every file at
    CCHDO appears to conform to this convention. Table 3.5 DOES NOT have a
    space between each header, to make things confusing.
* Parameter lists only contain the following chars ([0-9],-)
"""

from itertools import zip_longest, groupby
from collections import deque
import logging
import warnings

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

POSSIBILITIES = {
        "expocode": ("EXPOCODE", ),
        "woce_sect": ("SECT", "WHP-ID", "WOCE"),
        "stnnbr": ("STNNBR", ),
        "castno": ("CASTNO", ),
        "parameters": ("PARAMETERS", "PARAM", "PARAMETER", "PARAMS", "PARAMATER", "PARAMMETER"),
        "comments": ("COM", "COMM", "COMME", "COMMEN", "COMMUNTS", "COMMENTS", "COMMENT", "COMMMENTS"),
        "max_pressure": ("PRESS", "PRESSURE"),
        "wire": ("WIRE", "OUT"),
        "bottles": ("BOTTLES", "BOTTLE"),
        "height": ("BOTTOM", ),
        "lat": ("LATITUDE", ),
        "lon": ("LONGITUDE", ),
        "type": ("TYPE", ),
        }

class InvalidSumError(Exception):
    pass

def calculate_slices(space_columns):
    position = 0
    column_slices = []
    for value, group in groupby(space_columns):
        length = len(list(group))
        if value == False:
            column_slices.append(slice(position, position+length))
        position += length

    return column_slices

def read_sum(data):
    """
    data is expected to be some bytes string from a sumfile
    """

    # first up, decode the incoming data as ASCII
    try:
        data = data.decode("ascii")
    except UnicodeDecodeError as e:
        raise InvalidSumError("Sum files must be ASCII") from e

    # split into lines
    lines = data.splitlines()

    # Attempt to locate the header and body seperating line
    # we are going to accept the first line that starts with at least 10 ``-``
    # chars after stripping whitespace, we don't care about the line itself,
    # but what is before and after it
    for i, line in enumerate(lines):
        if line.strip().startswith("-" * 10):
            preheader_index = i -2
            header_index = i - 1
            body_index = i + 1
            break
    else:
        raise InvalidSumError("No header seperation line found") from e

    preheader = lines[preheader_index]
    header = lines[header_index]
    body = lines[body_index:]

    #TODO get order of "headers"
    try:
        uncorreced_depth = preheader.index("UNC")
    except ValueError:
        uncorreced_depth = None
    try:
        corrected_depth = preheader.index("COR")
    except ValueError:
        corrected_depth = None

    header_slices = calculate_slices([l == " " for l in header])
    headers = [header[slice] for slice in header_slices]
    log.debug(headers)


    # Figure out where the continious colums of "space" are:
    space_columns = [l == " " for l in body[0]]
    for line in body:
        sc = [l == " " for l in line]
        zipped = zip_longest(space_columns, sc, fillvalue=True)
        space_columns = [a and b for a,b in zipped]

    # convert the list of True/False to slices
    column_slices = calculate_slices(space_columns)

    #chop up the body into columns
    tokenized_body = [[line[slice] for slice in column_slices] for line in body]

if __name__ == "__main__":
    import os
    
    for root, dirs, files in os.walk("test_data"):
        for file in files:
            if not file.endswith(("su.txt", ".sum")):
                continue
            path = os.path.join(root, file)
            #print(path)
            with open(path, 'rb') as f:
                read_sum(f.read())
