# Aurora Operations Handbook

This compact handbook is a synthetic demo resource for Agentic Anything.

## Release procedure

Production releases happen on Tuesdays at 14:00 UTC. The release owner must
verify the canary dashboard for ten minutes before promoting traffic.

The emergency rollback command is `aurora rollback --release CURRENT`.
Rollback approval code **ORBIT-17** is required in the incident record.

## 缓存故障处理

错误码 **E42** 表示缓存写锁未释放。处理步骤是先运行
`aurora cache inspect`，确认锁的持有者；再运行
`aurora cache unlock --ticket INCIDENT_ID`。禁止直接重启全部节点。

## Support policy

Enterprise customers receive a response within 30 minutes. Standard customers
receive a response within four business hours. Refund requests are accepted
within 37 days of purchase.
