# 2025 Lecture 9 - Scaling laws basics — pages 33-40

- page_id: `2025-lecture-9-scaling-laws-basics__005__pages-33-40`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf
- type: segment

## Content

3. Depth/Width: and other Transformer hypers
Do hyperparameters like the aspect ratio depend on scale?

4. Batch size: Critical batch size
Batch size – known to have strong diminishing returns past a certain point.
Critical batch = min number of examples for target loss / min number of steps for target loss

4. Batch size: critical batch size
The smaller the loss target,
The bigger the batch

4. Batch size: selecting the optimal batch
Q: as we increase both compute and model size, how should we scale training?
• Huge batches, same number of steps
• Fixed batches, more steps
Good news for data parallel processing (?)

5. Learning rates: muP and scale-aware LR choices
Yao et al 2024Yang et al 2022
If we naively scale up – optimal learning rate depends on scale.
We need scaling aware initialization and learning rate scaling

Caution – scaling behaviors can differ downstream
Thus far : scaling is predictable and depends mainly on parameters
Catch: downstream scaling can often be much less predictable
Tay et al 2023

Some surprising takeaways
The effect of hyperparameters on big LMs can be predicted before  training!
- Optimizer choice
- Model depth
-  Architecture choice
The scaling law based design procedure.
1. Train a few smaller models
2. Establish a scaling law (e.g. ADAM vs SGD scaling law)
3. Select optimal hyperparam  based on the scaling law prediction.

One important use of scaling laws
Q: Do we need more data or bigger models?
Clearly, lots of data is wasted on small models
Joint data -model scaling laws describe how the two relate
From Rosenfeld+ 2020, 
𝐸𝑟𝑟𝑜𝑟 = 𝑛−𝛼 + 𝑚−𝛽 + 𝐶
From Kaplan+ 2020
𝐸𝑟𝑟𝑜𝑟 = 𝑚−𝛼 + 𝑛−1 𝛽
Provides surprisingly good fits to model -data joint error.
