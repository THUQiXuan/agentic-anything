# Stanford CS336 | Language Modeling from Scratch (2025)

- page_id: `spring2025`
- url: https://cs336.stanford.edu/spring2025
- type: content
- description: Archived course website for Stanford CS336: Language Modeling from Scratch (Spring 2025), including schedule, assignments, logistics, and materials.

## Content

- Coursework

- Schedule

## CS336: Language Modeling from Scratch

Stanford / Spring 2025

This is the archived website for the Spring 2025 offering of CS336. The latest offering is here.

### Course Staff

Instructor

Instructor

### Logistics

- Lectures: Tuesday/Thursday 3:00-4:20pm in NVIDIA Auditorium

- Office hours:

- Tatsu Hashimoto (Gates 364): Fridays at 3-4pm

- Percy Liang (Gates 350): Fridays at 11am-12pm

- Marcel Rød (Gates 415): Mondays 11am-12pm, Wednesdays 11am-12pm

- Neil Band (Gates 358): Mondays 4-5pm, Tuesdays 5-6pm

- Rohith Kuditipudi (Gates 358): Mondays 10-11am, Wednesdays 10-11am

- Contact: Students should ask all course-related questions in public Slack channels. All announcements will also be made in Slack. For personal matters, email cs336-spr2425-staff@lists.stanford.edu.

### Content

#### What is this course about?

Language models serve as the cornerstone of modern natural language processing (NLP) applications and open up a new paradigm of having a single general purpose system address a range of downstream tasks. As the field of artificial intelligence (AI), machine learning (ML), and NLP continues to grow, possessing a deep understanding of language models becomes essential for scientists and engineers alike. This course is designed to provide students with a comprehensive understanding of language models by walking them through the entire process of developing their own. Drawing inspiration from operating systems courses that create an entire operating system from scratch, we will lead students through every aspect of language model creation, including data collection and cleaning for pre-training, transformer model construction, model training, and evaluation before deployment.

#### Prerequisites

- Proficiency in Python

The majority of class assignments will be in Python. Unlike most other AI classes, students will be given minimal scaffolding. The amount of code you will write will be at least an order of magnitude greater than for other classes. Therefore, being proficient in Python and software engineering is paramount.

- Experience with deep learning and systems optimization

A significant part of the course will involve making neural language models run quickly and efficiently on GPUs across multiple machines. We expect students to be able to have a strong familiarity with PyTorch and know basic systems concepts like the memory hierarchy.

- College Calculus, Linear Algebra (e.g. MATH 51, CME 100)

You should be comfortable understanding matrix/vector notation and operations.

- Basic Probability and Statistics (e.g. CS 109 or equivalent)

You should know the basics of probabilities, Gaussian distributions, mean, standard deviation, etc.

- Machine Learning (e.g. CS221, CS229, CS230, CS124, CS224N)

You should be comfortable with the basics of machine learning and deep learning.

Note that this is a 5-unit class. This is a very implementation-heavy class, so please allocate enough time for it.

### Coursework

#### Assignments

- Assignment 1: Basics [leaderboard]

- Implement all of the components (tokenizer, model architecture, optimizer) necessary to train a standard Transformer language model.

- Train a minimal language model.

- Assignment 2: Systems [leaderboard]

- Profile and benchmark the model and layers from Assignment 1 using advanced tools, optimize Attention with your own Triton implementation of FlashAttention2.

- Build a memory-efficient, distributed version of the Assignment 1 model training code.

- Assignment 3: Scaling

- Understand the function of each component of the Transformer.

- Query a training API to fit a scaling law to project model scaling.

- Assignment 4: Data [leaderboard]

- Convert raw Common Crawl dumps into usable pretraining data.

- Perform filtering and deduplication to improve model performance.

- Assignment 5: Alignment and Reasoning RL

- Apply supervised finetuning and reinforcement learning to train LMs to reason when solving math problems.

- Optional Part 2: implement and apply safety alignment methods such as DPO.

