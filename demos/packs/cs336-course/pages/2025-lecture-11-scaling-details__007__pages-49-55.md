# 2025 Lecture 11 - Scaling details — pages 49-55

- page_id: `2025-lecture-11-scaling-details__007__pages-49-55`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf
- type: segment

## Content

What is muP robust to? Batch size 
Larger and smaller batches. 
The original derivation doesn’t handle batch size considerations.

What is muP robust to? initialization
There are new initializations that are sometimes used
• SP Unembedding – This is the pre -softmax  linear layer. 1/M (SP) vs 1/M^2 ( muP)
• Zero Query – Set the query matrix to zero (so that all items get uniform attention)

What is muP not robust to? RMSnorm gain
In our arch – RMSNorm  has learnable gains. This turns out to break muP
But these gains can be removed with little loss of perf..

What is muP not robust to? Exotic optimizers
There are other, exotic optimizers based on just gradient signs. Do they transfer?

What is muP not robust to? – (strong) weight decay 
What about strong (0.1) weight decay? – this is maybe the only significant muP failure

Is muP useful? At least to some extent..
Overall, muP generally seems useful – insofar that SP is quite a bit more unstable.
Current evidence suggests that muP parametrization / initialization may be easier to tune.

Recap: scaling in the wild
What are challenges in scaling ‘in practice’
1. Setting model arch hyperparameters ( width, etc)
2. Setting optimizer hyperparameters (LR, batch)
3. Compute needed to fit the big chinchilla sweep
Some solutions?
1. Assume stability (or use muP)
2. Search for optimal LR / batch in small scale, either keep fixed or predict scaling
3. Use alternative learning schedules (WSD -like)
