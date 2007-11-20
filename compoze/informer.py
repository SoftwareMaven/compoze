""" compoze -- build a new Python package index from source distributions

"""
import getopt
import optparse
import os
import pkg_resources
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
import StringIO

from setuptools.package_index import PackageIndex

class Informer:

    def __init__(self, global_options, *argv):
    
        argv = list(argv)
        parser = optparse.OptionParser(
            usage="%prog [OPTIONS] app_egg_name [other_egg_name]*")

        parser.add_option(
            '-p', '--path',
            action='store',
            dest='path',
            default='.',
            help="Specify the path in which to build the index")

        parser.add_option(
            '-u', '--index-url',
            action='append',
            dest='index_urls',
            default=[],
            help="Add a candidate index used to find distributions")

        parser.add_option(
            '-f', '--fetch-site-packages',
            action='store_true',
            dest='fetch_site_packages',
            default=False,
            help="Fetch requirements used in site-packages")

        parser.add_option(
            '-b', '--include-binary-eggs',
            action='store_false',
            dest='source_only',
            default=True,
            help="Include binary distributions")

        parser.add_option(
            '-d', '--include-develop-eggs',
            action='store_true',
            dest='develop_ok',
            default=False,
            help="Include development distributions")

        parser.add_option(
            '-q', '--quiet',
            action='store_false',
            dest='verbose',
            help="Run quietly")

        parser.add_option(
            '-v', '--verbose',
            action='store_true',
            dest='verbose',
            default=global_options.verbose,
            help="Show progress")

        options, args = parser.parse_args(argv)

        if (not options.fetch_site_packages and
            len(args) == 0):
            msg = StringIO.StringIO()
            msg.write('show: Either specify requirements, or else'
                                    '--fetch-site-packages .\n\n')
            msg.write(parser.format_help())
            raise ValueError(msg.getvalue())

        if len(options.index_urls) == 0:
            options.index_urls = ['http://pypi.python.org/simple']

        self.options = options
        self._expandRequirements(args)

        path = os.path.abspath(os.path.expanduser(options.path))

        if not os.path.exists(path):
            os.makedirs(path)

        if not os.path.isdir(path):
            msg = StringIO.StringIO()
            msg.write('Not a directory: %s\n\n' % path)
            msg.write(parser.format_help())
            raise ValueError(msg.getvalue())

        self.path = path

    def __call__(self):

        self.show_distributions()

    def show_distributions(self):

        # First, collect best sdist candidate for the requirment from each 
        # index into a self.tmpdir
        # XXX ignore same-name problem for now

        for index_url in self.options.index_urls:
            self._blather('=' * 50)
            self._blather('Package index: %s' % index_url)
            self._blather('=' * 50)
            index = PackageIndex(index_url=index_url)
            index.prescan()

            for rqmt in self.requirements:
                index.find_packages(rqmt)
                self._blather('Candidates: %s' % rqmt)
                for dist in self._findAll(index, rqmt):
                    self._blather('%s: %s' % (dist, dist.location))

        self._blather('=' * 50)

    def _blather(self, text):
        if self.options.verbose:
            print text

    def _expandRequirements(self, args):
        args = list(args)
        if self.options.fetch_site_packages:
            for dist in pkg_resources.working_set:
                args.append('%s == %s' % (dist.key, dist.version))

        self.requirements = list(pkg_resources.parse_requirements(args))

    def _findAll(self, index, rqmt):
        skipped = {}
        for dist in index[rqmt.key]:

            if (dist.precedence==pkg_resources.DEVELOP_DIST
                    and not self.options.develop_ok):
                if dist not in skipped:
                    self._blather("Skipping development or system egg: %s"
                                   % dist)
                    skipped[dist] = 1
                continue

            if dist in rqmt and (dist.precedence <= pkg_resources.SOURCE_DIST
                                  or not self.options.source_only):
                yield dist


def main():
    try:
        informer = Informer(sys.argv[1:])
    except ValueError, e:
        print str(e)
        sys.exit(1)
    informer()

if __name__ == '__main__':
    main()
