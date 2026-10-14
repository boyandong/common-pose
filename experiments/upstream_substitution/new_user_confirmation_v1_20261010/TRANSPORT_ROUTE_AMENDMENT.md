# 下载路线补充 — 2026-10-10

封存名单后、下载和预测前，用户直接指定“下载采用本地中转”。据此源文件在本地 `D:/CommonPose_confirmation_N80_20261010/source/<user>/<filename>` 首次获取和建立逐文件 SHA256 收据，再传至远端 `/root/autodl-tmp/common_pose_confirmation_N80_20261010/source/<user>/<filename>`。本地源直接作为完整核验备份保留，不在 C 盘重复保存。

此补充只规定 transport route。科学协议、80 人名单、2,768 个 member、官方源 URL/ETag、偏移、尺寸、资格门槛、推理方法、终点和统计规则不变。远端源必须与 D 盘收据哈希一致后才能通过资格核验。全部源与缓存远端保留；重建缓存、分数、收据另回传同一 D 盘备份根目录。

不购买、不删除；传输失败只重试同一封存 member。代码在执行下载前以 FROZEN_EXECUTION_MANIFEST.json 封存。
