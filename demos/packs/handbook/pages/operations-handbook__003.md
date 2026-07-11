# 缓存故障处理

- page_id: `operations-handbook__003`
- url: https://github.com/THUQiXuan/agentic-anything/blob/main/demos/sources/operations-handbook.md
- type: section

## Content

### 缓存故障处理

错误码 **E42** 表示缓存写锁未释放。处理步骤是先运行
`aurora cache inspect`，确认锁的持有者；再运行
`aurora cache unlock --ticket INCIDENT_ID`。禁止直接重启全部节点。
