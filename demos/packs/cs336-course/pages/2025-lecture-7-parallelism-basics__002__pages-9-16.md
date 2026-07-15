# 2025 Lecture 7 - Parallelism basics — pages 9-16

- page_id: `2025-lecture-7-parallelism-basics__002__pages-9-16`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

TPUs vs GPUs – design differences at the comm level
TPU networking 
toroidal mesh
GPU networking
All-to-all (up to 256)

Part 1 recap
❖ New unit of compute – the datacenter
❖ What we want from multi -machine scaling:
❖Linear memory scaling (max model params scales with num gpus)
❖Linear compute scaling (model flops scale linearly with num gpus)
❖ Simple collective comms primitives

Part 2 – Standard LLM parallelization primitives
How do we parallelize LLMs? 3 important ideas
• Data parallelism
• Naïve data parallel
• ZeRO levels 1-3
• Model parallelism
• Pipeline parallel
• Tensor parallel
• Activation parallelism
• Sequence parallel

Naïve data parallelism
Starting point – imagine we are doing naïve SGD
𝜃𝑡+1 = 𝜃𝑡 − 𝜂 ෍
𝑖=1
𝐵
∇𝑓(𝑥𝑖)
Naive parallelism: split the elements of B sized batch across M machines. Exchange gradients to 
synchronize
How does this do?
 Compute scaling – each GPU gets B/M examples. 
 Communication overhead – transmits 2x # params every batch. OK if batches are big
 Memory scaling – none. Every GPU needs # params at least

What’s wrong with naïve data parallel?
Memory seems like it’d be a problem – we copy the model parameters to each GPU. 
Let’s take a closer look..

What’s wrong with naïve data parallelism?  -  Memory 
Our memory situation is actually terrible.
Depending on our precision.. 
We need 5 copies of weights and 16 bytes per param! 
- 2 bytes for FP/BF 16 model parameters
- 2 bytes for FP/BF 16 gradients
- 4 bytes for FP32 master weights (the thing you accumulate into in SGD)
- 4 (or 2) bytes for FP32/BF16 Adam first moment estimates
- 4 (or 2) bytes for FP32/BF16 Adam second moment estimates
“Optimizer state”

ZeRO – solving the memory overhead issue of DP
Core idea: split up the expensive parts (state) and use the reduce -scatter equivalence.

ZeRO stage 1. optimizer state sharding
High level idea:
• Split up the optimizer state (first + second moments) across GPUs
• Everyone has the parameters + gradients 
Each worker is responsible for updating a subset of params (corresponding to their slice)
