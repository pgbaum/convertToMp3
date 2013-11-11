#!/usr/bin/env python

import argparse
import sys, os
import shutil
import glib
import unicodedata
import hashlib
import string
import re

def getTags( fileName, verbose ):
   class GetTags:
      def __init__( self ):
         self.__player = gst.parse_launch(
               "filesrc name=src ! decodebin ! fakesink" )
         bus = self.__player.get_bus()
         bus.add_signal_watch()
         bus.connect( "message", self.__onMessage )

      def start( self, fileName, expectedTags, verbose ):
         if not os.path.exists( fileName ):
            raise Exception( "File does not exist: \"", fileName, "\"" )
         src = self.__player.get_by_name( "src" )
         src.set_property( "location", fileName )

         self.__verbose = verbose
         self.__expected = expectedTags
         self.tags = dict()
         self.__player.set_state( gst.STATE_PLAYING )
         self.__loop = glib.MainLoop()
         self.__loop.run()

      def __onMessage( self, bus, message ):
         t = message.type
         if t == gst.MESSAGE_TAG:
            taglist = message.parse_tag()
            for key in taglist.keys():
               if self.__verbose:
                  print key
               if key in self.__expected:
                  self.tags[key] = taglist[key]
               # got all required tags
               if ( not self.__verbose
                     and len( self.tags ) == len( self.__expected ) ):
                  self.__quit()
                  break
         elif t == gst.MESSAGE_EOS:
            loop.quit()
         elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            self.tags.clear()
            self.tags["Error"] = err
            self.__quit()

      def __quit( self ):
         self.__player.set_state( gst.STATE_NULL )
         self.__loop.quit()
         self.__loop = None

   if not hasattr( getTags, "_obj" ):
      getTags._obj = GetTags( )
   expectedTags = ["artist", "album", "title", "track-number", "audio-codec"]

   getTags._obj.start( fileName, expectedTags, verbose )

   if len( getTags._obj.tags ) != len( expectedTags ):
      raise Exception( "Could not find all tags" )

   return getTags._obj.tags

def convert( inFile, outFile, quality ):
   class Convert:
      def __init__( self ):
         self.__player = gst.parse_launch(
            "filesrc name=src ! flacdec ! audioconvert ! "
            "lamemp3enc name=enc ! id3v2mux "
            "! filesink name=sink" )
         bus = self.__player.get_bus()
         bus.add_signal_watch()
         bus.connect( "message", self.__onMessage )

      def start( self, inFile, outFile, quality ):
         if not os.path.exists( inFile ):
            raise Exception( "File does not exist: \"", fileName, "\"" )

         src = self.__player.get_by_name( "src" )
         src.set_property( "location", inFile )
         sink = self.__player.get_by_name( "sink" )
         sink.set_property( "location", outFile )
         enc = self.__player.get_by_name( "enc" )
         enc.set_property( "quality", quality )
         self.__player.set_state( gst.STATE_PLAYING )
         self.__loop = glib.MainLoop()
         self.__loop.run()

      def __onMessage( self, bus, message ):
         t = message.type
         if t == gst.MESSAGE_EOS:
            self.__quit()
         elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.__quit()

      def __quit( self ):
         self.__player.set_state( gst.STATE_NULL )
         self.__loop.quit()
         self.__loop = None

   if not hasattr( convert, "_obj" ):
      convert._obj = Convert( )
   convert._obj.start( inFile, outFile, quality )

def cleanName( name ):
   return unicodedata.normalize( 'NFKD', name ).encode( 'ascii', 'ignore' )

def cleanFileName( fileName ):
   fileName = cleanName( fileName ).replace( " ", "_" )
   valid = "-_." + string.ascii_letters + string.digits
   fileName = ''.join( [c for c in fileName if c in valid] )
   return re.sub( "__+", "_", fileName )

def getDest( tags ):
   hashTags = ["artist", "album", "title", "track-number"]
   full = " ".join( [unicode( tags[el] ) for el in hashTags] )
   hashVal = hashlib.md5( cleanName( full ) ).hexdigest( )[:3]
   dirName = cleanFileName( tags["artist"] )
   fileName = cleanFileName( "%s-%s.mp3" % (tags["title"], hashVal) )
   return (dirName, fileName)

