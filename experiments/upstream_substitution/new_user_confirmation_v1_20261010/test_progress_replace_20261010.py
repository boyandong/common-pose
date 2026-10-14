"""Transient and permanent Windows sharing-denial controls, no source/effects."""
import ctypes
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import relay_completed_sources_v3_20261010 as runner


class Controls(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'progress.json'
        self.path.write_text('{"old":true}',encoding='utf-8')

    def tearDown(self):self.directory.cleanup()

    def error(self,code):
        error=PermissionError('injected Windows sharing/access denial');error.winerror=code;return error

    def test_transient_denial_then_complete_atomic_snapshot(self):
        real=os.replace;calls=[]
        def replace(a,b):
            calls.append(1)
            if len(calls)<3:raise self.error(5)
            return real(a,b)
        with patch.object(runner.os,'replace',side_effect=replace),patch.object(runner.time,'sleep'):
            runner.replace_progress(self.path,{'complete':17})
        self.assertEqual(len(calls),3);self.assertEqual(json.loads(self.path.read_text()),{'complete':17})

    def test_permanent_denial_bounded_preserves_prior_and_attempt(self):
        with patch.object(runner.os,'replace',side_effect=self.error(5)) as replace,patch.object(runner.time,'sleep'):
            with self.assertRaises(PermissionError):runner.replace_progress(self.path,{'new':True})
        self.assertEqual(replace.call_count,20)
        self.assertEqual(json.loads(self.path.read_text()),{'old':True})
        attempts=list(self.path.parent.glob(self.path.name+f'.v3.{os.getpid()}.*.partial'))
        self.assertEqual(len(attempts),1);tmp=attempts[0]
        self.assertEqual(json.loads(tmp.read_text()),{'new':True})

    def test_other_io_error_not_retried(self):
        with patch.object(runner.os,'replace',side_effect=OSError('unrelated I/O error')) as replace,patch.object(runner.time,'sleep'):
            with self.assertRaises(OSError):runner.replace_progress(self.path,{'new':True})
        self.assertEqual(replace.call_count,1)

    @unittest.skipUnless(os.name=='nt','Windows real file-sharing control')
    def test_real_windows_reader_without_delete_sharing(self):
        dll=ctypes.WinDLL('kernel32',use_last_error=True)
        create=dll.CreateFileW;create.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];create.restype=ctypes.c_void_p
        close=dll.CloseHandle;close.argtypes=[ctypes.c_void_p];close.restype=ctypes.c_int
        handle=create(str(self.path),0x80000000,0x1|0x2,None,3,0x80,None)
        self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
        released=[]
        def release():time.sleep(.15);released.append(close(handle))
        thread=threading.Thread(target=release);thread.start()
        try:runner.replace_progress(self.path,{'recovered':True})
        finally:thread.join()
        self.assertEqual(released,[1]);self.assertEqual(json.loads(self.path.read_text()),{'recovered':True})


if __name__=='__main__':unittest.main()
