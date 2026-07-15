# 2025 Lecture 7 - Parallelism basics — pages 57-60

- page_id: `2025-lecture-7-parallelism-basics__008__pages-57-60`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf
- type: segment

## Content

Llama3 405B
(Stage 1, small bsz training, Stage 2 pretraining, Stage 3 long-context)

Llama 3 405B
Side note – Lots of GPU failures at this scale!

Gemma 2
For 2, 9, 27B models
ZeRO-3, MP (=TP+SP), DP

Recap for the whole lecture
❖ Scaling beyond a certain point requires multi -gpu, multi -node parallelism 
❖ No single solution to the parallelism problem (probably want all 3 approaches)
❖ Simple, interpretable rules of thumb for combining different forms of parallelism
