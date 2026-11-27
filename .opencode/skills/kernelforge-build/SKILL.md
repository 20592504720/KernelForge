---
name: kernelforge-build
description: 管理 KernelForge GKI、Vendor、OKI 和支持设备的内核构建准入与产物完整性。
---

## 触发条件

涉及 OnePlus 13、后续设备、GKI/Vendor/OKI、Clang/LLD/Make/Bazel、ABI/KMI 或构建产物时使用。

## 执行流程

1. 核验源码锁、manifest、工具链来源、版本、SHA256 和工作树干净状态。
2. 检查 CPU/RAM/swap/磁盘、并发参数、缓存策略和构建目录边界。
3. 按授权执行构建；分别核验日志、产物、ABI/KMI、签名和摘要。
4. 区分软件准入、微基准和真实内核构建证据，不互相替代。

## 验收标准

- 来源、工具链和产物均可追溯且字节/摘要校验通过。
- 未获授权不得真实编译、刷机或把缺失的 ABI/KMI/启动证据计为通过。