All (currently tentative) deadlines are listed in the .

#### GPU compute for self-study

If you are following along at home, you can access GPU compute from a cloud provider to complete the assignments. Here are a few options (prices for a single H100 80GB GPU on June 6, 2025):

- RunPod: $1.99-$2.99/hour (RunPod Pricing)

- Lambda Labs: $2.49–$3.29/hour (Lambda Labs Pricing)

- Paperspace: $2.24/hour (Paperspace Pricing)

- Together: $2.85/hour, minimum 8 GPUs (Together Instant GPU Cluster Pricing)

For convenience and to save money, we recommend debugging correctness of your implementation on CPU first and then using GPU(s) (with the count recommended in the assignments) for completing training runs (A1, A4, A5) or benchmarking GPU operations (A2).

#### Honor code

Like all other classes at Stanford, we take the student seriously. Please respect the following policies:

- Collaboration: Study groups are allowed, but students must understand and complete their own assignments, and hand in one assignment per student. If you worked in a group, please put the names of the members of your study group at the top of your assignment. Please ask if you have any questions about the collaboration policy.

- AI tools: Prompting LLMs such as ChatGPT is permitted for low-level programming questions or high-level conceptual questions about language models, but using it directly to solve the problem is prohibited. We strongly encourage you to disable AI autocomplete (e.g., Cursor Tab, GitHub CoPilot) in your IDE when completing assignments (though non-AI autocomplete, e.g., autocompleting function names is totally fine). We have found that AI autocomplete makes it much harder to engage deeply with the content.

- Existing code: Implementations for many of the things you will implement exist online. The handouts we'll give will be self-contained, so that you will not need to consult third-party code for producing your own implementation. Thus, you should not look at any existing code unless when otherwise specified in the handouts.

#### Submitting coursework

- All coursework are submitted via Gradescope by the deadline. Do not submit your coursework via email.

- If anything goes wrong, please ask a question in Slack or contact a course assistant.

- You can submit as many times as you'd like until the deadline: we will only grade the last submission.

- Partial work is better than not submitting any work.

#### Late days

- Each student has 6 late days to use. A late day extends the deadline by 24 hours.

- You can use up to 3 late days per assignment.

#### Regrade requests

If you believe that the course staff made an objective error in grading, you may submit a regrade request on Gradescope within 3 days after the grades are released.

#### Sponsor

We would like to thank Together AI for sponsoring the compute for this class.

### Schedule

Date

Description

Course Materials

Deadlines

Tues April 1

Overview, tokenization (Percy)

lecture_01.py

Assignment 1 out [code] [preview] [leaderboard]

Thurs April 3

PyTorch, resource accounting (Percy)

lecture_02.py

Tues April 8

Architectures, hyperparameters (Tatsu)

lecture 3.pdf

Thurs April 10

Mixture of experts (Tatsu)

lecture 4.pdf

Tues April 15

GPUs (Tatsu)

lecture 5.pdf

Assignment 1 due Assignment 2 out [code] [preview] [leaderboard]

Thurs April 17

Kernels, Triton (Tatsu)

lecture_06.py

Tues April 22

Parallelism (Tatsu)

lecture 7.pdf

Thurs April 24

Parallelism (Percy)

lecture_08.py

Tues April 29

Scaling laws (Tatsu)

lecture 9.pdf

Assignment 3 out [code] [preview]

Wed April 30

Assignment 2 due

10

Thurs May 1

Inference (Percy)

lecture_10.py

11

Tues May 6

Scaling laws (Tatsu)

lecture 11.pdf

Assignment 3 due Assignment 4 out [code] [preview] [leaderboard]

12

Thurs May 8

Evaluation (Percy)

lecture_12.py

13

Tues May 13

Data (Percy)

lecture_13.py

14

Thurs May 15

Data (Percy)

lecture_14.py

15

Tues May 20

Alignment - SFT/RLHF (Tatsu)

lecture 15.pdf

16

Thurs May 22

Alignment - RL (Tatsu)

