
=== Page 1 ===
CLIP Under the Microscope: A Fine-Grained Analysis of Multi-Object
Representation
Reza Abbasi, Ali Nazari, Aminreza Seﬁd, Mohammadali Banayeeanzade,
Mohammad Hossein Rohban, Mahdieh Soleymani Baghshah
Sharif University of Technology, Tehran, Iran
{reza.abbasi, ali.nazari02, aminreza.sefid, a.banayeean, rohban, soleymani}@sharif.edu
Abstract
Contrastive Language-Image Pre-training (CLIP) mod-
els excel in zero-shot classiﬁcation, yet face challenges in
complex multi-object scenarios. This study offers a com-
prehensive analysis of CLIP’s limitations in these contexts
using a specialized dataset, ComCO, designed to evaluate
CLIP’s encoders in diverse multi-object scenarios.
Our
ﬁndings reveal signiﬁcant biases: the text encoder prior-
itizes ﬁrst-mentioned objects, and the image encoder fa-
vors larger objects.
Through retrieval and classiﬁcation
tasks, we quantify these biases across multiple CLIP vari-
ants and trace their origins to CLIP’s training process, sup-
ported by analyses of the LAION dataset and training pro-
gression. Our image-text matching experiments show sub-
stantial performance drops when object size or token order
changes, underscoring CLIP’s instability with rephrased
but semantically similar captions. Extending this to longer
captions and text-to-image models like Stable Diffusion,
we demonstrate how prompt order inﬂuences object promi-
nence in generated images. For more details and access to
our dataset and analysis code, visit our project repository:
https://clip-oscope.github.io/.
1. Introduction
The convergence of vision and language in artiﬁcial in-
telligence has led to the development of Vision-Language
Models (VLMs) that can interpret and generate multimodal
content. Among these, OpenAI’s Contrastive Language-
Image Pre-training (CLIP) model [13] has been particu-
larly inﬂuential, demonstrating remarkable capabilities in
zero-shot image classiﬁcation and setting new standards for
multimodal understanding [3, 5, 18, 20]. The success of
CLIP has catalyzed a wide array of applications—from im-
age retrieval and visual question answering to text-to-image
generation—signifying a paradigm shift in how models per-
ceive and relate visual and linguistic information.
Visual Language Models like CLIP face signiﬁcant
challenges in understanding and reasoning about complex
scenes with multiple objects and intricate relationships.
CLIP struggles to identify distinct objects and model their
relationships accurately, especially when captions contain
the same objects but differ in their relationships. This re-
sults in difﬁculty distinguishing between similar captions
with different object relationships.
Several benchmark
datasets have been introduced to elucidate the limitations of
existing models in capturing subtle relational nuances. No-
tably, Winoground [20], VL-CheckList [23], ARO [21], and
CREPE [10] have been instrumental in evaluating models’
capacities to accurately match images with semantically ap-
propriate captions.
Numerous studies have addressed compositionality chal-
lenges in multi-object scenarios, often through end-to-end
methods like ﬁne-tuning with hard-negative samples [21] to
improve model performance. However, these approaches
have faced criticism and subsequent reﬁnement, as seen in
methods like SUGARCREPE [8] and [17], which generate
negative captions with minor structural changes or LLMs
to highlight semantic distinctions.
While most focus on
CLIP’s ability to distinguish structurally similar yet concep-
tually different captions, few studies, such as Dumpala et al.
[4], explore CLIP’s performance on semantically equivalent
but structurally distinct captions, revealing a gap in under-
standing CLIP’s inconsistency with such prompts.
While previous studies have advanced our understanding
of CLIP’s limitations, our work uniquely focuses on CLIP’s
performance with semantically equivalent but structurally
varied captions rather than simply distinguishing conceptu-
ally different captions. This shift enables a deeper exam-
ination of the model’s grasp of language and visual con-
tent, where systematic errors reveal potential biases. Un-
like prior works that primarily propose benchmarks or end-
to-end solutions, we investigate the root causes of CLIP’s
behavior, delving into the mechanisms of both image and
text encoders to uncover why the model displays biases
and lacks robustness to certain linguistic and visual varia-
This CVPR paper is the Open Access version, provided by the Computer Vision Foundation.
Except for this watermark, it is identical to the accepted version;
the final published version of the proceedings is available on IEEE Xplore.
9308

