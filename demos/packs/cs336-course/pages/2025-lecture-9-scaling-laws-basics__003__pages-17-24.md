# 2025 Lecture 9 - Scaling laws basics — pages 17-24

- page_id: `2025-lecture-9-scaling-laws-basics__003__pages-17-24`
- url: https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf
- type: segment

## Content

Toy example: mean estimation
Input: 𝑥1  … 𝑥𝑛 ∼ 𝑁(𝜇, 𝜎2)
Task: estimate the average as ො𝜇 =
σ𝑖 𝑥𝑖
𝑛
What’s the error? By standard arguments..
 E ො𝜇 − 𝜇 2 = 𝜎2
𝑛  
This is a ‘scaling law’
log(𝐸𝑟𝑟𝑜𝑟 ) = −log 𝑛 + 2 log 𝜎
 More generally, any polynomial rate 1/𝑛𝛼 is a scaling law

Scaling law exponents: an intriguing mystery
Fact: Similar arguments show most ‘classical’ models (regression, etc) have 1
𝑛 scaling
This means we should see y = −𝑥 + 𝐶
What do we find in neural scaling laws?
Machine translation
 Speech
 Language modeling
Very different from predictions.. Why might this be?

Detour: scaling laws for (nonparametric) learning
Neural nets can approximate arbitrary functions. Lets turn that into an example.
Input : 𝑥1 … 𝑥𝑛 uniform in 2D unit box. 𝑦𝑖 = 𝑓 𝑥𝑖 + 𝑁(0,1)
Task: estimate f(x)
Approach : cut up the 2D space into boxes with length 𝑛−1
4
What’s our estimation error?
 Informally, we have 𝑛 boxes, each box gets 𝑛 samples.
𝐸𝑟𝑟𝑜𝑟 ≈ 1
𝑛 + 𝑜𝑡ℎ𝑒𝑟  𝑠𝑚𝑜𝑜𝑡ℎ𝑛𝑒𝑠𝑠  𝑡𝑒𝑟𝑚𝑠
In 𝑑-dimensions, this becomes 𝐸𝑟𝑟𝑜𝑟 = 𝑛−1/𝑑  - This means scaling is 𝒚 = − 𝟏
𝒅 𝒙 + 𝑪
Takeaway: flexible ‘nonparametric’ learning has dimension dependent scaling laws.

Intrinsic dimensionality theory of data scaling laws
Some have made the following argument ( Bahri 2021)
1. Scaling laws arise due to polynomial rates of learning 1
𝑛𝛼
2. Some argue the slope 𝛼 is closely connected to the intrinsic dimensionality  of the data.
But estimators of intrinsic dimension are sketchy, and this is not airtight..

Other data scaling laws
Data scaling thus far: how does dataset size relate to performance?
Related question: how does dataset composition affect performance
❖ Picking optimal data mixture using small scale models
❖ Deciding whether to repeat data or not
❖ Combing the two and balancing quality with repetition rate

Other advanced data scaling law: distribution shift
Data scaling thus far : how does dataset size relate to performance?
Related question : how does dataset composition affect performance
A: Data composition affects the offset, not the slope.
[Kaplan+ 2021]
These ‘distribution shift’ scaling laws can tell us about the importance of collecting diverse data!
[Hashimoto 2021]

Scaling laws under data repetition
In practice, we have finite data – how does repeating examples affect scaling?
D’ = Effective data
Ud = Unique tokens
Rd* = Constant
Rd = Repetition

Data selection scaling and accounting for finiteness
Given that repeated data is less valuable.. 
Data selection should then be adaptive to scale !
