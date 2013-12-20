#!/usr/bin/env python

import sys
import os
import subprocess


def convert( src ):
   root, ext = os.path.splitext( src )
   dest = root + ".mp3"
   print "%s -> %s " %  (src, dest),
   sys.stdout.flush()
   if os.path.exists( dest ):
     print "file exists"
     return
   cmd = 'gst-launch filesrc location="%s" ! decodebin ! audioconvert ! ' \
         'lamemp3enc name=enc quality=3 ! id3v2mux ' \
         '! filesink location="%s"' % (src, dest )
   subprocess.check_output( cmd, shell = True )
   print "done"


if len( sys.argv ) == 1:
   print "Usage: %s file [file...]" % sys.argv[0]
   sys.exit( 0 )

for el in sys.argv[1:]:
   convert( el )