=== Page 2 ===
Figure 1. Overview of our key contributions. Step 1: We create ComCO dataset for controlled multi-object experiments. Step 2: We
identify biases in CLIP’s image encoder (favoring larger objects) and text encoder (prioritizing ﬁrst-mentioned objects). Step 3: We
investigate the origin of these biases, ﬁnding a connection to training data characteristics. Step 4: We demonstrate the practical impacts of
these biases on image-text matching task, showing how they affect model performance in multi-object scenarios.
tions. To support this analysis, we introduce the ComCO
dataset, purpose-built for examining CLIP’s performance
under controlled multi-object scenarios. Our study spans
multiple versions of CLIP trained on diverse datasets and ar-
chitectures, ensuring the broad applicability of our ﬁndings.
This comprehensive approach aims to deepen our under-
standing of CLIP’s limitations and pave the way for more
adaptable vision-language models. Beyond CLIP, our in-
sights have signiﬁcant implications for text-to-image (T2I)
generative models and multimodal large language models
(MLLMs), where decoding CLIP’s encoding intricacies can
inform advancements in artiﬁcial intelligence across do-
mains. As shown in Figure 1, our key contributions are as
follows:
• Development of Novel Dataset: We introduce ComCO,
a specialized dataset for creating controlled multi-object
scenarios.
Unlike previous benchmarks, ComCO al-
lows control over object size and caption order, enabling
precise analysis of model performance across composi-
tional challenges and enhancing understanding of VLMs’
strengths and weaknesses.
• Encoder Analysis: We conduct an in-depth examination
of CLIP’s image and text encoders in multi-object scenes,
revealing weaknesses in preserving information for object
distinction and identifying where compositional informa-
tion is lost.
• Bias Identiﬁcation: Our study reveals that CLIP’s im-
age encoder prefers larger objects, while the text encoder
favors ﬁrst-mentioned and visually larger objects, high-
lighting biases in CLIP’s handling of visual and linguistic
information.
• Investigation of Bias Origins: We explore the origins of
these biases, showing that larger objects are often men-
tioned earlier in CLIP’s training captions, and are favored
in embeddings due to the abundance of their visual to-
kens. We substantiate this with analyses of the LAION
dataset and CLIP’s training progression.
• Practical Impact: We show how these biases affect per-
formance in multi-object tasks, with signiﬁcant drops in
image-text matching accuracy in ComCO and COCO [9].
These biases also extend to text-to-image models, inﬂu-
encing object prominence based on prompt order.
These ﬁndings reveal how biases in CLIP’s text and im-
age encoders signiﬁcantly reduce its performance in multi-
object scenarios, emphasizing the need to address these bi-
ases to enhance vision-language models’ robustness. Our
work offers key insights into CLIP’s behavior and lays
groundwork for improving model performance in real-
world applications.
2. Methodology
2.1. Dataset Design
To thoroughly evaluate the performance of CLIP models
in multi-object scenarios under controlled conditions, we
constructed the ComCO (Complex COCO Objects) dataset.
Utilizing Blender software allowed us precise control over
the number, location, and dimensions of objects in the im-
ages (see Appendix 7.1). The ComCO dataset comprises
72 objects derived from the COCO dataset. We generated
9309

=== Page 3 ===
images containing 2, 3, 4, and 5 objects. Each image is
paired with a speciﬁc caption that accurately describes the
objects present. This approach ensures high control over
the dataset and minimizes confounding factors, providing a
robust platform for evaluating the CLIP models.
We deliberately chose not to use text-to-image models
for generating these datasets due to two main reasons. First,
these models often lack the capability to produce high-
quality, fully controlled multi-object images. Second, since
CLIP is used in many of these models, utilizing them could
introduce unwanted biases into our evaluations.
2.2. Experimental Framework for Encoder Analy-
sis
The main goal of this study is to evaluate the performance of
CLIP’s text and image encoders separately in multi-object
scenarios. We aim to analyze the impact and contribution of
each object in the ﬁnal output of the encoders. To achieve
this, we conducted experiments using our designed ComCO
dataset, with images and captions containing two to ﬁve ob-
jects. To ensure the generalizability of our ﬁndings, we also
validated our results on the widely-used COCO dataset. We
designed two sets of experiments: retrieval-based experi-
ments and classiﬁcation-based experiments. Given the con-
sistency of the results in both types of experiments, we have
included the classiﬁcation results in the appendix 7.2 and
7.4 and explain the retrieval-based experiments bellow.
2.2.1. TEXT-BASED OBJECT RETRIEVAL (TOR)
The Text-based Object Retrieval task evaluates how well
CLIP’s text encoder can identify individual objects within
multi-object captions. As illustrated in Figure 2a, this ex-
periment involves several steps: First, we use CLIP’s text
encoder to create embeddings for both multi-object captions
and single-object captions. We then measure the similar-
ity between each multi-object caption embedding and all
single-object caption embeddings. The single-object cap-
tion with the highest similarity score is considered the ”re-
trieved” object. To assess performance, we calculate re-
trieval accuracy for each object position in the multi-object
captions. This helps us identify any biases related to an
object’s position within a caption, such as favoring objects
mentioned ﬁrst or last.
2.2.2. IMAGE-BASED OBJECT RETRIEVAL (IOR)
The Image-based Object Retrieval task is similar to TOR
but focuses on CLIP’s image encoder. As shown in Fig-
ure 2b, this experiment involves several steps: We begin
by using CLIP’s image encoder to generate embeddings
for multi-object images and single-object images. We then
compute similarity scores between each multi-object image
embedding and all single-object image embeddings. The
single-object image with the highest similarity score is con-
sidered the ”retrieved” object. To evaluate performance, we
calculate retrieval accuracy for different object size cate-
gories (e.g., large, small) within the multi-object images.
This allows us to determine if the image encoder shows any
preference for objects of a particular size.
We also experimented with a variation of ComCO, called
SimCO, where objects were replaced with simple geometric
shapes from the CLEVR dataset. This was done to conﬁrm
that bias persists even with non-natural, geometric objects.
Further details are provided in Appendix 7.1.
3. Results and Analysis
Our experiments revealed signiﬁcant biases in both the
text and image encoders of the CLIP model. This section
presents our ﬁndings, organized by encoder type and focus-
ing on retrieval tasks.
3.1. Text Encoder Biases
We observed a consistent bias in the text encoder towards
the ﬁrst object mentioned in descriptions. In the TOR ex-
periment, the retrieval accuracy (as shown in Table 1) was
highest for the ﬁrst object, indicating its dominant inﬂuence
on the overall text representation. This suggests that the
text encoder prioritizes the initial object, leading to its more
accurate retrieval compared to subsequent objects. The de-
tailed results for the scenarios involving 2, 3, and 5 objects
can be found in the appendix 7.3, and experiments on longer
caption templates are in Appendix 7.6 and 7.7.
3.2. Image Encoder Biases
In multi-object images, the image encoder exhibited a
strong bias towards larger objects. The Image-based Ob-
ject Retrieval IOR experiment, detailed in Table 2, shows
that larger objects were more frequently and accurately re-
trieved during single-object image searches. This ﬁnding
highlights the image encoder’s bias towards larger objects,
which receive disproportionate emphasis in the ﬁnal image
representation. Further detailed results, speciﬁcally for sce-
narios with 2, 3, and 5 objects, are provided in the appendix
7.5.
3.3. COCO Dataset Experiments
To validate the generalizability of our ﬁndings from the
synthetic dataset, we conducted similar experiments on the
COCO dataset, which comprises real images with accom-
panying captions. This real-world dataset allowed us to in-
vestigate whether the previously observed biases persist in
more naturalistic settings.
Due to the absence of single-object images for COCO
objects, we approached the IOR experiment in two ways.
First, we used single-object images from the DomainNet
dataset [11] as retrieval targets. Second, we introduced an
alternative approach called Image-to-Text Object Retrieval
(I2TOR). In I2TOR, we used the textual names of COCO
9310

