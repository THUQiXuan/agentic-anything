# 2025 Lecture 5 - GPUs — pages 1-8

- page_id: `2025-lecture-5-gpus__001__pages-1-8`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf
- type: segment

## Content

Lecture 5
CS336
T atsuH
G P US

Outline and goals
❖ Make CUDA and GPUs less magic
http s://www.thonking.ai/p/what -shapes-do-mat rix-multiplic at ions
 Dao et al, Flash At ten tion
Understand when GPUs get slow Understand how to make fast algorithms

Before we start..
Substantial credit goes to a few sources that I’d like to highlight..
Horace He’s blog
 CUDA Mode group
And other sources including https://nichijou.co/ , https://jonathan -hui.medium.com/

Organization today:
❖ Part 1: GPUs in depth – how they work and important parts
❖ Part 2: Understanding GPU performance
❖ Part 3: Putting it together – unpacking FlashAttention

Setting the stage: compute leads to predictable perf
Often times, compute leads to predictable performance gains  for language models
Faster hardware, better utilization, improved parallelization alone can drive progress (for now..)
Kaplan et al, Neural Scalin g Laws

How do we get compute scaling? Early on – Dennard scaing
But the traditional form of scaling ( Dennard scaling ) from 1980 -2000s has tapped out.
.. How do we feed LLMs’ insatiable appetite for compute?

Parallel scaling continues
Parallel scaling with GPUs has scaled > 1000x in 10 years. 
There is no LLM scaling without GPU scaling
Bill dally, HotChips keynote

How is a GPU different from a CPU?
CPUs optimize for a few, fast threads while GPUs optimize for many many threads
Many tiny compute units (ALUs). 
Much less support for branching (control, cache)
CPUs optimize for latency (each thread finishes quickly)
GPUs optimize for throughput (total processed data)
https://developer.nvidia.com/blog/cuda-refresher-reviewing-the-origins-of-gpu-computing/
