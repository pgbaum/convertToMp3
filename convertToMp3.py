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
      def __init__( self, fileName, verbose = False ):
         if not os.path.exists( fileName ):
            raise Exception( "File does not exist: \"", fileName, "\"" )

         self.player = gst.parse_launch(
               "filesrc name=src ! decodebin ! fakesink" )
         self.__verbose = verbose
         bus = self.player.get_bus()
         bus.add_signal_watch()
         bus.connect( "message", self.__onMessage )
         src = self.player.get_by_name( "src" )
         src.set_property( "location", fileName )
         self.player.set_state( gst.STATE_PLAYING )
         self.tags = dict()
         self.allTags =["artist", "album", "title", "track-number",
               "audio-codec"]

      def __onMessage( self, bus, message):
         t = message.type
         if t == gst.MESSAGE_TAG:
            taglist = message.parse_tag()
            for key in taglist.keys():
               if self.__verbose:
                  print key
               if key in self.allTags:
                  self.tags[key] = taglist[key]
               # got all required tags
               if ( not self.__verbose
                     and len( self.tags ) == len( self.allTags ) ):
                  self.__quit()
                  break
         elif t == gst.MESSAGE_EOS:
            loop.quit()
         elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.__quit()

      def __quit( self ):
         self.player.set_state( gst.STATE_NULL )
         loop.quit()

   getTag = GetTags( fileName, verbose )
   loop = glib.MainLoop()
   loop.run()

   if len( getTag.tags ) != len( getTag.allTags ):
      raise Exception( "Could not find all tags" )

   return getTag.tags

def convert( inFile, outFile, quality ):
   class Convert:
      def __init__( self, inFile, outFile, quality ):
         if not os.path.exists( inFile ):
            raise Exception( "File does not exist: \"", fileName, "\"" )

         self.player = gst.parse_launch(
            "filesrc name=src ! flacdec ! audioconvert ! "
            "lamemp3enc target=quality quality=%d ! id3v2mux "
            "! filesink name=sink" % quality )
         bus = self.player.get_bus()
         bus.add_signal_watch()
         bus.connect( "message", self.__onMessage )
         src = self.player.get_by_name( "src" )
         src.set_property( "location", inFile )
         sink = self.player.get_by_name( "sink" )
         sink.set_property( "location", outFile )
         self.player.set_state( gst.STATE_PLAYING )

      def __onMessage( self, bus, message ):
         t = message.type
         if t == gst.MESSAGE_EOS:
            loop.quit()
         elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.__quit()

      def __quit( self ):
         self.player.set_state( gst.STATE_NULL )
         loop.quit()

   conv = Convert( inFile, outFile, quality )
   loop = glib.MainLoop()
   loop.run()

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
   tags = getTags( inFile, verbose )
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

parser = argparse.ArgumentParser( description='Convert audio files to mp3' )
parser.add_argument( "--verbose", help="Print all tags", action = "store_true" )
parser.add_argument( "--dry-run", help="Don't write anything",
      action = "store_true" )
group = parser.add_mutually_exclusive_group( required = True )
group.add_argument( "--dir", help="Input directory" )
group.add_argument( "--file", help="Input file" )
parser.add_argument( "--dest", help="Destination filder", required = True )
parser.add_argument( "--quality", help="Quality of mp3", default = 2,
      type = int, required = True )
args = parser.parse_args()
# if this is before parse_args, --help prints only gstreamer help
import pygst
pygst.require( "0.10" )
import gst

if args.file:
   convertFile( args.file, args.dest, args.verbose, args.quality, args.dry_run )
else:
   convertDir( args.dir, args.dest, args.verbose, args.quality, args.dry_run )

