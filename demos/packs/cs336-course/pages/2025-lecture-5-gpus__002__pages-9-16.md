# 2025 Lecture 5 - GPUs — pages 9-16

- page_id: `2025-lecture-5-gpus__002__pages-9-16`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf
- type: segment

## Content

Anatomy of a GPU (execution units)
Each SM further contains many SPs 
(streaming processor)  that can 
execute ‘threads’ in parallel
GPUs have many SM (streaming 
multiprocessors) that independently 
execute ‘blocks’ (jobs).

Anatomy of a GPU (memory)
The closer the memory to the SM, the faster it is – L1 and shared memory is inside 
the SM. L2 cache is on die, and global memory are the memory chips next to the GPU
SRAM (shared/cache memory) is much more expensive (100x) but ~ 8x faster than DRAM (Global memory)

Execution model of a GPU
There are 3 important players in the execution model
Threads: Threads ‘do the work’ in parallel – all threads execute the same instructions but with 
different inputs (SIMT). 
Blocks: Blocks are groups of threads. Each block runs on a SM w/ its own shared memory.
Warp: Threads always execute in a ‘warp’ of 32 consecutively numbered threads each.

Memory model of a GPU
Each thread can access its own register, and shared memory within the block.
Information that goes across blocks need to be read/written to global memory (slow)

Side thread – What about TPUs?
GPUs, TPUs, and many other accelerators are at a high level, similar
Core structure – lightweight control, fast (big) matmul unit, fast memory. 
Differences -  how the accelerators are networked (in the parallelism lecture)
      -   no warps (just blocks – tradeoffs in matmul vs non-matmul)
A GPU has more SMs
TPUs has fewer TCs
(but similar matmul perf)

Strengths of the GPU model
❖ Easily scales up hard workloads (by adding more SMs)
❖ Easy (?) to program due to the SIMT model
❖ Threads are ‘lightweight’ and can be stopped and started

GPUs as fast matrix multipliers
Early days of NVIDIA GPUs – programmable shaders. Researchers hacked this to do matmuls

New matmul hardware means matmuls are fast and special
Tensor cores (introduced in V, T series) are specialized matrix multiplication circuits.
Matmuls  are >10x faster than other floating point ops!
