
=== Page 1 ===
SEESAW: HIGH-THROUGHPUT LLM INFERENCE VIA MODEL RE-SHARDING
Qidong Su123 Wei Zhao34 Xin Li3 Muralidhar Andoorveedu3 Chenhao Jiang12 Zhanda Zhu123 Kevin Song12
Christina Giannoula123 Gennady Pekhimenko123
ABSTRACT
To improve the efficiency of distributed large language model (LLM) inference, various parallelization strategies,
such as tensor and pipeline parallelism, have been proposed. However, the distinct computational characteristics
inherent in the two stages of LLM inference—prefilling and decoding—render a single static parallelization
strategy insufficient for the effective optimization of both stages. In this work, we present Seesaw, an LLM
inference engine optimized for throughput-oriented tasks. The key idea behind Seesaw is dynamic model re-
sharding, a technique that facilitates the dynamic reconfiguration of parallelization strategies across stages, thereby
maximizing throughput at both phases. To mitigate re-sharding overhead and optimize computational efficiency,
we employ tiered KV cache buffering and transition-minimizing scheduling. These approaches work synergistically
to reduce the overhead caused by frequent stage transitions while ensuring maximum batching efficiency. Our
evaluation demonstrates that Seesaw achieves a throughput increase of up to 1.78× (1.36× on average) compared
to vLLM, the most widely used state-of-the-art LLM inference engine.
1
INTRODUCTION
Large language models (LLMs), such as the LLaMA (Tou-
vron et al., 2023a) and GPT (Achiam et al., 2023) families,
have demonstrated exceptional performance across a wide
range of tasks. Beyond their prevalent use in interactive
applications like chatbots (OpenAI, 2024), LLMs are also
gaining high interest in throughput-oriented offline inference
workloads such as information extraction (Narayan et al.,
2022), database querying (Liu et al., 2024), and knowledge
graph processing (Edge et al., 2024). Unlike interactive
applications where low latency is crucial, these offline in-
ference tasks prioritize high throughput over response time.
These offline inference workloads are widely adopted in in-
dustry (Kamsetty et al., 2023; Yu et al., 2024; Dell Technolo-
gies, 2024; Chan et al., 2024), leading MLPerf to develop
benchmarks specifically for them (MLCommons, 2024). In
this work, we focus on improving inference efficiency for
offline, throughput-oriented LLM inference workloads.
As LLMs often exceed the memory capacity of individual
GPUs, parallelization is essential for their deployment (Ben-
Nun & Hoefler, 2019; Shoeybi et al., 2019). Several paral-
lelization strategies, including tensor parallelism (Shoeybi
et al., 2019) and pipeline parallelism (Narayanan et al., 2019;
Huang et al., 2019), have been proposed, each presenting
distinct trade-offs in memory efficiency, inter-device com-
munication, and computational efficiency. Tensor paral-
lelism distributes model weights across devices but suffers
1 University of Toronto
2 Vector Institute
3 CentML
4 Stan-
ford University
TP1PP8
TP2PP4
TP4PP2
TP8PP1
0.00
0.25
0.50
0.75
1.00
Normalized Time
communication
compute
weight transfer
(a) Prefill
TP1PP8
TP2PP4
TP4PP2
TP8PP1
0.00
0.25
0.50
0.75
1.00
Normalized Time
communication
compute
weight transfer
(b) Decode
Figure 1. Breakdown of execution time for the prefill and decode
stages for LLaMA2-13B inference on 8 L4 GPUs (The global
batch size is 16. Pipeline parallelism further divides the data into
micro-batches of size 16/PP to fully utilize pipelining).
from high communication costs due to frequent all-reduce
operations at each layer (Pope et al., 2023; Chang et al.,
2024). The communication cost becomes particularly severe
in systems connected via PCIe (Dell Technologies, 2023) or
with partial high-speed connections (NVIDIA Corporation,
2020). In contrast, pipeline parallelism partitions the model
into sequential stages, reducing inter-device communica-
tion by passing only activations between them. However,
to enable pipelining, each data batch needs to be divided
into micro-batches, leading to extra execution overheads,
since every micro-batch repeatedly loads weights into the
compute units (see Section 3.1 for details).
While numerous studies have proposed methods to optimize
parallelization strategies for LLMs (Miao et al., 2023; Kwon
et al., 2023; Li et al., 2023; Pope et al., 2023), prior works
typically rely on a single, static configuration throughout
arXiv:2503.06433v1  [cs.DC]  9 Mar 2025

=== Page 2 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
the entire generation process. However, our findings indi-
cate that this one-size-fits-all approach is often inefficient
for throughput-oriented LLM inference because it fails to
leverage the distinct patterns between the two stages in LLM
generation: the prefill stage, where the input sequence is pro-
cessed at once to produce the initial token, and the decode
stage, where subsequent tokens are generated sequentially
based on prior tokens. These two stages exhibit fundamen-
tally different computational characteristics (Yuan et al.,
2024). During the prefill stage, multiple tokens from the
input prompt are processed simultaneously, making com-
putation and communication the dominant contributors to
runtime. In contrast, the decode stage processes one token at
a time for each sequence, increasing the relative time spent
on weight transfer. This difference indicates that the optimal
parallelization strategy for each stage may also vary.
To illustrate the performance limitations of applying a uni-
form parallelization strategy for both prefill and decode,
we measure the execution time of each stage under various
combinations of tensor and pipeline parallelism, as shown
in Figure 1. In the prefill stage, as the degree of tensor par-
allelism increases, the communication overhead increases
significantly due to additional GPUs participating in all-
reduce operations. As a result, tensor parallelism performs
significantly worse than pipeline parallelism. In contrast,
during the decode stage, pipeline parallelism is slower than
tensor parallelism, largely due to increased weight trans-
ferring overhead caused by micro-batching required for
pipelining (see Section 3.1 for more details). Therefore,
we need stage-specific parallelization strategies to provide
better LLM inference throughput.
An existing approach is disaggregated prefill-decode (Zhong
et al., 2024; Qin et al., 2024), which assigns prefill and de-
code computation to different GPU instances. The prefill
instances and decode instances form a two-stage pipeline
to serve inference requests. Therefore, the overall through-
put of disaggregated prefill-decode is constrained by the
slower of the two stages, and balancing throughput between
these two stages is essential. The key drawback of disag-
gregated prefill-decode is that it can cause large amounts of
pipeline bubbles under resource-constrained environments.
For example, when deploying a 70B model on 8×40GB
GPUs, even the most balanced configuration results in a
6× difference in throughput between the prefill and decode
stages. In this setup, the decode stage operates at one-sixth
the throughput of the prefill stage, resulting in a significant
bottleneck at the prefill stage that slows down the entire
system (see Section 3.2 for details).
To address these challenges, we present Seesaw, a high-
throughput LLM inference engine that dynamically recon-
figures parallelization strategies between the prefill and de-
code stages. The key idea behind Seesaw is model re-
time
GPU max #seqs
time
GPU max #seqs
time
CPU max #seqs
#seqs
#seqs
#seqs
under-utilize
too frequent transitions
(a) Prefill-prioritizing
(b) Decode-prioritizing
(c) Tiered KV cache buffering 
    + transition-minimizing scheduling
p
d
p
d
p
d
p
d
p
d
p
d
p
d
p
d
GPU max #seqs
p
d
p
d
p
Figure 2. Different scheduling policies considering transition over-
head. Decoding throughput is positively correlated with the num-
ber of sequences in GPU memory (the maximal batch size), which
is highlighted as light green area.
sharding, a novel technique that dynamically re-partitions
model weights and KV cache 1 between prefill and decode
stages. By tailoring parallelization strategies to the dis-
tinct computational demands of each stage, Seesaw reduces
communication overhead during the prefill stage, while en-
hancing memory efficiency in the decode stage, resulting in
a substantial increase in overall throughput.
However, the overhead associated with model re-sharding
can be high due to frequent transitions between prefill and
decode. To maximize throughput, existing systems typi-
cally adopt prefill-prioritized scheduling (Yu et al., 2022;
Kwon et al., 2023), which interleaves prefill and decode
stages across batches to achieve continuous batching. Yet,
as illustrated in Figure 2(a), integrating this approach with
model re-sharding can result in significant overhead due
to frequent transitions between prefill and decode. On the
other hand, decode-prioritized scheduling (NVIDIA, 2024a)
completes all decode steps for a batch before proceeding to
the next, resulting in lower re-sharding overhead. However,
as depicted in Figure 2(b), this method suffers from low
resource utilization due to smaller batch sizes.
To overcome this constraint and achieve both minimal
re-sharding overhead and large batch size, we propose
two synergetic techniques: tiered KV cache buffering
and transition-minimizing scheduling. Tiered KV cache
buffering leverages CPU memory as auxiliary storage for
the KV cache, enabling Seesaw to store the KV cache for
a large number of prefill requests. Transition-minimizing
scheduling reduces re-sharding overhead by minimizing the
number of transitions to the decode stage. Seesaw transi-
tions from prefill to decode only after the CPU KV cache is
full. During decoding, the large number of KV cache in the
CPU buffer enables Seesaw to perform decode with large
batch sizes, and thus enabling high throughput. As depicted
1 The tensors cached for each sequence’s decoding steps.

