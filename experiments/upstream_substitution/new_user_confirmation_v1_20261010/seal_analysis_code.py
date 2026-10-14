"""Seal inference/statistical implementation after successful old-only controls."""
from runtime_common import LANE,read,sha,save

def main():
    validation=read(LANE/'OLD_CACHE_EXECUTION_VALIDATION.json')
    assert validation['status']=='PASS' and not validation['new_user_features_read']
    assert validation['canonical_seven_method_risk_checks']==840
    assert validation['analysis_code_sha256']==sha(LANE/'analyze_new_users.py')
    assert validation['independent_code_sha256']==sha(LANE/'verify_new_results.py')
    names=['reconstruct_users.py','analyze_new_users.py','verify_new_results.py',
           'validate_execution_on_old_cache.py','run_stage_job.py','seal_analysis_code.py']
    save(LANE/'ANALYSIS_CODE_SEAL.json',{'status':'FROZEN_BEFORE_FIRST_NEW_USER_PREDICTION',
        'files':{n:sha(LANE/n) for n in names},'old_cache_validation_sha256':sha(LANE/'OLD_CACHE_EXECUTION_VALIDATION.json'),
        'protocol_sha256':sha(LANE/'SCIENTIFIC_SPEC.md'),'cohort_sha256':sha(LANE/'ENROLLMENT_MANIFEST.json'),
        'acquisition_execution_manifest_sha256':sha(LANE/'FROZEN_EXECUTION_MANIFEST.json'),
        'no_new_user_features_or_effects_seen':True})
    print('ANALYSIS_CODE_SEALED_BEFORE_INFERENCE')

if __name__=='__main__':main()
