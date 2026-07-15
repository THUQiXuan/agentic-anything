# 2025 Lecture 4 - MoEs — pages 33-40

- page_id: `2025-lecture-4-moes__005__pages-33-40`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/98455ec198c9a88ec1ab2b1c4058662431b54ce3/nonexecutable/2025%20Lecture%204%20-%20MoEs.pdf
- type: segment

## Content

Training MoEs – the systems side
MoE routing allows for parallelism, but also some complexities
Modern libraries like MegaBlocks  (used in many open MoEs) use smarter sparse MMs

Fun side issue – stochasticity of MoE models
There was speculation that GPT -4’s stochasticity was due to MoE.. 
Why would a MoE have additional randomness?
Token dropping from routing happens at a batch level – this means that
other people’s queries can drop your token!

Issues with MoEs - stability
Solution: Use Float 32 just for the expert router (sometimes with an aux z -loss)
[Zoph 2022]

Z-loss stability for the router
What happens when we remove the z -loss?

Issues with MoEs – fine-tuning
Sparse MoEs can overfit on smaller fine -tuning data
Zoph et al solution – finetune non -MoE MLPs
 DeepSeek  solution – use lots of data 1.4M SFT

Other training methods - upcycling
Can we use a pre -trained LM to initialize a MoE?

Upcycling example - MiniCPM
Uses the MiniCPM  model ( topk=2, 8 experts, ~ 4B active params).
Simple MoE, shows gains from the base model with ~ 520B tokens for training

Upcycling example – Qwen MoE
Qwen MoE – Initialized from the Qwen 1.8B model top -k=4, 60 experts w/ 4 shared.
Similar architecture / setup to DeepSeekMoE , but one of the first (confirmed) upcycling successes
