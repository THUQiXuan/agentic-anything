# 2025 Lecture 4 - MoEs — pages 25-32

- page_id: `2025-lecture-4-moes__004__pages-25-32`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/98455ec198c9a88ec1ab2b1c4058662431b54ce3/nonexecutable/2025%20Lecture%204%20-%20MoEs.pdf
- type: segment

## Content

RL for MoEs
RL via REINFORCE does work, but not so much better that it’s a clear win
(REINFORCE baseline approach, Clark et al 2020)
RL is the ‘right solution’ but gradient variances and complexity 
means it’s not widely used

Stochastic approximations
From Shazeer  et al 2017 – routing decisions are stochastic  with gaussian perturbations.
1. This naturally leads to experts that are a bit more robust. 
2. The softmax  means that the model learns how to rank K experts

Stochastic approximations
Stochastic jitter in Fedus  et al 2022. This does a uniform multiplicative perturbation for the 
same goal of getting less brittle experts. This was later removed in Zoph et al 2022

Heuristic balancing losses
Another key issue – systems efficiency requires that we use experts evenly..
The derivative with respect to 𝑝𝑖(𝑥) is 𝛼𝑁
𝑇2 σ 1𝑎𝑟𝑔𝑚𝑎𝑥 𝑝 𝑥 =𝑖, 
so more frequent use = stronger downweighting  
From the Switch Transformer [ Fedus  et al 2022]

Example from deepseek (v1-2)
Per-expert balancing – same as the switch transformer
Per-device balancing – the objective above, but aggregated by device.

DeepSeek v3 variation – per-expert biases
Set up a per -expert bias (making it more likely to get tokens) and use online learning
They call this ‘ auxiliary loss free balancing ’
(but the approach is not fully aux loss free..)

What happens when removing load balancing losses?

Training MoEs – the systems side
MoEs parallelize nicely – Each FFN 
can fit in a device
Enables additional kinds of parallelism
