# 2025 Lecture 9 - Scaling laws basics — pages 41-48

- page_id: `2025-lecture-9-scaling-laws-basics__006__pages-41-48`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf
- type: segment

## Content

Model-data joint scaling is accurate
From Rosenfeld – fit scaling exponents on small data, small models. Predict rest.
Trading off data size and model size: optimize 𝑛−𝛼+𝑚−𝛽 + 𝐶 with your costs.

Compute tradeoffs.
Q: what about other resources? Compute vs performance?
For a fixed compute budget…
Big model that’s undertrained vs small model that’s well trained?
Scaling laws let us navigate this tradeoff
[Kaplan+ 2021] [Brown+ 2020]

Caution – ‘Optimal’ scaling laws are hard to get
Rosenfeld, Kaplan both predict relationship of data, model and perf.
Chinchilla [Hoffman et al] argue these fits are quite off.
Hoffman+ 2022

Main difference – accounting for LR schedules

Chinchilla in depth – 3 methods
The chinchilla authors suggest 3 ways of fitting scaling laws – we’ll go over each.
They mostly (minus method 3) suggest similar constants. More on this later..

Method 1 – minimum over runs.
Similar to the FLOPS figure on Kaplan – 
the minimum over the union of all training curves is a power law.

Method 2 - IsoFLOPS
Pick a range of FLOP budgets, vary the total parameter count, take the min over these 
convex shapes. The minima form a power law.

Method 3 – Joint fits
Run a bunch of models on the size -data grid. Use least squares to fit a joint scaling law