=== Page 3 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
in Figure 2(c), this approach maintains the maximal batch
size during the decode stage, while significantly reducing
the frequency of stage transitions, thereby minimizing re-
sharding overhead. Additionally, to mitigate the overhead
of KV cache transfers between CPU and GPU, Seesaw em-
ploys asynchronous pipelining to overlap data transfers with
computation.
In summary, we make the following contributions.
• We identify and quantitatively analyze the different pref-
erences for parallelisms in the prefill and decode stages of
throughput-oriented LLM inference tasks. Our analysis
comprehensively accounts for data movement, computa-
tion, and communication costs.
• We propose dynamic model re-sharding, a novel technique
that dynamically reconfigures the parallelization strategies
for prefill and decode stages. We address the challenge of
transition overhead in model re-sharding with continuous
batching by introducing tiered KV cache buffering and
transition-minimizing scheduling. Based on these tech-
niques, we implement Seesaw, a high-throughput offline
inference system that optimizes parallelization strategies
for each LLM inference stage.
• We conduct a comprehensive evaluation of Seesaw across
a variety of workloads and hardware configurations. Our
results show Seesaw achieves an average speedup of
1.36× and a throughput improvement of up to 1.78×
compared to the state-of-the-art LLM inference engines.
2
BACKGROUND
2.1
LLM Inference
Transformer Architecture.
Modern large language mod-
els are based on the transformer architecture (Vaswani et al.,
2017), which typically consists of multiple identical decoder
layers (OpenAI, 2024). Each layer includes several linear
layers and an attention layer. The weights of the linear
layers account for the majority of the model’s parameters.
Auto-regressive Generation.
LLM inference follows an
auto-regressive paradigm (Bengio et al., 2000), which takes
an input prompt and generates a sequence of output tokens.
This process is divided into two stages: prefilling, which
processes the input tokens, and decoding, which generates a
token per step. These stages exhibit distinct computational
properties (Zhong et al., 2024; Yuan et al., 2024). Prefilling
processes the prompt that are typically hundreds to thou-
sands of tokens long. The computation and communication
costs, both of which scale with the number of tokens, domi-
nate the runtime during this stage. Since the cost of loading
weights is amortized over a larger set of tokens, the overall
performance is primarily bound by compute and/or commu-
nication. In contrast, Decoding processes only the newly
generated tokens in each auto-regressive step and has com-
paratively smaller computation in each step. Therefore the
cost for loading the weight data from off-chip memory to
computation units has a relatively higher percentage. In each
generation step, the intermediate tensors K and V in each
attention operator can be cached for reuse in the future gen-
eration, which is called Key-value cache (KV cache) (Pope
et al., 2023). While being able to accelerate computation,
it occupies a substantial amount of GPU memory, which is
proportional to the total number of tokens.
2.2
LLM Inference Optimization
Parallelism.
As the size of LLMs grows, the memory
capacity on a single GPU becomes insufficient. Conse-
quently, various techniques are developed to partition mod-
els onto multiple GPUs (Zheng et al., 2022). These paral-
lelization strategies can be classified as (1) inter-operator,
which places different operators or layers across multiple
GPUs, overlapping them with pipelining (known as Pipeline
parallelism, PP) (Huang et al., 2019; Narayanan et al., 2019;
Li et al., 2023), and (2) intra-operator, which partitions
different dimensions of tensors involved in computation,
including data parallelism (Srivatsa et al., 2024), tensor
parallelism (Shoeybi et al., 2019), etc. Data parallelism du-
plicates models on different devices and dispatches requests
among them. Tensor parallelism shards model weights and
each device performs a portion of the computation, then
aggregates these partial results to produce the final output.
Batching.
Batching more tokens in a single forward pass
increases inference efficiency by, for example, amortizing
the time required to load model weights (Sheng et al., 2023;
Fang et al., 2021). However, its effectiveness differs be-
tween the prefilling and decoding stages (Yuan et al., 2024;
He & Zhai, 2024; Agrawal et al., 2023). In decoding, where
weight-loading overhead occupies a larger portion of the
runtime, batching significantly boosts throughput by effec-
tively amortizing this overhead. Conversely, in the prefilling
stage, batching has a less pronounced impact since the token
count in input prompts is generally sufficient to keep the
process compute-bound. Overall, larger batch sizes yield
higher throughput, though the maximum batch size is lim-
ited by available GPU memory, as it requires additional
space for activations and the KV cache.
Continuous Batching and Scheduling.
Continuous
batching is an essential optimization for throughput-oriented
LLM inference (Yu et al., 2022; Kwon et al., 2023). By
batching multiple sequences at the token level, it allows the
system to onboard new sequences and clear the KV cache of
completed sequences at any generation step. This approach
enables prefill-prioritizing scheduling, which removes se-
quences as they finish, frees up their KV cache, and eagerly

=== Page 4 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
Tensor Parallel
Pipeline Parallel
L1
L1
GPU1
GPU2
GPU1
GPU2
GPU1
GPU2
GPU1
GPU2
L1
1/2
L1
2/2
L1
L1
Prefill
Decode
S1
S2
S1
S2
S2
S3
L1
S1
L2
S1
L2
S2
0.5x load weight
0.5x compute
+ allreduce
per-sequence time
time
1x load weight
0.5x compute
S2
S1
S1 S2
S1
S1 S2
S1
S2
S2
L2
S1
L2
S2
L1
S1
time
0.5x load weight
0.5x compute
+ allreduce
per-sequence time
1x load weight
0.5x compute
layer
token
sequence
batch
allreduce
PP is better because of
lower allreduce overhead
TP is better because of more
effective batching
Proportion of allreduce is
larger in prefilling
Proportion of loading weights is
higher in decoding
TP shards weights, so load
weights is parallelized
L2
1/2
L2
2/2
S2
S1
S2
S1
L1
1/2
L1
2/2
L2
1/2
L2
2/2
PP has smaller
batch sizes
Figure 3. Different effects of tensor and pipeline parallelisms on prefilling and decoding. Tensor parallelism incurs all-reduce overhead,
which has a higher percentage in prefilling, therefore pipeline parallelism is better for prefilling. Conversely, pipeline parallelism splits
batches into smaller micro-batches, which leads to more forward passes and repetitive loading weights, which is insufficient in decoding.
schedules the prefilling of new sequences whenever GPU
memory becomes available. This strategy maximizes the
number of concurrent sequences being processed, resulting
in higher throughput. Another alternative is to use decode-
prioritizing scheduling, which minimizes the frequency of
transitions. Instead of scheduling to prefilling eagerly, this
approach waits until all sequences in a batch have finished
decoding before initiating the next round of prefilling. How-
ever, this scheduling policy results in suboptimal decoding
throughput (Agrawal et al., 2024).
3
MOTIVATION AND ANALYSIS
In this section, we provide an in-depth analysis of two key
observations we identify from Figure 1 in Section 1: (1)
Tensor parallelism often exhibits significantly worse per-
formance than pipeline parallelism during the prefill stage
due to its substantial communication overhead; (2) Pipeline
parallelism tends to fall short in the decode stage owing to
the considerable weight loading overhead it incurs. We then
argue that a dynamic parallelization strategy is essential to
attain optimal performance across both stages.
Given the importance of batching in throughput-oriented
tasks, it can be useful to consider how different paralleliza-
tion strategies impact the maximum batch size, rather than
assuming batch size as a tunable parameter, as is often done
in online-serving contexts such as DistServe (Zhong et al.,
2024) and Sarathi-serve (Agrawal et al., 2024).
3.1
Parallelism Analysis
Observation 1: Tensor parallelism incurs substantial
communication overhead during the prefill stage.
In
Tensor parallelism, each device performs a part of computa-
tion and aggregate the partial result. The activations at each
layer are synchronized across all GPUs using all-reduce
operations. The overhead associated with this operation can
be quantified as:
#tokens × activation size
all-reduce bandwidth
,
where all-reduce bandwidth refers to the rate of data transfer
during all-reduce operations, calculated as the size of the
tensor being all-reduced divided by the all-reduce runtime.
As the degree of tensor parallelism increases, the proportion
of execution time of all-reduce operations grows substan-
tially. This growth is attributed to two main factors. First,
while model weights are partitioned, activations in tensor
parallelism remain fully replicated across GPUs, leading to
a constant activation size regardless of the degree of tensor
parallelism. Second, all-reduce bandwidth decreases as the
number of GPUs grows, due to more complex communi-
cation schemes. Therefore, increasing the degree of tensor
parallelism not only fails to reduce the traffic of all-reduce
operations but further limits the communication bandwidth,
resulting in escalated communication overhead. This is-
sue is particularly pronounced in the prefill stage, where a
large number of tokens are processed simultaneously, mak-
ing communication overhead the primary bottleneck. Thus,
tensor parallelism tends to perform worse than pipeline par-
allelism due to its large communication overhead.
Observation 2: Pipeline parallelism suffers from signifi-
cant weight transferring overhead in the decode stage.
Pipeline parallelism distributes model layers sequentially
across devices, with each device responsible for processing
a set of consecutive layers before passing the output to the
next device. Due to the auto-regressive nature of LLM infer-
ence, a sequence cannot enter the pipeline until its preceding
token is generated. As a result, at any given time step, a
sequence can appear in only one stage of the pipeline, mak-
ing the batches processed by each device mutually exclusive.
However, the total number of sequences that the pipeline
can handle at a time, referred to as the global batch size,

