# CommonPose clone execution handover — 2026-10-14

## Objective
Complete all locally/server-computable evidence experiments before editing the EMBC2027paper;preserve original scientific artifacts and separately track external-evidence requirements. User initially requested local-only, then explicitly authorized the cloned server and all remaining experiments.

## Frozen decisions
Currentpaper unchanged. Local analysis lane `experiments/paper_evidence/local_closeout_20261014`. Server execution lane `experiments/paper_evidence/server_closeout_20261014`; remote root `/root/autodl-tmp/commonpose_paper_closeout_20261014`. Server SCIENTIFIC_SPEC.md froze feature8-combination factorial,lag[-2,-1,0,1,2]nominal20msblocks,windowwidth[1,10,40],3-recordofflineGPUprofiling,originalcohorts/weights/thresholdcriteria and independentrecount. No final-user retuning,originalmodelreplacement,online/physical/semanticaccuracy claims or publicrepo publishing.

## Verified state
Local61743checksPASS;all48S3/12S4cells match;187paperfiles unchanged. SixsourceLOSO procedures249folds exactly match priorOOFpredictions;clean-directory analysis reproduces10CSVhashes. Kinuser/parent/phase implementation correction documented,firstfive passes retained.

Onclone:sixcriticalsourcehashes match `/root/work/common-pose-db9-no-calibration-20261011`;`/root/work/common-pose` is an older minimal tree andnot the scientificcode root. Python3.10.13,numpy1.26.4,sklearn1.5.2,torch2.8.0+cu128. GPUqueryRTX4090/49140MiB,initiallyidle;disk116GiBfree;memorycgroup72GiB,CPUquota20cores. Current authenticatedtransportexecsession39440. Do not assume this transport will survive a new session.

## Scientific evidence
LocalN80Full/U−Boundary overall improvements remainpositive on6consumers,withpointwiseparticipant95%intervals. SHOW same79participants Uimprovement2.608pp[1.708,2.960],Bimprovement−20.880pp[−27.156,−12.280]. TTA-only increment is small;4/6primaryN80Uintervals cross0. FullthresholdDEVfeasibleU3/6,B0/6. DetailsLOCAL_REPORT.md.

ServerGPUprofileCOMPLETE:6timedfour-view passes across3fixedfiles,~1.694–1.730secwhole-recordinference/transfer onthisclone. MaximumnewGPU−oldcachepose difference0.0019130111rad,identical perfilerepeat;cause not established. Do not replace frozen caches or label bitwiseinference reproductionPASS. Scientificfeature comparisons useoldcache andriskbaselinechecks.

Serverfactorialfit COMPLETE:60newmodels,36originalinstances reused,0failedfits. Downloadedreceipts inverified_remote/. Evaluation/sensitivity/independentrecount/fullsealedlocaldelivery are NOT yetdeclaredcomplete bythis handover.

## Unknown/contaminated state
Actualupstreamtrainmembership unverified despitepublictrainfileoverlap1969/2768. Absolutephysicalzero,optical/EMGtiming,independenttargetlabels/humanreaders unavailable. OldS6unblinding mustbechecked againstoriginals,not restoredbylaterlabels. CohortsA20/N80previouslyexamined;newvariants exploratory. NewGPUfloatingdifferencecauseUNKNOWN;allmain cachedinputs preserved. GitHEADunavailable inremoteextractedscientifictree;contenthashesprovide verified binding.

## External runtime state
User-providedclonehost connect.westd.seetacloud.com:29596. No password persisted. HOST_IDENTITY.json pins SHA256 from firstauthorizedobservation. Runtime `/root/miniconda3/envs/commonpose-supplement/bin/python`. Exactlyone controller launched:PID2885,startticks907758190. LAUNCH_RESPONSE.json/verified_remote/LAUNCH.json record launch. LastLIVE_STATUS_01 confirmed matchingcontroller,stagefactorial_evaluation,validationfinished/A20 15of20;childPID2967. This is a historical observation,not currentliveness.

Controllerstages:GPUcost→factorialfit→factorialevaluation→lag/window→independentverification→reportpackage. Eachlaunch/terminalrecord hasPID/startticks/knownexitstate. Read remotePIPELINE_STATE.json/PROGRESS.json and currentownPIDidentity beforeanydecision. No other processes modified. Do not start a duplicatecontroller ordeleteEXECUTION.lock.

## Worktree state
Preserve all preexisting tracked/untracked changes. New scientific work only in two paper_evidence datedlanes and reviewchecklists. No commit/push/release. Originalpaperfiles not modified. Runtimeplot/transport vendor packages isolated andignored. Credentials are stdin-only;do not place them in handovers/scripts/manifests.

## Next actions
Monitor exactcontroller sparsely while continuing independentwork;reverify lateststage/PID. On knownterminal failure,preserve logs andaffectedphase;do not rerun blindly. OnceindependentrecountPASS andREMOTEdeliverypending,download FINAL_DELIVERY/manifest/package,check packageSHA andsafe regularmembers,then verify eachcontainedfilehash locally. Keep large decision/training arrays remotely andrecordpaths/hashes. Update scientificreport andremainingchecklist onlyafter evidencecompletion. Further externaldata/labels and controllednewupstream/online methods are separatebranches.

## Do NOT
Do not infer actualtrainmembers frommetadataonly. Do not claim successfulGPUcost is bitwisecachevalidation. Do not changeoriginalscorers,thresholds,cohorts,ties,labels orclasssupport. Do not selectbestlag/window/factorialvariant fromtestdata. Do not equatepairedrisk withall-runtime risk,referenceclasswithphysicalgesture,orpointwiseCIswith24independentrepeats. Do not killotherjobs,cleanupstorage,publishrepo or editpaper inthisexecutionphase.

## Recommended next session
CommonPose-EVIDENCE-20261014-SERVER-CLOSEOUT. Newremotephase is a session-hygiene handoverpoint;no crashorunknownexecutionincident hasbeen declared. Successor mustfreshlyverify all externalstate andreadspec/seals/runtime receipts.
