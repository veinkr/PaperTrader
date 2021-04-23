# PaperTrader
基于A股的回测账户类

## 致谢
quantaxis
qifiaccount
鸭神

## 解决痛点
1. 当前的回测框架大多没有t+n的配置，在回测层面缺少约束
2. 除权除息数据大多采用复权的方式进行回测，本程序采用计算除权复权时候的账户变化来描述真实的账户变更
3. qifiaccount的文档缺失太多，而且与mongodb和页面的耦合程度较高，本着极简主义的思想，把耦合的部分用python实现，因此本程序的最佳实践是jupyter

## example
参考 回测-除权除息.ipynb