=== Page 5 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
is constrained by the size of KV cache. Given the mutual
exclusion of batches at each device, pipeline parallelism can
process only approximately 1/PP of the global batch per
forward pass. We denote this reduced batch size in pipeline
parallelism as the micro-batch size.
Dividing batches into micro-batches increases the number
of LLM forward passes required to process the same amount
of requests. Specifically, a pipeline parallelism degree of
PP necessitates PP times more forward passes for a given
global batch. This repeated execution degrades inference
performance, as model weight matrices must be loaded from
global memory repeatedly. This inefficiency is especially
significant in the decode stage, where weight-loading over-
head accounts for a substantial portion of total execution
time. As a result, pipeline parallelism generally underper-
forms relative to tensor parallelism in the decode stage due
to the amplified weight loading overhead.
Discussion on Data Parallelism.
Unlike tensor and
pipeline parallelism, which distribute the model across de-
vices, data parallelism distributes the data while duplicating
the model. While data parallelism has minimal commu-
nication overhead, it has two key disadvantages: (1) the
volume of weight transferring is higher by the number of
duplicates compared to tensor parallelism; and (2) it occu-
pies more GPU memory, reducing the available space for
the KV cache and thus limiting the maximum batch size re-
sulting in lower throughput. Data parallelism can be applied
orthogonally alongside both tensor and pipeline parallelism.
We do not dynamically adjust data parallelism, which will
be explained in Section 4.1.
Conclusion: No one-size-fits-all
When comparing these
three parallelism strategies for high-throughput LLM infer-
ence, a key observation is that prefilling and decoding stages
benefit from different parallelism approaches. This differ-
ence arises from the distinct characteristics of each stage, as
illustrated in Figure 3. Tensor parallelism is preferred for
decoding due to its ability to efficiently accelerate weight
matrix loading. However, it incurs significant communica-
tion overhead, as it requires all-reduce operations at each
layer. In contrast, pipeline and data parallelism have much
lower communication overhead, making them preferable for
prefilling. However, their decoding throughput is limited by
inefficient batching and additional weight-loading overhead.
To quantitatively analyze the trade-offs across different par-
allelisms, we model the average runtime per sequence (the
inverse of throughput) as follows. Derivations and further
details are provided in the Appendix A.
T ∝T linear
dm
TP
+ T attn
dm + Tcomp
DP · TP · PP + Tcomm(TP)
PP · DP
Here T linear
dm
represents data movement for linear layers (pri-
GPU0
GPU1
GPU2
GPU3
GPU4
GPU5
GPU6
GPU7
prefill worker
decode worker
prefill
throughput
decode
throughput
0.0
0.5
1.0
1.5
2.0
Throughput (reqs/sec)
Decode (8 GPUs)
Decode (4 GPUs)
Prefill (4 GPUs)
Throughput Mismatch
Figure 4. An example of spatially disaggregating prefilling and
decoding has a restricted search space. Deploying a 70B model on
eight 40GiB GPUs allows only one disaggregation strategy: four
GPUs for prefilling and four for decoding. However, this causes
severe throughput mismatch between the two stages.
marily model weights), T attn
dm represents data movement for
attention layers (primarily KV cache) , Tcomp represents
computation time, Tcomm represents communication time.
Note that Tcomm is a monotonically increasing function
with respect to TP, as all-reduce operations require more
time as TP increases.
Tensor parallelism can effectively accelerate loading model
weights, which is T linear
dm , while pipeline and data parallelism
cannot. On the other hand, pipeline and data parallelism
effectively reduce the overhead of communication, while
tensor parallelism contrarily increases the communication
overhead. In prefilling, T linear
dm
is negligible, and Tcomm be-
comes larger, so pipeline and data parallelisms are more
preferred, while in decoding, T linear
dm
occupies a larger pro-
portion so tensor parallelism is more advantageous.
3.2
Why not Disaggregate Prefilling and Decoding?
Spatially disaggregating prefilling and decoding with sepa-
rate hardware resources, as done in online serving systems
such as DistServe (Zhong et al., 2024) and MoonCake (Qin
et al., 2024), is one approach to separately select paralleliza-
tion strategies for prefilling and decoding. Sequences are
first processed by the devices dedicated for prefilling before
being transferred to decoding devices.
However, there are two obstacles when applying prefill-
decode disaggregation to purely throughput-oriented sce-
narios.
First, since the overall throughput is bound by
the slower stage, the throughput of prefilling and decod-
ing needs to be matched by adjusting the devices allocated
for each stage. However, it can be impractical in resource-
constrained scenarios. As shown in Figure 4, to deploy
a 70B model (which takes 140GiB memory for model
weights) on eight 40GiB GPUs, there is only one disag-
gregation strategy, that is four GPUs for prefilling and four

=== Page 6 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
L1
KV1
L2
KV2
L1
1/2
KV1
1/2
L2
1/2
KV2
1/2
L1
2/2
KV1
2/2
L2
2/2
KV2
2/2
model
resharding
GPU 1
GPU 2
prefill
 (pipeline parallelism)
decode 
(tensor parallelism)
Figure 5. Model weights and KV cache need to be re-sharded when
switching between different parallelism.
for decoding2. However, it causes severe throughput mis-
match where prefilling has more than 6× higher throughput
than decoding. Second, disaggregation duplicates the model
weights similarly to data parallelism, bringing similar draw-
backs, such as limited KV cache space and increased weight
transfer. As a result, decoding throughput with four GPUs
is only 15% of that with eight GPUs.
In conclusion, although disaggregation allows for select-
ing different parallelization strategies for each stage, the
throughput mismatch between stages and limited resources
allocated to each can lead to suboptimal performance. This
calls for a method that offers flexibility in parallelization
while maximizing hardware resource utilization.
4
SEESAW: KEY IDEAS
4.1
Dynamic Model Re-sharding
Observing that prefilling and decoding have distinct pref-
erences for parallelism, we propose a technique called dy-
namic model re-sharding. This technique enables the se-
lection of different parallelism strategies for each stage and
automatically transitions between them. This approach ex-
pands the configuration space, allowing for separate opti-
mization of the two stages, potentially improving overall
throughput compared to using a single configuration. In the
following paragraphs, we denote the parallelization strategy
used in prefilling as cp and that in decoding as cd.
To support transitions between different parallelization con-
figurations, the cluster must rearrange the data stored on
each device to align with the new parallelism which involves
both model weights and KV cache, as illustrated in Figure 5.
In Seesaw, model weights are re-sharded by reloading the re-
quired shards from CPU memory, and KV cache re-sharding
is performed through CPU shared memory.
The inter-device movement of tensors incurs overhead. To
mitigate this re-sharding cost, we design an asynchronous
pipeline to overlap data transfer with computation, as de-
tailed in Section 5.2.
Discussion on data parallelism.
Unlike switching be-
tween tensor and pipeline parallelism, adjusting the degree
2 At least four GPUs (160 GiB memory) are needed to fit the
model weights.
asynchronous 
swap in
CPU
GPUs
prefill
CPU
GPUs
CPU memory is 
empty
CPU
GPUs
decoding
CPU
GPUs
CPU memory is
filled
CPU
GPUs
prefill
(warm up)
Figure 6. Tiered KV cache buffering and transition-minimizing
scheduling, and the change of KV cache occupancy.
request
cp
cd
GPU 1 (worker 1)
GPU 2 (worker 2)
CPU
write back kv
after prefill
load kv before decode
cp
cp
(prefill)
cd
cd
(decode)
CPU KV cache is empty
CPU KV cache is full
scheduler
Figure 7. KV cache re-sharding is completed during swapping,
leveraging CPU shared memory.
of data parallelism alters the proportion of GPU memory al-
located to model weights versus KV cache. This adjustment
increases system complexity or necessitates additional data
movement between the CPU and GPU. Therefore, we only
dynamically adjust tensor and pipeline parallelism.
4.2
Tiered KV Cache Buffering and
Transition-minimizing Scheduling
Challenge: Transition Overhead.
In practice, dynamic
model resharding encounters an obstacle of transition
overhead, which is amplified by the widely-used contin-
uous batching and prefill-prioritizing scheduling. Prefill-
prioritizing scheduling eagerly schedules new prefilling
tasks, causing frequent transitions between the two stages.
As a result, directly applying model re-sharding with this in-
terleaved prefill-decode scheduling policy would introduce
significant re-sharding overhead. On the other hand, decode-
prioritizing scheduling minimizes the frequency of transi-
tions but results in suboptimal decoding throughput. Other
compromise solutions involve setting a threshold-based ap-
proach for managing the prefill-decode transition (Cheng
et al., 2024). However, they still involve a trade-off be-
tween reducing transition overhead and maximizing decod-
ing throughput.
To address this problem, we propose 1) tiered KV cache
buffering, which leverages CPU memory offloading 2)
transition-minimizing scheduling policy. These two syn-
ergistic techniques prevent frequent stage transitions and
maintain a high decoding throughput.
Tiered KV cache buffering uses CPU memory as auxiliary
storage for the KV cache, enabling the pre-computation
of a large batch of prefilling consecutively. During the