lecture 16.pdf

Fri May 23

Assignment 4 due Assignment 5 out [code] [preview]

17

Tues May 27

Alignment - RL (Percy)

lecture_17.py

18

Thurs May 29

Guest Lecture by Junyang Lin

19

Tues June 3

Guest lecture by Mike Lewis

Fri June 6

Assignment 5 due

## Links

- [CS336](https://cs336.stanford.edu/spring2025/index.html) (nav)
- [Coursework](https://cs336.stanford.edu/spring2025/#coursework) → `spring2025` (nav)
- [Schedule](https://cs336.stanford.edu/spring2025/#schedule) → `spring2025` (nav)
- [Stanford Natural Language Processing Group logo](https://nlp.stanford.edu/)
- [Stanford Center for Research on Foundation Models logo](https://crfm.stanford.edu)
- [here](https://cs336.stanford.edu/)
- [Tatsunori Hashimoto headshot Tatsunori Hashimoto](https://thashim.github.io/)
- [Percy Liang headshot Percy Liang](https://cs.stanford.edu/~pliang/)
- [Neil Band headshot Neil Band](https://nband.github.io/)
- [Marcel Rod headshot Marcel Rød](https://marcel.roed.me)
- [Rohith Kuditipudi headshot Rohith Kuditipudi](https://web.stanford.edu/~rohithk/)
- [NVIDIA Auditorium](https://campus-map.stanford.edu/?srch=NVIDIA+Auditorium)
- [cs336-spr2425-staff@lists.stanford.edu](mailto:cs336-spr2425-staff@lists.stanford.edu)
- [Assignment 1 : Basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)
- [leaderboard](https://github.com/stanford-cs336/assignment1-basics-leaderboard/tree/master)
- [Assignment 2 : Systems](https://github.com/stanford-cs336/assignment2-systems/tree/main)
- [leaderboard](https://github.com/stanford-cs336/assignment2-systems-leaderboard/tree/main)
- [Assignment 3 : Scaling](https://github.com/stanford-cs336/assignment3-scaling/tree/main)
- [Assignment 4 : Data](https://github.com/stanford-cs336/assignment4-data/tree/main)
- [leaderboard](https://github.com/stanford-cs336/assignment4-data-leaderboard)
- [Assignment 5 : Alignment and Reasoning RL](https://github.com/stanford-cs336/assignment5-alignment)
- [Optional Part 2](https://github.com/stanford-cs336/assignment5-alignment/blob/main/cs336_spring2025_assignment5_supplement_safety_rlhf.pdf)
- [schedule](https://cs336.stanford.edu/spring2025/#schedule) → `spring2025`
- [RunPod](https://docs.runpod.io/get-started)
- [RunPod Pricing](https://runpod.io/pricing)
- [Lambda Labs](https://docs.lambda.ai/public-cloud/on-demand/creating-managing-instances/#launching-instances)
- [Lambda Labs Pricing](https://lambda.ai/pricing)
- [Paperspace](https://docs.digitalocean.com/products/paperspace/deployments/getting-started/quickstart/)
- [Paperspace Pricing](https://www.paperspace.com/pricing)
- [Together](https://www.together.ai/blog/instant-gpu-clusters)
- [Together Instant GPU Cluster Pricing](https://www.together.ai/blog/instant-gpu-clusters)
- [Honor Code](https://ed.stanford.edu/academics/masters-handbook/honor-code)
- [Together AI](https://together.ai)
- [lecture_01.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_01.json) → `spring2025-lectures__q_59ae59be`
- [code](https://github.com/stanford-cs336/assignment1-basics/tree/main)
- [preview](https://github.com/stanford-cs336/assignment1-basics/blob/main/cs336_spring2025_assignment1_basics.pdf)
- [leaderboard](https://github.com/stanford-cs336/spring2025-assignment1-basics-leaderboard/tree/master)
- [lecture_02.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_02.json) → `spring2025-lectures__q_f5c60497`
- [lecture 3.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/e9cb2488fdb53ea37f0e38924ec3a1701925cef3/nonexecutable/2025%20Lecture%203%20-%20architecture.pdf)
- [lecture 4.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/98455ec198c9a88ec1ab2b1c4058662431b54ce3/nonexecutable/2025%20Lecture%204%20-%20MoEs.pdf)
- [lecture 5.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/main/nonexecutable/2025%20Lecture%205%20-%20GPUs.pdf)
- [code](https://github.com/stanford-cs336/assignment2-systems/tree/main)
- [preview](https://github.com/stanford-cs336/assignment2-systems/blob/main/cs336_spring2025_assignment2_systems.pdf)
- [leaderboard](https://github.com/stanford-cs336/assignment2-systems-leaderboard/tree/main)
- [lecture_06.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_06.json) → `spring2025-lectures__q_0a2f1484`
- [lecture 7.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/4eff81bee0a853217209e163936b264f03572b66/nonexecutable/2025%20Lecture%207%20-%20Parallelism%20basics.pdf)
- [lecture_08.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_08.json) → `spring2025-lectures__q_8451f641`
- [lecture 9.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/fb79eb018fa047bf99c4c785dcbbd62fff361e54/nonexecutable/2025%20Lecture%209%20-%20Scaling%20laws%20basics.pdf)
- [code](https://github.com/stanford-cs336/assignment3-scaling/tree/main)
- [preview](https://github.com/stanford-cs336/assignment3-scaling/blob/main/cs336_spring2025_assignment3_scaling.pdf)
- [lecture_10.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_10.json) → `spring2025-lectures__q_d665f0c2`
- [lecture 11.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/00191bba00d6d64621dc46ccaed9122681413a24/nonexecutable/2025%20Lecture%2011%20-%20Scaling%20details.pdf)
- [code](https://github.com/stanford-cs336/assignment4-data/tree/main)
- [preview](https://github.com/stanford-cs336/assignment4-data/blob/main/cs336_spring2025_assignment4_data.pdf)
- [leaderboard](https://github.com/stanford-cs336/assignment4-data-leaderboard)
- [lecture_12.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_12.json) → `spring2025-lectures__q_24e05133`
- [lecture_13.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_13.json) → `spring2025-lectures__q_cc6050c6`
- [lecture_14.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_14.json)
- [lecture 15.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/61eddac004df975466cff0329b615f2d24230069/nonexecutable/2025%20Lecture%2015%20-%20RLHF%20Alignment.pdf)
- [lecture 16.pdf](https://github.com/stanford-cs336/spring2025-lectures/blob/e94e33f433985e57036b25215dff2a4292e67a4f/nonexecutable/2025%20Lecture%2016%20-%20RLVR.pdf)
- [code](https://github.com/stanford-cs336/assignment5-alignment)
- [preview](https://github.com/stanford-cs336/assignment5-alignment/blob/master/cs336_spring2025_assignment5_alignment.pdf)
- [lecture_17.py](https://cs336.stanford.edu/spring2025-lectures/?trace=var/traces/lecture_17.json)
- [Junyang Lin](https://justinlin610.github.io/)
- [Mike Lewis](https://ai.meta.com/people/209431298931133/mike-lewis/)

## Images

- Stanford Natural Language Processing Group logo: https://cs336.stanford.edu/assets/images/stanford-nlp-logo-new.jpg
- Stanford Center for Research on Foundation Models logo: https://cs336.stanford.edu/assets/images/crfm-rgb.png
- Tatsunori Hashimoto headshot: https://cs336.stanford.edu/assets/images/thashim.jpeg
- Percy Liang headshot: https://cs336.stanford.edu/assets/images/pliang.jpeg
- Neil Band headshot: https://cs336.stanford.edu/assets/images/nband.jpg
- Marcel Rod headshot: https://cs336.stanford.edu/assets/images/mroed.jpg
- Rohith Kuditipudi headshot: https://cs336.stanford.edu/assets/images/rohithk.jpg
