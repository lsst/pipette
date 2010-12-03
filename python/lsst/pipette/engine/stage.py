#!/usr/bin/env python

import lsst.pex.logging as pexLog

"""This module defines various types of stages that can be executed."""

class BaseStage(object):
    """BaseStage is the base class for stages.
    Users should subclass BaseStage and override the __init__ and run methods.

    Data flows through stages in the form of a 'clipboard' (a regular Python dict).
    We find it convenient to pass this as **clipboard, so that methods can pick
    out components they're interested in using the function definition, e.g.,
    def run(exposure=None, **clipboard) will pick the exposure out of the clipboard.
    The checkRequire() method can be used to ensure that these will exist, but the
    user is encouraged to assert on them as well.
    """
    
    def __init__(self, name, config=None, log=None, requires=None, provides=None):
        """Constructor

        @param name Name of the stage; used for logging
        @param config Configuration
        @param log Logger
        @param requires Set of required data on clipboard
        @param provides Set of provided data on clipboard
        """
        self.name = name
        self.config = config
        if log is None: log = pexLog.getDefaultLog()
        self.log = pexLog.Log(log, name)
        if requires is not None and isinstance(requires, basestring): requires = [requires,]
        if provides is not None and isinstance(provides, basestring): provides = [provides,]
        self.requires = set(requires) if requires is not None else set()
        self.provides = set(provides) if provides is not None else set()
        return

    def __str__(self):
        return "%s: (%s) --> (%s)" % (self.name, ','.join(self.requires), ','.join(self.provides))

    def _check(self, check, which, clipboard):
        """Check that stage dependencies or provisions are met by the clipboard

        @param check Set to check
        @param which Which set is being checked (for log messages)
        @param clipboard Clipboard dict
        """
        if check is None:
            self.log.log(self.log.DEBUG, "Stage %s has no %s" % (self.name, which))
            return True
        for key in check:
            if clipboard is None or not clipboard.has_key(key):
                self.log.log(self.log.WARN, "Stage %s %s not satisfied: %s" %
                             (self.name, which, key))
                return False
        self.log.log(self.log.DEBUG, "Stage %s satisfies %s" % (self.name, which))
        return True


    def checkRequire(self, **clipboard):
        """Check that stage dependencies are met by the clipboard

        @param **clipboard Clipboard dict
        """
        return self._check(self.requires, "requirements", clipboard)

    def checkProvide(self, **clipboard):
        """Check that stage provisions are met by the clipboard

        @param **clipboard Clipboard dict
        """
        return self._check(self.provides, "provisions", clipboard)

    def run(self, **clipboard):
        """Run the stage.  This method needs to be overridden by inheriting classes.

        @param **clipboard Clipboard dict
        """
        raise NotImplementedError("This method needs to be overridden by inheriting classes")


class IgnoredStage(BaseStage):
    """A stage that has been ignored for processing.  It does nothing except exist."""
    def __init__(self, *args, **kwargs):
        super(IgnoredStage, self).__init__(*args, **kwargs)
        self.requires = set()
        self.provides = set()
        return

    def run(self, **clipboard):
        self.log.log(self.log.DEBUG, "Stage %s has been ignored." % self.name)
        return

    def __str__(self):
        return "%s: IGNORED" % (self.name)

class MultiStage(BaseStage):
    """A stage consisting of multiple stages.  The stages are executed in turn."""    
    def __init__(self, name, stages, factory=None, *args, **kwargs):
        """Constructor.

        Note that we can work out the requirements and provisions using the
        components, so there's no need to provide those.
        If a factory is provided, it is used to create each of the stages.

        @param name Name of the stage; used for logging
        @param stages Stages to run
        @param factory Factory to create stages, or None
        """               
        super(MultiStage, self).__init__(name, *args, **kwargs)
        if factory is None:
            self._stages = stages
        else:
            self._stages = factory.create(stages, *args, **kwargs)
        requires = set()                # Requirement list for set
        provides = set()                # Provision list for set
        for stage in self._stages:
            assert isinstance(stage, BaseStage), \
                   "Stage %s is not of type BaseStage (%s)" % (stage, type(stage))
            stage.log = pexLog.Log(self.log, stage.name) # Make stage log subordinate
            for req in stage.requires:
                if not (req in requires or req in provides):
                    requires.add(req)
            for prov in stage.provides:
                if not prov in provides:
                    provides.add(prov)
        requires.update(self.requires)
        provides.update(self.provides)
        self.requires = requires
        self.provides = provides
        return

    def __str__(self):
        stages = []
        for stage in self._stages:
            stages.append(stage.__str__())
        return "%s [%s]: (%s) --> (%s)" % (self.name, ', '.join(stages),
                                           ','.join(self.requires), ','.join(self.provides))

    def run(self, **clipboard):
        """Run the stage.  Each stage is executed in turn.

        @param **clipboard Clipboard dict
        """
        if not self.checkRequire(**clipboard):
            raise RuntimeError("Stage %s requirements not met" % self.name)
        for stage in self._stages:
            assert stage.checkRequire(**clipboard), \
                   "Stage %s requirements not met within %s" % (stage.name, self.name)
            ret = stage.run(**clipboard)
            if ret is not None:
                assert stage.checkProvide(**ret), \
                       "Stage %s provisions not met within %s" % (stage.name, self.name, )
                clipboard.update(ret)
        return clipboard


class IterateStage(BaseStage):
    """A stage that runs on a list of components."""
    def __init__(self, name, iterate, *args, **kwargs):
        """Constructor

        @param name Name of the stage; used for logging
        @param iterate Component or list of components to iterate over
        """
        super(IterateStage, self).__init__(name, *args, **kwargs)
        self.iterate = iterate
        return

    def run(self, **clipboard):
        """Run the stage.  The stage is executed for each of the components.

        The components nominated for iteration must be passed in as lists.

        @param **clipboard Clipboard dict
        """
        assert self.checkRequire(**clipboard), "Stage %s requirements not met" % self.name
        iterate = dict()                # List of lists to iterate over
        # Pull out things we're iterating over
        length = None                   # Length of iteration
        for name in self.iterate:
            array = clipboard[name]
            assert hasattr(array, "__iter__"), "Component %s is not iterable: %s" % (name, array)
            if length is None:
                length = len(array)
            elif len(array) != length:
                raise RuntimeError("Iteration sequences have different length: %s" % self.iterate)
            iterate[name] = array
        # Iterate over each element set
        for index in range(length):
            # Make new clipboard with elements of interest
            clip = clipboard.copy()
            for name in self.iterate:
                array = iterate[name]
                value = array[index]
                clip[name] = value                
            clip = super(IterateStage, self).run(**clip)
            # Put result back
            for name in self.iterate:
                array = iterate[name]
                array[index] = clip[name]
        assert self.checkProvide(**clipboard), "Stage %s provisions not met" % self.name
        return clipboard

class IterateMultiStage(IterateStage, MultiStage):
    """A stage that runs multiple stages on a list of components

    Note that, by virtue of the order of the multiple inheritance, the
    constructor is __init__(self, name, iterate, stages, config, ...)
    and the behaviour of run(self, **clipboard) should be like:
        for each iteration component set:
            for each stage:
                run stage with component set
    """
    # Multiple inheritance should automagically do everything we desire
    pass