=== Page 7 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
prefill stage, the generated KV cache is offloaded to CPU
KV cache storage, freeing it from the limitations of GPU
memory space. During decoding, continuous batching runs
as normal, except that new sequences are on-boarded by
swapping in its KV cache from the CPU memory.
Transition-minimizing scheduling controls the transition to
only happen when the CPU KV storage is either full or
empty. During prefill, once the CPU KV cache storage
is fully utilized, re-sharding is triggered, and the cluster
transitions to decoding. During decoding, GPUs continue
processing requests and loading KV cache from CPU mem-
ory, keeping GPU KV cache fully utilized for high decod-
ing throughput. When the entire CPU KV cache has been
transferred to GPU memory, the cluster switches back to
prefilling. The whole process is illustrated in Figure 6.
KV cache re-sharding occurs throughout this process. As
illustrated in Figure 7, in a multi-GPU setup, the CPU KV
cache storage is shared among all GPUs. During swap-out,
each GPU pushes its shard (based on cp) of the generated
KV cache to the shared CPU storage, where these shards
collectively form the complete KV cache. During swap-
in, each GPU retrieves its required KV shard (based on
cd) from the shared storage. We implement the shared KV
cache using shared memory of the operating system.
5
SYSTEM DESIGN AND IMPLEMENTATION
5.1
Scheduler-worker Architecture
In order to support dynamically switching parallelization
configurations for prefilling and decoding, we build Seesaw,
a new LLM inference engine designed for high-throughput
LLM inference. The overall architecture of Seesaw fol-
lows a single-scheduler, multi-worker design. The sched-
uler manages all generation requests, organizes them into
batches, and sends instructions to the workers. To fully
utilize pipelining, each decoding step processes 1/PP of the
sequences in GPU KV storage. Once a batch is formed, it is
sent to workers through shared queues. Each worker is re-
sponsible for controlling a single GPU and maintains a task
queue to receive and execute instructions sequentially. This
architecture facilitates the implementation of asynchronous
features, such as pipeline parallelism and the asynchronous
pipeline for tiered KV cache buffering.
5.2
Asynchronous Pipeline
While re-sharding and tiered KV cache buffering offer sub-
stantial benefits, they also introduce new overhead related
to moving model weights and KV cache. The overhead of
reloading model weights remains constant relative to batch
size, allowing it to be amortized with larger batches. In con-
trast, swapping the KV cache incurs overhead proportional
to batch size, making it harder to amortize. Fortunately,
swap out
qkv_proj
attn + ffn
   swap in
main thread
prefetcher thread
scheduler
(prefill)
scheduler
(decode)
decode
CPU KV
GPU KV
non-blocking copy
CPU KV  is empty
CPU KV  is full
Figure 8. Async pipeline of Seesaw: Swap-in overlaps with prefill
computation, while swap-out occurs in a separate asynchronous
prefetcher thread.
these overheads can be mitigated through computation-
communication overlap. We implement an asynchronous
pipeline to overlap KV cache transfer with ongoing compu-
tation, as illustrated in Figure 8.
Overlap swap-out with computation.
The KV cache
generated during the prefilling stage is not used until decod-
ing begins, allowing the KV cache swap-out to overlap with
other computations during prefilling. Although CPU-GPU
data transfer is relatively slow due to PCIe bandwidth limi-
tations, it can still be overlapped with computation, given
the high FLOPS involved in prefilling.
In practice, CPU-GPU data transfer can only overlap with
computation when using pinned memory, but shared mem-
ory cannot be pinned (AlbanD, 2023). To address this, we
split the transfer into two stages: GPU to pinned memory
(overlapped with computation) and then pinned to shared
memory, which is a host-side operation that also runs con-
currently with GPU kernels.
Asynchronous swap-in.
We implement swap-in using a
background thread called the prefetcher on each worker, op-
erating in a fully asynchronous paradigm. The prefetcher is
controlled directly by the scheduler and runs independently
of the main thread, whether the main thread is handling pre-
filling or decoding. In each iteration, the scheduler creates
new prefetching tasks when there are free slots in the GPU
KV store. Once the prefetcher completes moving the KV
cache for certain sequences, it notifies the scheduler via a
shared queue, allowing those sequences to be scheduled for
decoding tasks later. As long as the output length is not too
short, the swap-in can also be well overlapped.
Bandwidth-aware KV cache layout.
The data layout of
the KV cache significantly impacts the bandwidth efficiency
of data movement. There are two common layouts for stor-
ing KV cache: (seq len, num heads, head dim) (NHD) and
(num heads, seq len, head dim) (HND). NHD is less opti-
mal for memory access because tensor parallelism shards
the KV cache along the H dimension (number of heads),
which is the second-to-last dimension, leading to more non-
contiguous memory access. Therefore, we use the HND

=== Page 8 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
layout for storing the KV cache in CPU memory.
6
EVALUATION
In this section, we evaluate the performance of Seesaw under
a variety of hardware configurations and workloads.
6.1
Experiment Settings
Hardware.
We use three types of GPUs: NVIDIA A10,
L4, and A100. The A10 and L4 are deployed on AWS EC2
instances (g5.48xlarge and g6.48xlarge (Amazon
Web Services, 2024)), and the A100 is used on GCP (Google
Cloud, 2024). GPU specifications are listed in Table 1. The
PCIe connection for each GPU is PCIe 4.0 8×, providing 16
GiB/s bandwidth (PCI-SIG, 2017), while NVLink (NVIDIA
Corporation, 2024) offers a bandwidth of 600 GiB/s. Addi-
tionally, we allocate 80 GiB of CPU memory per GPU.
Model.
We use three different LLMs with different
sizes: (1) a 15B variety of LLaMA3 (Elinas, 2024); (2)
CodeLLaMA-34B (Roziere et al., 2023); (3) LLaMA2-
70B (Touvron et al., 2023b). They all use Grouped Query
Attention (GQA) (Ainslie et al., 2023). For brevity, we refer
to them as 15B, 34B, and 70B, respectively, in the following
sections. We use float16 as the data type.
Workload.
We use two different datasets in our eval-
uation,
namely
sharegpt
(ShareGPT,
2023)
and
arxiv-summarization (Cohan et al., 2018). They
correspond
to
two
different
distributions
of
work-
load.
sharegpt is a dataset of chatting history, so
its input and output have comparable lengths, while
arxiv-summarization dataset is a summarization
dataset where inputs are much longer than outputs. The
characteristics of these two datasets are shown in Figure 9.
We sample 2000 requests from the sharegpt dataset and
500 requests from arxiv-summarization and also use
constant-length workloads in Section 6.5. Since Seesaw
is purely throughput-oriented, we measure the end-to-end
throughput as the metrics.
Baselines.
We use vLLM 0.5.4 (Kwon et al., 2023) as
the baseline. It is the most widely used open-source LLM
serving engine with wide support for different parallelisms.
We also directly use the vLLM’s model implementation for
a straightforward comparison. SGLang (Zheng et al., 2023)
and DeepSpeed-FastGen (Holmes et al., 2024) do not sup-
port pipeline parallelism. TensorRT-LLM (NVIDIA, 2024b)
is not included in the comparison because it uses a simi-
lar scheduling policy as vLLM, and vLLM demonstrates
comparable performance (vLLM Team, 2024) in throughput-
oriented tasks. The techniques proposed in Seesaw can also
be applied to modifying TensorRT-LLM.
Table 1. GPU hardware specification
GPU Model
Memory Size
Memory
Bandwidth
FLOPS
NVLink
A10
24 GiB
600 GiB/s
125T
✗
L4
24 GiB
300 GiB/s
121T
✗
A100
40 GiB
1,555 GiB/s
312T
✓
0
2000
4000
#tokens
0
2
4
Density
1e
3
input tokens
output tokens
(a) arxiv-summarization
0
2000
4000
#tokens
0.0
0.5
1.0
Density
1e
2
input tokens
output tokens
(b) ShareGPT
Figure 9. Input and output length distributions of the datasets
We enable chunked prefill and tune the chunk size for vLLM
to get the optimal throughput, following the practice of
Sarathi-serve (Agrawal et al., 2024). Otherwise, suboptimal
chunk sizes would cause severe throughput degradation.
6.2
End-to-end Throughput on PCIe Systems
First, we measure the end-to-end throughput of Seesaw. We
sweep over all available single parallelism configurations
for vLLM and show the result of the best configuration. We
use four GPUs for the 15B model, and eight GPUs for the
34B and 70B models. The result is shown in Figure 10, with
the used parallelism labeled above each bar.
On A10, compared with the highest single parallelism base-
line, Seesaw achieves a geometrically average speedup of
1.45×, with up to 1.78× speedup. On L4, Seesaw achieves
a geometrically average speedup of 1.29×, with up to 1.52×
speedup.
The overall average speedup is 1.36×.
The
speedup is more significant on A10, because A10 has better
single GPU performance than L4, while they have similar
PCIe inter-connection bandwidth, causing a higher percent-
age of communication overhead.
6.3
Speedup Breakdown: An Example
Figure 12 illustrates how Seesaw merges the advantages
of different parallelisms. Using CodeLLaMA34B on the
arxiv-summarization dataset with four A10 GPUs
as an example, we measured the runtime of each stage. TP4
is optimal for decoding but significantly slower for prefilling,
while PP4 excels at prefilling but is slower during decoding.
Seesaw uses a mixed parallelism strategy, applying PP4
for prefilling and TP4 for decoding, achieving performance
comparable to the best configuration for each stage.
Compared to the optimal single parallelism configuration
(TP2PP2) with chunked prefill, Seesaw is still faster because
(1) chunked prefill does not piggy-back all decoding steps,

