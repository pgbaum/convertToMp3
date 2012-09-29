#!/usr/bin/env python

import argparse
import sys, os
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
         bus.connect( "message", self.onMessage )
         src = self.player.get_by_name( "src" )
         src.set_property( "location", fileName )
         self.player.set_state( gst.STATE_PLAYING )
         self.tags = dict()
         self.numTags = 4

      def onMessage(self, bus, message):
         t = message.type
         if t == gst.MESSAGE_TAG:
            taglist = message.parse_tag()
            for key in taglist.keys():
               if self.__verbose:
                  print key
               if key == "artist":
                  self.tags["artist"] = taglist[key]
               elif key == "album":
                  self.tags["album"] = taglist[key]
               elif key == "title":
                  self.tags["title"] = taglist[key]
               elif key == "track-number":
                  self.tags["trackNumber"] = taglist[key]
               # got all required tags
               if not self.__verbose and len( self.tags ) == self.numTags:
                  self.__quit()
                  break
         elif t == gst.MESSAGE_EOS:
            loop.quit()
         elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.__quit()

      def __quit( self ):
         self.player.set_state(gst.STATE_NULL)
         loop.quit()

   getTag = GetTags( fileName, verbose )
   loop = glib.MainLoop()
   loop.run()

   if len( getTag.tags ) != getTag.numTags:
      raise Exception( "Could not find all tags" )

   return getTag.tags

def convert( inFile, outFile ):
   class Convert:
      def __init__( self, inFile, outFile ):
         if not os.path.exists( inFile ):
            raise Exception( "File does not exist: \"", fileName, "\"" )

         self.player = gst.parse_launch(
            "filesrc name=src ! flacdec ! audioconvert ! "
            "lamemp3enc target=quality quality=2 ! id3v2mux "
            "! filesink name=sink" )
         bus = self.player.get_bus()
         bus.add_signal_watch()
         bus.connect( "message", self.onMessage )
         src = self.player.get_by_name( "src" )
         src.set_property( "location", inFile )
         sink = self.player.get_by_name( "sink" )
         sink.set_property( "location", outFile )
         self.player.set_state( gst.STATE_PLAYING )

      def onMessage(self, bus, message):
         t = message.type
         if t == gst.MESSAGE_EOS:
            loop.quit()
         elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.__quit()

      def __quit( self ):
         self.player.set_state(gst.STATE_NULL)
         loop.quit()

   convert = Convert( inFile, outFile )
   loop = glib.MainLoop()
   loop.run()

def cleanName( name ):
   return unicodedata.normalize( 'NFKD', name ).encode('ascii', 'ignore')

def cleanFileName( fileName ):
   fileName = cleanName( fileName ).replace( " ", "_" )
   valid = "-_." + string.ascii_letters + string.digits
   fileName = ''.join( [c for c in fileName if c in valid] )
   return re.sub( "__+", "_", fileName )

def getDest( tags ):
   full = " ".join( [unicode( el ) for el in tags.itervalues() ] )
   hashVal = hashlib.md5( cleanName( full ) ).hexdigest( )[:3]
   dirName = cleanFileName( tags["artist"] )
   fileName = cleanFileName( "%s-%s.mp3" % (tags["title"], hashVal ) )
   return (dirName, fileName)

def checkExistence( dirName, fileName ):
   if not os.path.exists( dirName ):
      os.makedirs( dirName )
      return False
   return os.path.exists( dirName + "/" + fileName )

def convertFile( inFile, dest, verbose ):
   tags = getTags( inFile, verbose )
   (dirName, fileName) = getDest( tags )
   fullDir = "%s/%s" % (dest, dirName)
   fullName = "%s/%s" % (fullDir, fileName)
   if checkExistence( fullDir, fileName ):
      print "Exists:", fullName
   else:
      print "Creating:", fullName,
      sys.stdout.flush()
      convert( inFile, fullName )
      print "done"

def convertDir( inDir, dest, verbose ):
   for root, dirs, files in os.walk( inDir ):
      for inFile in files:
         convertFile( root + "/" + inFile, dest, verbose )
      for dd in dirs:
         convertDir( root + "/" + dd, dest, verbose )

parser = argparse.ArgumentParser( description='Convert audio files to mp3' )
parser.add_argument( "--verbose", help="Print all tags", action = "store_true" )
group = parser.add_mutually_exclusive_group( required = True )
group.add_argument( "--dir", help="Input directory" )
group.add_argument( "--file", help="Input file" )
parser.add_argument( "--dest", help="Destination filder", required = True )
args = parser.parse_args()
# if this is before parse_args, --help prints only gstreamer help
import pygst
pygst.require("0.10")
import gst

if args.file:
   convertFile( args.file, args.dest, args.verbose )
else:
   convertDir( args.dir, args.dest, args.verbose )

