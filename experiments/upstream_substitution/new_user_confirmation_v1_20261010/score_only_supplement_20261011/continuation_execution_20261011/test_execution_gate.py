"""Exercise rejection of invented success or mismatched continuation evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from execution_gate import verify_execution_gate,sha

class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.here=Path(self.temp.name);self.cont=self.here/'continuation';self.cont.mkdir()
        self.write(self.here/'INTEGRATED_CONTROLLER_LAUNCH_20261011.json',{'old':'launch'})
        self.write(self.here/'INCIDENT_CONTROLLER_LOST_20261011.json',{'exit':'UNKNOWN'})
        self.write(self.cont/'PREFLIGHT.json',{'status':'PASS'})
        self.write(self.cont/'EXECUTION_CODE_SEAL.json',{'files':{}})
        self.write(self.cont/'LAUNCHER_IDENTITY.json',{'pid':11})
        launch={'pid':22,'launcher_pid':11,'original_controller_exit':'UNKNOWN','launcher_identity_sha256':sha(self.cont/'LAUNCHER_IDENTITY.json'),'preflight_sha256':sha(self.cont/'PREFLIGHT.json'),'original_launch_sha256':sha(self.here/'INTEGRATED_CONTROLLER_LAUNCH_20261011.json'),'original_incident_sha256':sha(self.here/'INCIDENT_CONTROLLER_LOST_20261011.json'),'execution_code_seal_sha256':sha(self.cont/'EXECUTION_CODE_SEAL.json')}
        self.write(self.cont/'LAUNCH.json',launch)
        digest=sha(self.cont/'LAUNCH.json')
        self.write(self.cont/'CONTROLLER_TERMINAL.json',{'pid':22,'exit_code':0,'original_controller_exit':'UNKNOWN','continuation_launch_sha256':digest,'original_launch_sha256':launch['original_launch_sha256'],'finished_epoch':10})
        self.write(self.cont/'PROCESS_EXIT_OBSERVATION.json',{'pid':22,'exit_code':0,'status':'ACTUAL_CHILD_PROCESS_WAIT_RETURNED','original_controller_exit':'UNKNOWN','launch_sha256':digest,'observer_pid':11,'observer_identity_sha256':launch['launcher_identity_sha256'],'observed_epoch':11})
        self.write(self.here/'EXECUTION_COMPLETE.json',{'original_controller_exit':'UNKNOWN','continuation_launch_sha256':digest,'execution_identity':'continuation_execution_20261011','status':'PRIMARY_AND_SCORE_ONLY_VERIFIED_AND_FULLY_BACKED_UP'})
    def tearDown(self):self.temp.cleanup()
    def write(self,path,obj):path.write_text(json.dumps(obj),encoding='utf-8')
    def change(self,path,key,value):
        r=json.loads(path.read_text());r[key]=value;self.write(path,r)
    def test_matching_actual_exit(self):self.assertEqual(verify_execution_gate(self.here,self.cont)['original_controller_exit'],'UNKNOWN')
    def test_missing_os_exit_rejected(self):
        (self.cont/'PROCESS_EXIT_OBSERVATION.json').unlink()
        with self.assertRaises(FileNotFoundError):verify_execution_gate(self.here,self.cont)
    def test_nonzero_os_exit_rejected(self):
        self.change(self.cont/'PROCESS_EXIT_OBSERVATION.json','exit_code',1)
        with self.assertRaises(AssertionError):verify_execution_gate(self.here,self.cont)
    def test_foreign_pid_rejected(self):
        self.change(self.cont/'PROCESS_EXIT_OBSERVATION.json','pid',27444)
        with self.assertRaises(AssertionError):verify_execution_gate(self.here,self.cont)
    def test_mismatched_launch_rejected(self):
        self.change(self.cont/'CONTROLLER_TERMINAL.json','continuation_launch_sha256','foreign')
        with self.assertRaises(AssertionError):verify_execution_gate(self.here,self.cont)
    def test_invented_original_exit_rejected(self):
        self.write(self.here/'CONTROLLER_TERMINAL.json',{'exit_code':0})
        with self.assertRaises(AssertionError):verify_execution_gate(self.here,self.cont)
    def test_original_unknown_must_remain(self):
        self.change(self.here/'EXECUTION_COMPLETE.json','original_controller_exit',0)
        with self.assertRaises(AssertionError):verify_execution_gate(self.here,self.cont)

if __name__=='__main__':unittest.main()