=== Page 9 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
15b
34b
70b
15b
34b
70b
0
1
2
Normalized
Throughput
 D2T2
 P4->T4
 D2T2P2
 D2P4->D2T4
 T2P4
 P8->T4P2
 D2P2  P4->T4  D2T2P2
 D2P4->D2T4
 T4P2
 P8->T4P2
 arxiv
 sharegpt
vllm
seesaw
(a) End-to-end Throughput on A10
15b
34b
70b
15b
34b
70b
0
1
2
Normalized
Throughput
 T2P2
 P4->T4
 D2T4
 D2P4->D2T4
 T4P2
 P8->T4P2
 P4
 P4->T4
 D2T4
 P8->T4P2
 T4P2 P8->T4P2
 arxiv
 sharegpt
vllm
seesaw
(b) End-to-end Throughput on L4
Figure 10. End-to-end throughput comparison on PCIe systems.
The used parallelization strategies are labelled above each bar.
Labels such as “P4 →D4” represent the parallelization strategies
for prefilling and decoding respectively in Seesaw.
arxiv
sharegpt
0.0
0.5
1.0
Throughput
(Normalized)
0.61
0.62
0.89
0.82
1.00
1.00
1.00
1.13
vllm+pcie
seesaw+pcie
vllm+nvlink
seesaw+nvlink
Figure 11. Throughput comparison on A100.
leaving some purely decoding steps, and (2) chunked prefill
with TP2PP2 is slower than prefilling with PP4.
6.4
End-to-end Throughput on A100
Speedup on A100 + NVLink
The NVLink interconnec-
tion across A100 GPUs significantly reduces the all-reduce
overhead and further scales tensor parallelism. Usually,
tensor parallelism alone is enough to achieve optimal per-
formance when there are no more than four GPUs. Never-
theless, there is still a noticeable percentage of all-reduce
overhead in prefilling when tensor parallelism scales be-
yond four GPUs. Seesaw can still provide speedup in this
case. As shown in Figure 11, Seesaw still achieves a 13%
throughput increase over vLLM for the sharegpt dataset
on LLaMA3-70B on eight A100s.
Speedup on A100 + PCIe
Besides A100 SXM with
NVLink inter-connection, there is also another version of
A100 that is inter-connected with PCIe links, where Seesaw
can achieve noticeable speedup. As shown in Figure 11, See-
saw provides 46% speedup on arxiv-summarization
and 30% speedup on sharegpt. Seesaw brings the per-
formance of the A100 PCIe version much closer to the per-
formance level of the NVLink version. vLLM gets roughly
60% throughput on A100 PCIe compared with A100 SXM,
while Seesaw boosts it up to 82% – 89%.
tp4
pp4
p4->t4
tp2pp2
+chunked prefill
0
500
1000
1500
End-to-end time (s)
prefill
mix
decode
other
Figure 12. Speedup breakdown. “mix” represents batches contain-
ing both prefilling and decoding when chunked prefill is enabled.
We disable chunked prefill for TP4 and PP4 in order to show the
reference prefilling and decoding time. TP2PP2 with chunked
prefill is the optimal parallelism for vLLM.
0.0
0.1
0.2
0.3
D:P
0.5
1.0
throughput
(normalized)
tp4pp2
tp2pp4
pp8
pp8->tp4pp2
Figure 13. Throughput of various parallelization strategies with
different ratios between output and input lengths (D : P), mea-
sured on 70B model and eight A10 GPUs.
6.5
Sensitivity Study
Ratio between Input and Output Length
The speedup
of Seesaw depends on the ratio between the input and output
length, or P : D. Model re-sharding has the opportunity
to provide speedup when prefilling and decoding have bal-
anced time. To investigate to what extent model re-sharding
would be effective, we measure the throughput of various
parallelization strategies on synthesized datasets with uni-
form lengths and different P : D ratios. We fix the input
length as 3000 and vary the output length.
As shown in Figure 13, PP8 achieves the highest throughput
during prefilling, while TP4PP2 excels in decoding. When
the output length equals one (prefilling only), Seesaw and
PP8 show similar throughput, and TP4PP2 performs worse
due to high communication overhead. As output length
increases, the inefficiency of PP in decoding outweighs its
advantage in prefilling, causing PP8’s throughput to drop
rapidly. There is a range where TP2PP4 becomes optimal
before decoding dominates the runtime and TP4PP2 takes
over as the fastest. Nonetheless, Seesaw achieves the highest
overall throughput across all data points. In real scenarios
with variable input and output lengths, Seesaw is even more
advantageous due to its adaptive capabilities.
Inter-connection Bandwidth
The effectiveness of See-
saw also depends on the inter-connection bandwidth. We
investigate this by measuring the runtime and tracing all-
reduce operations of running arxiv-summarization
and 34B model on eight A10s. We then mutate the all-
reduce time to project the end-to-end throughput with dif-

=== Page 10 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
10
1
100
101
Bandwidth scale (× all_reduce through PCIe)
0.0
0.5
1.0
Throughput
(Normalized)
d2t1p4
d2t2p2
d2t4p1
d1t1p8
d1t2p4
d1t4p2
d1t8p1
d2p4->d2t4
Figure 14. Projected throughput of various parallelization strate-
gies with different inter-connection bandwidth, measured and
traced on 34B model and eight A10 GPUs.
ferent inter-connection bandwidths. As shown in Figure 14,
when the inter-connection bandwidth is slow (for example,
among geographically distributed devices (Borzunov et al.,
2022)), pipeline parallelism is optimal; when the bandwidth
is very high, tensor parallelism is optimal. The throughput
of Seesaw is superior to fixed parallelization strategies on a
wide range from 0.1× to 50× of PCIe bandwidth.
7
RELATED WORK
7.1
Heterogenity between Prefilling and Decoding
Due to the different computational characteristics between
prefilling and decoding leading to under-utilization of hard-
ware resources, prior research has investigated two direc-
tions to address this problem, namely disaggregating or
merging the two stages. Disaggregation places prefilling
and decoding onto different devices to avoid their interfer-
ence while merging processes prefilling and decoding in
one batch.
Disaggregate Prefill and Decoding
DistServe (Zhong
et al., 2024) proposed placing prefilling and decoding on
different devices to prevent interference and leverage dif-
ferent characteristics of the two stages. Mooncake (Qin
et al., 2024) uses similar through a distributed KV cache
pool. P/D-Serve (Jin et al., 2024) uses the device-to-device
network to transfer the KV cache between prefill and decode
devices. Splitwise (Patel et al., 2024) proposes using dif-
ferent GPU models for the two stages. TetriInfer (Hu et al.,
2024) further disaggregates different downstream tasks to
avoid interference. These works are designed for online
serving while Seesaw focuses on offline inference. More-
over, they are usually designed for large clusters.
Merge Prefill and Decode
Chunked prefill, as proposed
by SplitFuse (Holmes et al., 2024), Sarathi (Agrawal et al.,
2023), and Sarathi-serve (Agrawal et al., 2024), splits long
prompts in the prefilling stage into smaller chunks, combin-
ing them with decoding steps to strike a balance between
data movement and computation and reduce pipeline bub-
bles in pipeline parallelism. However, determining the opti-
mal chunk size is challenging. A chunk size that’s too large
results in excessive decode-only steps, closely resembling
traditional prefill-decode scheduling. Conversely, a chunk
size that’s too small reduces kernel efficiency.
7.2
Parallel and Distributed LLM Inference
Aside from tensor parallelism, pipeline parallelism, and data
parallelism discussed in Section 2.2, there are also other
types of parallelisms, such as sequence parallelism (SP) (Li
et al., 2021; Liu et al., 2023; Lin et al., 2024; Brandon et al.,
2023; Xue et al., 2024) and fully sharded data parallelism
(FSDP) (Zhao et al., 2023; Rajbhandari et al., 2020). Se-
quence parallelism is especially designed for long sequence
lengths, and is orthogonal with our work. FSDP requires
frequently transferring weight matrices across GPUs, thus
mainly used in training.
HexGen (Jiang et al., 2023), LLM-PQ (Zhao et al., 2024),
Helix (Mei et al., 2024) investigate parallelisms in hetero-
geneous clusters. Intra-device parallelism leverages over-
lapping functions using different resources within each de-
vice, including NanoFlow (Zhu et al., 2024) and Liger (Du
et al., 2024).
Petals (Borzunov et al., 2022) explores
LLM inference in geographically distributed setups, em-
ploying pipeline parallelism to minimize communication
costs. SpotServe (Miao et al., 2024) runs LLM inference on
preemptible instances.
7.3
Offloading in LLM Inference
Offloading is a widely used technique to run LLM applica-
tions in resource-constrained scenarios (Ren et al., 2021).
FlexGen (Sheng et al., 2023) swaps tensors across GPU
memory, CPU memory, and disks. Fiddler (Kamahori et al.,
2024), HeteGen (Xuanlei et al., 2024), PowerInfer (Song
et al., 2023) and FastDecoder (He & Zhai, 2024) perform
part of computation in CPU, which require CPUs with
strong compute capability or external CPU nodes connected
with high-bandwidth networking. Instinfer (Pan et al., 2024)
offloads computation to Computational Storage Drives.
8
CONCLUSION
This paper proposes Seesaw, a high-throughput LLM infer-
ence engine, to address the inefficiencies of fixed paralleliza-
tion by selecting different parallelization strategies for the
prefilling and decoding stages and switching between them
using model re-sharding. It uses tiered KV cache buffering
to minimize re-sharding overheads. Our experiments show
that Seesaw outperforms widely-used open-source inference
engines, with a throughput increase of 1.06-1.78× and an
average throughput improvement of 1.36×. These results
highlight Seesaw’s effectiveness and adaptability.

