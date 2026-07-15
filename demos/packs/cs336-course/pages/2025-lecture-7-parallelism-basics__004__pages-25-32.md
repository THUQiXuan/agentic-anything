# 2025 Lecture 7 - Parallelism basics — pages 25-32

- page_id: `2025-lecture-7-parallelism-basics__004__pages-25-32`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

ZeRO in practice: will it fit?
Pure BF16 training (with Kahan summation), is viable and optimizer states are less 
beefy. Let’s say BF16 for everything but the master weights – 12 bytes per param
On a 8X A100 80G..
Max size (params) Formula for B/param
Baseline 6.66.. B 12
Zero stage 1 16 B 5
Zero stage 2 24.62 B 2 (param) + (10 
(grad+state))/8) 
Zero stage 3 53.33 B 12/8

Issues remain with data parallel – compute scaling
With data parallel , #machines < batch size (and near this, comm overhead is high)
And there’s diminishing returns to batch sizes

Issues remain with data parallel – models don’t fit
Zero stages 1 and 2 don’t let you scale memory
Zero stage 3 is nice in principle, but can be slow and does not reduce activation memory
Better ways to split up the model is needed…

Beyond data parallel – model parallelism
Scaling up in memory (without changing batch size) with model parallelism
What model parallelism is..
• It splits up the parameters across GPUs (like zero3).. 
• But communicate activations (while zero3 sends params).
We cover two different types of parallelism
1. Pipeline parallel
2. Tensor parallel (+ Sequence parallel)
These correspond to two different ways of cutting up the model.

Layer-wise parallel
Layer-wise parallel cuts up layers, assigns some subset to GPUS.
Activations and partial gradients are passed back and forth

What’s wrong with layer-wise parallel
Utilization of layer -wise parallelism is terrible.. 
With n gpus, each gpu is active 1
n of the time.
Each GPU is idling most of the time, waiting for the backward pass to propagate back

A solution: pipeline parallel
Solution: Pipeline -parallel.
Process ‘micro -batches’ (in this case, 4). 
Send off the first microbatch  and start computing the second. 
The ratio of bubble time to useful compute is .. 
𝑛𝑠𝑡𝑎𝑔𝑒𝑠−1
𝑛𝑚𝑖𝑐𝑟𝑜
 so we need a big batch size!

Why pipeline parallel?
Pipelines seem terrible. Why do we do it?
1. Pipelines save memory (compared to DDP)
2. Pipelines can have good communication properties (compared to FDSP) – it 
depends only on activations ( 𝑏 × 𝑠 × ℎ) and is point to point
 
Generally, we will use pipelines on slower network links (i.e. inter -node) as a way to get 
better memory -wise scaling.
