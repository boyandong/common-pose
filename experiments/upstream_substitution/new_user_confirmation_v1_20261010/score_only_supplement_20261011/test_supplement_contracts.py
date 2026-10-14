"""Meaningful missing-support and independent exact-sign controls."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import numpy as np
import analyze_score_only as producer
import verify_score_only as verifier
from runtime_common import LANE,BASE,load_module

class Contracts(unittest.TestCase):
    def test_missing_frozen_class_is_not_zero_risk(self):
        old=load_module('control_old_measures',BASE/'paper_supplement_v1_20261009/analyze_comparisons.py')
        independent=load_module('control_independent_measures',LANE/'verify_new_results.py')
        gt=np.asarray([1]*40+[2]*40);v={'ygt':gt,'ypred':gt.copy(),'flip':np.zeros(80,dtype=np.int8)}
        mask=np.zeros(80,bool);mask[:24]=True
        result=old.maskmetric(v,mask,[1,2]);other,_,_=independent.measure(v['flip'],gt,np.flatnonzero(mask),[1,2])
        self.assertEqual(result['ordinary_risk'],0.)
        self.assertIsNone(result['fixed_common_risk']);self.assertIsNone(other['fixed_common_risk'])
        self.assertEqual(result['baseline_set_risk_lower'],0.);self.assertEqual(result['baseline_set_risk_upper'],.5)

    def test_sign_and_missing_pairs_independently_match(self):
        values=[.1]*8
        for values in [values,[0.]*8,[.1]*7+[None],[-.1]*4+[.1]*4]:
            left=producer.describe(values);right=verifier.describe(values);verifier.verify_summary(left,right)
        self.assertEqual(producer.describe([.1]*8)['descriptive_sign_p'],.0078125)
        self.assertEqual(producer.describe([0.]*8)['n_nonzero'],0)
        self.assertEqual(producer.describe([0.]*8)['descriptive_sign_p'],1.)
        self.assertIsNone(producer.describe([.1]*7+[None])['descriptive_sign_p'])

if __name__=='__main__':unittest.main()
