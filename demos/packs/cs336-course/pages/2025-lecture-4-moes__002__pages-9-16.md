# 2025 Lecture 4 - MoEs — pages 9-16

- page_id: `2025-lecture-4-moes__002__pages-9-16`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/98455ec198c9a88ec1ab2b1c4058662431b54ce3/nonexecutable/2025%20Lecture%204%20-%20MoEs.pdf
- type: segment

## Content

Earlier MoE results from Chinese groups – Qwen 
Chinese LLM companies are also doing quite a bit of MoE work on the smaller end

Earlier MoE results from Chinese groups - DeepSeek
There’s also some good recent ablation work on MoEs showing they’re generally good

Recent MoE results – DeepSeek v3

Why haven’t MoEs been more popular?
Infrastructure is complex / advantages on multi node
Training objectives are somewhat heuristic (and sometimes unstable)
[Zoph et al 2022]
[Fedus et al 2022]

What MoEs generally look like
Typical: replace MLP with MoE layer
 Less common: MoE for attention heads
[ModuleFormer , JetMoE ]

MoE – what varies?
❖ Routing function
❖ Expert sizes
❖ Training objectives

Routing function - overview
Many of the routing algorithms boil down to ‘choose top k’
Token chooses 
expert
Expert chooses 
token
Global routing via 
optimization
[Fedus et al 2022]

Routing type
Almost all the MoEs do a standard ‘token choice topk’ routing. Some recent ablations
