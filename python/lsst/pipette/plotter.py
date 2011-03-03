#!/usr/bin/env python

import math
import matplotlib
matplotlib.use('pdf')
import matplotlib.pyplot as plot
import numpy
import numpy.ma as ma

import lsst.afw.math as afwMath

def gaussian(param, x):
    norm = param[0]
    offset = param[1]
    width = param[2]
    return norm * numpy.exp(-0.5*((x - offset)/width)**2)    

class FakePdf(object):
    def close(self): pass
    def savefig(self):
        plot.draw()
        plot.show()

class Plotter(object):
    def __init__(self, name):
        self.name = name
        if not self.name.endswith(".pdf"):
            self.name += ".pdf"
        self.pdf = matplotlib.backends.backend_pdf.PdfPages(self.name)
#        self.pdf = FakePdf()

    def close(self):
        self.pdf.close()

    def xy(self, x, y, axis=None, title=None):
        plot.figure()
        if axis is not None:
            plot.axis(axis)
        if title is not None:
            plot.title(title)
        print x
        print y
        plot.plot(x, y, ',')
        self.pdf.savefig()
        plot.close()

    def histogram(self, data, bounds, bins=51, gaussFit=True, iterations=3, clip=3.0, title=None):
        plot.figure()
        n, bins, patches = plot.hist(data, bins=bins, range=bounds, normed=False,
                                     histtype='bar', align='mid')

        if gaussFit:
            calc = afwMath.vectorF()
            for value in data:
                if value > bounds[0] and value < bounds[1]:
                    calc.push_back(value)
            stats = afwMath.makeStatistics(calc, afwMath.MEANCLIP | afwMath.STDEVCLIP)
            mean = stats.getValue(afwMath.MEANCLIP)
            stdev = stats.getValue(afwMath.STDEVCLIP)
            num = len(calc)

            print "Histogram statistics:", num, mean, stdev
            norm = num * (bins[1:] - bins[:-1]).mean() / math.sqrt(2.0 * math.pi) / stdev
            middle = (bins[:-1] + bins[1:]) / 2.0
            gauss = gaussian([norm, mean, stdev], middle)
            plot.plot(middle, gauss, 'r-', label='%d*N(%.3f, %.3f^2)' % (num, mean, stdev))
            leg = plot.legend(loc='upper right')
            for t in leg.get_texts():
                t.set_fontsize('small')

        if title is not None:
            plot.title(title)
        self.pdf.savefig()
        plot.close()

    def xy2(self, x1, y1, x2, y2, axis1=None, axis2=None, title1=None, title2=None):
        plot.figure()
        plot.subplot(2, 1, 1)
        if axis1 is not None:
            plot.axis(axis1)
        plot.scatter(x1, x2, marker='+')
        if title1 is not None:
            plot.title(title1)

        plot.subplot(2, 1, 2)
        if axis2 is not None:
            plot.axis(axis2)
        plot.scatter(x2, y2, marker='+')
        if title2 is not None:
            plot.title(title2)

        self.pdf.savefig()
        plot.close()

    def quivers(self, x, y, dx, dy, title=None, scale=None):
        plot.figure()
        plot.quiver(x, y, dx, dy, scale=scale, headwidth=2, headlength=3)
        if title is not None:
            plot.title(title)
        self.pdf.savefig()
        plot.close()
