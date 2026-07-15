# 2025 Lecture 5 - GPUs — pages 33-40

- page_id: `2025-lecture-5-gpus__005__pages-33-40`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf
- type: segment

## Content

Trick (?) 4: Memory coalescing and DRAM
DRAM (global memory) is read in ‘burst mode’ – each read gives you many bytes! 
[https://blog.csdn.net/xll_bit/article/details/117702476]
Burst mode comes from the slow per -row copy to the sense amplifier 
[https://www.youtube.com/watch?v=9BjVUmaXaCQ]

Memory coalescing 
Memory accesses are coalesced  if all the threads (in a warp) fall within the same burst 
Reminder: a warp is a set of 32 consecutively 
numbered threads that execute together in a 
block. Memory accesses happen together

Coalescing for matrix multiplication
For row -major matrices – threads that move along rows are not coalesced
Note how the second diagram reads the entire vector at each step!

Trick 5 (the big one): tiling
Tiling  is the idea of grouping and ordering threads to minimize global memory access.
Let’s go back to matrix multiplication..
Note that memory access is not coalesced, and repeated (M0,0 and N1,0)

Tiling – store and reuse information in shared memory
Cut up the matrix into smaller ‘tiles’, and load this into shared memory
Compute the matrix multiply in ‘phases’
1. Load 𝑀0,0 and 𝑁0,0 tiles into SHM
2. Compute partial sums for 𝑃
(Done with one tile)
3. Load the 𝑀0,0 and 𝑁2,0 tile into SHM
4. … 
Advantages: repeated reads now access shared, not global memory
 and memory access can be coalesced

Tiling math
Non-tiled matrix multiply: each input is read 𝑁 times from global memory
Tiled matrix multiply: each input is read 
𝑁
𝑇 times from global memory, and 𝑇 times 
within each tile. This is a factor of 𝑇 reduction in global memory access

Complexities with tiling
Tile sizes may not divide the matrix size and lead to low utilization
https://docs.nvidia.com/deeplearning/perform ance/dl-performance-matrix-multiplication/index.html#tile-quant
Factors affecting tile sizes
• Coalesced memory access
• Shared memory size
• Divisibility of the matrix dim

Complexities with tiling 2 – memory alignment
Coalesced accesses may be impossible depending on the dimension of the matrix..
(have to do padding)
Memory comes in bursts
Loading tiles are fast if 
bursts align with the matrix
https:/ /www.thonking.ai/p/ what-shapes-do-matrix-multiplications
