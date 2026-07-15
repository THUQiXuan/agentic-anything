# 2025 Lecture 3 - architecture — pages 65-68

- page_id: `2025-lecture-3-architecture__009__pages-65-68`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

Sparse / sliding window attention
Attending to the entire context can be expensive (quadratic). 
Build sparse / structured attention that trades off expressiveness vs runtime (GPT3)
[Child et al 2019]

Sliding window attention
Another variation on this idea – sliding window attention
Just use the main part of the strided  pattern – let depth extend effective context (Mistral)

Current standard trick – interleave ‘full’ and ‘LR’ attention
From Cohere Command A – Every 4 th layer is a full attention
Long-range info via NoPE, short -range info via RoPE + SWA.
Other models – LLaMA  4, Gemma does SWA+Full  RoPE.

Recap, conclusion, etc.
Many aspects (arch, hparams ) of transformers are in common across the big LMs
Major differences? Position embeddings, activations, tokenization