=== Page 11 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
REFERENCES
Achiam, J., Adler, S., Agarwal, S., Ahmad, L., Akkaya, I.,
Aleman, F. L., Almeida, D., Altenschmidt, J., Altman, S.,
Anadkat, S., et al. Gpt-4 technical report. arXiv preprint
arXiv:2303.08774, 2023.
Agrawal, A., Panwar, A., Mohan, J., Kwatra, N., Gulavani,
B. S., and Ramjee, R. Sarathi: Efficient llm inference
by piggybacking decodes with chunked prefills. arXiv
preprint arXiv:2308.16369, 2023.
Agrawal, A., Kedia, N., Panwar, A., Mohan, J., Kwatra, N.,
Gulavani, B. S., Tumanov, A., and Ramjee, R. Taming
throughput-latency tradeoff in llm inference with sarathi-
serve. arXiv preprint arXiv:2403.02310, 2024.
Ainslie, J., Lee-Thorp, J., de Jong, M., Zemlyanskiy, Y.,
Lebr´on, F., and Sanghai, S. Gqa: Training generalized
multi-query transformer models from multi-head check-
points. arXiv preprint arXiv:2305.13245, 2023.
AlbanD.
Why not multiprocess pin memory in
data loader?
https://discuss.pytorch.org/t/why-not-
multiprocess-pin-memory-in-data-loader/197345/2, 2023.
Accessed: 2024-10-14.
Amazon Web Services.
Amazon EC2 Instance Types,
2024.
URL https://aws.amazon.com/ec2/
instance-types/. Accessed: 2024-10-26.
Ben-Nun, T. and Hoefler, T. Demystifying parallel and dis-
tributed deep learning: An in-depth concurrency analysis.
ACM Computing Surveys (CSUR), 52(4):1–43, 2019.
Bengio, Y., Ducharme, R., and Vincent, P. A neural proba-
bilistic language model. Advances in neural information
processing systems, 13, 2000.
Borzunov, A., Baranchuk, D., Dettmers, T., Ryabinin, M.,
Belkada, Y., Chumachenko, A., Samygin, P., and Raffel,
C. Petals: Collaborative inference and fine-tuning of
large models. arXiv preprint arXiv:2209.01188, 2022.
Brandon, W., Nrusimha, A., Qian, K., Ankner, Z., Jin, T.,
Song, Z., and Ragan-Kelley, J. Striped attention: Faster
ring attention for causal transformers. arXiv preprint
arXiv:2311.09431, 2023.
Chan, V., Zhang, H., and Wang, F.
Snowflake llm
inference:
Optimizing gpu capacity for interactive
workloads.
https://www.snowflake.com/engineering-
blog/snowflake-llm-inference-interactive-workloads/,
September 2024. Accessed: 2024-10-30.
Chang, L., Bao, W., Hou, Q., Jiang, C., Zheng, N., Zhong,
Y., Zhang, X., Song, Z., Jiang, Z., Lin, H., et al. Flux: Fast
software-based communication overlap on gpus through
kernel fusion. arXiv preprint arXiv:2406.06858, 2024.
Cheng, K., Hu, W., Wang, Z., Peng, H., Li, J., and Zhang,
S. Slice-level scheduling for high throughput and load
balanced llm serving. arXiv preprint arXiv:2406.13511,
2024.
Cohan, A., Dernoncourt, F., Kim, D. S., Bui, T., Kim, S.,
Chang, W., and Goharian, N. A discourse-aware attention
model for abstractive summarization of long documents.
arXiv preprint arXiv:1804.05685, 2018.
Dell
Technologies.
Poweredge
server
gpu
matrix,
2023.
URL
https://www.
delltechnologies.com/asset/en-ca/
products/servers/briefs-summaries/
poweredge-server-gpu-matrix.pdf.
Ac-
cessed: 2024-10-24.
Dell Technologies.
Inferencing performance for gen-
erative ai in the enterprise with amd accelerators.
https://infohub.delltechnologies.com/en-au/l/generative-
ai-in-the-enterprise-with-amd-accelerators/inferencing-
performance/, 2024. Accessed: 2024-10-30.
Du, J., Wei, J., Jiang, J., Cheng, S., Huang, D., Chen, Z.,
and Lu, Y. Liger: Interleaving intra-and inter-operator
parallelism for distributed large model inference. In Pro-
ceedings of the 29th ACM SIGPLAN Annual Symposium
on Principles and Practice of Parallel Programming, pp.
42–54, 2024.
Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody,
A., Truitt, S., and Larson, J. From local to global: A graph
rag approach to query-focused summarization. arXiv
preprint arXiv:2404.16130, 2024.
Elinas.
Llama-3-15b
instruct-zeroed.
https://huggingface.co/elinas/
Llama-3-15B-Instruct-zeroed, 2024.
Fang, J., Yu, Y., Zhao, C., and Zhou, J. Turbotransformers:
an efficient gpu serving system for transformer models.
In Proceedings of the 26th ACM SIGPLAN Symposium
on Principles and Practice of Parallel Programming, pp.
389–402, 2021.
Google Cloud.
GPU platforms:
A100 GPUs, 2024.
URL https://cloud.google.com/compute/
docs/gpus#a100-gpus. Accessed: 2024-10-26.
He, J. and Zhai, J.
Fastdecode: High-throughput gpu-
efficient llm serving using heterogeneous pipelines. arXiv
preprint arXiv:2403.11421, 2024.
Holmes, C., Tanaka, M., Wyatt, M., Awan, A. A., Rasley, J.,
Rajbhandari, S., Aminabadi, R. Y., Qin, H., Bakhtiari, A.,
Kurilenko, L., et al. Deepspeed-fastgen: High-throughput
text generation for llms via mii and deepspeed-inference.
arXiv preprint arXiv:2401.08671, 2024.

