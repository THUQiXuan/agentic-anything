# 2025 Lecture 5 - GPUs — pages 41-48

- page_id: `2025-lecture-5-gpus__006__pages-41-48`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf
- type: segment

## Content

Putting it together: understanding a matrix mystery
Why is it faster  to have bigger matrices? 
This section is from https://www.thonking.ai/p/what-shapes-do-matrix-multiplications

Matrix mystery
We understand some of this (compute intensity, tiling). Let’s take a closer look..

Part 1: tiling
Tiling has a major impact through alignment.

Part 2: wave quantization
What’s with the periodic behavior?
This happens at 1792 to 1793 size.
Why? Using a tile size of 256 × 128,  there are
1792
256 × 1792
128 = 7 × 14 = 98
tiles. If we increase this to 1793, we have 
8 × 15 = 120
tiles.
An A100 has 108 SMs, so it cannot execute all 120

Recap of part 2: making ML workloads go fast
❖ Reduce memory accesses
❖Coalescing
❖Fusion
❖ Move memory to shared memory
❖Tiling
❖ Trade memory for compute/accuracy
❖Quantization
❖Recomputation

Part 3: Using what we know to understand Flash Attention
Flash attention [Dao et al] dramatically accelerates attention.. But how?
Technique from paper:

Recap of attention computation
Attention  computation : 3 matrix multiplies (K, Q, V) with a softmax  in between

Tiling part 1: tiling for the KQV matrix multiply
This figure 1 from the paper is literally just tiling for a KQV matrix multiply..
But what do we do about the softmax ?
