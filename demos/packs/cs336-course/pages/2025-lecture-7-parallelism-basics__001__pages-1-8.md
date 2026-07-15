# 2025 Lecture 7 - Parallelism basics — pages 1-8

- page_id: `2025-lecture-7-parallelism-basics__001__pages-1-8`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

Lecture 7
CS336
T atsuH
PA R A L L E L I S M B A S I C S

Outline and goals
• Understand the systems complexities of training huge models
• Different parallelization paradigms and why people use multiple at once
• What large scale training runs often look like

Organization today:
❖ Part 1: Basics of networking for LLMs
❖ Part 2: Different forms of parallel LLM training
❖ Part 3: Scaling and training big LMs with parallelism

Limits to GPU-based scaling – compute 
There are limits to single -GPU scaling. 
The word’s fastest supercomputers have exaflops of compute

Limits to GPU-based scaling - memory
Models are getting really big..
A single GPU can’t fit most of these large models!

What do we do? Multi-GPU, multi-machine parallelism
Intra-node parallelism 
via high -speed interconnects High-speed inter -node parallelism
Split up memory and compute requirements across GPUs and machines

But first.. Some basics about collective communication
All reduce
Broadcast
Reduce
All Gather
Reduce Scatter

Important detail – all reduce vs reduce-scatter-gather.
Reduce can be implemented as two steps: reduce -scatter and all -gather
Importantly, in the bandwidth -limited regime, this is the best you can do
