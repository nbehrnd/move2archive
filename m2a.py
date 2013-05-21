#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-05-21 11:59:57 vk>

import os
import sys
import re
import time
import logging
from optparse import OptionParser
import shutil ## for copying and moving items

## TODO:
## * fix parts marked with «FIXXME»
## * document folder shortcut for "lp" and "rp"
## * document "no target folder given" with askfordir (just like no askfordir)

PROG_VERSION_NUMBER = u"0.2"
PROG_VERSION_DATE = u"2013-01-01"
INVOCATION_TIME = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

## better performance if ReEx is pre-compiled:

## search for: «YYYY-MM-DD»
DATESTAMP_REGEX = re.compile("([12]\d\d\d)-([012345]\d)-([012345]\d)")
DATESTAMP_REGEX_DAYINDEX = 3
DATESTAMP_REGEX_MONTHINDEX = 2
DATESTAMP_REGEX_YEARINDEX = 1

DEFAULT_ARCHIVE_PATH = os.environ['HOME'] + "/archive/events_memories"

PAUSEONEXITTEXT = "    press <Enter> to quit"

USAGE = u"\n\
    " + sys.argv[0] + u" <options> <file(s)>\n\
\n\
This script moves items (files or directories) containing ISO datestamps \n\
like \"YYYY-MM-DD\" into a directory stucture for the corresponding year.\n\
\n\
You define the base directory either in this script (or using the\n\
command line argument \"--archivedir\"). The convention is e.g.:\n\
\n\
        <archivepath>/2009\n\
        <archivepath>/2010\n\
        <archivepath>/2011\n\
\n\
Per default, this script extracts the year from the datestamp of\n\
each file and moves it into the corresponding directory for its year:\n\
\n\
     " + sys.argv[0] + u" 2010-01-01_Jan2010.txt 2011-02-02_Feb2011.txt\n\
... moves \"2010-01-01_Jan2010.txt\" to \"<archivepath>/2010/\"\n\
... moves \"2011-02-02_Feb2011.txt\" to \"<archivepath>/2011/\"\n\
\n\
OPTIONALLY you can define a sub-directory name with option \"-d DIR\". If it\n\
contains no datestamp by itself, a datestamp from the first file of the\n\
argument list will be used. This datestamp will be put in front of the name:\n\
\n\
     " + sys.argv[0] + u"  -d \"2009-02-15 bar\"  one two three\n\
... moves all items to: \"<archivepath>/2009/2009-02-15 bar/\"\n\
\n\
     " + sys.argv[0] + u"  -d bar  2011-10-10_one 2008-01-02_two 2011-10-12_three\n\
... moves all items to: \"<archivepath>/2011/2011-10-10 bar/\"\n\
\n\
If you feel uncomfortable you can simulate the behavior using the \"--dryrun\"\n\
option. You see what would happen without changing anything at all.\n\
\n\
\n\
:copyright: (c) 2011 by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v2 or any later version\n\
:bugreports: <tools@Karl-Voit.at>\n\
:version: "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE+"\n"

parser = OptionParser(usage=USAGE)

parser.add_option("-d", "--directory", dest="targetdir",
                  help="name of a target directory that should be created (optionally add datestamp)", metavar="DIR")

parser.add_option("--askfordirectory", dest="askfordir", action="store_true",
                  help="similar to \"-d\" but tool asks for an input line when invoked")

parser.add_option("-a", "--append", dest="append", action="store_true",
                  help="if target directory already exists, append to it " + \
                      "instead of aborting.")

parser.add_option("--archivepath", dest="archivepath",
                  help="overwrite the default archive base directory which contains one " + \
                      "subdirectory per year. DEFAULT is currently \"" + DEFAULT_ARCHIVE_PATH + \
                      "\" (which can be modified in \"" + sys.argv[0] + "\")", metavar="DIR")

## parser.add_option("-b", "--batch", dest="batchmode", action="store_true",
##                   help="Do not ask for user interaction (at the end of the process)")

parser.add_option("--dryrun", dest="dryrun", action="store_true",
                  help="Does not make any changes to the file system. Useful for testing behavior.")

parser.add_option("--pauseonexit", dest="pauseonexit", action="store_true",
                  help="Asks for pressing the Enter key on any exit.")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                  help="enable verbose mode")

parser.add_option("--version", dest="version", action="store_true",
                  help="display version and exit")

(options, args) = parser.parse_args()


def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def error_exit(errorcode, text):
    """exits with return value of errorcode and prints to stderr"""

    sys.stdout.flush()
    logging.error(text)

    if options.dryrun or options.pauseonexit:
        raw_input(PAUSEONEXITTEXT)

    sys.exit(errorcode)


