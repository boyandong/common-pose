# Additional numerical reproducibility diagnostic

Registered after the offlinecostprofile observed a repeatable newGPU−oldcache difference of0.0019130111rad. This is a diagnostic of runtime reproducibility,not a new predictive-method evaluation or a rescue of oldresults. Originalcaches andmaincomparisoninputs remain unchanged.

Use the samefirst3prespecifiedGPUcostfiles. Evaluate defaultbackendflags,IEEE-styleFP32(TF32off/highestmatmulprecision),and deterministicIEEE-styleFP32,with2repeats each. SetCUBLAS_WORKSPACE_CONFIGbeforeCUDAinitialization. ReportposeRMS/max/p99difference tooriginalcache,repeatdifference,backendflags andsixconsumeroutputdifference fractions onpredictionvalid andpairedGTvalidblocks. Meanposes infloat64 thenserializefloat32 tofolloworiginalcacheaggregation. No choosinga newpipeline setting fromperformance,no recalibration,nounseen/semantic/physical/online claim. These3files are a smallruntime audit,not exhaustivecross-GPUvalidation.

Negative/nonmatchingoutcomes retained. Ifdeterministicalgorithmunsupported,recordthatpolicyerror. Subsequentproposalfor runtimepolicy mayrefer totheseobservations butwould require itsown frozen replay andbroadverification.
