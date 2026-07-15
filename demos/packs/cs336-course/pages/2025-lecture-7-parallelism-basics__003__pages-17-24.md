# 2025 Lecture 7 - Parallelism basics — pages 17-24

- page_id: `2025-lecture-7-parallelism-basics__003__pages-17-24`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

ZeRO stage 1. how it works
Step 1. Everyone computes a full gradient on their subset of the batch
Step 2. ReduceScatter  the gradients – incur #params communication cost
Step 3. Each machine updates their param using their gradient + state.
Step 4. All Gather the parameters – incur #params communication cost

Comparing ZeRO stage 1 and naïve data parallel
Naïve DDP ZeRO stage 1
Communication 
primitive
One all-reduce 
(gradients)
One reduce scatter (send 
gradients) + all gather 
(collect params)
Communication cost 2* # params 2* # params
Memory (4+K) * #params (4+K/Ngpu) * #params
ZeRO stage 1 is free (in the bandwidth limited regime) memory wins

ZeRO stage 2. the simple extension to gradient sharding
Emboldened by our success, let’s shard even more stuff
High level idea
• Also keep the gradients (pink slices) sharded across the machines. 
• Use the same (rough) tricks as stage 1.
Complexity  – we can never instantiate a full gradient vector, but each worker must 
compute a full gradient (since we’re data parallel)

ZeRO stage 2. how it works
Step 1. Everyone incrementally goes backward on the computation graph
 Step 1a. After computing a layer’s gradients, immediately reduce to send this to the 
right worker
 Step 1b. Once gradients are not needed in the backward graph, immediately free it.
Step 2. Each machine updates their param using their gradient + state.
Step 3. All Gather the parameters.

ZeRO stage 3 (aka FSDP) shard everything 
We’ve gotten almost everything for free so far.. lets try to solve all our memory issues
High level idea
• Shard everything – incl parameters!
• Use the same ‘incremental communication / computation’ ideas
• Send and request parameters on demand while stepping through the compute graph.
Is it possible to do this with low overhead?

ZeRO stage 3 (aka FSDP) how it works (baby version)
https://pytorch.org/tutorials/intermediate/FSDP_tutorial.html
Communication cost – 2 all gather (#param), 1 reduce-scatter (#param).

Actual picture of how FDSP / ZeRO stage 3 works
Let’s walk through a FSDP example to see some important ideas
Incremental computation / communication
• Parameters / gradients are requested / sent and then immediately freed
Overlapping communication and computation ( 𝑾𝟏𝑾𝟎 + 𝑾𝟐𝑾𝟎)𝒙 = 𝒚 
•  The all -gathers happen all at once while forward happens, masking the comm cost.
https://arxiv.org/pdf/2304.11277.pdf

What’s the point? 
Distributed data parallel costs 2*# param communication
What about ZeRO?
• Zero stage 1 is 2*# param – it’s free! – you might as well always do it
• Zero stage 2 is 2*# param – it’s (almost) free (ignoring overhead)
• Zero stage 3 is 3*# param – 1.5x comm cost, but that’s not bad! (ignoring latency..)
This is also conceptually very simple – write a FSDP block wrapper.