=== Page 4 ===
%DVH,PDJHb
7KUHH2EMHFWV,PDJH
6LQJOH2EMHFW,PDJHZKLFK
PDWFKLQJb%DVH,PDJH
&/,36FRUH
&/,36FRUH
&/,36FRUH
2WKHUb6LQJOHb2EMHFW
,PDJHV
&/,36FRUH
&/,36FRUH

&/,36FRUH






E
D
&/,3b
,PDJH
(QFRGHU
&/,3b
,PDJH
(QFRGHU
&/,3b
,PDJH
(QFRGHU
&/,3b
,PDJH
(QFRGHU
&/,3b
,PDJH
(QFRGHU
&/,3b
,PDJH
(QFRGHU
&/,3b
,PDJH
(QFRGHU
&/,36FRUH
&/,36FRUH
&/,36FRUH
&/,36FRUH
&/,36FRUH

&/,36FRUH






&/,3b
7H[W
(QFRGHU
&/,3b
7H[W
(QFRGHU
&/,3b
7H[W
(QFRGHU
&/,3b
7H[W
(QFRGHU
&/,3b
7H[W
(QFRGHU
&/,3b
7H[W
(QFRGHU
&/,3b
7H[W
(QFRGHU
%DVH7H[Wb
7KUHH2EMHFWV7H[W
6LQJOH2EMHFW7H[WZKLFK
PDWFKLQJb%DVH7H[W
2WKHUb6LQJOHb2EMHFW
7H[WV
SL]]DDQGbDSSOH
DQGbGHVN
DSSOH
SL]]D
GHVN
KDW
FDU
D[H


725
,25
Figure 2. Experimental setup for Text-based Object Retrieval (TOR) and Image-based Object Retrieval (IOR) tasks. a) TOR: The CLIP
text encoder generates embeddings for multi-object and single-object texts. Cosine similarity scores are calculated between the base text
embedding and single-object text embeddings to identify the most similar object. b) IOR: The CLIP image encoder generates embeddings
for multi-object and single-object images. Cosine similarity scores are calculated between the base image embedding and single-object
image embeddings to identify the most similar object.
Table 1. Performance on TOR for ComCO datasets
Task
Model
First Obj
Second Obj
Third Obj
Fourth Obj
TOR
CLIP LAION
63.96
21.59
10.68
3.76
CLIP Datacomp
71.13
16.26
8.74
3.87
CLIP Roberta
44.03
23.73
18.07
14.18
SIGLIP
58.11
21.16
10.99
9.73
CLIP openAI
50.31
20.74
14.45
6.79
NegCLIP
51.63
28.92
14.86
4.59
SugarCrepe
44.29
30.32
18.73
6.66
Table 2. Performance on IOR for ComCO datasets
Task
Model
Large Object
Small Obj 1
Small Obj 2
Small Obj 3
IOR
CLIP LAION
85.45
6.36
5.45
2.73
CLIP Datacomp
85.16
5.65
4.95
4.24
CLIP Roberta
87.40
8.66
2.36
1.57
SIGLIP
77.66
10.11
6.38
5.85
CLIP openAI
65.22
17.39
8.70
8.70
NegCLIP
61.67
15.00
13.33
10.00
SugarCrepe
60.0
18.38
16.85
4.7
objects instead of single-object images. These object names
were embedded using CLIP’s text encoder, allowing us to
perform a retrieval task consistent with the IOR methodol-
ogy while adapting to the constraints of the COCO dataset.
Tables 3 and 4 present the results of our COCO dataset
experiments. In TOR, the ﬁrst-mentioned object in COCO
captions was retrieved with higher accuracy, which aligns
with our earlier ﬁndings of bias in the text encoder. Simi-
larly, in IOR, larger objects in COCO images were retrieved
more accurately, consistent with the trends observed in our
synthetic dataset experiments. The I2TOR results further
conﬁrmed this bias, demonstrating that even when using
textual object representations, the bias towards larger ob-
Table 3. Performance on TOR for coco dataset
Task
Model
First Obj
Second Obj
Third Obj
Fourth Obj
TOR
CLIP openAI
35.24
21.90
20.48
22.38
CLIP LAION
67.89
13.76
8.26
10.09
CLIP Datacomp
57.68
17.68
12.75
11.88
CLIP Roberta
40.78
23.30
20.39
15.53
SIGLIP
49.47
26.84
12.11
11.58
NegCLIP
38.69
22.11
17.09
22.11
Table 4. Performance on IOR for coco dataset
Task
Model
Large Object
Small Obj 1
Small Obj 2
Small Obj 3
IOR
CLIP openAI
43.02
28.82
17.13
11.03
CLIP LAION
39.44
28.45
17.70
14.41
CLIP Datacomp
36.71
29.55
19.13
14.61
CLIP Roberta
36.71
28.61
19.82
14.86
SIGLIP
36.63
28.29
20.02
15.06
NegCLIP
44.04
28.86
16.48
10.62
I2TOR
CLIP openAI
51.49
24.87
13.68
9.97
CLIP LAION
45.50
27.02
15.91
11.56
CLIP Datacomp
46.64
26.82
14.53
12.01
CLIP Roberta
44.69
26.98
16.04
12.29
SIGLIP
47.09
27.07
15.10
10.74
NegCLIP
49.04
27.07
14.08
9.81
jects persists.
Our experiments reveal two signiﬁcant biases in the
CLIP model: the text encoder shows a strong preference for
the ﬁrst mentioned object in textual descriptions, while the
image encoder exhibits greater sensitivity to larger objects
in images. These biases can signiﬁcantly impact the overall
system performance in various vision-language tasks, par-
ticularly in multi-object scenarios.
9311

=== Page 5 ===
4. Origin of Bias in CLIP Models
In this section, we investigate the potential origins of the
biases observed in CLIP models and provide evidence sup-
porting our hypotheses.
4.1. Bias in the Image Encoder
The observed bias favoring larger objects within the image
domain can be attributed to the architectural characteristics
of Vision Transformers (ViT) [2] utilized in CLIP’s image
encoder. Our hypothesis is that larger objects, which occupy
a greater number of patches in the ViT’s patch-based image
representation, exert a more signiﬁcant inﬂuence on the ﬁ-
nal class (CLS) token representation. This bias is not exclu-
sive to CLIP; it appears to be a consistent feature across ViT
models, as demonstrated by our experiments detailed in the
appendix.
To substantiate this hypothesis, we designed an experi-
ment to quantify the attention allocated by the CLS token
to each image patch. By calculating the cumulative atten-
tion received by each object from the CLS token, we could
assess the inﬂuence of object size on attention allocation.
We applied this analysis to our three-object ComCO dataset,
and the results are illustrated in Figure 3. The ﬁndings con-
ﬁrm our hypothesis: larger objects indeed receive more at-
tention from the CLS token.
4.2. Bias in the Text Encoder
We explore the bias present in the text encoder from two
perspectives: the attention mechanism in the model struc-
ture and the model’s training method.
4.2.1. Impact of Attention Mechanism
Text encoder models can be categorized based on their at-
tention mechanisms: uni-directional (causal) attention and
bi-directional attention. In models with causal attention,
each token attends only to preceding tokens, whereas in bi-
directional models, each token attends to all tokens in the
sequence.
When OpenAI introduced the CLIP model, its text en-
coder employed causal attention, meaning each token could
only attend to tokens before it and itself.
This differs
from typical self-attention mechanisms, where tokens at-
tend to all other tokens. Most CLIP models use causal self-
attention, with the exception of the variant using the XLM-
Roberta text encoder, which also employs self-attention.
However, as shown in Table 1, even this model exhibits the
mentioned bias. This indicates that the bias does not origi-
nate from the attention mechanism itself.
4.2.2. Role of Training Method
To determine whether the observed bias is speciﬁc to CLIP
models, we compared CLIP’s text encoder with two other
Table 5. Performance on TOC and TOR for ComCO datasets
Task
Model
First Obj
Second Obj
Third Obj
Fourth Obj
TOR
CLIP
56.28
22.71
13.17
7.48
SBERT
29.02
19.80
17.50
33.57
SimCSE [7]
27.59
19.07
17.76
34.83
models designed to embed sentences into a meaningful se-
mantic space: Sentence-BERT (SBERT) [14] and SimCSE
[7]. The primary distinction is that CLIP’s embedding space
is shared between images and text, whereas SBERT and
SimCSE operate solely in the text domain.
We conducted the TOR experiment on our dataset using
these models. As presented in Table 5, the bias observed in
CLIP differs from that in the other models. This suggests
that CLIP’s unique training method, which aligns images
and text in a shared embedding space through contrastive
learning, contributes to the bias. Therefore, to uncover the
root cause of the bias, we focus on the speciﬁcs of CLIP’s
training procedure.
4.3. Hypothesized Origin of Text-Side Bias in CLIP
We hypothesize that the text-side bias in CLIP, which fa-
vors objects mentioned earlier in text descriptions, origi-
nates from the image-side bias toward larger objects and is
transferred to the text encoder during contrastive training.
We present evidence supporting this hypothesis through two
key claims and an analysis of the training progression.
Claim 1: Larger Objects Have More Inﬂuence on Text
Embeddings.
Building upon the established image-side
bias discussed earlier, we posit that objects with larger
physical sizes exert more inﬂuence on CLIP’s text em-
beddings due to the alignment enforced during contrastive
training. To test this, we categorized objects in the Domain-
Net dataset into large, medium, and small groups based on
their relative physical sizes in real-world (with the full list of
objects provided in the appendix 7.10). Speciﬁcally, objects
smaller than a school bag were categorized as small, objects
sized between a school bag and a medium-sized car were
classiﬁed as medium, and objects larger than a car—up to
signiﬁcantly larger items—were considered large. We then
constructed two sets of sentences, each containing four ob-
jects: one set with a large object mentioned ﬁrst followed by
three medium-sized objects, and another with a small object
mentioned ﬁrst followed by three medium-sized objects.
Figure 4.a compares the TOR accuracy for the ﬁrst ob-
ject in these two groups. The higher TOR accuracy for sen-
tences beginning with large objects supports our hypothe-
sis that larger objects, when mentioned ﬁrst, have a more
signiﬁcant impact on the text embeddings due to the cross-
modal alignment with their prominent representation in im-
ages.
9312

=== Page 6 ===
a)
b)
Figure 3. Attention allocation from the CLS token to objects of different sizes in the ComCO dataset. a) Qualitative results showing the
CLS token’s attention to each object. b) Quantitative analysis of attention distribution across 8,000 images, with each image containing one
large and two small objects. The bar chart shows the average attention allocated to the large object versus the smaller ones, demonstrating
a bias towards larger objects.
a)
b)
c)
Figure 4. a) Top-1 Object Retrieval accuracy comparison for sentences where the ﬁrst object is either large or small. The higher TOR
accuracy for sentences beginning with large objects supports the hypothesis that larger objects, when mentioned ﬁrst, exert a stronger
inﬂuence on text embeddings due to cross-modal alignment with their prominent visual representation in images. b) Distribution of the
position of the largest object within image captions from the LAION datasets. The results show a consistent bias where larger objects
tend to be mentioned earlier in text descriptions. c) Progression of TOR rates across different training stages, indicating that text-side bias
strengthens as the model is exposed to more data, suggesting the cumulative effect of image-side bias being transferred to the text encoder
through contrastive learning.
Claim 2: Caption Bias in Training Datasets.
To inves-
tigate potential biases in CLIP’s training data, we analyzed
both the LAION [19] and COCO datasets. Due to limited
computational resources and the large size of the LAION
dataset, which contains over 2 billion image-text pairs, we
randomly selected a subset of 200,000 samples for our anal-
ysis. Using the Llama3 model, we extracted objects from
the image captions and employed the Language Segment-
Anything tool to generate object masks in the correspond-
ing images, calculating their areas based on these masks. A
detailed description of our LAION dataset analysis method-
ology can be found in Appendix 7.8.
Figure4.b shows the position of the largest object within
each caption. The results indicate that, in the majority of
cases, the largest object in an image is mentioned earlier
in its caption. The same experiment was conducted on the
COCO dataset, with detailed results and the distribution for
two to ﬁve object scenarios provided in Appendix 7.9. This
demonstrates a consistent bias in the training data, where
larger objects are not only more visually prominent but are
also described earlier in text annotations.
Analysis of Bias Development During Training.
To fur-
ther validate our hypothesis, we examined the progression
of text-side bias during CLIP’s training. We utilized model
checkpoints from the LAION dataset at ﬁve training stages,
corresponding to exposure to 2, 4, 6, 8, and 10 billion sam-
ples. We conducted TOR experiments at each stage, focus-
9313

=== Page 7 ===
ing on the retrieval accuracy for the ﬁrst object mentioned
in text descriptions.
Figure4.c depicts the evolution of the TOR rate across
different training stages for scenarios with varying numbers
of objects (from 3 to 8). The consistent upward trend in
the TOR rate as the model is exposed to more training data
suggests that the text-side bias strengthens over time, likely
due to the cumulative effect of the image-side bias being
transferred to the text encoder through contrastive learning.
Incomplete Text Representation of CLIP
Here we want
to theoretically highlight why the CLIP text encoder could
learn an incomplete representation of the text. Let z and
w represent a latent representation of an image content de-
scribed in the caption, and such visual content not men-
tioned in the text, respectively. For example, z represents
the fact that an image contains “a horse that is eating the
grass.” In this case, w might represent other details in the
image, like the “horse color,” “where the horse is located,”
etc. We assume a data generative process as follows:
I := g(z,w)
T := h(z),
where I is the image, and T is its corresponding caption.
Now we want to learn a joint embedding of the image
and text through the CLIP. Here, we assume that fθ(.) and
iω(.) as learnable functions that map the image and text into
the joint embedding space, respectively.
Theorem 1 Let elements of z be independent, zero-mean,
and unit-variance. The contrastive loss for the ideal text en-
coder, iω(T) = z converges to that of a non-ideal incomplete
one, i.e. iω′(T) = zs, where zs is the ﬁrst d −k dimensions
of z, with k being a constant, and d →∞.
Proof: The contrastive loss in making this learning hap-
pen can be written as:
Ez,z′,w

exp(sim(z,z))
exp(sim(z,z))+∑k exp(sim(z,z′
k))

(1)
with
sim(z,z′) = S(fθ(g(z,w),iω(h(z′)))),
and z and {z′
k|1 ≤k ≤b} are b + 1 i.i.d. samples of the
content in the representation space, and S is some normal-
ized similarity metric, e.g. cosine similarity, and b+1 is the
batch size. We assume that elements of z are independent,
unit-variance, and zero mean. We further assume that the
dimensionality of z, denoted as d, goes to inﬁnity.
Under such conditions, and based on Law of Large
Numbers, ∥z∥
p−→
√
d, when d is large.
Therefore, for
any two independent copies of z, z′
k, we have sim(z,z′
k) =
z⊤z′
k/(∥z∥∥z′
k∥)
p−→0.
It is evident that in the ideal case, fθ(g(z,w)) = z and
also iω(h(z)) = z, so the contrastive loss would converge
to e/(e + b), as the numerator is e, and the second term in
the denominator converges to exp(0) = 1, according to the
Mann-Wald’s theorem.
However, we show that other learning of this representa-
tion could achieve the same amount of loss. For instance, let
zs be the ﬁrst d −k elements of z, with k being a constant.
We show that if fθ′(I) = zs and iω′(T) = zs, the same loss
would be achieved in the limit of large d. To see this, note
that the numerator stays the same, i.e. e, while the second
term in the denominator still converges to bexp(0) = b.
This means that even if the image and text encoder of
the CLIP only partially recover the content embedding, they
reach an excellent loss. But such possible incomplete rep-
resentations of z are combinatorially large, making conver-
gence of the CLIP to such local minima pretty likely. This
makes the text encoding of CLIP be far from ideal. Fur-
thermore, the text encoder would become biased, depend-
ing on which of such local minima it converges to. Based
on this explanation, we would expect a text encoder that has
learned a complete representation to exhibit such biases to a
lesser degree. As mentioned earlier, the subject of learning
text representations in VLMs that are discriminative of hard
negatives (e.g. NegCLIP) has been around for few years.
We tested one of strongest such models, [8], in our bench-
mark to validate the hypothesis that an incomplete text rep-
resentation is one of the causes of the bias in the VLMs.
We noticed that this model shows lower bias based on our
benchmark (see the SugarCrepe model in tables 1 and 2).
We have developed an initial approach to address the
identiﬁed bias in the CLIP model, which is presented in
Appendix 7.12. While this method is speciﬁc to our cur-
rent dataset, it represents a promising step toward address-
ing these challenges and can inspire further advancements.
This work demonstrates our commitment to exploring prac-
tical solutions while maintaining the primary focus of this
study on the analysis of bias and its implications.
5. Practical Impacts of Encoder Biases
The biases observed in CLIP’s image and text encoders sig-
niﬁcantly impact model performance in real-world appli-
cations. This section explores how these biases manifest in
image-text matching tasks, while further analyses of text-to-
image generation impacts are presented in Appendix 7.11.
Our analysis in this section serves two primary purposes.
First, it provides concrete evidence of how these theoretical
biases can translate into practical limitations. Second, it of-
fers insights into potential areas for improvement in vision-
language models, particularly in handling complex, multi-
9314

=== Page 8 ===
Figure 5. An example of the correct and incorrect caption structures in the ﬁrst and second scenarios.
object scenarios. Through a series of carefully designed ex-
periments, we illustrate how the biases in both text and im-
age encoders can lead to unexpected or suboptimal results
in tasks that are crucial for many downstream applications.
5.1. Image-Text Matching
Building upon our ﬁndings of biases in CLIP’s image and
text encoders, we now demonstrate how these biases tangi-
bly affect the model’s performance in image-caption match-
ing tasks. We designed two experimental scenarios, con-
ducted on both the ComCO and COCO datasets, to evaluate
these biases. The results of these experiments are summa-
rized in Table 6. To better illustrate the differences between
these two scenarios, an example of the caption structures is
shown in Figure 5. In each scenario, we created incorrect
captions by switching one object in the caption with an ob-
ject that is not present in the image. Additionally, GPT-4O
[1] was used to rewrite the captions in the COCO dataset.
First Scenario
In the ﬁrst scenario, biases assist the
model in distinguishing between the correct and incorrect
captions. In the correct captions, the largest object in the
image is placed at the beginning, aligning with the model’s
bias towards prioritizing ﬁrst-mentioned objects and larger
objects. For the incorrect captions, the non-existent object is
deliberately placed at the beginning, which helps the model
recognize the difference between the correct and incorrect
captions more effectively. This positioning emphasizes the
discrepancy early on, allowing the model to better detect the
mismatch between the caption and the image. The perfor-
mance of different models in this scenario can be seen in
Table 6 under the ”First Scenario” column.
Second Scenario
In the second scenario, biases lead the
model to make errors. The correct captions place the largest
object at the end of the sentence, disrupting the model’s
bias towards objects mentioned earlier and its preference
for larger objects. In the incorrect captions, the non-existent
object is placed at the end, making it more difﬁcult for the
model to differentiate between correct and incorrect cap-
tions as its attention is drawn away from the critical discrep-
ancies. The performance of different models in this scenario
is shown in Table 6 under the ”Second Scenario” column.
Table 6. Performance Comparison on Image-Text Matching for
ComCO and COCO Datasets
Dataset
Model
First Scenario
Second Scenario
ComCO
CLIP Datacomp [6]
99.99
67.50
CLIP Roberta
99.98
64.75
SIGLIP [22]
99.49
72.36
CLIP openAI
99.59
52.23
NegCLIP
96.82
46.94
SugarCrepe
98.55
60.43
COCO
CLIP Datacomp [6]
71.2
54.2
CLIP Roberta
72.2
54.1
SIGLIP [22]
64.8
39.5
CLIP openAI
63.5
26.4
NegCLIP
72
28.7
SugarCrepe
80.0
40.9
By comparing these two scenarios, we demonstrate that
biases in CLIP can either help or hinder the model’s perfor-
mance depending on how captions are structured. The ex-
perimental results, particularly with the use of GPT-4O for
caption rephrasing in the COCO dataset, reveal how such
biases can inﬂuence the accuracy of image-text matching
tasks. These biases must be addressed to improve CLIP’s
robustness in real-world multi-object scenarios.
For further insights on how these biases affect text-to-
image generation, refer to our extended experiments in Ap-
pendix 7.11.
6. Conclusion
This study uncovers biases in CLIP’s encoders, with the
text encoder favoring ﬁrst-mentioned objects and the im-
age encoder emphasizing larger ones, which impacts per-
formance in multi-object tasks. Using the ComCO dataset,
we highlighted these biases’ effects on object representation
and positioning, underscoring the need for balanced train-
ing. We attribute these biases to CLIP’s contrastive frame-
work, where alignment issues propagate across modalities.
Addressing these biases is essential for vision-language ad-
vancements, as seen with models like Stable Diffusion.
9315

=== Page 9 ===
References
[1] Josh Achiam, Steven Adler, Sandhini Agarwal, Lama Ah-
mad, Ilge Akkaya, Florencia Leoni Aleman, Diogo Almeida,
Janko Altenschmidt, Sam Altman, Shyamal Anadkat, et al.
Gpt-4 technical report.
arXiv preprint arXiv:2303.08774,
2023. 8
[2] Dosovitskiy Alexey. An image is worth 16x16 words: Trans-
formers for image recognition at scale. arXiv preprint arXiv:
2010.11929, 2020. 5
[3] Mehdi Cherti, Romain Beaumont, Ross Wightman, Mitchell
Wortsman, Gabriel Ilharco, Cade Gordon, Christoph Schuh-
mann, Ludwig Schmidt, and Jenia Jitsev.
Reproducible
scaling laws for contrastive language-image learning.
In
2023 IEEE/CVF Conference on Computer Vision and Pat-
tern Recognition (CVPR). IEEE, 2023. 1
[4] Sri Harsha Dumpala, Aman Jaiswal, Chandramouli Sas-
try, Evangelos Milios, Sageev Oore, and Hassan Saj-
jad.
Sugarcrepe++ dataset: Vision-language model sensi-
tivity to semantic and lexical alterations.
arXiv preprint
arXiv:2406.11171, 2024. 1
[5] Samir Yitzhak Gadre, Gabriel Ilharco, Alex Fang, Jonathan
Hayase, Georgios Smyrnis, Thao Nguyen, Ryan Marten,
Mitchell Wortsman, Dhruba Ghosh, Jieyu Zhang, Eyal Or-
gad, Rahim Entezari, Giannis Daras, Sarah Pratt, Vivek
Ramanujan, Yonatan Bitton, Kalyani Marathe, Stephen
Mussmann, Richard Vencu, Mehdi Cherti, Ranjay Krishna,
Pang Wei Koh, Olga Saukh, Alexander Ratner, Shuran
Song, Hannaneh Hajishirzi, Ali Farhadi, Romain Beaumont,
Sewoong Oh, Alex Dimakis, Jenia Jitsev, Yair Carmon,
Vaishaal Shankar, and Ludwig Schmidt.
Datacomp: In
search of the next generation of multimodal datasets, 2023.
1
[6] Samir Yitzhak Gadre, Gabriel Ilharco, Alex Fang, Jonathan
Hayase, Georgios Smyrnis, Thao Nguyen, Ryan Marten,
Mitchell Wortsman, Dhruba Ghosh, Jieyu Zhang, et al. Dat-
acomp:
In search of the next generation of multimodal
datasets. Advances in Neural Information Processing Sys-
tems, 36, 2024. 8, 17
[7] Tianyu Gao, Xingcheng Yao, and Danqi Chen.
Simcse:
Simple contrastive learning of sentence embeddings. arXiv
preprint arXiv:2104.08821, 2021. 5
[8] Cheng-Yu Hsieh, Jieyu Zhang, Zixian Ma, Aniruddha Kem-
bhavi, and Ranjay Krishna.
Sugarcrepe: Fixing hackable
benchmarks for vision-language compositionality. Advances
in neural information processing systems, 36, 2024. 1, 7
[9] Tsung-Yi Lin, Michael Maire, Serge Belongie, Lubomir
Bourdev, Ross Girshick, James Hays, Pietro Perona, Deva
Ramanan, C. Lawrence Zitnick, and Piotr Doll´ar. Microsoft
coco: Common objects in context, 2015. 2
[10] Zixian Ma, Jerry Hong, Mustafa Omer Gul, Mona Gandhi,
Irena Gao, and Ranjay Krishna. Crepe: Can vision-language
foundation models reason compositionally? In Proceedings
of the IEEE/CVF Conference on Computer Vision and Pat-
tern Recognition, pages 10910–10921, 2023. 1
[11] Xingchao Peng, Qinxun Bai, Xide Xia, Zijun Huang, Kate
Saenko, and Bo Wang. Moment matching for multi-source
domain adaptation. In Proceedings of the IEEE/CVF inter-
national conference on computer vision, pages 1406–1415,
2019. 3
[12] Dustin
Podell,
Zion
English,
Kyle
Lacey,
Andreas
Blattmann, Tim Dockhorn, Jonas M¨uller, Joe Penna, and
Robin Rombach.
Sdxl: Improving latent diffusion mod-
els for high-resolution image synthesis.
arXiv preprint
arXiv:2307.01952, 2023. 17
[13] Alec Radford, Jong Wook Kim, Chris Hallacy, Aditya
Ramesh, Gabriel Goh, Sandhini Agarwal, Girish Sastry,
Amanda Askell, Pamela Mishkin, Jack Clark, Gretchen
Krueger, and Ilya Sutskever.
Learning transferable visual
models from natural language supervision, 2021. 1
[14] N Reimers.
Sentence-bert:
Sentence embeddings using
siamese bert-networks.
arXiv preprint arXiv:1908.10084,
2019. 5
[15] Dillon Reis, Jordan Kupec, Jacqueline Hong, and Ahmad
Daoudi. Real-time ﬂying object detection with yolov8. arXiv
preprint arXiv:2305.09972, 2023. 17
[16] Robin Rombach, Andreas Blattmann, Dominik Lorenz,
Patrick Esser, and Bj¨orn Ommer.
High-resolution image
synthesis with latent diffusion models.
In Proceedings of
the IEEE/CVF Conference on Computer Vision and Pattern
Recognition (CVPR), pages 10684–10695, 2022. 17
[17] Ugur Sahin, Hang Li, Qadeer Khan, Daniel Cremers, and
Volker Tresp. Enhancing multimodal compositional reason-
ing of visual language models with generative negative min-
ing. In Proceedings of the IEEE/CVF Winter Conference on
Applications of Computer Vision, pages 5563–5573, 2024. 1
[18] Christoph Schuhmann, Richard Vencu, Romain Beaumont,
Robert Kaczmarczyk, Clayton Mullis, Aarush Katta, Theo
Coombes, Jenia Jitsev, and Aran Komatsuzaki. Laion-400m:
Open dataset of clip-ﬁltered 400 million image-text pairs,
2021. 1
[19] Christoph Schuhmann, Romain Beaumont, Richard Vencu,
Cade Gordon,
Ross Wightman,
Mehdi Cherti,
Theo
Coombes, Aarush Katta, Clayton Mullis, Mitchell Worts-
man, et al. Laion-5b: An open large-scale dataset for training
next generation image-text models. Advances in Neural In-
formation Processing Systems, 35:25278–25294, 2022. 6
[20] Tristan Thrush, Ryan Jiang, Max Bartolo, Amanpreet
Singh, Adina Williams, Douwe Kiela, and Candace Ross.
Winoground: Probing vision and language models for visio-
linguistic compositionality. In Proceedings of the IEEE/CVF
Conference on Computer Vision and Pattern Recognition,
pages 5238–5248, 2022. 1
[21] Mert Yuksekgonul, Federico Bianchi, Pratyusha Kalluri,
Dan Jurafsky, and James Zou.
When and why vision-
language models behave like bags-of-words, and what to
do about it?
In The Eleventh International Conference on
Learning Representations, 2023. 1
[22] Xiaohua Zhai, Basil Mustafa, Alexander Kolesnikov, and
Lucas Beyer. Sigmoid loss for language image pre-training.
In Proceedings of the IEEE/CVF International Conference
on Computer Vision, pages 11975–11986, 2023. 8, 17
[23] Tiancheng Zhao, Tianqi Zhang, Mingwei Zhu, Haozhan
Shen, Kyusong Lee, Xiaopeng Lu, and Jianwei Yin.
Vl-
checklist:
Evaluating pre-trained vision-language models
9316

=== Page 10 ===
with objects, attributes and relations.
arXiv preprint
arXiv:2207.00221, 2022. 1
9317
