# 2025 Lecture 5 - GPUs — pages 25-32

- page_id: `2025-lecture-5-gpus__004__pages-25-32`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf
- type: segment

## Content

Low precision drives faster matrix multiplies
Lots of operations in modern GPUs are accelerated via low / mixed precision operations
Tensor cores
https://nvlab s.github.io/eccv2020-mixed-precision-tutorial/files/dusan_stosic-training-neural-networks-with-tensor-cores.pdf

Trick 2: Operator fusion
Think of a GPU like a factory – inputs come from a warehouse (memory) and is 
processed at a factory
https://horace.io/brrr_intro.html
Compute scales up, memory doesn’t

Operator fusion to minimize memory access
What if we have to do many operations? Shipping back and forth is somewhat silly
Fused kernel
Naïve (non-fused)

Example – sines and cosines
Computing sin2𝑥 + cos 2 𝑥 naively launches 5 CUDA kernels (back and forth)
https://towardsdatascience.com/how-pytorch-2-0-accelerates-deep-learning-with-operator-fusion-and-cpu-gpu-code-generation-35132a85bd26

Fusion example
All 5 pointwise operations can be fused into a single CUDA kernel call.
‘Easy’ fusions like this can be done automatically by compilers ( torch.compile )

Trick 3: recomputation
In backpropagation, we store the activations (yellow) and compute Jacobians (green)
[From cs221]

Storing (and retrieving) activations can be expensive!
Let’s say we stack 3 sigmoids  on top of each other. 
This is really terrible for perf – 8 mem read/writes, very low arithmetic intensity.
https://dev-discuss.pytorch.org/t/min-cut-optimal-recomputation-i-e-activation-checkpointing-with-aotautograd/467

Throw away the activations, re-compute them!
Throwing away computation can actually be optimal, w/ 5/8 th the memory accesses!
https://dev-discuss.pytorch.org/t/min-cut-optimal-recomputation-i-e-activation-checkpointing-with-aotautograd/467
