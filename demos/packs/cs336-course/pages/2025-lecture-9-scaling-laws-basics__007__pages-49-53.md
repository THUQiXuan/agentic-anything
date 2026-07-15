# 2025 Lecture 9 - Scaling laws basics — pages 49-53

- page_id: `2025-lecture-9-scaling-laws-basics__007__pages-49-53`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf
- type: segment

## Content

Fun addendum – errors in chinchilla method 3
Note that this method three was likely flawed in the original paper. Some authors did 
data forensics, recovered the raw data, and re -did the fit and got results more 
consistent with methods 1 and 2
[Besiroglu et al 2024]

Important note – train-optimal may not be what you want
Chinchilla  aims to tell you what gives the best model for fixed training compute..
 But most of the compute in a real deployment is inference.. So we should ‘over’ train
• GPT3 – 2 tokens / param
• Chinchilla  – 20 tokens / param
• LLaMA65B  – 22 tokens / param
• Llama 2 70B  – 29 tokens / param
• Mistral 7B  – 110 tokens / param
• Llama 3 70B – 215 tokens / param
The more usage we expect, the more it becomes worth it to pay the upfront cost

Recent example for different (diffusion) models 
Gulrajani + 2023.
Methods like IsoFLOPS  are pretty easy to execute, and our group has replicated these results

Scaling laws for models and compute
Log-linearity extends to model parameters and compute!
Lets us set the following based on small models
- Pick optimizer
- Pick architecture and model sizes
Also lets us make smart resource tradeoffs
- Big models vs more data?

Recap: scaling laws – surprising and useful!
- Data scaling : understand how data affects models, clean theory
- Model scaling : dramatically reduce costs for training 
- Scaling as prediction: understand what problems can be ‘brute forced’
