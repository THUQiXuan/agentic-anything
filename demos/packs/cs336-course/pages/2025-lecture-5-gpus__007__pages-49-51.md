# 2025 Lecture 5 - GPUs — pages 49-51

- page_id: `2025-lecture-5-gpus__007__pages-49-51`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf
- type: segment

## Content

Tiling part 2: incremental computation of the softmax
From Mikailov  and Gimelshein  2018,
Normal softmax
Online softmax
To keep track of the max, incrementally update the max, and set up a telescoping sum
This lets you compute the softmax tile-by-tile

Putting it all together – the forward pass of flash attention
From Dao 2023, we see
• Tile-wise computation of the inner products,  ( 𝑆) 
• Fusion of the exponential operator
• Tile-wise computation of the softmax  via the online, telescoping sum trick
(We won’t cover the backward pass – but they recompute tile-by-tile..)

Recap for the whole lecture
❖ Hardware powers scale, and low -level details 
determine what scales or doesnt
❖ Curent  GPU based compute strongly 
encourages thinking about matmul  + data 
movement
❖ Thinking carefully about the GPU (coalescing, 
tiling, fusion) leads us to good performance
