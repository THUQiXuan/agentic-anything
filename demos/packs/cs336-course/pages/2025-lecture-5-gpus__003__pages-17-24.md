# 2025 Lecture 5 - GPUs — pages 17-24

- page_id: `2025-lecture-5-gpus__003__pages-17-24`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf
- type: segment

## Content

Compute scaling is faster than memory scaling
FLOPs scale faster than memory – it’s hard to keep our compute units fed with data!
https://medium.com /riselab/ai-and-memory-wall-2cb4265cb0b8

Recap: GPUs – what are they and how do they work
❖ GPUs are massively parallel – same instructions 
applied across many workers
❖ Compute (and esp matmuls ) have scaled faster 
than memory
❖ We have to respect the memory hierarchy to 
make things go fast.

Part 2: Making ML workloads fast on a GPU
Performance on a GPU can be complex, even for something as simple as a square matmul

What makes ML workloads fast?
The roofline model  
Key to this section: how do we avoid being memory bound?

How do we make GPUs go fast?
1. Control divergence (not a memory bottleneck..)
2. Low precision computation
3. Operator fusion
4. Recomputation
5. Coalescing memory
6. Tiling

Control divergence (not a memory issue)
GPUs operate in a SIMT model – every thread in a warp is executing the same instruction
Conditionals are fine, but lead to significant overhead from the execution model

Trick 1: Low precision computation
If you have fewer bits, you have fewer bits to move

Low precision improves arithmetic intensity
Example: elementwise ReLU (𝑥 = max(0, 𝑥)) on a vector of size 𝑛.
(Float 32 case)
Memory access : 1 read (x), 1 write (if x < 0), float 32 = 8 bytes
Operations: 1 comparison op, 1 FLOP.
Intensity: 8 bytes / FLOP
(Float 16)
Memory access : 1 read (x), 1 write (if x < 0), float 16 = 4 bytes
Operations: 1 comparison op, 1 FLOP.
Intensity: 4 bytes / FLOP
