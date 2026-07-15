# 2025 Lecture 7 - Parallelism basics — pages 41-48

- page_id: `2025-lecture-7-parallelism-basics__006__pages-41-48`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

A final complexity – activation memory
Thus far, we have only really discussed parameter memory. 
Tensor and pipeline parallel can linearly reduce those.. but what about activations?
[Korthikanti et al 2022]

What’s the activation memory per layer?
Starting point: activation memory needed if storing everything
• The 5𝑎𝑠
ℎ  terms come from the quadratic attention terms incl dropout
• As with flash attention, we can drop this term via recomputation

Activation under tensor parallel
Tensor parallel splits out the matrix multiplies in attention + MLP
The remaining 10 term is for the LayerNorm  (4sbh), Dropout (2sbh), and inputs to the 
attention and MLP (4sbh). These terms alone will continue to grow with size

Making memory truly linear – sequence parallel
Observation: all the 10sbh terms are pointwise ops over the sequence
 … so split up the layer norm/dropout layers along the sequence axis. 
• In the forward pass, ‘ 𝑔’ is an all gather, ‘ ത𝑔’ is reduce -scatter
• In the backward pass, the two are reversed.

Making activation memory fully scale with more machines
Putting it together to get full linear scaling for memory.

Other parallelism strategies
Context parallel / Ring attention 
(split activations across GPUs 
in a long sequence)
Expert parallel 
(split experts across GPUs)

Recap: LLM parallelism table..
What are each of the parallelism primitives good for?
Sync 
overhead
Memory Bandwidth Batch size Easy to 
use?
DDP/ZeRO1 Per-batch No 
scaling
2* # param Linear Very
FSDP 
(ZeRO3)
3x Per-FSDP 
block
Linear 3 * # param Linear Very
Pipeline Per-pipeline Linear Activations Linear NO
Tensor+seq 2x transformer 
block
Linear 8*activations per-
layer all-reduce
No impact No
Have to balance limited resource – memory, bandwidth, batch size

Model vs Tensor parallel (TPU book)
Key quantity
Global batch size (divided by GPU)
