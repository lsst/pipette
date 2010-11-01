#/usr/bin/env python

import os
import sys
import lsst.obs.suprime as suprime
import lsst.gb3.config as gb3Config
import lsst.gb3.crank as gb3Crank


def run(rerun,                          # Rerun name
        frame,                          # Frame number
        ccd,                            # CCD number
        config,                         # Configuration
        ):
    roots = config['roots']
    basename = os.path.join(roots['output'], '%s-%d%d' % (rerun, frame, ccd))
    crank = gb3Crank.Crank(basename, suprime.SuprimeMapper, config=config)
    dataId = { 'visit': frame, 'ccd': ccd }
    crank.turn(dataId)
    return


if __name__ == "__main__":
    parser = gb3Config.OptionParser(usage=__doc__)
    parser.add_option("-r", "--rerun", default=os.getenv("USER", default="rerun"), dest="rerun",
                      help="rerun name (default=%default)")
    parser.add_option("-f", "--frame", dest="frame",
                      help="visit to run (default=%default)")
    parser.add_option("-c", "--ccd", default="0:1:2:3:4:5:6:7:8:9", dest="ccd",
                      help="CCD to run (default=%default)")
    parser.add_option("--debug", dest="debug", action="store_true", default=False,
                      help="Debugging output?")
    opts, args = parser.parse_args()

    if opts.debug:
        try: import debug
        except ImportError: print "No 'debug' module found"

    config = gb3Config.configuration("policy/suprimecam.paf", opts.config)
    if len(args) > 0 or len(sys.argv) == 1 or opts.rerun is None or opts.frame is None or opts.ccd is None:
        parser.print_help()
        sys.exit(1)

    run(opts.rerun, int(opts.frame), int(opts.ccd), config)
