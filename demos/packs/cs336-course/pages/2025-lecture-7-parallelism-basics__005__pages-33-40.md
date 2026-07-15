# 2025 Lecture 7 - Parallelism basics — pages 33-40

- page_id: `2025-lecture-7-parallelism-basics__005__pages-33-40`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

Pipeline performance is highly dependent on batch size
Batch sizes are key to hiding the bubble – otherwise pipeline rapidly degrades perf

Trading communication bandwidth for utilization
Some more crazy pipeline patterns can improve utilization, but at the cost of bandwidth

‘Zero bubble’ pipelining
Split up backwards into two parts
1. Backpropagating activations ( z,x)
2. Computing weight gradients (W)
The second part can be done whenever

Model parallel along the width axes
Are there model parallel schemes with better utilization?
We can think of pipeline parallel as cutting up along depth. What about width?
Simple matrix multiplication observation: decompose into submatrices, add partial sums

Tensor parallel – GPUs have submatrices
Assign columns (A1, A2) and rows (B1, B2) to separate GPUs. 
• In the forward pass, f is the identity, and g is an all -reduce. 
• In the backward pass, f is an all -reduce, g is the identity.

When do we tensor parallel?
On GPUs, tensor parallel within a node (up to 8 GPUs) due to high speed interconnects.

Tensor parallel – pros and cons vs pipeline parallel
How do things compare to pipeline parallel?
 Pros – no bubble. If your network is fast enough, there’s no waiting for others.
          – low complexity – simple to ‘wrap’ models without major infra changes
          – doesn’t need large batch sizes to work well
 Cons – much larger communication than pipeline parallel.
• Pipeline: 𝑏𝑠ℎ point-to-point communication per microbatch
• Tensor: 8𝑏𝑠ℎ 𝑛𝑑𝑒𝑣𝑖𝑐𝑒𝑠 −1
𝑛𝑑𝑒𝑣𝑖𝑐𝑒𝑠
 per layer and all-reduce communication.
Use tensor parallel whenever we have low -latency, high -bandwidth interconnects

A final complexity – memory is dynamic!
Memory isn’t just the static bits, but also activations! This can be big
