#!/usr/bin/env python

import sys
import glib
import pygst
pygst.require("0.10")
import gst

def getTags( fileName, verbose ):
   class GetTags:
      def __init__( self, fileName, verbose = False ):
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
               if len( self.tags ) == 4:
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

   return getTag.tags

tags = getTags( sys.argv[1], False )
for el in "artist", "album", "trackNumber", "title":
   print el, ":", tags[el]