=== Page 12 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
Hu, C., Huang, H., Xu, L., Chen, X., Xu, J., Chen, S., Feng,
H., Wang, C., Wang, S., Bao, Y., et al. Inference without
interference: Disaggregate llm inference for mixed down-
stream workloads.
arXiv preprint arXiv:2401.11181,
2024.
Huang, Y., Cheng, Y., Bapna, A., Firat, O., Chen, D., Chen,
M., Lee, H., Ngiam, J., Le, Q. V., Wu, Y., et al. Gpipe:
Efficient training of giant neural networks using pipeline
parallelism. Advances in neural information processing
systems, 32, 2019.
Jiang, Y., Yan, R., Yao, X., Zhou, Y., Chen, B., and Yuan, B.
Hexgen: Generative inference of large language model
over heterogeneous environment. In Forty-first Interna-
tional Conference on Machine Learning, 2023.
Jin, Y., Wang, T., Lin, H., Song, M., Li, P., Ma, Y., Shan, Y.,
Yuan, Z., Li, C., Sun, Y., et al. P/d-serve: Serving disag-
gregated large language model at scale. arXiv preprint
arXiv:2408.08147, 2024.
Kamahori, K., Gu, Y., Zhu, K., and Kasikci, B. Fiddler:
Cpu-gpu orchestration for fast inference of mixture-of-
experts models. arXiv preprint arXiv:2402.07033, 2024.
Kamsetty, A., Chen, H., and Xie, L. How bytedance scales
offline inference with multi-modal llms to 200tb data.
https://www.anyscale.com/blog/how-bytedance-scales-
offline-inference-with-multi-modal-llms-to-200TB-data,
August 2023. Accessed: 2024-10-30.
Kwon, W., Li, Z., Zhuang, S., Sheng, Y., Zheng, L., Yu,
C. H., Gonzalez, J., Zhang, H., and Stoica, I. Efficient
memory management for large language model serving
with pagedattention. In Proceedings of the 29th Sym-
posium on Operating Systems Principles, pp. 611–626,
2023.
Li, S., Xue, F., Baranwal, C., Li, Y., and You, Y. Sequence
parallelism: Long sequence training from system perspec-
tive. arXiv preprint arXiv:2105.13120, 2021.
Li, Z., Zheng, L., Zhong, Y., Liu, V., Sheng, Y., Jin, X.,
Huang, Y., Chen, Z., Zhang, H., Gonzalez, J. E., et al.
{AlpaServe}: Statistical multiplexing with model paral-
lelism for deep learning serving. In 17th USENIX Sympo-
sium on Operating Systems Design and Implementation
(OSDI 23), pp. 663–679, 2023.
Lin, B., Peng, T., Zhang, C., Sun, M., Li, L., Zhao, H., Xiao,
W., Xu, Q., Qiu, X., Li, S., et al. Infinite-llm: Efficient llm
service for long context with distattention and distributed
kvcache. arXiv preprint arXiv:2401.02669, 2024.
Liu, H., Zaharia, M., and Abbeel, P. Ring attention with
blockwise transformers for near-infinite context. arXiv
preprint arXiv:2310.01889, 2023.
Liu, S., Biswal, A., Cheng, A., Mo, X., Cao, S., Gonzalez,
J. E., Stoica, I., and Zaharia, M. Optimizing llm queries in
relational workloads. arXiv preprint arXiv:2403.05821,
2024.
Mei, Y., Zhuang, Y., Miao, X., Yang, J., Jia, Z., and Vinayak,
R. Helix: Distributed serving of large language models
via max-flow on heterogeneous gpus. arXiv preprint
arXiv:2406.01566, 2024.
Miao, X., Oliaro, G., Zhang, Z., Cheng, X., Jin, H., Chen,
T., and Jia, Z. Towards efficient generative large language
model serving: A survey from algorithms to systems.
arXiv preprint arXiv:2312.15234, 2023.
Miao, X., Shi, C., Duan, J., Xi, X., Lin, D., Cui, B., and Jia,
Z. Spotserve: Serving generative large language models
on preemptible instances. In Proceedings of the 29th ACM
International Conference on Architectural Support for
Programming Languages and Operating Systems, Volume
2, pp. 1112–1127, 2024.
MLCommons. Mlperf inference: Datacenter benchmark
suite. https://mlcommons.org/benchmarks/
inference-datacenter/, 2024. Accessed: 2024-
10-30.
Narayan, A., Chami, I., Orr, L., Arora, S., and R´e, C. Can
foundation models wrangle your data? arXiv preprint
arXiv:2205.09911, 2022.
Narayanan, D., Harlap, A., Phanishayee, A., Seshadri, V.,
Devanur, N. R., Ganger, G. R., Gibbons, P. B., and Za-
haria, M. Pipedream: Generalized pipeline parallelism for
dnn training. In Proceedings of the 27th ACM symposium
on operating systems principles, pp. 1–15, 2019.
NVIDIA. Fastertransformer: Transformer related optimiza-
tion, including bert, gpt.
https://github.com/
NVIDIA/FasterTransformer, 2024a.
NVIDIA. Tensorrt-llm: Optimized inference for large lan-
guage models.
https://github.com/NVIDIA/
TensorRT-LLM, 2024b.
NVIDIA Corporation. Nvidia a100 pcie product brief, 2020.
URL
https://www.nvidia.com/content/
dam/en-zz/Solutions/Data-Center/a100/
pdf/A100-PCIE-Prduct-Brief.pdf. Accessed:
2024-10-24.
NVIDIA Corporation. NVIDIA NVLink: High-Speed GPU
Interconnect, 2024.
URL https://www.nvidia.
com/en-us/data-center/nvlink/. Accessed:
2024-10-26.
OpenAI. Chatgpt (gpt-4), 2024. URL https://www.
openai.com/research/gpt-4. Accessed: 2024-
08-02.

