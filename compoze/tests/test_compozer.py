import unittest
import os
import tempfile

here = os.path.abspath(os.path.dirname(__file__))

class ArchiveTests:
    fixturedir = os.path.join(here, 'fixtures', 'archive')
    fixturefiles = [ {'name':'archive/1.txt',
                      'path':os.path.join(fixturedir, '1.txt')},
                     {'name':'archive/folder/2.txt',
                      'path':os.path.join(fixturedir, 'folder', '2.txt')} ]

    def tearDown(self):
        import shutil
        shutil.rmtree(self.archive_tmpdir, ignore_errors=True)

    def _makeOne(self):
        return self._getTargetClass()(self.archive_file)

    def test_names(self):
        archive = self._makeOne()
        names = archive.names()
        expected = [ x['name'] for x in self.fixturefiles ]
        self.assertEqual(names, expected)

    def test_lines(self):
        archive = self._makeOne()
        name = self.fixturefiles[0]['name']
        lines = archive.lines(name)
        self.assertEqual(lines[:2], ['This is the first line of text file 1.',
                                     'This is the second line of text file 1.'])
        
    def test_extract(self):
        archive = self._makeOne()
        name = self.fixturefiles[1]['name']
        lines = archive.extract(name, self.archive_tmpdir)
        path = os.path.join(self.archive_tmpdir, name)
        expected = ('This is the first line of text file 2.\n'
                    'This is the second line of text file 2.\n')
        self.assertEqual(open(path).read(), expected)
        
    def test_close(self):
        archive = self._makeOne()
        archive.close()
        self.assertRaises(IOError, archive.names)

class ZipArchiveTests(ArchiveTests, unittest.TestCase):
    def _getTargetClass(self):
        from compoze.compozer import ZipArchive
        return ZipArchive
        
    def setUp(self):
        import tempfile
        self.archive_tmpdir = tempfile.mkdtemp()
        self.archive_file = os.path.join(self.archive_tmpdir, 'archive.zip')
        import zipfile
        archive = zipfile.ZipFile(self.archive_file, 'w')
        for data in self.fixturefiles:
            archive.write(data['path'], data['name'])
        archive.close()

class TarGzArchiveTests(ArchiveTests, unittest.TestCase):
    def _getTargetClass(self):
        from compoze.compozer import TarArchive
        return TarArchive

    def setUp(self):
        import tempfile
        self.archive_tmpdir = tempfile.mkdtemp()
        self.archive_file = os.path.join(self.archive_tmpdir, 'archive.tgz')
        import tarfile
        archive = tarfile.open(self.archive_file, 'w:gz')
        for data in self.fixturefiles:
            archive.add(data['path'], data['name'])
        archive.close()
    
class TarBz2ArchiveTests(ArchiveTests, unittest.TestCase):
    def _getTargetClass(self):
        from compoze.compozer import TarArchive
        return TarArchive

    def setUp(self):
        import tempfile
        self.archive_tmpdir = tempfile.mkdtemp()
        self.archive_file = os.path.join(self.archive_tmpdir, 'archive.tar.bz2')
        import tarfile
        archive = tarfile.open(self.archive_file, 'w:bz2')
        for data in self.fixturefiles:
            archive.add(data['path'], data['name'])
        archive.close()

