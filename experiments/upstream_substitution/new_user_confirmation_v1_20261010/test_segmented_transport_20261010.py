"""Meaningful transport recovery/integrity controls; no scientific effects."""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import acquire_sources_segmented_20261010 as runner
from runtime_common import read


class Stream(io.BytesIO):
    def read1(self, count):
        return self.read(count)


class Controls(unittest.TestCase):
    def setUp(self):
        runner.STOP.clear()
        self.tmp=tempfile.TemporaryDirectory()
        self.data=Path(self.tmp.name)
        self.row={'user':'control','source_member':'archive/control.hdf5','size':23,'archive_data_offset':100}
        self.cohort={'source_url':'https://example.invalid/frozen','etag':'"frozen"','archive_bytes':999}
        self.raw=b'0123456789abcdefghijklm'
        self.p=self.data/'source/control/control.hdf5'
        self.p.parent.mkdir(parents=True)
        self.partial=self.p.with_name(self.p.name+'.partial')

    def tearDown(self):
        self.tmp.cleanup()
        runner.STOP.clear()

    def test_resume_and_transient_read_failure_preserve_all_bytes(self):
        self.partial.write_bytes(self.raw[:7]);calls=[];failed=[False]
        class Broken(Stream):
            def read1(stream,count):
                if stream.tell():
                    raise TimeoutError('injected after persisted progress')
                return stream.read(min(3,count))
        def response(cohort,begin,end):
            calls.append((begin,end))
            body=self.raw[begin-100:end-100+1]
            if begin==107 and not failed[0]:
                failed[0]=True
                return Broken(body)
            return Stream(body)
        with patch.object(runner,'DATA',self.data),patch.object(runner,'SEGMENT',8),patch.object(runner,'response',response),patch.object(runner,'event'),patch.object(runner.STOP,'wait',return_value=False):
            self.assertEqual(runner.acquire(self.cohort,self.row),23)
        self.assertEqual(self.p.read_bytes(),self.raw)
        self.assertFalse(self.partial.exists())
        meta=read(self.p.with_name(self.p.name+'.receipt.json'))
        self.assertEqual(meta['sha256'],hashlib.sha256(self.raw).hexdigest())
        self.assertIn((100,106),calls)
        self.assertIn((100,109),calls)
        self.assertIn((110,114),calls)

    def test_tail_mismatch_stops_and_preserves_partial(self):
        self.partial.write_bytes(b'corrupt')
        with patch.object(runner,'DATA',self.data),patch.object(runner,'response',return_value=Stream(self.raw[:7])),patch.object(runner,'event'):
            with self.assertRaises(runner.IntegrityError):runner.acquire(self.cohort,self.row)
        self.assertEqual(self.partial.read_bytes(),b'corrupt')
        self.assertFalse(self.p.exists())

    def test_wrong_range_etag_or_length_rejected(self):
        for field,value in [('ETag','"changed"'),('Content-Range','bytes 101-107/999'),('Content-Length','8')]:
            stream=Stream(b'1234567');stream.status=206
            stream.headers={'ETag':'"frozen"','Content-Range':'bytes 100-106/999','Content-Length':'7'}
            stream.headers[field]=value
            with patch.object(runner.urllib.request,'urlopen',return_value=stream):
                with self.assertRaises(runner.IntegrityError):runner.response(self.cohort,100,106)
            self.assertTrue(stream.closed)

    def test_finite_retry_exhaustion_retains_partial(self):
        self.partial.write_bytes(self.raw[:7]);counter=[0]
        def response(cohort,begin,end):
            if end==106:return Stream(self.raw[:7])
            counter[0]+=1
            raise TimeoutError('injected stalled request')
        with patch.object(runner,'DATA',self.data),patch.object(runner,'response',response),patch.object(runner,'event'),patch.object(runner.STOP,'wait',return_value=False):
            with self.assertRaises(TimeoutError):runner.acquire(self.cohort,self.row)
        self.assertEqual(counter[0],8)
        self.assertEqual(self.partial.read_bytes(),self.raw[:7])
        self.assertFalse(self.p.exists())


if __name__=='__main__':unittest.main()