=== Page 13 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
Pan, X., Li, E., Li, Q., Liang, S., Shan, Y., Zhou, K., Luo,
Y., Wang, X., and Zhang, J. Instinfer: In-storage attention
offloading for cost-effective long-context llm inference.
arXiv preprint arXiv:2409.04992, 2024.
Patel, P., Choukse, E., Zhang, C., Shah, A., Goiri, ´I., Maleki,
S., and Bianchini, R. Splitwise: Efficient generative llm
inference using phase splitting. In 2024 ACM/IEEE 51st
Annual International Symposium on Computer Architec-
ture (ISCA), pp. 118–132. IEEE, 2024.
PCI-SIG.
PCI-SIG
Releases
PCIe
4.0,
Ver-
sion
1.0,
2017.
URL
https://pcisig.
com/pci-sig-releases-pcie%C2%
AE-40-version-10.
Pope, R., Douglas, S., Chowdhery, A., Devlin, J., Bradbury,
J., Heek, J., Xiao, K., Agrawal, S., and Dean, J. Efficiently
scaling transformer inference. Proceedings of Machine
Learning and Systems, 5:606–624, 2023.
Qin, R., Li, Z., He, W., Zhang, M., Wu, Y., Zheng, W., and
Xu, X. Mooncake: Kimi’s kvcache-centric architecture
for llm serving. arXiv preprint arXiv:2407.00079, 2024.
Rajbhandari, S., Rasley, J., Ruwase, O., and He, Y. Zero:
Memory optimizations toward training trillion parameter
models. In SC20: International Conference for High Per-
formance Computing, Networking, Storage and Analysis,
pp. 1–16. IEEE, 2020.
Ren, J., Rajbhandari, S., Aminabadi, R. Y., Ruwase, O.,
Yang, S., Zhang, M., Li, D., and He, Y. {Zero-offload}:
Democratizing {billion-scale} model training. In 2021
USENIX Annual Technical Conference (USENIX ATC
21), pp. 551–564, 2021.
Roziere, B., Gehring, J., Gloeckle, F., Sootla, S., Gat, I.,
Tan, X. E., Adi, Y., Liu, J., Sauvestre, R., Remez, T., et al.
Code llama: Open foundation models for code. arXiv
preprint arXiv:2308.12950, 2023.
ShareGPT.
Sharegpt
vicuna
unfiltered
dataset.
https://huggingface.co/datasets/
anon8231489123/ShareGPT_Vicuna_
unfiltered, 2023. Apache 2.0 License.
Sheng, Y., Zheng, L., Yuan, B., Li, Z., Ryabinin, M., Chen,
B., Liang, P., R´e, C., Stoica, I., and Zhang, C. Flexgen:
High-throughput generative inference of large language
models with a single gpu. In International Conference
on Machine Learning, pp. 31094–31116. PMLR, 2023.
Shoeybi, M., Patwary, M., Puri, R., LeGresley, P., Casper,
J., and Catanzaro, B.
Megatron-lm: Training multi-
billion parameter language models using model paral-
lelism. arXiv preprint arXiv:1909.08053, 2019.
Song, Y., Mi, Z., Xie, H., and Chen, H. Powerinfer: Fast
large language model serving with a consumer-grade gpu.
arXiv preprint arXiv:2312.12456, 2023.
Srivatsa, V., He, Z., Abhyankar, R., Li, D., and Zhang, Y.
Preble: Efficient distributed prompt scheduling for llm
serving. 2024.
Touvron, H., Lavril, T., Izacard, G., Martinet, X., Lachaux,
M.-A., Lacroix, T., Rozi`ere, B., Goyal, N., Hambro, E.,
Azhar, F., et al. Llama: Open and efficient foundation lan-
guage models. arXiv preprint arXiv:2302.13971, 2023a.
Touvron, H., Martin, L., Stone, K., Albert, P., Almahairi,
A., Babaei, Y., Bashlykov, N., Batra, S., Bhargava, P.,
Bhosale, S., et al. Llama 2: Open foundation and fine-
tuned chat models. arXiv preprint arXiv:2307.09288,
2023b.
Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones,
L., Gomez, A. N., Kaiser, Ł., and Polosukhin, I. At-
tention is all you need. Advances in neural information
processing systems, 30, 2017.
vLLM Team. Performance update: Bringing vllm to the
next level.
https://blog.vllm.ai/2024/09/
05/perf-update.html, 2024. Accessed: 2024-10-
14.
Xuanlei, Z., Jia, B., Zhou, H., Liu, Z., Cheng, S., and You,
Y. Hetegen: Efficient heterogeneous parallel inference for
large language models on resource-constrained devices.
Proceedings of Machine Learning and Systems, 6:162–
172, 2024.
Xue, F., Chen, Y., Li, D., Hu, Q., Zhu, L., Li, X., Fang, Y.,
Tang, H., Yang, S., Liu, Z., et al. Longvila: Scaling long-
context visual language models for long videos. arXiv
preprint arXiv:2408.10188, 2024.
Yu,
C.,
Lee,
S.,
Xu,
R.,
Lin,
W.,
Gorthy,
P.,
and Liaw, R.
Batch llm inference on anyscale
slashes aws bedrock costs by up to 6x, October
2024. URL https://www.anyscale.com/blog/
batch-llm-inference-announcement.
Ac-
cessed: 2024-10-30.
Yu, G.-I., Jeong, J. S., Kim, G.-W., Kim, S., and Chun, B.-
G. Orca: A distributed serving system for {Transformer-
Based} generative models. In 16th USENIX Symposium
on Operating Systems Design and Implementation (OSDI
22), pp. 521–538, 2022.
Yuan, Z., Shang, Y., Zhou, Y., Dong, Z., Xue, C., Wu, B.,
Li, Z., Gu, Q., Lee, Y. J., Yan, Y., et al. Llm inference
unveiled: Survey and roofline model insights.
arXiv
preprint arXiv:2402.16363, 2024.

=== Page 14 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
Zhao, J., Wan, B., Peng, Y., Lin, H., and Wu, C. Llm-
pq: Serving llm on heterogeneous clusters with phase-
aware partition and adaptive quantization. arXiv preprint
arXiv:2403.01136, 2024.
Zhao, Y., Gu, A., Varma, R., Luo, L., Huang, C.-C., Xu, M.,
Wright, L., Shojanazeri, H., Ott, M., Shleifer, S., et al.
Pytorch fsdp: experiences on scaling fully sharded data
parallel. arXiv preprint arXiv:2304.11277, 2023.
Zheng, L., Li, Z., Zhang, H., Zhuang, Y., Chen, Z., Huang,
Y., Wang, Y., Xu, Y., Zhuo, D., Xing, E. P., et al. Alpa:
Automating inter-and {Intra-Operator} parallelism for
distributed deep learning. In 16th USENIX Symposium
on Operating Systems Design and Implementation (OSDI
22), pp. 559–578, 2022.
Zheng, L., Yin, L., Xie, Z., Huang, J., Sun, C., Yu, C. H.,
Cao, S., Kozyrakis, C., Stoica, I., Gonzalez, J. E., et al.
Efficiently programming large language models using
sglang. arXiv preprint arXiv:2312.07104, 2023.
Zhong, Y., Liu, S., Chen, J., Hu, J., Zhu, Y., Liu, X., Jin,
X., and Zhang, H. Distserve: Disaggregating prefill and
decoding for goodput-optimized large language model
serving. arXiv preprint arXiv:2401.09670, 2024.
Zhu, K., Zhao, Y., Zhao, L., Zuo, G., Gu, Y., Xie, D., Gao,
Y., Xu, Q., Tang, T., Ye, Z., et al. Nanoflow: Towards
optimal large language model serving throughput. arXiv
preprint arXiv:2408.12757, 2024.
A
PERFORMANCE MODEL
In this section, we examine the trade-offs of various paral-
lelism strategies by developing an analytical performance
model. We break down the model’s inference time into
multiple components and analyze the impact of each paral-
lelism type on these components. The results reveal that the
proportion of these components differs across workloads,
resulting in distinct scaling behaviors for each parallelism
strategy. Table 2 lists the notations used in our analysis. We
assume the data type is float16.
Table 2. Notations
N
number of output tokens
T linear
dm
time of moving weights
r
number of requests
T attn
dm
time of moving kvcache
b
(global) batch size
T linear
c
time of computation
s
average sequence length
T attn
c
computation of attention
hq
number of heads
Tnw
time of communication
d
head dimension
hkv
number of KV heads
L
number of layers
W
#parameters of one layer
PP
pipeline parallel degree
DP
data parallel degree
TP
tensor parallel degree
Table 3. Different components of the runtime of a forward pass.
The batch size b representing the batching effect is emphasized.
T linear
dm
T linear
comp
T attn
dm
T attn
comp
Tnw(TP)
Prefill
2W
BHBM
2bW s
FLOPS
2bs(hq+2hkv)d
BHBM
bhqs2d2
FLOPS
4bshqd
Bar(T P )
Decode
2W
BHBM
2bW
FLOPS
4bshkvd
BHBM
2bhqsd2
FLOPS
4bhqd
Bar(T P )
A.1
Runtime Break-Down
The runtime of each decoding layer can be divided into three
components: 1) data movement (Tdm) from GPU global
memory (HBM) to compute units, which includes transfer-
ring weights (T linear
dm ) and KV cache (T attn
dm), 2) computation
Tcomp, including T linear
comp and T attn
comp, and 3) communication
cost Tnw (nw stands for network), primarily arising from the
all-reduce operation in tensor parallelism. Based on the roof-
line model, the runtime of each layer can be approximated
as TL = max(T linear
dm , T linear
comp) + max(T attn
dm, T attn
comp) + Tnw.
Data Movement.
The runtime of data movement can be
approximated as transferred data volume divided by the
bandwidth, which is the HBM bandwidth for GPUs. For lin-
ear layers, the transferred data is mostly weight matrices, of
which the size is 2W bytes, which is constant. For attention
layers, the transferred data is most the Q, K, and V matrices,
which is 2bs(hq + 2hkv)d bytes in prefilling and 4bshkvd
in decoding.
Compute.
The computation time can be approximated as
the number of floating operations (FLOPs) divided by the
number of floating operations per second of the hardware
(FLOP/s). For linear layers, the FLOPs is proportional to
the weight parameters times the number of tokens, which
is 2Wbs in prefilling and 2Wb in decoding. For attention
layers, most operations come from computing the attention
score, which is approximated as bhqs2d2 in prefilling and
2bhqsd2 in decoding.
Communication.
The communication cost mostly comes
from the all-reduce operation in tensor parallelism. It can
be modeled as the transferred data volume divided by the
bandwidth. We denote it as Tnw(TP), and approximate it as
b · A/Bar(TP) where A is the size of the activation of one
request within a batch and Bar(TP) is the all-reduce band-
width. Tnw(TP) is monotonically increasing with TP as
additional GPUs and more replicas of activations are added
to all-reduce. We omit the peer-to-peer communication over
in pipeline parallel since it is negligible compared to the
all-reduce operation of tensor parallel.
A.2
Batching Analysis
Batching is critical in decoding. It significantly affects the
latency and throughput. Batch size represents how many

=== Page 15 ===
Seesaw: High-throughput LLM Inference via Model Re-sharding
TP1DP8
TP2DP4
TP4DP2
TP8DP1
0.00
0.25
0.50
0.75
1.00
Runtime per Request
OOM
load weight
compute
allreduce
0
50
100
150
Batch Size
Batch Size
Figure 15. How data parallelism affects the decoding throughput.
Data parallelism has minimal communication overhead but suffers
from caused by inefficient memory access caused by duplicating
model weights. Model duplicates occupy more GPU memory,
leaving less space for KV cache and smaller batch sizes. With
more data parallelism, the overhead of loading data from GPU
global memory to compute units significantly increases.
requests are processed in one forward pass, and larger batch
sizes can amortize the cost of transferring weights, thus
improving the throughput.
Global and micro-batch size.
In distributed inference
such as multi-GPU settings, we define the global batch size
b as the number of requests being actively processed by the
whole cluster. It is a tunable hyper-parameter that represents
the overall workload of the system. It is bounded by the
maximal batch size, which is determined by the memory
budget. On the other side, the micro batch size is defined
at the device level as the batch size processed during each
forward pass. Tensor parallelism does not affect the batch
size while DP and PP shrink the micro batch size.
A.3
Parallelism Analysis
We consider three types of parallelism: data parallelism,
tensor parallelism, and pipeline parallelism, and denote their
degree of parallelism as DP, TP, and PP respectively.
Tensor parallelism
can accelerate both data moving
(T linear
dm
and T attn
dm are reduced to 1/TP) and computation
Tcomp (reduced to Tcomp/TP), at the cost of all reduce over-
head Tnw.
Data parallelism
distributes the global batch size b onto
DP micro-batches processed in parallel. The model is du-
plicated so T linear
dm
remains unchanged. T attn
dw , T linear
comp, T attn
comp,
Tnw are reduced as the batch size is smaller. Due to the
need to duplicate model weights, the GPU memory left for
the KV cache is smaller. The spare space for KV cache on
each GPU is Mkv = M −
2LW
T P ·P P . The maximal batch size
is
bmax = DP · Mkv · TP · PP
4Lhkvds
= DP · M · TP · PP −2LW
4Lhkvds
While TP and PP can super-linearly scale the batch size, DP
can only linearly scale the batch size. The trade-off between
limited batch sizes and reduced communication overhead is
shown in Figure 15.
Pipeline parallelism
distributes different layers to dif-
ferent devices, and each device will have L/PP layers. It
cannot reduce single-request latency but is more suitable for
throughput-oriented scenarios as it introduces less commu-
nication overhead. However, it is not the ultimate answer
of high-throughput applications because of an important
observation that pipeline parallelism harms maximal batch
size. A tricky nuance is that given a batch size b, pipeline
parallelism can only process b/PP of them simultaneously
in order to utilize and pipeline all PP GPUs, which is harm-
ful to batching. If the workload is not uniformly distributed
across GPUs, there will be bubbles, or in the worst case,
some GPUs might be idle. When the pipeline is fully and
stably pipelining, each time the last pipeline stage finishes
its L/PP layers of forward pass, a micro-batch of b/PP will
be finished.
Throughput.
The micro-batch size on each GPU is
b/(PP · DP). The total runtime of generating one micro
batch with size b/(PP · DP) on one DP replica (or more
specifically, the time of the last pipeline stage finishing a
micro-batch) is
Tstage = L
PP ·
"
max(T linear
dm
TP ,
T linear
comp
DP · TP · PP)+
+ max(T attn
dm, T attn
comp)
DP · TP · PP
+ Tnw(TP)
PP · DP

The throughput (number of processed requests per unit time)
is b/PP/T. For simplicity, we calculate the inverse of it as
throughput−1 = Tstage
b/PP = L
b ·
"
max(T linear
dm
TP ,
T linear
comp
DP · TP · PP)
+ max(T attn
dm, T attn
comp)
DP · TP · PP
+ Tnw(TP)
PP · DP

(1)
If we approximate the roof-line model with a simplified
additional model, this expression can be simplified as:
throughput−1 ∝T linear
dm
TP
+ T linear
comp + T attn
dm + T attn
comp
DP · TP · PP
+ Tnw(TP)
PP · DP
(2)