class Test__getArchiver(unittest.TestCase):

    def _getFilename(self, base):
        return os.path.join(os.path.dirname(__file__),
                            'fixtures', 'archive', base)

    def test_tar_gz(self):
        from compoze.compozer import _getArchiver
        from compoze.compozer import TarArchive
        fname = self._getFilename('folder.tar.gz')
        self.failUnless(isinstance(_getArchiver(fname), TarArchive))

    def test_tgz(self):
        from compoze.compozer import _getArchiver
        from compoze.compozer import TarArchive
        fname = self._getFilename('folder.tgz')
        self.failUnless(isinstance(_getArchiver(fname), TarArchive))

    def test_bz2(self):
        from compoze.compozer import _getArchiver
        from compoze.compozer import TarArchive
        fname = self._getFilename('folder.bz2')
        self.failUnless(isinstance(_getArchiver(fname), TarArchive))

    def test_zip(self):
        from compoze.compozer import _getArchiver
        from compoze.compozer import ZipArchive
        fname = self._getFilename('folder.zip')
        self.failUnless(isinstance(_getArchiver(fname), ZipArchive))

    def test_egg(self):
        from compoze.compozer import _getArchiver
        from compoze.compozer import ZipArchive
        fname = self._getFilename('folder.egg')
        self.failUnless(isinstance(_getArchiver(fname), ZipArchive))


class CompozerTests(unittest.TestCase):

    def _getTargetClass(self):
        from compoze.compozer import Compozer
        return Compozer

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_empty_argv_raises(self):
        self.assertRaises(ValueError, self._makeOne, argv=[])

    def test_ctor_no_download_invalid_path_raises(self):
        self.assertRaises(ValueError, self._makeOne,
                          argv=['--no-download', '--path=%s' % __file__])

    def test_ctor_default_index_url_cheeseshop(self):
        tested = self._makeOne(argv=['--fetch-site-packages'])
        self.assertEqual(tested.options.index_urls,
                         ['http://pypi.python.org/simple'])

    def test__extractNameVersion_non_archive(self):
        non_archive = tempfile.NamedTemporaryFile()
        non_archive.write('This is a test.\n')
        non_archive.flush()
        tested = self._makeOne(argv=['--no-download'])
        self.assertEqual(tested._extractNameVersion(non_archive.name),
                         (None, None))

    def test__extractNameVersion_archive_no_egg_info_or_setup(self):
        import tarfile
        tested = self._makeOne(argv=['--no-download', '--quiet'])
        tfile = tempfile.NamedTemporaryFile(suffix='.tgz')
        archive = tarfile.TarFile(fileobj=tfile)
        archive.close()
        tfile.flush()
        self.assertEqual(tested._extractNameVersion(tfile.name),
                         (None, None))

    def test__extractNameVersion_archive_w_pkg_info(self):
        import tarfile
        import StringIO
        tested = self._makeOne(argv=['--no-download', '--quiet'])
        tfile = tempfile.NamedTemporaryFile(suffix='.tgz')
        archive = tarfile.TarFile(fileobj=tfile, mode='w')
        buffer = StringIO.StringIO()
        buffer.writelines(['Name: testpackage\n', 'Version: 3.14\n'])
        size = buffer.tell()
        buffer.seek(0)
        info = tarfile.TarInfo('PKG-INFO')
        info.size = size
        archive.addfile(info, buffer)
        archive.close()
        tfile.flush()
        self.assertEqual(tested._extractNameVersion(tfile.name),
                         ('testpackage', '3.14'))

    def test__extractNameVersion_archive_w_setup(self):
        import tarfile
        import StringIO
        tested = self._makeOne(argv=['--no-download', '--quiet'])
        tfile = tempfile.NamedTemporaryFile(suffix='.tgz')
        archive = tarfile.TarFile(fileobj=tfile, mode='w')
        dinfo = tarfile.TarInfo('testpackage')
        dinfo.type = tarfile.DIRTYPE
        dinfo.mode = 0777
        archive.addfile(dinfo)
        buffer = StringIO.StringIO()
        buffer.write(_DUMMY_SETUP)
        size = buffer.tell()
        buffer.seek(0)
        finfo = tarfile.TarInfo('testpackage/setup.py')
        finfo.size = size
        archive.addfile(finfo, buffer)
        archive.close()
        tfile.flush()
        self.assertEqual(tested._extractNameVersion(tfile.name),
                         ('testpackage', '3.14'))

_DUMMY_SETUP = """\
print 'testpackage'
print '3.14'
"""
