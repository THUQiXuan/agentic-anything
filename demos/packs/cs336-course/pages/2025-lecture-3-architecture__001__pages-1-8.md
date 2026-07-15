# 2025 Lecture 3 - architecture — pages 1-8

- page_id: `2025-lecture-3-architecture__001__pages-1-8`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf
- type: segment

## Content

Lecture 3
CS336
T atsuH
E V E R Y T H I N GYO U D I D N’ T W A N T TO K N O W A B O U T
L M  A R C H I T E C T U R EA N D T R A I N I N G

Logistics
❖ Join the slack! 
❖ Check to make sure you have the latest version of the assignment!

Outline and goals
❖ Quick recap of the ‘standard’ transformer (what you implement)
❖ What do most of the large LMs have in common?
❖ What are common variations to the architecture / training process?
Today’s theme: the best way to learn is hands-on experience
the second best way is to try to learn from others’ experience

Starting point: the ‘original’ transformer
Review: choices in the standard transformer
Position embedding: sines and cosines
FFN: ReLU
Norm type: post-norm, LayerNorm

What you implemented – simple, modern variant
Differences:
•  LayerNorm  is in front of the block
• Rotary position embeddings ( RoPE)
• FF layers use SwiGLU , not ReLU
•  Linear layers (and layernorm ) have no 
bias (constant) terms
Why did we pick these?
What should you pick?

How should we think about architectures?
Lots of architecture. Just in the last year since last 336..
Over 19 new dense model releases, many of them with minor architecture tweaks..

Let’s look at the data (on dense architectures)
Learn from the many other models (and papers) out there
We will talk through many major 
architecture and hyperparameter variants. 
• What do all these models have in common? 
• What parts vary? 
• What can we learn from this?

What are we going to cover?
Common architecture variations
• Activations, FFN
• Attention variants
• Position embeddings
Hyperparameters that (do or don’t) matter
• What is ff_dim ? Do multi_head  dims always sum to model_dim ? 
• How many vocab elements? 
Stability tricks
