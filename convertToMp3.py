#!/usr/bin/env python

import argparse
import sys, os
import shutil
import unicodedata
import hashlib
import string
import re
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

def getTags( fileName, verbose ):
   expectedTags = ["artist", "album", "title", "track-number", "audio-codec"]

   if not os.path.exists( fileName ):
      raise Exception( "File does not exist: \"", fileName, "\"" )

   player = Gst.parse_launch(
         "filesrc name=src ! decodebin ! fakesink" )
   bus = player.get_bus()

   src = player.get_by_name( "src" )
   src.set_property( "location", fileName )

   tags = dict()
   player.set_state( Gst.State.PLAYING )

   while True:
      message = bus.pop()
      if not message:
         continue
      t = message.type
      if t == Gst.MessageType.TAG:
         taglist = message.parse_tag()
         for key in expectedTags:
            typeName = Gst.tag_get_type( key ).name
            if typeName == "gchararray":
               isValid, value = taglist.get_string( key )
            elif typeName == "guint":
                isValid, value = taglist.get_uint( key )
            if verbose:
               print( key, value )
            if isValid:
               tags[key] = str( value )
            # got all required tags
            if ( not verbose
                  and len( tags ) == len( expectedTags ) ):
               break;
      elif t == Gst.MessageType.EOS:
         break;
      elif t == Gst.MessageType.ERROR:
         err, debug = message.parse_error()
         tags.clear()
         tags["Error"] = err
         print( f"in MessageType Error: {err}" )
         break

   player.set_state( Gst.State.NULL )

   if len( tags ) != len( expectedTags ):
      raise Exception( "Could not find all tags" )

   return tags

def convert( inFile, outFile, quality ):

   if not os.path.exists( inFile ):
      raise Exception( "File does not exist: \"", fileName, "\"" )

   player = Gst.parse_launch(
      "filesrc name=src ! flacparse ! flacdec ! audioconvert ! "
      "lamemp3enc name=enc ! id3v2mux "
      "! filesink name=sink" )
   bus = player.get_bus()

   src = player.get_by_name( "src" )
   src.set_property( "location", inFile )
   sink = player.get_by_name( "sink" )
   sink.set_property( "location", outFile )
   enc = player.get_by_name( "enc" )
   enc.set_property( "quality", quality )
   player.set_state( Gst.State.PLAYING )

   while True:
      message = bus.pop()
      if not message:
         continue
      t = message.type
      if t == Gst.MessageType.EOS:
         break
      elif t == Gst.MessageType.ERROR:
         err, debug = message.parse_error()
         print( f"Error: {err}, {debug}" )
         break

   player.set_state( Gst.State.NULL )

def cleanName( name ):
   return unicodedata.normalize( 'NFKD', name ).encode( 'ascii', 'ignore' ).decode( "utf-8" )

def cleanFileName( fileName ):
   fileName = cleanName( fileName ).replace( " ", "_" ).replace( ".", "_" )
   valid = "-_." + string.ascii_letters + string.digits
   fileName = ''.join( [c for c in fileName if c in valid] )
   return re.sub( "__+", "_", fileName )

def getDest( tags ):
   hashTags = ["artist", "album", "title", "track-number"]
   full = " ".join( [ tags[el] for el in hashTags] )
   hashVal = hashlib.md5( cleanName( full ).encode() ).hexdigest( )[:3]
   dirName = cleanFileName( tags["artist"] )
   fileName = cleanFileName( "%s-%s" % (tags["title"], hashVal) ) + ".mp3"
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
      print( f"Skipping (no tags): {inFile}" )
      return

   sys.stdout.flush()
   (dirName, fileName) = getDest( tags )
   fullDir = os.path.join( dest, dirName )
   fullName = os.path.join( fullDir, fileName )
   if checkExistence( fullDir, fileName, dryRun ):
      print( f"Exists: {inFile} -> {fullName}" )
   elif "MPEG" in tags["audio-codec"]:
      print( f"Copying: {inFile} -> {fullName}", end = "" )
      if not dryRun:
         shutil.copyfile( inFile, fullName )
      print( "done" )
   else:
      print( f"Creating: {inFile} -> {fullName}", end = "" )
      sys.stdout.flush()
      if not dryRun:
         convert( inFile, fullName, quality )
      print( "done" )

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
   print( f"# Checking: {inFile}", end = "" )
   try:
      tags = getTags( inFile, verbose )
   except Exception:
      write( "Skipping (no tags)" )
      return

   write( tags["title"] )
   title = cleanName( tags["title"] ).lower()
   title += cleanName( tags["artist"] ).lower()
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
         print( "# Possible dupes:" )
         for el in title:
            tags = getTags( el, verbose )
            (dirName, fileName) = getDest( tags )
            fullName = os.path.join( dest, dirName, fileName )
            write( "   # %s: %s" % (tags["artist"], tags["title"] ) )
            if dupesDir == None:
               print( "   # rm -f \"%s\" %s" % (el, fullName) )
            else:
               print( "   # mv \"%s\" %s; rm -f %s" % (el, dupesDir, fullName) )

parser = argparse.ArgumentParser( description='Convert audio files to mp3' )
parser.add_argument( "--verbose", help="Print all tags", action = "store_true" )
parser.add_argument( "--dry-run", help="Don't write anything",
      action = "store_true" )
group = parser.add_mutually_exclusive_group( required = True )
group.add_argument( "--dir", help="Input directory" )
group.add_argument( "--file", help="Input file" )
parser.add_argument( "--dest", help="Destination folder", required = True )
parser.add_argument( "--quality", help="Quality of mp3", default = 3,
      type = int, required = False )
parser.add_argument( "--find-dupes",
      help="Check for dupes instead of converting", action = "store_true" )
parser.add_argument( "--dupes-dir", help="Directory for dupes" )

args = parser.parse_args()

Gst.init( None )

if args.find_dupes:
   if args.dir == None:
      print( "%s: Error: argument --dir is required" % sys.argv[0] )
      sys.exit( 1 )
   checkForDupes( args.dir, args.dest, args.dupes_dir, args.verbose )
elif args.file:
   convertFile( args.file, args.dest, args.verbose, args.quality, args.dry_run )
else:
   convertDir( args.dir, args.dest, args.verbose, args.quality, args.dry_run )

