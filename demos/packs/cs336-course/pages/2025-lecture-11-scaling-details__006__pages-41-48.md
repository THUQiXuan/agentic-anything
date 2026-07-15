# 2025 Lecture 11 - Scaling details — pages 41-48

- page_id: `2025-lecture-11-scaling-details__006__pages-41-48`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf
- type: segment

## Content

Deriving muP (condition A2) part 2
Recall – we want all 3 terms of Δhl = WlΔℎ𝑙−1 + Δ𝑊𝑙(ℎ𝑙−1 + Δℎ𝑙−1) to be Θ( 𝑛𝑙)
And the key is to pick LR such that Δ𝑊𝑙 ∗ 𝑛𝑙−1 = Θ 𝑛𝑙 . How can we do that?
Suppose that the loss update also scales O(1). Then we can write down..
Δℓ = Θ Δ𝑊𝑙, ∇𝑊𝑙ℓ = Θ Δ𝑊𝑙 𝐹 ∇𝑊𝑙ℓ 𝐹 = Θ Δ𝑊𝑙 ∗ ∇𝑊𝑙ℓ ∗
Where we use the fact that Δ𝑊𝑙 = −𝜂∇𝑊𝑙ℓ in standard SGD updates. 
Now plug in Δℓ = O 1 , Δ𝑊𝑙 ∗ = Θ 𝑛𝑙
𝑛𝑙−1 to get that ∇𝑊𝑙ℓ ∗ = Θ 𝑛𝑙−1
𝑛𝑙
Finally, from the previous slide, recall that Δ𝑊𝑙 = −𝜂𝑙∇ℎ𝑙ℓ ℎ𝑙−1
⊤  and thus
𝜂𝑙 = Θ 𝑛𝑙
𝑛𝑙−1
 
[with Adam, Δ𝑊𝑙 ∗ 𝑛𝑙−1 = Θ 1 ]

muP mini recap..
So, what is (baby) muP about? Controlling activations (and changes) via 𝑊 and Δ𝑊
Initialization: Set to Θ 1
𝑛𝑙−1
min 1, 𝑛𝑙
𝑛𝑙−1
Learning rates: Set to 𝑛𝑙
𝑛𝑙−1
Compared to ‘standard’ parametrizations – these set  
Initialization: Set to 1
𝑛𝑙−1
 
Learning rates: Set to Θ(1)
Differences – LR changes for Adam, also init diffs when fanout 𝑛𝑙 < fanin
(for Adam 1
nl−1
)

Implementation in Cerebras GPT
We now have the background to follow cerebrasGPT

Deeper dive into muP
Recall – muP is a scaling procedure for hyperparams  (as a function of width)
Attention params
Embedding
Input/output MLP MM
Softmax linear

Scaling protocol in the work
Architecture – mostly similar to what’s in the class
Important limitation of the work: only width scaling

Replicating muP
Q1: Does muP work as claimed? When we scale widths, is optimal LR constant?

What is muP robust to?
Modern LMs have many components that deviate from muP’s  theory
• Activations – SwiGLU  and squared relu
• Batch sizes – Large / small 
• Initialization variations – zero attention, etc.
• RMS norm gains
• Exotic optimizers (Lion)
• Regularizers
Which of these (if any) break muP?

What is muP robust to? Nonlinearities
SwiGLU , Squared ReLU have the same optimal LR (and both provide minor gains)