def extract_targetdirbasename_with_datestamp(targetdirbasename, args):
    """extracts the full targetdirname including ISO datestamp"""

    # targetdirbasename = os.path.basename(targetdir)
    # targetdirpath = os.path.dirname(targetdir)

    re_components = re.match(DATESTAMP_REGEX, targetdirbasename)

    first_datestamp = current_datestamp = None

    if re_components:
        logging.debug("targetdir \"%s\" contains datestamp. Extracting nothing." % targetdirbasename)
        return targetdirbasename
    else:
        logging.debug("targetdir \"" + targetdirbasename + "\" contains no datestamp. " +\
                          "Trying to extract one from the arguments ...")
        datestamp = None
        for item in args:
            itembasename = os.path.basename(item.strip())
            itemdirname = os.path.dirname(item.strip())
            re_components = re.match(DATESTAMP_REGEX, itembasename)
            if re_components:
                logging.debug("found datestamp \"%s\" in item \"%s\"" % ( re_components.group(0), item.strip() ))
                current_datestamp = re_components.group(0)
                if first_datestamp:
                    logging.debug("comparing current datestamp \"%s\" with first datestamp" % re_components.group(0) )
                    if current_datestamp != first_datestamp:
                        logging.warning("Datestamp of item \"" +\
                                            item.strip() + "\" differs from previously found datestamp \"" +\
                                            first_datestamp + "\". Taking previously found.")
                    else:
                        logging.debug("current datestamp is the same as the first one")
                else:
                    logging.debug("setting first datestamp to \"%s\"" % re_components.group(0) )
                    first_datestamp = current_datestamp
            else:
                logging.warning("item \"%s\" has got no datestamp!" % item.strip() )
                    
        if first_datestamp:
            final_targetdir = first_datestamp + " " + targetdirbasename
            logging.debug("proposed targetdir \"" + final_targetdir + "\"")
            return final_targetdir
        else:
            error_exit(2, "could not generate any targetdir containing datestamp. Exiting.")

    error_exit(9, "should not reach this line! internal error.")


def assert_each_item_has_datestamp(items):
    """make sure that each item has a datestamp"""

    logging.debug("checking each item for datestamp")
    for item in items:
        re_components = re.match(DATESTAMP_REGEX, os.path.basename(item.strip()))

        if not re_components:
            error_exit(3, "item \"%s\" has got no datestamp! Can not process this item." % item )


def make_sure_targetdir_exists(archivepath, targetdir):
    """create directory if necessary; abort if existing and no append options given"""

    logging.debug("make_sure_target_exists: archivepath [%s] targetdir [%s]" % ( archivepath, targetdir ) )
    year = get_year_from_itemname(targetdir)
    complete_target_path = os.path.join(archivepath, year, targetdir)

    if os.path.isdir(complete_target_path):
        if options.append:
            logging.debug("target directory already exists. Appending files...")
        else:
            error_exit(4, "target directory already exists. Aborting.")
    else:
        if not options.dryrun:
            logging.info("creating target directory: \"" + complete_target_path + "\"")
            os.mkdir(complete_target_path)
        else:
            logging.info("creating target directory: \"" + complete_target_path + "\"")

    return complete_target_path

            
def make_sure_subdir_exists(currentdir, subdir):
    """create directory if necessary; abort if existing and no append options given"""

    logging.debug("make_sure_subdir_exists: currentdir [%s] subdir [%s]" % ( currentdir, subdir ) )
    complete_target_path = os.path.join(currentdir, subdir)

    if os.path.isdir(complete_target_path):
        logging.debug("target directory already exists. Appending files...")
    else:
        if not options.dryrun:
            logging.info("creating directory: \"" + complete_target_path + "\"")
            os.mkdir(complete_target_path)
        else:
            logging.info("creating directory: \"" + complete_target_path + "\"")

    return complete_target_path

            
def get_year_from_itemname(itemname):
    """extract year from item string"""

    ## assert: main() makes sure that each item has datestamp!
    components = re.match(DATESTAMP_REGEX, os.path.basename(itemname))

    if not components:
        error_exit(7, "item \"%s\" should have a datestamp in it. " + \
                          "Should have been checked before, internal error :-(" % str(itemname) )

    return components.group(DATESTAMP_REGEX_YEARINDEX)


