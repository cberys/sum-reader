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
        "bottle": 36 # integer or omit key
    }
  }
}

An entire sum file is a collectino of these cast objects
"""

def read_sum_file(f):
    """
    """
