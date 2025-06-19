
=== Page 1 ===
ECE 1508 Multiuser Information Theory
Prof. Wei Yu
Homework Set #2
1. Cover and Thomas, Problem 9.8. Parallel Gaussian channels.
2. Cover and Thomas, Problem 9.9. Vector Gaussian channel.
3. Cover and Thomas, Problem 9.12. Time-varying channel.
4. Cover and Thomas, Problem 9.17. Impulse power.
5. Pulse Position Modulation (PPM): In the previous problem, you ﬁnd that the impulse
scheme is suboptimal. In this problem, we show that if you are allowed to choose where
to place the impulse (among the time indices i = 1, 2, · · · , n), this PPM scheme is capacity
achieving on n uses of the Gaussian channel Yi = Xi + Zi at low SNR.
(a) Let Z1, · · · , Zn be i.i.d. Gaussian random variables N(0, σ2). Let U = maxi{Zi}. Let
t > 0. Justify each of the following steps:
exp(tE[U]) ≤E[exp(tU)] = E max
i {exp(tZi)} ≤
n
X
i=1
E[exp(tZi)] = n exp(t2σ2/2).
You may recognize the moment generating function of Gaussian random variable in
the last step.
(b) Rewrite E[U] ≤ln n
t + tσ2
2 . Minimize over t to arrive at the inequality
E[U] ≤σ
p
2 ln(n).
(c) Use the Chernoﬀbound to show that for all a > 0
Prob{U ≥σ(
√
2 ln n + a)} ≤exp(−a2/2).
(d) In PPM, information is encoded in the position of the pulse.
Over n uses of the
Gaussian channel, we set Xi =
√
nP for one of i = 1, · · · , n, and zero elsewhere.
Please express the information rate R of PPM per channel use in nats, assuming that
there is no detection error.
(e) Please argue that it is possible to choose a constant L that depends on some (arbi-
trarily small) Pe target, and then by setting
√
nP = σ(
√
2 ln n + L)
we can achieve a bounded target probability of detection error (e.g. Pe = 10−6).
1

=== Page 2 ===
(f) Consider the low SNR regime, i.e.,
P
σ2 ≪1. Please write down an approximation of
the Gaussian channel capacity in the low SNR limit, call it C. Show that for the
achievable rate R of PPM under Pe, we have
C < R(1 + δ)
for some δ that goes to zero as SNR goes to zero. Hence, PPM is capacity approaching
at low SNR.
6. Achievable Rate of Pulse Amplitude Modulation (PAM): Please generate the following plots
in a graph with SNR (in dB) on the x-axis and achievable rates on the y-axis.
• Gaussian channel capacity C = 1
2 log(1 + SNR).
• The capacity of a 2-PAM input additive Gaussian noise channel as a function of SNR.
• Repeat for 4-PAM, 8-PAM and 16-PAM, assuming uniform distribution on the input.
Which constellation(s) are optimum at low SNR? At high SNR, please numerically ﬁnd the
value of shaping loss (in dB), deﬁned as the amount of extra power needed to achieve the
same rate as the Shannon capacity limit.
Please provide the derivations of the mutual information expressions for numerical evalu-
ation and the code for generating the plot.
7. Shaping Loss: In this problem we will ﬁnd the theoretical limit of shaping loss of PAM at
high SNR. Consider the following two input distributions over n uses of the additive white
Gaussian noise channel Yi = Xi + Zi, where Xi is subject to power constraint P:
• X(1)
i
∼N(0, P) i.i.d.
• X(2)
i
∼Unif[−L, L] i.i.d.
We write the mutual information I(X; Y ) = h(Y ) −h(Y |X), where h(Y |X) = h(Z) is the
same in both cases, and approximate h(Y ) ≈h(X) in high SNR.
(a) What is the relationship between P and L for which we have h(X(1)) = h(X(2))?
(b) Find the amount of extra power needed for X(2) in order to achieve the same mutual
information as X(1). The amount of extra power is a multiplicative factor which can be
found analytically. Please ﬁnd this analytic expression. Please also ﬁnd its numerical
value in dB.
(c) Compare the theoretical shaping loss with the numerical value found in the previous
problem.
8. Phase Shift Keying on Complex AWGN Channel: Suppose that we use a phase-shift keying
(PSK) modulation on a complex additive white Gaussian noise channel where the i.i.d.
noises in the real and imaginary components both have a variance of
σ2
2 .
An M-PSK
2

=== Page 3 ===
modulation has M constellation points equally spaced on a circle of radius
√
P from the
origin, where P is the power of the constellation. Suppose that we wish to achieve a symbol
probability of error of 10−6.
Please derive an expression of the achievable rate of PSK signalling as a function of the
SNR, deﬁned as P/σ2. (You may approximate the distance between two neighbouring
constellation points on a circle of radius r as 2πr/M.)
At high SNR, does the achievable rate of the PSK constellation have the same SNR scaling
as the capacity of the complex AWGN channel?
3