def move_item(item, destination):
    """move an item to the destination directory"""

    if options.dryrun:
        print "moving: \"%s\"  -->   \"%s\"" % ( item, destination )
    elif os.path.isdir(destination):
        try:
            print "moving: \"%s\"  -->   \"%s\"" % ( item, destination )
            shutil.move(item, destination) 
        except IOError, detail:
            error_exit(5, "Cannot move \"%s\" to \"%s\". Aborting.\n%s" % ( item, destination, detail ) )
    else:
        error_exit(6, "Destination directory \"%s\" does not exist! Aborting." % destination )


def handle_item(itemname, archivepath, targetdir):
    """handles one item and moves it to targetdir"""

    logging.debug( "--------------------------------------------")
    logging.debug("processing item \""+ itemname + "\"")
    logging.debug("with archivepath[%s]  and  targetdir[%s]" % (archivepath, targetdir))

    if not os.path.exists(itemname):
        logging.error("item \"" + itemname + "\" does not exist! Ignoring.")
    elif targetdir and (options.targetdir or options.askfordir):
        ## targetdir option is given and this directory is created before
        ## so just move items here:
        move_item(itemname, targetdir)
    else:
        ## find the correct <YYYY> subdirectory for each item:
        year = get_year_from_itemname(itemname)
        logging.debug("extracted year \"%s\" from item \"%s\"" % ( year, itemname ) )
        destination = os.path.join(archivepath, year)
        move_item(itemname, destination) 


def generate_absolute_target_dir(targetdir, args, archivepath):
    """returns existing target directory containing a datestamp"""

    logging.debug("trying to find a target dir with datestamp")
    targetdirname = extract_targetdirbasename_with_datestamp(targetdir, args)
    logging.debug("extract_targetdirbasename... returned \"%s\"" % targetdirname)
    return make_sure_targetdir_exists(archivepath, targetdirname)

            

def main():
    """Main function"""

    if options.version:
        print os.path.basename(sys.argv[0]) + " version "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE
        sys.exit(0)

    handle_logging()
    logging.debug("options: " + str(options))
    logging.debug("args: " + str(args))

    if options.dryrun:
        logging.info("Option \"--dryrun\" found, running a simulation, not modifying anything on file system:")

    if options.append and not options.targetdir:
        logging.warning("The \"--append\" options is only necessary in combination " + \
                            "with the \"--directory\" option. Ignoring this time.")

    if options.targetdir and options.askfordir:
        error_exit(8, "Options \"--directory\" and \"--askfordirectory\" are mutual exclusive: " +\
                       "use one at maximum.")

    archivepath = None
    if options.archivepath:
        logging.debug("overwriting default archive dir with: \"" + options.archivepath + "\"")
        archivepath = options.archivepath
    else:
        archivepath = DEFAULT_ARCHIVE_PATH

    if not os.path.isdir(archivepath):
    	error_exit(1, "\n\nThe archive directory \"" + archivepath + \
                          "\" is not a directory!\n" + \
                       "modify default setting in " + sys.argv[0] + " or provide a valid " + \
                          "directory with command line option \"--archivepath\".\n")
        
    if len(args)<1:
        parser.error("Please add at least one file name as argument")

    targetdirname = None
    if options.targetdir:
        targetdirname = generate_absolute_target_dir(options.targetdir, args, archivepath)
    elif options.askfordir:
        print "Please enter directory basename: "
        targetdirname = sys.stdin.readline().strip()
        if (not targetdirname):
            ## if no folder is given by the user, act like askfordir is not the case:
            logging.debug("targetdirname was empty: acting, like --askfordir is not given")
            assert_each_item_has_datestamp(args)
        else:
            if targetdirname == 'lp':
                ## overriding targetdir with lp-shortcut:
                logging.debug("targetdir-shortcut 'lp' (low prio) found")
                targetdirname = make_sure_subdir_exists( os.getcwd(), 'lp' )
            elif targetdirname == 'rp':
                ## overriding targetdir with rp-shortcut:
                logging.debug("targetdir-shortcut 'rp' (Rohpanorama) found")
                targetdirname = make_sure_subdir_exists( os.getcwd(), 'Rohpanoramas' )
            else:
                targetdirname = generate_absolute_target_dir(targetdirname, args, archivepath)
    else:
        assert_each_item_has_datestamp(args)

    if targetdirname:
        logging.debug("using targetdirname \"%s\"" % targetdirname)
    else:
        logging.debug("using no targetdir, sorting each item into %s/<YYYY>" % archivepath)

    for itemname in args:
        handle_item(itemname.strip(), archivepath, targetdirname)

    logging.debug("successfully processed all items.")

    if options.dryrun or options.pauseonexit:
        raw_input(PAUSEONEXITTEXT)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################
          
#end
