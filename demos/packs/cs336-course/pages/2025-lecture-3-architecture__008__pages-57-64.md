# 2025 Lecture 3 - architecture — pages 57-64

- page_id: `2025-lecture-3-architecture__008__pages-57-64`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

Logit soft-capping.
Soft-capping  the logits to some maximum value via Tanh
Prevents logits from blowing up, but also might have perf issues?

Attention heads
Most models don’t touch the attention heads much at all with a few minor exceptions..
GQA / MQA  : Saving inference costs by reducing the number of heads
Sparse or sliding window attention (GPT4/Mistral): restricting the attention pattern 
to reduce compute cost
Exotic SSM stuff (Jamba, Falcon 3, etc): not covered (sorry!)

GQA/MQA – Reducing attention head cost
Let’s think about the compute involved for attention
Total arithmetric  operations (𝑏𝑛𝑑2), total memory accesses (𝑏𝑛𝑑 + 𝑏ℎ𝑛2 + 𝑑2)
Arithmetic intensity is high 𝑂 1
𝑘 + 1
𝑏𝑛
−1
 - we can keep our GPUs running
X softmax projection

GQA/MQA – Reducing attention head cost
What about the incremental  case when we generate text?
 Key difference:  can’t parallelize the generation process – needs to be step by step
In this case – we need to incrementaly  re-compute/update attention via the ‘KV cache’
 
[Animation from https://medium.com/@joaolages/kv -caching-explained-276520203249]

GQA/MQA – Reducing attention head cost
What’s the incremental arithmetic intensity?
Total arithmetric  operations (𝑏𝑛𝑑2), total memory accesses (𝑏𝑛2𝑑 + 𝑛𝑑2)
Arithmetic intensity is not good 𝑂
𝑛
𝑑 +
1
𝑏
−1
 - need large batches + short seq length 
(n) or big model dimensions (d) 
X projection
Is there some way around this? The n/d term is difficult to reduce.

MQA – just have fewer key dimensions.
Key idea – have multiple queries, but just one dimension for keys and values
We have much fewer items to move in and out of memory (KV Cache) 
Total memory access (𝑏𝑛𝑑 + 𝑏𝑛2𝑘 + 𝑛𝑑2), Arithmetic intensity  𝑂
1
𝑑 +
𝑛
𝑑ℎ +
1
𝑏
−1
[figure from https://blog.fireworks.ai/multi-query-attention-is-all-you-need-db072e758055]

Recent extension – GQA
Don’t go all the way to one dimension of KV – have fewer dims
Simple knob to control expressiveness (key -query ratio) and inference efficiency

Does MQA hurt? Sometimes..
Small PPL hit w/ MQA [ Shazeer 2019]
 Low/no hit w/ GQA [Ainslie 2023]
