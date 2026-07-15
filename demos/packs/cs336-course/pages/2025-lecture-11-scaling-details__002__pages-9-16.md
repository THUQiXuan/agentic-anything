# 2025 Lecture 11 - Scaling details — pages 9-16

- page_id: `2025-lecture-11-scaling-details__002__pages-9-16`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf
- type: segment

## Content

Setting the empirical values
muP is combined with aggressive scaling for hyperparameter optimization.
Generally stable hyperparameters.

MiniCPM
MiniCPM  (2024) – new small, high -perf LM from Tsinghua group.
Careful, extensive scaling computations + muP to stabilize and simplify scaling

MiniCPM
High performance 1 -2.5 B parameter models. These models beat most out 2Bs and 
match many modern 7B models.

Techique 1: muP to stabilize scaling
Scale_emb  = 12, scale_depth  = 1.4, init_std  = 0.1, lr =0.01
c.f. CerebrasGPT – Scale_emb = 10, lr=6e-3, init_base = 0.08

Scaling recipe / strategy
Use muP for initialization, fix the aspect ratio, scale up the overall model size.
Note that the gap between the largest model here and the actual model they train is ~5x
Optimal batch, LR, token -to-size ratios are directly fitted via scaling analysis

Optimal batch
Three model sizes (9m, 30m, 170m) as a function of data size (y), batch (x) and loss (col)
Vertical columns of points represent a single training curve (fixed batch, more points).
Red line attempts to identify minimum loss points for each y -value 
– this is the ‘optimal batch size’ for a model size / dataset size combination.

Optimal batch size
We can then follow the Kaplan 2020 analysis and plot optimal batch size vs final loss.
Fairly clean trend – polynomially  increase the batch size as loss decreases.

Optimal LR 
According to muP – optimal learning rate should be (roughly) stable. Is it?
