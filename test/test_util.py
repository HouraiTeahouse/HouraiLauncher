import os
from unittest import TestCase, main
from util import list_files, namedtuple_from_mapping, ProtectedDict,\
     sha256_hash, tupperware


class UtilTest(TestCase):

    def test_sha256_hash_empty_file(self):
        # need to figure out how to mock a file object
        pass

    def test_sha256_hash_4kb_of_0xff(self):
        # need to figure out how to mock a file object
        pass

    def test_list_files_in_test_directory(self):
        splitext = os.path.splitext
        this_dir = os.path.dirname(__file__)
        filenames = set()
        for fullpath, relpath in list_files(this_dir):
            relpath = relpath.replace('/', os.path.sep)
            self.assertEqual(os.path.join(this_dir, relpath), fullpath)
            filenames.add(splitext(os.path.basename(relpath))[0])

        module_name = splitext(os.path.basename(__file__))[0]

        self.assertTrue(filenames)
        self.assertIn(module_name, filenames)

    def test_namedtuple_from_mapping_can_succeed(self):
        test_tupp = namedtuple_from_mapping({'attr': 'qwer'})
        self.assertEqual(test_tupp.attr, 'qwer')

    def test_tupperware_is_formatted_properly(self):
        test_dict = dict(
            list=[0, '1'],
            dict={
                'zxcv': ProtectedDict(
                    {1234: '1234', '': 'test'}
                    )
                },
            actual_dict=ProtectedDict({1: 2, 3: 4})
            )
        tupp = tupperware(test_dict)
        self.assertIsNot(tupp, test_dict)
        self.assertEqual(tupp.list, [0, '1'])
        self.assertIsInstance(tupp.dict.zxcv, ProtectedDict)
        self.assertEqual(tupp.dict.zxcv,   {1234: '1234', '': 'test'})
        self.assertEqual(tupp.actual_dict, {1: 2, 3: 4})


if __name__ == "__main__":
    main()