def checkExistence( dirName, fileName, dryRun ):
   if not os.path.exists( dirName ):
      if not dryRun:
         os.makedirs( dirName )
      return False
   return os.path.exists( os.path.join( dirName, fileName ) )

def convertFile( inFile, dest, verbose, quality, dryRun ):
   try:
      tags = getTags( inFile, verbose )
   except Exception:
      print "Skipping (no tags):", inFile
      return

   sys.stdout.flush()
   (dirName, fileName) = getDest( tags )
   fullDir = os.path.join( dest, dirName )
   fullName = os.path.join( fullDir, fileName )
   if checkExistence( fullDir, fileName, dryRun ):
      print "Exists:", inFile, "->", fullName
   elif "MPEG" in tags["audio-codec"]:
      print "Copying:", inFile, "->", fullName,
      if not dryRun:
         shutil.copyfile( inFile, fullName )
      print "done"
   else:
      print "Creating:", inFile, "->", fullName,
      sys.stdout.flush()
      if not dryRun:
         convert( inFile, fullName, quality )
      print "done"

def convertDir( inDir, dest, verbose, quality, dryRun ):
   for dirPath, dirs, files in os.walk( inDir ):
      for inFile in files:
         convertFile( os.path.join( dirPath, inFile ), dest, verbose,
               quality, dryRun )

# this is necessary, if the output is a pipe, since sys.stdout.encoding
# is then None. But for filenames encode does not work, why?
def write( line ):
    print( line.encode('utf-8') )

def addFileToDict( inFile, verbose, fileInfos ):
   print "# Checking: %s" % (inFile),
   try:
      tags = getTags( inFile, verbose )
   except Exception:
      write( "Skipping (no tags)" )
      return

   write( tags["title"] )
   title = cleanName( tags["title"] ).lower()
   title = ''.join( [c for c in title if c in string.ascii_letters] )
   if title in fileInfos:
      fileInfos[title].append( inFile )
   else:
      fileInfos[title] = [inFile]

def checkForDupes( inDir, dest, dupesDir, verbose ):
   fileInfos = dict()
   for dirPath, dirs, files in os.walk( inDir ):
      for inFile in files:
         addFileToDict( os.path.join( dirPath, inFile ), verbose, fileInfos )

   for title in fileInfos.itervalues():
      if len( title ) > 1:
         print "# Possible dupes:"
         for el in title:
            tags = getTags( el, verbose )
            (dirName, fileName) = getDest( tags )
            fullName = os.path.join( dest, dirName, fileName )
            write( "   # %s: %s" % (tags["artist"], tags["title"] ) )
            print "   # mv \"%s\" %s; rm -f %s" % (el, dupesDir, fullName)

parser = argparse.ArgumentParser( description='Convert audio files to mp3' )
parser.add_argument( "--verbose", help="Print all tags", action = "store_true" )
parser.add_argument( "--dry-run", help="Don't write anything",
      action = "store_true" )
group = parser.add_mutually_exclusive_group( required = True )
group.add_argument( "--dir", help="Input directory" )
group.add_argument( "--file", help="Input file" )
parser.add_argument( "--dest", help="Destination filder", required = True )
parser.add_argument( "--quality", help="Quality of mp3", default = 3,
      type = int, required = False )
parser.add_argument( "--find-dupes",
      help="Check for dupes instead of converting", action = "store_true" )
parser.add_argument( "--dupes-dir", help="Directory for dupes" )

args = parser.parse_args()
# if this is before parse_args, --help prints only gstreamer help
import pygst
pygst.require( "0.10" )
import gst

if args.find_dupes:
   if args.dir == None:
      print "%s: Error: argument --dir is required" % sys.argv[0]
      sys.exit( 1 )
   if args.dupes_dir == None:
      print "%s: Error: argument --dir is required" % sys.argv[0]
   checkForDupes( args.dir, args.dest, args.dupes_dir, args.verbose )
elif args.file:
   convertFile( args.file, args.dest, args.verbose, args.quality, args.dry_run )
else:
   convertDir( args.dir, args.dest, args.verbose, args.quality, args.dry_run )

