# 2025 Lecture 7 - Parallelism basics — pages 49-56

- page_id: `2025-lecture-7-parallelism-basics__007__pages-49-56`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

‘3D parallelism’ – putting it all together
Simple rules of thumb from the literature.
1. Until your model fits in memory..
• Tensor parallel up to GPUs / machine
• Pipeline parallel across machines
› (Or use Zero-3, depending on BW)
2. Then until you run out of GPUs
• Scale the rest of the way with data parallel
If your batch size is small.. gradient accumulate to trade higher 
batch sizes for better communication efficiency.

Scaling strategies from Narayanan 2021
Notes
- Tensor parallel first up to 8, then caps out at 8. 
- Pipeline parallel goes up to make the model fit. 
- Dara parallel gradually decreases with scale, with the largest model having DP=6
32
32
32
32
32
32
24
15
9
6
DP size

Careful ‘3D’ parallelism gives linear gains
More GPUS, same, flat utilization!

Tensor parallel = 8 is often optimal
When parallelizing across 64 machines – it’s best to use a 8 x 8 configuration.

Activation recomputation can pay for itself (via memory)
Activation recomputation  enables larger batches, improving throughput (t=8, p=16)

Recent LMs – what do they do?
Dolma  – 7B model, FDSP (probably fits intra -node)

DeepSeek
DeepSeek – ZeRO stage 1 with Tensor, Sequence, and Pipeline parallel
V3 – PP (16), EP (64 -way, 8 nodes), ZeRO stage 1

Yi 
Yi - ZeRO stage 1 + Tensor + Pipeline parallel
Yi-lightning (2025) – Tensor replaced by Expert parallelism
