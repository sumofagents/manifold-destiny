// Manifold Destiny
// Thompson & Horowitz
// Preprint — 2026

#set page(numbering: "1", margin: (top: 1in, bottom: 1in, left: 1in, right: 1in))
#set text(font: "New Computer Modern", size: 11pt)
#set par(justify: true, leading: 0.8em)

// Title block
#align(center)[
  #text(size: 18pt, weight: "bold")[Manifold Destiny: Continuous Learning by Consumption of Truth-Verified Structure from the Zero-Information Floor]
  #v(0.5em)
  Jeremiah Thompson, Justin Horowitz
  #v(0.3em)
  #text(size: 10pt)[
    Thompson: Independent Researcher
    #linebreak()
    Horowitz: PhD, Bioengineering, University of Illinois Chicago
  ]
  #v(0.3em)
  #link("mailto:jeremiah@jeremiahai.com")  ·  #link("mailto:justin.horowitz@gmail.com")
]

#v(1em)

// Abstract
#align(center)[
  #block(width: 85%, stroke: 0.5pt + gray, inset: 1em, breakable: true)[
      #text(size: 10pt)[
        *Abstract.* We present a learning architecture in which inductive bias is split between a typed bounded grammar (what can be expressed) and an admissibility verifier (what is retained): the grammar hypothesizes candidate quotients and the verifier accepts each by a binary test, retaining only those that preserve every distinction a downstream decision depends on. The learner constructs candidate abstractions $q$ from the grammar and submits each to the verifier, which accepts $q$ iff, for all states $x, y$, it preserves every distinction a downstream decision $c$ depends on:

        $ forall x, y: q(x) = q(y) arrow.r c(x) = c(y) $

        Accepted abstractions are retained in an information manifold; rejected ones are discarded. The procedure has no weights, no gradients, and no parameter optimization; all learning is the accumulation of truth-verified structure. Without verifier feedback the system is trapped on a _null trajectory_ of the manifold — a path along which no information about the hidden structure is gained. Verifier feedback is the only force that moves it off this null trajectory, one verified step at a time, toward recovery of the hidden structure. This differs from version-space learning (Mitchell, 1982), active learning with membership queries (Angluin, 1987), and counterexample-guided synthesis: in those frameworks the oracle labels instances or returns counterexamples against a logical specification, whereas here the verifier evaluates whether a grammar-constructed abstraction satisfies a consumer-relative admissibility criterion — the consumer is the specification, the verdict is binary, and candidate quotients are constructed and verified by that verdict.

        Within each studied domain, the system recovers the targeted hidden quotient. On synthetic $"GF"(2)$ partition problems with $k$ independent bits, it recovers the hidden structure in $2^k - 1$ probes — the worst case for elimination over the $2^k$ candidate functionals. The minimum success rate without verifier feedback — the _zero-information floor_ — zero mutual information between state and hidden structure — equals $1\/C^k$ exactly, where $C$ is the number of choices per independent decision. On quantum measurements, the grammar with atoms ${alpha, beta}$ and operator $sans("sub")$ constructs the angle-difference invariant $alpha - beta$; the verifier accepts it because it is the reduction under which the data exhibits a CHSH violation exceeding the classical bound — the system did not know to look for $alpha - beta$, it constructed it. On a Lean 4.31.0 kernel, it recovers $k$-step compositional proofs in $k$ probes (linear in proof depth), rather than the $|T|^k$ probes required by exhaustive search over a tactic vocabulary $T$. Because the grammar is bounded but not catalog-bound, the system also constructs quotients absent from a restricted demonstration catalog $Q_0$ — $u xor v$ in $"GF"(2)$, $alpha - beta$ in the quantum domain, and a kernel-certified quotient in Lean — which the verifier accepts and which remain $c$-admissible on held-out instances.

        Parameters are not primitive in this architecture. A verified quotient first earns the symmetry on which parameterization may later sit: it identifies observations that are indistinguishable to the consumer, and when the sampling design or verifier establishes finite within-fiber exchangeability, the representation principle introduced by de Finetti #cite(<definetti1937>) and its finite approximation due to Diaconis and Freedman #cite(<diaconisfreedman1980>) can introduce latent parameters. In the smooth quantum projection, $alpha - beta$ is the verified reduction that supplies the coordinate on which Fisher-Rao geometry is defined — geometry earned by verification, not assumed in advance.

        We validate the replay machinery on a 218,866-record public Lean-Github corpus and fully replay a pinned real theorem against a real Lake build: recorded tactics are accepted, forbidden proof tokens are absent, and falsifier candidates are rejected.
      ]
    ]
  ]

#v(1em)

= Introduction

Dominant approaches to artificial intelligence place knowledge inside a trained model. Neural networks, large language models, and many deployed systems encode what they know in fitted weights; training is how the encoding gets there; inference retrieves what training put there. The trained weights are fixed at deployment — barring further training runs or external retrieval — and new knowledge typically requires an external update path rather than emerging from the system's own operation.

We present a learning regime that hypothesizes structural typings from a bounded grammar and verifies each against a consumer-relative criterion. The system has no weights, no gradients, and no training phase. It learns by constructing candidate abstractions from a typed bounded grammar and submitting each to an admissibility verifier; the verifier accepts the abstraction iff it preserves every distinction a downstream consumer requires, and the system retains accepted abstractions in a shared store. Learning is the accumulation of verifier-accepted structure. In the tested bounded grammars, exhaustive enumeration finds the accepted generated quotients, and held-out or variant checks confirm admissibility where defined.

This mechanism differs from standard query-learning and synthesis frameworks. In Mitchell's version-space learning #cite(<mitchell1982>), the learner maintains the set of hypotheses consistent with labeled training instances; the labels are the source of information, and the hypothesis is fit to them. In Angluin's active learning with membership queries #cite(<angluin1987>), the oracle answers labels for proposed instances. In counterexample-guided inductive synthesis (CEGIS) #cite(<solarlezama2008>), syntax-guided synthesis (SyGuS) #cite(<alur2013>), and inductive logic programming #cite(<muggleton1991>), the oracle returns counterexamples to a candidate program against a logical specification, and the synthesizer revises against them. Here, the oracle labels candidate quotients rather than data instances; those quotients are binary-verified against the admissibility criterion, not statistically fit to those labels. The grammar constructs a quotient $q$; the verifier evaluates whether $q$ satisfies the consumer-relative admissibility criterion

$ forall x, y: q(x) = q(y) arrow.r c(x) = c(y); $

the system retains $q$ iff that criterion holds. The consumer $c$ functions as the specification; the criterion is consumer-relative rather than absolute. The verifier returns a binary verdict — not a counterexample — and the retained object is a quotient, not a fitted model. This criterion also appears as decision-preserving state abstraction in Markov decision processes #cite(<li2006abstraction>), where the same factorization $c = g op("∘") q$ determines admissibility. The zero-information baseline — $1\/C^k$ for $C$ choices per independent decision and $k$ decisions — makes the information channel explicit: without the verifier, the system's state is independent of the hidden structure.

We demonstrate the mechanism in three domains, chosen because each admits an independently certifiable verifier and exhibits qualitatively different structure. In each, the system also constructs a quotient absent from a restricted demonstration catalog $Q_0$ — bounded generation, not selection from a catalog — and the verifier independently accepts it.

In _synthetic_ $"GF"(2)$ fixtures, the verifier checks partition equality against a hidden linear functional. We prove that the system recovers the hidden structure in $2^k - 1$ probes — the worst case for elimination over the $2^k$ candidate functionals — while the zero-information floor sits at exactly $1\/2^k$. The grammar constructs the quotient $u xor v$ that is absent from $Q_0$; the verifier accepts it, and it remains $c$-admissible on held-out instances.

In _quantum_ measurements on entangled states, the grammar with atoms ${alpha, beta}$ and operator $sans("sub")$ constructs the angle-difference invariant $alpha - beta$ from raw two-qubit measurement counts. The verifier accepts the construction because the data, reduced under $alpha - beta$, exhibit a CHSH score $S > 2 + delta$ beyond the classical bound #cite(<chsh1969>) #cite(<bell1964>) — the system did not know to look for $alpha - beta$; the grammar produced it and the verifier independently certified it against measurements collected on a 156-qubit superconducting processor. The mechanism operates on real entanglement data rather than a synthetic simulator; the grammar-mediated recovery of the correlation structure is the contribution, certified by the CHSH criterion against real entanglement data.

In _formal mathematics_, the verifier is the Lean 4.31.0 kernel #cite(<demoura2021>) #cite(<lean2024>). The grammar constructs $k$-step compositional proofs in $k$ probes — linear in proof depth, rather than $|T|^k$ probes for a tactic vocabulary $T$ — and constructs a kernel-certified quotient absent from $Q_0$. We validate the replay machinery on a 218,866-record public Lean-Github corpus and fully replay a pinned real theorem (`Lean4Axiomatic.Integer.one_mul_one_eqv_one`) against a real Lake build: recorded tactics are accepted, forbidden proof tokens ("sorry", "admit") are absent, and falsifier candidates (weaker tactics, wrong-orientation quotients, classical surrogates) are rejected. This validates the retention criterion against publicly maintained Lean 4 repositories, not only synthetic fixtures.

The grammar and verifier are human-supplied. What is autonomous is the construction of specific quotients within those bounds and the binary retention decision that follows the verifier's verdict. The system does not invent grammars or propose verifiers; it extends its vocabulary — not its grammar class — by promoting verifier-accepted quotients to new composition atoms (the self-extending theorem). What it does delimit is a regime of learning in which inductive bias is split between a typed bounded grammar (what can be expressed) and an admissibility verifier (what is retained): candidate abstractions are hypothesized within the grammar and retained by binary verification, a regime that we show is sufficient for three substantive domains.

These demonstrations also reframe what a parameter is in this architecture. A verified quotient is not a coordinate chosen in advance; it is an equivalence structure earned from data. By Definition 1, if $q$ is $c$-admissible then $c$ is constant on the fibers of $q$, so any two observations in the same fiber are indistinguishable to $c$; that earned symmetry is what later makes parameterization non-arbitrary (developed in Section 8, where the verified coordinate $theta = alpha - beta$ indexes the quantum measurement family on which Fisher-Rao geometry can sit). The architecture therefore does not refuse parameters; it delays parameterization until a verified quotient earns it. Learning is not fitting parameters; learning is discovering the verified invariances that make parameters exist. The parameters of this architecture are the typings themselves — the verifier-accepted quotients — not coordinates of a model family chosen in advance. One does not first fix a model family and then parameterize it; one learns the typings under which the consumer cannot tell members of a fiber apart, and therefore the natural unit on which — once a sampling design or verifier establishes within-fiber symmetry — exchangeability can be established (Section 8). The typings are non-arbitrary in this precise sense: they are the coordinates earned by verification, not posited before it. The quantum domain is the concrete case: the grammar constructs $alpha - beta$, and only once the verifier accepts it does the angle difference become a legitimate coordinate for the measurement family — geometry earned, not assumed.

This architecture formalizes, in modern terms, a problem that Baconian induction could only pose informally: how a learner earns the distinctions on which later scientific parameterization depends. Bacon's tables of presence, absence, and degree #cite(<bacon1620>) were pre-statistical devices for resisting premature essences and retaining only distinctions that survived contact with observation. Here that role is made explicit and executable. A bounded grammar proposes candidate quotients; a verifier rejects those that collapse distinctions required by the downstream consumer and retains those that preserve them. Each retained quotient is therefore not a fitted coefficient but a learned structural parameter: a certified distinction that defines fibers of observations. When the sampling design supports exchangeability within those fibers — repeated observations at a fixed value of the certified coordinate — de Finetti's representation theorem #cite(<definetti1937>) and its finite approximation due to Diaconis and Freedman #cite(<diaconisfreedman1980>) license ordinary latent parameters for that fiber. Separately, in the smooth quantum projection, it is the certified coordinate $theta = alpha - beta$ itself, indexing the measurement family across fibers, that carries Fisher-Rao geometry and supports Amari's dual-projection machinery. The Baconian element is therefore not the foundation of the method but its historical shadow: the architecture supplies the statistical and geometric machinery Bacon lacked, turning disciplined elimination of false distinctions into verifier-certified coordinates for modern parameterized science.

The three domains share a single mathematical backbone. The zero-information floor is the condition $I("state"; M) = 0$ — zero mutual information between the Consumptor's state and the hidden structure #cite(<cover2006>). In the finite case the floor is $1\/C^k$ exactly; in a smooth family, the same condition forces the observation distribution to be constant in the hidden parameter, so $g_(theta theta) equiv 0$ globally #cite(<fisher1922>) #cite(<rao1945>). Fisher geometry is not the primitive object; it is the geometry that appears after the verifier has stabilized a parameter-bearing family of measures. In the smooth quantum case, the verified coordinate is what supplies the parameterization on which Amari's dual information geometry sits #cite(<amari2016>) #cite(<chentsov1982>): the trajectory from the zero-information point to verified recovery is a dual (e-/m-) projection onto the certified measurement family. This projection is not bought by committing to a fragile parametric family — a Gaussian, say — in advance; the coordinate is earned by verification first, and the dual projection is then carried out on structure the verifier has already certified. In the discrete synthetic and formal-proof cases, the same trajectory traces a finite graph — vertices are information states, edges are verifier queries, and the counting baseline $1\/C^k$ #cite(<cover2006>) is its operational origin. This is the same dual-projection pattern carried out without a smooth metric: each verifier query performs the discrete counterpart of an information projection, restricting the posterior to the states consistent with the verdict, so the finite graph realizes Amari's dual projection on earned structure rather than paying for it with a parametric family assumed up front. We claim no Fisher metric on these graphs (Section 8); what is shared is not merely a pattern but a quantity — $I("state"; M)$ is defined natively on finite graphs and smooth families alike, carried by counting and posterior structure. The three demonstrations are projections of a common geometric object onto domain-specific spaces — one smooth manifold and two finite graphs — not three unrelated experiments.

The remainder of the paper is organized as follows. Section 2 fixes the architecture and its formal components. Section 3 collects the formal properties: c-admissibility, the zero-information floor, and the verifier-mediated information channel. Section 4 establishes bounded generation across the three domains. Section 5 presents the real-corpus replay on the Lean-Github corpus. Section 6 develops the cross-domain quotient store. Section 7 reports experimental results. Section 8 develops the information-geometric framing. Section 9 discusses limitations. All code, test artifacts, and quantum data are public #cite(<github_repo>).

= Architecture

== The Verifier-Mediated Architecture

The Consumptor operates through a construct-verify-retain-extend mechanism:

+ *Construct*: enumerate a candidate quotient $q: W arrow.r A$ from a bounded typed grammar $G$
+ *Verify*: submit $q$ to the verifier $V$, which returns a binary accept/reject verdict
+ *Retain*: store accepted quotients in the Consumptor's manifold store $cal(M)$; discard rejected quotients
+ *Extend*: promote retained quotients to new typed grammar atoms for later composition

#figure(
  image("figures/fig0_process_flow.pdf", width: 90%),
  caption: [The construct-verify-retain-extend architecture. The grammar $G$ generates candidate quotients; the verifier $V$ accepts or rejects each; accepted quotients are retained in the manifold store $cal(M)$; retained quotients promote to new grammar atoms, extending $G$ for subsequent construction. Rejected quotients are discarded.]
)

The inductive bias is split across two components. The grammar $G$ determines what can be expressed; the verifier $V$ determines what is retained. Neither alone suffices: an unconstrained grammar searches forever, an unconstrained verifier admits incoherence. The Consumptor has no weights, no gradients, and no parameter optimization. Learning is the accumulation of truth-verified structure.

The verifier has access to hidden structure $M$ that the Consumptor cannot read. The binary verdict is the only channel from $M$ to the Consumptor. Accepted abstractions are therefore not statistically fitted coefficients; they are verifier-certified quotients retained in the manifold and made available for transfer and further construction.

== Formal Components

The architecture consists of seven components:

- *World* $W$: the set of states the system operates over. In the synthetic domain, $W$ is a set of binary vectors over $"GF"(2)$. In the quantum domain, $W$ is the set of measurement outcomes on entangled states. In the formal-proof domain, $W$ is the set of Lean proof states.

- *Consumer* $c$: a downstream decision function $c: W arrow.r D$ that maps world states to decisions. The consumer determines which distinctions matter: two states $x$ and $y$ must be distinguished by any admissible abstraction if $c(x) != c(y)$.

- *Grammar* $G$: a bounded typed grammar that generates candidate abstractions. It has a finite atom set, a finite operator set, and a maximum expression depth. Its denotation ⟦G⟧ is the class of quotients the Consumptor may construct. The grammar is domain-specific and human-supplied; retained quotients are promoted to new atoms, so $G$ evolves as the system learns.

- *Restricted demonstration catalog* $Q_0 subset.eq ⟦G⟧$: a human-supplied baseline subset of candidate abstractions used for comparison. It is not the full hypothesis space. The grammar's expressive class is strictly larger than $Q_0$, so the Consumptor can construct quotients absent from the demonstration catalog.

- *Verifier* $V$: a mechanism that checks whether a candidate $q$ is valid for consumer $c$. The verifier has access to information the Consumptor cannot see — the hidden structure $M$ — and uses this to accept or reject each candidate. The verifier is domain-specific: in the synthetic domain it checks partition validity; in the quantum domain it checks measurement consistency and non-classicality; in the formal-proof domain it is the Lean kernel.

- *Evidence* $M$: the hidden structure accessible only to the verifier. The Consumptor never reads $M$ directly. In the synthetic domain, $M$ is a linear functional over $"GF"(2)^k$. In the quantum domain, $M$ is the held-out measurement outcomes. In the formal-proof domain, $M$ is the correct tactic sequence.

- *Consumptor*: the structured store that enumerates candidates from $G$, receives binary feedback from the verifier, retains accepted abstractions, and promotes retained quotients to new grammar atoms. It operates in two modes:

  - *Adaptation*: the Consumptor enumerates candidates from $G$ against the verifier. Each accepted candidate is stored as a verified abstraction keyed by the family signature of the world state, and promoted to a new grammar atom for subsequent composition. The probe budget is the number of verifier queries allowed during adaptation.

  - *Evaluation*: the Consumptor applies the retained abstractions to a new instance (held-out from adaptation). No further verifier feedback is available. The success rate is measured against the consumer's ground-truth decision.

A structural mapping, in this framework, is a quotient: a function $q$ that maps world states to equivalence classes. Two states $x$ and $y$ belong to the same class if $q(x) = q(y)$. The verifier confirms that this quotient preserves every distinction the consumer $c$ needs: whenever $q$ merges two states, the consumer's decision must also treat them identically. If the verifier finds a pair where $q(x) = q(y)$ but $c(x) != c(y)$, it rejects the quotient as invalid for that consumer. The Consumptor retains only the quotients the verifier accepted.

== Consumer-Relative Validity

The validity criterion is consumer-relative:

$ q(x) = q(y) arrow.r c(x) = c(y) $

A summary $q$ is admissible for downstream consumer $c$ only when it preserves every distinction the consumer needs. This criterion echoes the idea behind sufficient statistics — that a summary need only preserve what a downstream decision depends on — but is deterministic rather than probabilistic: it requires that $c$ factors through $q$ (i.e., $c$ is constant on the fibers of $q$), rather than that the conditional distribution of the data given $q$ is parameter-independent. It also relates to decision-preserving state abstractions in Markov decision processes #cite(<li2006abstraction>), where an abstraction is valid only if it preserves the optimal decision. The information bottleneck principle #cite(<tishby1999>) addresses a related question — finding minimal representations that preserve information about a target variable — but optimizes a rate-relevance tradeoff rather than enforcing binary validity. Analogously, at the zero-information point the consumer must decide without any information and succeeds with probability $1\/C^k$, just as rate-distortion theory #cite(<shannon1959>) characterizes the minimum information needed to achieve a given distortion.


== Transfer Mechanism

The transfer mechanism is how verified abstractions acquired during adaptation are applied to new instances during evaluation. The key property is _family signature matching_: the Consumptor indexes retained abstractions by a structural signature of the world state (in the formal-proof domain, this is the goal skeleton, the hypothesis type skeletons, and the catalog shape; each domain has its own signature). When a new instance arrives during evaluation, the Consumptor computes the same signature and retrieves the matching abstraction. If the signature matches, the retained abstraction is applied directly; if no match exists, the Consumptor falls back to a default candidate (yielding a success rate equal to the zero-information floor).

Transfer is demonstrated across _variants_: within each domain, the adaptation phase uses one set of variants (e.g., specific Bell states or proof branches), and the evaluation phase uses different variants of the same structure. The family signature is identical across variants — the goal skeleton and catalog shape do not change — so the retained abstraction transfers. The zero-information floor controls this: if the signature does not match (shuffled family control), the Consumptor falls to the floor and succeeds with probability $1\/C^k$.

== Channel Isolation

The hidden structure $M$ is accessible only to the verifier, not to the Consumptor. The Consumptor learns about $M$ exclusively through the verifier's binary verdict. Without verifier feedback, the Consumptor remains on a _null trajectory_ of the information manifold: a path along which its state gains no information about $M$.

The operational consequence is the zero-information floor. If the Consumptor's state is independent of $M$, and $M$ is drawn uniformly from $C^k$ possible hidden structures with exactly one valid per instance, then its success probability is $1\/C^k$ by Lemma 1. Equivalently, $I("state"; M) = 0$ — the mutual information between the Consumptor's state and the hidden structure vanishes. In the smooth projection this same condition forces Fisher information to vanish identically (Section 8).

Corollary 1 formalizes the channel restriction: if the Consumptor's state can depend on $M$ only through verifier feedback, then any performance above $1\/C^k$ implies that information about $M$ entered through the verifier channel. The full Fisher/Amari information-geometric framing #cite(<amari2016>) #cite(<chentsov1982>) applies in the continuous quantum domain and is developed in the Information Manifold section. Throughout, "state" denotes the Consumptor's full observable configuration, including the retained store $cal(M)$ and its decision output. Lemma 1 applies directly to domains where the instance presentation is independent of $M$ ($"GF"(2)$ and Lean); the quantum domain, where observed and held-out counts are drawn from the same state, is handled through the smooth statement above.

== Domain-Specific Verifiers

The verifier is constructed differently in each domain:

- *Synthetic domain*: the verifier checks whether a proposed partition $q$ matches the partition induced by the hidden linear functional $M$. This is an exact, structural check — no statistics, no approximation. The verifier accepts if and only if $q$ and $M$ induce the same partition of $W$.

- *Quantum domain*: the verifier operates in two tiers. Tier A checks structural consistency: does the proposed correlation law produce homogeneous predictions across measurement settings? Tier B checks non-classicality: does the selected law produce a CHSH score $S > 2 + delta$, where $delta = 0.05$ is a noise-robustness margin above the classical bound of $S = 2$? A candidate must pass both tiers, plus a held-out accuracy check: the selected law must produce a forced prediction at a held-out measurement setting that matches the measured outcomes within shot noise. The verifier does not know quantum mechanics — it knows consistency and a threshold.

- *Formal-proof domain*: the verifier is the Lean 4.31.0 kernel. It checks whether a proposed tactic (e.g., `exact h_0`) produces a valid proof step. The check is structural: the tactic either type-checks or it does not. No statistics, no heuristics, no language model. The kernel's verdict is binary and exact.

In all three domains, the verifier provides binary feedback (accept or reject) and the Consumptor retains only accepted candidates. The verifier's access to $M$ — the hidden structure — is what makes the feedback informative: without it, the Consumptor cannot distinguish correct from incorrect candidates (the channel isolation guarantee).


= Formal Properties

We state the architecture's core properties as elementary results. These are not new theorems; each is adjacent to a known result, noted below. They make explicit the assumptions and baselines used throughout the experiments.

*Definition 1 (c-admissible quotient).* A quotient $q: W arrow.r A$ is _c-admissible_ for consumer $c: W arrow.r D$ if $q(x) = q(y) arrow.r c(x) = c(y)$. Equivalently, $c$ factors through $q$ via a unique $g: "im"(q) arrow.r D$. This is the deterministic analog of sufficient statistics #cite(<fisher1922>) and the decision-preserving abstraction criterion of Li et al. #cite(<li2006abstraction>).

*Lemma 1 (zero-information floor).* If $I("state"; M) = 0$ — in particular, whenever the Consumptor receives no verifier feedback and its inputs are independent of $M$ — and $M$ is uniform over $C^k$ structures with exactly one valid per instance, then $P("success") = 1\/C^k$ exactly. _Proof:_ $I("state"; M) = 0$ iff state and $M$ are independent. The prediction $hat(S)$ is a function of state, hence $hat(S) and M$ are independent. Then $P(hat(S) = M) = sum_m P(M=m) P(hat(S)=m) = (1/C^k) sum_m P(hat(S)=m) = 1/C^k$.

*Corollary 1 (verifier-mediated information).* If the Consumptor's state can depend on $M$ only through verifier feedback — i.e., the Markov chain $M -> V_(1:n) -> "state"$ holds — then by the data-processing inequality $I("state"; M) <= I(V_(1:n); M)$. Any success rate exceeding $1\/C^k$ forces $I("state"; M) > 0$ (contrapositive of Lemma 1), hence $I(V_(1:n); M) > 0$: information about $M$ entered through the verifier channel. This isolates the verifier-mediated property: above-floor performance is attributable to verifier feedback under the stated channel restriction; in the experiments below, sufficient feedback recovers the selected hidden structure, while masked-verifier controls remain at the floor.

*Assumption 1 (signature coherence).* For instances $x, x' in W$ with $sigma(x) = sigma(x')$, let $N_x$ and $N_(x')$ be their local state neighborhoods. There exists a bijection $phi: N_x arrow.r N_(x')$ such that for all $z in N_x$, $c(phi(z)) = c(z)$ and $q(phi(z)) = q(z)$. Under this assumption, a quotient verified for instance $x$ is c-admissible at every $x'$ sharing its signature.

We now state the guarantee that licenses extending the grammar with already-verified quotients — the _self-extending grammar_ mechanism. Fix an initial bounded grammar $G_0$ generated by a finite operator set $O_0$ over atomic quotients $A_0$. Let $⟦G⟧$ denote the set of quotients expressible in grammar $G$, and let $"retained"(G) subset.eq ⟦G⟧$ denote those quotients the verifier $V$ has accepted as c-admissible. For $e in "retained"(G)$, let $"expand"(G, e)$ be the grammar obtained from $G$ by promoting $e$ to a new typed atomic symbol $s_e$ with $⟦s_e⟧ := ⟦e⟧$. The _self-extending hierarchy_ is the sequence $G_0, G_1, G_2, dots$ defined by $G_(n+1) = "expand"(G_n, e_n)$ for each retained $e_n in "retained"(G_n)$, with promoted-atom definitions preserved across stages.

We assume:

+ $V$ is a sound and complete decidable oracle for c-admissibility on $⟦G_n⟧$ for every $n$.
+ $V$ is _compositional_: it resolves promoted atoms via their definitions in $⟦G_0⟧$ before deciding.
+ Enumeration of candidates is _fair_: every $e in ⟦G_n⟧$ is presented to $V$ within finitely many rounds.
+ Fiber dedup is _syntactic_, applied via a commutative canonicalization of expressions.

*Theorem (self-extending soundness and completeness).* Under the four conditions above:

_(A) Bootstrapped primitive soundness._ For every $n >= 0$ and every $e in "retained"(G_n)$, the quotient $e$ is c-admissible for $c$.

_(B) Self-extending completeness._ Define $"CC"(G_0, V)$ as the smallest set containing the $c$-admissible seed atoms (those that $V$ accepts under fair enumeration) and closed under the rule: for every $"op" in O_0$ and every $q_1, dots, q_k in "CC"(G_0, V)$, if $"op"(q_1, dots, q_k)$ is c-admissible then $"op"(q_1, dots, q_k) in "CC"(G_0, V)$. Then, up to syntactic-fiber dedup,

$ "CC"(G_0, V) subset.eq union.big_(n >= 0) { ⟦e⟧ : e in "retained"(G_n) } . $

_Proof of (A)._ If $V$ accepts $e in ⟦G_n⟧$, then $e$ is c-admissible by Definition 1 and soundness of $V$. Compositionality (Condition 2) ensures promoted atoms are resolved via their definitions before $V$ decides, so the argument holds at every level without requiring an inductive hypothesis on prior levels. $square$

_Proof of (B)._ Induct on the construction of $"CC"(G_0, V)$. For the base case, each $c$-admissible seed atom appears as a depth-0 expression in $⟦G_0⟧$; by fair enumeration and completeness of $V$, each such seed is accepted and therefore lies in $"retained"(G_0)$. For the inductive step, let $q = "op"(q_1, dots, q_k)$ be c-admissible with each $q_i$ already in $"CC"(G_0, V)$. By the induction hypothesis, each $q_i$ is represented either by an accepted seed atom or by a retained promoted atom at some level $n_i$. Let $n = max_i n_i + 1$. In $G_n$, representatives for $q_1, dots, q_k$ are available as atoms (where $s_(q_i)$ denotes the existing seed atom when $q_i$ is a seed and the promoted atom otherwise), and by fair enumeration, the composition $"op"(s_(q_1), dots, s_(q_k))$ is presented as a candidate in $⟦G_n⟧$ (provided $"max"("depth") >= 1$ for the relevant operators). By completeness of $V$, it is accepted; hence $q in "retained"(G_n)$. $square$

*Saturation (finite $W$).* If $W$ is finite, the number of distinct quotient fibers on $W$ is finite. Once the system has retained at least one expression per fiber, subsequent rounds may still introduce syntactically novel expressions for already-realized fibers (since dedup is syntactic, not algebraic), but no genuinely new fiber is discovered. Semantic saturation is reached; syntactic enumeration may continue until the round limit is reached.

*Scope.* The theorem is intentionally narrow. Termination is guaranteed only when $W$ is finite; in the Lean proof-state domain $W$ is unbounded, so coverage is bounded by a `max_rounds` parameter rather than by saturation. Completeness covers only quotients with a fully c-admissible compositional witness — quotients realizable only through inadmissible intermediates are never promoted and lie outside $"CC"(G_0, V)$. Fiber dedup is syntactic via canonicalization, not algebraic: $(u op("⊕") (v op("⊕") v))$ is not identified with $u$ unless the canonicalizer encodes that law. The theorem is symbolic; _semantic_ completeness — that retained quotients faithfully summarize world states — reduces to faithfulness of the interpreter underlying $V$. Finally, $G_0$ and $V$ are human-supplied: the system extends its vocabulary within the grammar class generated by $O_0$, not the grammar class itself.

The self-extending procedure and the verifier instances $V$ used in the experiments below are implemented in the public repository #cite(<github_repo>).


= Bounded Generation

== Construction, Not Selection

The central result of this paper is bounded and direct: the grammar $G$ constructs verified quotients that the fixed demonstration catalog $Q_0$ does not contain, the verifier $V$ accepts them, and falsifiers are rejected. The case of interest is $c in ⟦G⟧ minus Q_0$ — the quotient is constructible from the grammar but absent from the finite catalog the system was shown. Selection picks from a fixed pool; construction enumerates $⟦G⟧$ and submits $q not in Q_0$ to $V$. The catalog never contained the answer.

Formally, throughout this section:

$ Q_0 subset ⟦G⟧, quad "candidates" in ⟦G⟧ \ Q_0, quad V(q, W) = "accept" arrow.r q "retained in" cal(M). $

The evidence is six frozen formal gates and 148 tests, all returning MATCH. Each gate is cited below as a receipt, not as illustration. Acceptance throughout means the candidate is c-admissible per Definition 1, certified by the domain-specific $V$. Gates 01–03 establish construction across three independent verification regimes; Gate 04 hardens the formal regime against real-corpus replay with negative controls; Gate 05 documents retention and same-fiber alias merging in the manifold store $cal(M)$; Gate 06 establishes self-extension under the theorem.

== GF(2): Bounded Generation from Atoms and XOR

Gate 01 supplies the cleanest construction instance.

*Setup.* Grammar atoms ${u, v, w}$ over $"GF"(2)$. Operation $xor$. Restricted demonstration catalog $Q_0 = {0, u, v, w}$. The hidden functional $M$ induces a partition compatible with the quotient $u xor v$. The constructed candidate is $q = u xor v$, with $q not in Q_0$ and $q in ⟦G⟧$.

*Acceptance.* $V(q, W) = "accept"$ because the partition induced by $c$ matches the partition of the hidden functional on the probe workload $W$. The acceptance is not retrieval: $u xor v$ is not an element of $Q_0$. It belongs to the closure $⟦G⟧$ generated by the atoms under $xor$.

*Scaling.* Bounded generation requires $2^k - 1$ probes to discriminate among the $2^k$ candidate functionals. The zero-information floor is $1/C^k$: without verifier feedback, the Consumptor has zero information about which of the $C^k$ hidden structures is correct. The comparison is between a concrete probe schedule on a constructed candidate and uninformed selection over a closure of size $C^k$.

Receipts: Gate 01 (frozen MATCH), scaling receipt.

(Figures presenting these results appear in § Experimental Results.)

== Quantum: Constructing the Reduction $alpha - beta$

Gate 02 supplies a construction in which the accepted quotient is a generated reduction rather than a catalog-selected one.

*Setup.* Grammar atoms ${alpha, beta}$. Operation $sans("sub")$. The constructed candidate is $q = alpha - beta$, with $q not in Q_0$ and $q in ⟦G⟧$.

*Acceptance.* $V(q, W) = "accept"$ because the empirical CHSH statistic computed under the reduction $alpha - beta$ exceeds the classical bound $2 + delta$ (with $delta = 0.05$) on the verifier's workload $W$. The criterion is the frozen CHSH inequality; acceptance is by threshold, not by string match or parameter fit.

*Scope.* The system did not know in advance to search for $alpha - beta$. It constructed $alpha - beta$ from the available atoms under $sans("sub")$. The catalog $Q_0$ did not contain this reduction. The claim is exactly: $Q_0$ lacked $alpha - beta$; $⟦G⟧$ contained it; the verifier accepted it under the CHSH criterion. CHSH serves as the verifier in Gate 02; the result is that the grammar constructed the angle-difference reduction and the verifier certified it.

Receipts: Gate 02 (frozen MATCH), CHSH verifier receipt.


== Lean: Kernel-Certified Quotient Outside the Catalog

Gate 03 places the construction inside the formal proof regime.

*Setup.* The grammar constructs $c in ⟦G⟧ minus Q_0$ whose acceptance condition is kernel certification by Lean 4.31.0. The candidate is accepted only when the Lean kernel succeeds; parser tolerance, surface-string heuristics, and model-side confidence play no role in $V$. Scaling for the construction is linear in $k$ probes against an exhaustive comparison of $|T|^k$, where $T$ is the tactic vocabulary.

*Acceptance.* $V(q, W) = "accept"$ iff Lean kernel checking succeeds on $c$ under workload $W$. The quotient is not accepted because it resembles a proof, because it is close to a catalog entry, or because it satisfies an external score; it is accepted because Lean 4.31.0 certifies the term against the theorem.

Receipts: Gate 03 (construction, kernel verification, scaling). The real-corpus replay (Gate 04) is developed in the next section.

== Scaling

Across the three domains, the probe budgets share a common structure: each domain's construction terminates in a bounded number of verifier queries, and the zero-information floor $1/C^k$ is the baseline a non-constructing system would achieve.

/ GF(2): $2^k - 1$ probes to recover the hidden functional among $C^k$ candidates.
/ Quantum: the grammar constructs $alpha - beta$ in one composition step; the verifier accepts under the CHSH threshold.
/ Lean: $k$ probes (linear in proof depth) versus $|T|^k$ probes for exhaustive search over a tactic vocabulary $T$.

The rates are reported without editorializing. The point is the existence of a probe schedule that terminates with a verifiable candidate outside $Q_0$: bounded generation, demonstrated.

== The Grammar Self-Extends

Retained quotients in $cal(M)$ promote to new atoms in an extended grammar $G^+ supset.eq G$. By the self-extending theorem, retained quotients promote to atoms of an extended grammar $G^+$; the mechanism is demonstrated in two domains — GF(2) and the Lean kernel — where promoted atoms enable compositions that the bounded-depth grammar $G$ alone cannot reach.

The important thesis: bounded generation is not a one-shot expansion of the search space. An accepted construction enters the atom set used by subsequent constructions. This is the bootstrapping mechanism.

Receipts: Gate 06 (31 tests: GF(2) + Lean); the self-extending theorem.

== Position Against Prior Art

The construction described here is adjacent to several established programs.

*Version-space learning* maintains hypothesis sets consistent with observations; the emphasis here is quotient construction outside a deliberately restricted catalog $Q_0$, paired with verifier receipts. *CEGIS* #cite(<solarlezama2008>) iteratively refines candidates from counterexamples; bounded generation is evidenced under frozen gates by domain verifiers, with falsifiers rejected by the same $V$. *SyGuS* #cite(<alur2013>) frameworks supply grammars for synthesis; this work couples grammar-generated quotients to retention in $cal(M)$ and self-extension under the theorem. *Symbolic regression* #cite(<schmidtlipson2009>) searches expression spaces for fitted forms; here acceptance is by domain-specific verifiers — partition matching on $"GF"(2)$, the CHSH threshold, and Lean kernel certification — rather than by goodness-of-fit.

These fields construct; the distinction is the specific architecture coupling $G$, $⟦G⟧$, $Q_0$, $V$, $cal(M)$, and the self-extending theorem.

== Construction, Not Retrieval

If $q not in Q_0$, no selector over $Q_0$ returns $c$. Each gate is constructed so that the accepted quotient is absent from $Q_0$. Success therefore requires entering $⟦G⟧ minus Q_0$. The three regimes — GF(2), quantum, Lean — are three verification contexts for one construction thesis. They are not three demonstrations among which the system chose.

The bounded claim stands: the grammar constructs what $Q_0$ does not contain; the verifier accepts the constructions and rejects the falsifiers; the accepted constructions are retained and can become atoms of subsequent constructions.


= Real-Corpus Replay

The bounded-generation results in GF(2), quantum, and Lean (Gates 01–03) demonstrate construction under controlled, synthetic-style fixtures. The question that remains is whether the retention invariant survives when the candidate is not authored for the experiment but drawn from real, publicly maintained mathematics. Gate 04 answers this question.

We validate the replay machinery on the Lean-Github corpus — 218,866 tactic-step records from public Lean 4 repositories. The corpus is external: fetched via `reproduce/04_real_corpus_replay/fetch_data.sh` with SHA-256 verification, not bundled with the repository.

A pinned theorem ($"Lean4Axiomatic.Integer.one_mul_one_eqv_one"$ from the $"Lean4Axiomatic"$ package, row 69032, commit $"3b1fa53"$) is the replay target. The frozen canonical receipt (Gate 04, lite mode) covers the lite claim surface: provenance checks, forbidden-token audit, proof-block matching, candidate-row validation, and receipt determinism. The full real Lake build — replaying the pinned proof against the real source repository at the recorded commit, compiled with the pinned nightly toolchain ($"leanprover/lean4:nightly-2024-06-08"$) — is the full mode ($"RUN_FULL_REPLAY=1"$). The replay verifies:

+ *Build succeeds.* The recorded tactic, when applied to the real source repository at the recorded commit, produces a kernel-accepted proof. This is not a reconstructed self-contained file — it is a proof swapped into the real source repo, compiled against real imports and the real Lake build graph.

+ *Forbidden tokens absent.* The proof block contains no $"sorry"$, $"admit"$, $"axiom"$, or $"unsafe"$ tokens. These tokens would constitute false proofs (Lean accepts them but they bypass verification). Their absence is enforced by a scoped substring scan over the proof text.

+ *Falsifier rejected.* The verifier rejects a $"rfl"$-only bad proof block — a proof that uses only the reflexivity tactic where a non-trivial proof is required. The same $V$ that accepts the correct candidate rejects this falsifier.

+ *Receipt determinism.* Both canonical receipts are frozen and reproduce across runs. A reviewer running `bash reproduce/04_real_corpus_replay/run.sh` produces a lite receipt with $"DIGEST=MATCH"$. A reviewer with Lean and the pinned toolchain installed who runs $"RUN_FULL_REPLAY"=1$ produces a full receipt with $"DIGEST=MATCH"$ against the frozen full canonical.

The claim is not corpus-wide theorem discovery. The claim is that the construction protocol used in Gate 03 is reproducible against real build infrastructure with negative controls, and that the verifier rejects the falsifiers it is required to reject. The Lean-Github corpus validates the retention invariant on real published mathematics — not only on synthetic fixtures authored for the experiment.

Receipts: Gate 04 (frozen MATCH).

= Cross-Domain Manifold Store

The bounded-generation results produce verified quotients in three independent domains: $u xor v$ in $"GF"(2)$, $alpha - beta$ in the quantum domain, and a kernel-certified quotient in Lean. Gate 05 establishes that these quotients are not isolated outputs — they are retained in a shared manifold store $cal(M)$.

The store operates on verified fibers within each domain. Two quotients that induce the same partition of that domain's world states — the same fiber structure — are identified as a single record, even if their surface syntax differs. This same-fiber alias merging is the mechanism that allows a grammar-constructed quotient and a catalog baseline to be recognized as the same verified structure within a domain.

The scope of merging is domain-local: each domain has its own world space $W$, and fibers are witnessed only by that domain's verifier. The claim is not that arbitrary semantic equivalence is solved, nor that fibers transfer across domains, nor that the store certifies truth on its own — the verifier is always the trust boundary. The claim is that two retained constructions sharing a verified fiber within a domain are merged into a single record, and that records across domains are linked by a shared retention pattern.

The store demonstrates three properties:

+ *Cross-domain indexing.* Records from GF(2), quantum, and Lean are stored in a unified structure. Cross-domain entries are linked by storage and provenance under a shared bounded-generation retention pattern, not by claimed fiber equivalence — fibers are domain-local (each domain has its own world space $W$).

+ *Same-fiber alias merge.* Within a domain, distinct surface expressions that induce the same verified fiber — for example, the grammar-constructed $alpha - beta$ and the built-in reduction $R_"diff"$ in the quantum domain — are identified into a single store record. The receipt witnesses the merge.

+ *Store never certifies.* The store retains and links; it does not accept or reject. Every entry in $cal(M)$ carries the receipt of the verifier that accepted it. The store is an index of verified structure, not a verifier itself.

Receipts: Gate 05 (frozen MATCH).

= Experimental Results

== Reading guide

This section reports the empirical evidence for the mechanism defined above. The selection baselines are not the central claim. They witness that the verifier-mediated information channel of Corollary 1 is non-trivial: with verifier feedback the system recovers the hidden structure in the GF(2) baseline; with the verifier masked, success remains at the zero-information floor $1\/C^k$. The gap is the channel.

The headline result is generation. In each domain, the bounded grammar constructs a quotient $q$ absent from the restricted demonstration catalog $Q_0$, and the domain verifier $V$ accepts it. Tables 1--3 summarize the domains, falsifiers, and receipt gates.

== Domain-summary table (Table 1)

#figure(
  table(
    columns: (0.8fr, 0.9fr, 1.5fr, 1.0fr, 0.5fr),
    inset: (x: 6pt, y: 5pt),
    align: (left, left, left, left, center),
    stroke: none,
    table.hline(stroke: 0.5pt),
    table.header(
      [*Domain*],
      [*Constructed $q$*],
      [*$V$ criterion*],
      [*Probes (floor)*],
      [*Gate*],
    ),
    table.hline(stroke: 0.5pt),
    [$"GF"(2)$],
    [$u xor v$],
    [Partition equality against hidden functional],
    [$2^k - 1$ ($1\/2^k$)],
    [01],

    [Quantum],
    [$alpha - beta$],
    [Tier A consistency + held-out accuracy + CHSH $S > 2 + delta$],
    [One step (n/a)],
    [02],

    [Lean],
    [Kernel-certified quotient],
    [Lean 4.31.0 kernel acceptance],
    [$k$ vs. $|T|^k - 1$],
    [03],
    table.hline(stroke: 0.5pt),
  ),
  caption: [Domain summary. Each row records the generated quotient, verifier criterion, probe budget vs. zero-information floor, and gate receipt. The restricted catalog $Q_0$ excludes each constructed quotient; the verifier criterion and observed CHSH scores are reported in the text above.]
)

== Selection Baseline: The Verifier Channel Works

The selection experiment isolates the information channel. In the $"GF"(2)$ fixtures, the verifier-feedback condition succeeds with rate $1.0$. When the verifier verdict is masked, the Consumptor receives no information about the hidden functional and remains at the zero-information floor $1\/2^k$. More generally, with $C$ choices across $k$ independent decisions, the masked success probability is $1\/C^k$.

This is not presented as the main discovery claim. It is the empirical witness for Corollary 1: above-floor recovery requires information to enter through the verifier-mediated channel. In the controlled $"GF"(2)$ setting, exhaustive elimination over the $2^k$ functionals takes $2^k - 1$ probes in the worst case.

#figure(
  image("figures/fig1_scaling_curve.pdf", width: 80%),
  caption: [Selection baseline and zero-information floor in $"GF"(2)$. With verifier feedback, recovery reaches success $1.0$; with the verifier masked, success follows $1\/2^k$.]
)

#figure(
  image("figures/fig4_probe_budget.pdf", width: 80%),
  caption: [Compositional vs elimination probe budget. Worst-case probes required for recovery: compositional construction scales linearly ($k$ probes), while exhaustive elimination over $2^k$ candidate functionals scales exponentially ($2^k - 1$ probes).]
)

== Generated Quotients Outside $Q_0$

The generation tests ask whether the grammar can construct quotients that the restricted catalog $Q_0$ does not contain. The answer is positive in all three domains.

In $"GF"(2)$, $Q_0 = {0, u, v, w}$ and the grammar constructs $u xor v$. The verifier accepts it because it induces the partition required by the hidden functional. Since $u xor v not in Q_0$, the result is construction from $⟦G⟧$, not selection from the catalog.

In the quantum domain, the grammar has atoms ${alpha, beta}$ and operator $sans("sub")$. It constructs $alpha - beta$, which is absent from $Q_0$. The verifier accepts the reduction under a four-part conjunct: Tier A structural consistency, transfer consistency, held-out accuracy, and the CHSH threshold $S > 2 + delta$. The measured CHSH values are $S = 2.274$ for $Phi^+$ and $S = 2.317$ for $Psi^-$. The expanded ladder crosses the classical bound $S = 2$ #cite(<tsirelson1980>) at $theta = pi\/8$; acceptance, however, requires the stronger threshold $S > 2 + delta = 2.05$, which the measured $Phi^+$ and $Psi^-$ states exceed at $2.274$ and $2.317$ respectively. The IBM job IDs are d8unl5propqc738b1m4g for the CHSH run and d8usul0pknjs739vsua0 for the expanded run.

#figure(
  image("figures/fig3_entanglement_ladder.pdf", width: 80%),
  caption: [Quantum generation result. The entanglement ladder crosses the classical CHSH bound $S = 2$ at $theta = pi\/8$; the generated quotient $alpha - beta$ is accepted at the stronger threshold $S > 2 + delta = 2.05$.]
)

In Lean, the constructed quotient is accepted only by kernel certification. The compositional path uses $k$ probes for $k$ proof steps. The flattened baseline requires search over $|T|^k$ candidates, hence $|T|^k - 1$ probes in the worst case. Families A, B, and C witness the same compositional-vs-flattened separation under the Lean 4.31.0 verifier.

#figure(
  image("figures/fig2_compositional_probes.pdf", width: 80%),
  caption: [Compositional vs flattened probe scaling. Compositional construction reaches success $1.0$ in $k$ probes (one per proof step); flattened exhaustive search over a minimal tactic vocabulary ($|T| = 2$) requires $2^k - 1$ probes in the worst case.]
)

Each verifier verdict is binary — at most one bit per query. Recovering $k$ bits about the hidden structure $M$ therefore requires at least $k$ verifier queries. The $"GF"(2)$ domain uses $2^k - 1$ probes (exhaustive elimination over $2^k$ candidates — the most query-intensive schedule that still succeeds). The Lean domain achieves $k$ probes (one per compositional proof step), matching the information-theoretic lower bound $n >= k log_2 C$ bits (here $C = 2$, so $n >= k$). The manifold framing predicts this optimum: each verified step is a one-bit displacement along the channel, and the compositional grammar's factorization of the target into $k$ independent steps is what makes the bound attainable. A flattened (non-compositional) search cannot exploit this factorization and pays the exponential cost.

== Controls and Falsifiers (Table 2)

#figure(
  table(
    columns: (1.0fr, 0.6fr, 1.3fr, 1.1fr, 1.3fr),
    inset: (x: 6pt, y: 5pt),
    align: (left, left, left, left, left),
    stroke: none,
    table.hline(stroke: 0.5pt),
    table.header(
      [*Control*],
      [*Domain*],
      [*Expected*],
      [*Observed*],
      [*Interpretation*],
    ),
    table.hline(stroke: 0.5pt),
    [Masked verifier],
    [$"GF"(2)$],
    [No information about hidden functional; success $1\/2^k$],
    [Masked success at floor],
    [Above-floor recovery is attributable to verifier feedback],

    [Catalog exclusion],
    [$"GF"(2)$],
    [Setup: $u xor v not in Q_0$],
    [$V$ accepts $u xor v$],
    [Generation outside the restricted catalog],

    [Classical / shuffled surrogate],
    [Quantum],
    [Reduction should fail CHSH or consistency criterion],
    [Surrogate rejected; accepted law yields $S > 2$],
    [Acceptance is by verifier threshold, not by string match],

    [Forbidden-token audit],
    [Lean],
    [`sorry`, `admit`, `axiom`, and `unsafe` absent],
    [Forbidden tokens absent in replay receipt],
    [Kernel evidence is not bypassed by proof holes],

    [Bad proof block],
    [Lean],
    [`rfl`-only falsifier rejected],
    [Rejected in full replay mode],
    [The same verifier accepts the recorded proof and rejects the falsifier],

    [Flattened baseline],
    [Lean],
    [Flattened search requires $|T|^k - 1$ probes],
    [$k$ compositional probes for Families A/B/C],
    [The result is compositional construction, not exhaustive flattened selection],
    table.hline(stroke: 0.5pt),
  ),
  caption: [Controls and falsifiers. Each control specifies the expected failure or floor behavior, the observed outcome, and the interpretation licensed by that observation.]
)

== Gate Receipts (Table 3)

#figure(
  table(
    columns: (0.4fr, 1.4fr, 1.6fr, 0.8fr),
    inset: (x: 6pt, y: 5pt),
    align: (center, left, left, left),
    stroke: none,
    table.hline(stroke: 0.5pt),
    table.header(
      [*Gate*],
      [*Claim surface*],
      [*Result*],
      [*Section*],
    ),
    table.hline(stroke: 0.5pt),
    [01],
    [$"GF"(2)$ bounded generation and scaling],
    [Frozen MATCH; $u xor v$ accepted outside $Q_0$; $2^k - 1$ probes],
    [Bounded Generation],

    [02],
    [Quantum generated reduction],
    [Frozen MATCH; $alpha - beta$ accepted; CHSH jobs d8unl5propqc738b1m4g, d8usul0pknjs739vsua0],
    [Bounded Generation],

    [03],
    [Lean kernel-certified generation],
    [Frozen MATCH; quotients accepted; $k$ probes compositional vs. $|T|^k - 1$ flattened],
    [Bounded Generation],

    [04],
    [Real-corpus Lean replay],
    [Lite: frozen MATCH (18 tests). Full ($"RUN_FULL_REPLAY"=1$): frozen MATCH (25 tests, real Lake build, rfl-only falsifier rejected)],
    [Real-Corpus Replay],

    [05],
    [Cross-domain manifold store],
    [Frozen MATCH; retained records and same-fiber alias merge],
    [Cross-Domain Store],

    [06],
    [Self-extension of retained quotients],
    [Frozen MATCH; retained quotients promoted as grammar atoms under the self-extending theorem],
    [Bounded Generation],
    table.hline(stroke: 0.5pt),
  ),
  caption: [Gate receipts. Gates are cited as receipts for claim surfaces, not as illustrative examples.]
)

The receipts delimit the claims. Gates 01--03 support generated quotients outside $Q_0$ in three verifier regimes. Gate 04 supports real-corpus replay and falsifier rejection in Lean. Gate 05 supports retention in the manifold store. Gate 06 supports self-extension by promotion of retained quotients.

= The Information Manifold

The information manifold is the space of relationships between the Consumptor's observable state and the hidden structure $M$. A point on this space records how much structure about $M$ is present in the Consumptor's state: no retained relationship sits at the origin ($I("state"; M) = 0$); a verified quotient displaces the state toward a more informative point.

The notation is intentionally separated:

- $M$ is the hidden structure, accessible to the verifier and not directly readable by the Consumptor.
- $cal(M)$ is the Consumptor's retained store of verifier-accepted quotients.
- The information manifold is the space in which different observable relationships to $M$ are located.

Thus $cal(M)$ is not the hidden structure itself. It is the Consumptor's position on the manifold: the accumulated set of certified relationships it has been allowed to retain. Each accepted quotient changes that position by adding information about $M$ through the verifier channel.

== The Zero-Information Origin

The origin is the point at which the Consumptor's observable state is independent of $M$. At that point, the Consumptor has no channel by which to distinguish one hidden structure from another, and any success is baseline success under the prior.

Lemma 1 is the operational statement of this origin. If $M$ is drawn uniformly from $C^k$ possible hidden structures, exactly one is valid per instance, and the Consumptor receives no verifier feedback, then

$ P("success") = 1\/C^k . $

This is the finite zero-information floor.

In a smooth statistical projection, the zero-information condition $I("state"; theta) = 0$ means the Consumptor's state is independent of the parameter. For a regular parameterized family $p_theta$, local information is measured by the Fisher-Rao quantity

$ g_(theta theta) = E_theta[(partial_theta log p_theta(X))^2] . $

Independence forces $p_theta$ to be constant in $theta$, so $partial_theta log p_theta equiv 0$ and $g_(theta theta) equiv 0$ on the connected parameter space — not merely at the origin, but everywhere. The family degenerates to a single distribution at this point, consistent with the identifiability caveat below; this is the same condition as the counting baseline, expressed on a smooth family, grounded in Fisher's information, Rao's geometric formulation, and the Cramér–Rao bound #cite(<fisher1922>) #cite(<rao1945>) #cite(<cramer1946>).

In a discrete projection, the origin is the uniform-prior vertex. With $C^k$ hidden structures and no verifier feedback, each candidate is indistinguishable before the query channel opens, so the counting baseline is again $1\/C^k$ #cite(<cover2006>).

== Null Trajectories and Verifier Forcing

A _null trajectory_ means a trajectory with zero information gain about $M$. It is not a relativistic null geodesic. The Fisher-Rao metric, where it is defined on a regular identifiable statistical model, is a positive-definite Riemannian metric; it does not contain nonzero self-orthogonal tangent vectors. The zero-information origin is precisely where identifiability fails and the metric degenerates — the family collapses to a single distribution, so the origin is a boundary point, not an interior point of the statistical manifold. The nullness here is operational: along such a path, the Consumptor's observable state remains independent of $M$.

Verifier feedback is the only force that displaces the Consumptor off a null trajectory. Without accepted or rejected verifier responses, every update available to the Consumptor is independent of the hidden structure, so the state remains at the zero-information floor. Corollary 1 isolates this channel: any success rate above $1\/C^k$ implies that information about $M$ entered through verifier feedback.

Each accepted quotient is therefore a certified step of bounded informational displacement. The step is bounded by the grammar, the query budget, and the verifier's binary criterion; it is certified because the verifier, not the store, supplies the acceptance judgment.

== The Continuous Quantum Projection

The quantum experiment is the continuous projection of the same object. The relevant family is a parameterized measurement family, smooth in the angle-difference coordinate $theta = alpha - beta$, with observable distributions induced by measurement settings such as $alpha$ and $beta$. In this setting the Fisher-Rao metric is well-defined on the regular statistical family, and Amari's and Chentsov's information geometry applies directly #cite(<amari2000>) #cite(<amari2016>) #cite(<chentsov1982>).

What makes that family legitimate is the verified quotient itself. Once the verifier accepts $alpha - beta$, the measurement records support a family indexed by the angle difference; under the within-fiber sampling symmetry established by the experimental design, repeated shots at a fixed angle difference form a finite exchangeable sequence #cite(<definetti1937>) #cite(<diaconisfreedman1980>). The geometry is therefore earned from verified structure, not posited in advance — the metric describes distinguishability in a family the verifier has already certified as the right reduction.

The grammar constructs the reduction $alpha - beta$. The verifier accepts it when the reduced data satisfy the empirical criterion: structural consistency, held-out agreement, and CHSH violation above the classical threshold. The crossing at

$ theta = pi\/8 $

is not a singularity or threshold of the Fisher-Rao metric. It is a property of the verifier's criterion. The metric describes where information about the parameterized measurement family lives; the verifier decides when enough of that information has accumulated to accept the quotient.

Thus the continuous projection separates geometry from certification. The Fisher-Rao geometry locates distinguishability in the measurement family. The verifier turns a domain-specific acceptance rule into a retained element of $cal(M)$.

== The Discrete Projections: Synthetic and Formal

The $"GF"(2)$ and Lean demonstrations are discrete projections of the same trajectory.

In the $"GF"(2)$ projection, vertices are posterior information states over hidden functionals, the origin is the uniform-prior vertex, and edges are verifier queries. A path begins at the counting baseline $1\/C^k$ and terminates when the verifier has isolated the hidden functional. The accepted quotient, such as $u xor v$, is the retained endpoint of that verified path.

In the Lean projection, the graph is unbounded because proof states and tactic compositions are not globally finite. A single run, however, is finite and bounded by `max_rounds`. Vertices are proof-state information states, edges are kernel queries, and accepted steps are retained only when the Lean kernel certifies them.

We do not claim a Fisher metric on these graphs. The discrete projections use counting, posterior states, and verifier edges, not a smooth Riemannian structure. Their information baseline is the uniform-prior counting floor from finite information theory #cite(<cover2006>). The shared structure is the trajectory from origin to recovery, not a shared metric — within-fiber consumer-indistinguishability holds here as in the smooth case, but it supports counting and posterior structure rather than a parameterized Riemannian family.

The formal-mathematical case clarifies why the architecture should not be read as requiring a completed geometry of all future proofs. For any fixed bit budget $B$ — the maximum string length under consideration — the ambient inscription space is entirely ordinary: ${0,1}^(<= B)$, finite for each $B$ though growing without bound across all $B$, equipped, if desired, with bitwise mutation or edit distance. The temporal structure enters not because this space changes, but because more of it becomes interpretable — meaningful given the certified structure already retained — and verifier-acceptable as certified structure accumulates. Proofs cite other proofs; definitions introduce new usable atoms; lemmas compress future derivations; and a short string that was once opaque can become meaningful after the intervening theory has been built. A modern phrase such as "the contributions of Albert Einstein" would not exceed Euler's finite string space, but it would not yet be situated in an interpretable mathematical-physical library; Euler would have had to reconstruct the missing intermediate structure. Formal proof behaves the same way. Verification does not alter the ambient space of possible strings; it increases the time-foliated interpretability and acceptance density within that space. The architecture therefore recovers hidden truth locally: conjecture proposes a candidate path, the verifier rejects obstructions or accepts certificates, and accepted certificates are recorded in $cal(M)$ so that future paths through the same finite space become shorter, denser, and more available. It proves and records finite additions; it does not claim to specify in advance the completed geometry induced by all future proofs.

== One Object, Three Projections

The three demonstrations instantiate one verifier-mediated information pattern:

- the smooth manifold projection in the quantum measurement family;
- the finite graph projection in the $"GF"(2)$ fixtures;
- the unbounded graph projection in Lean, with finite verifier-bounded paths per run.

In all three, the Consumptor starts at the zero-information origin relative to $M$. It moves only when verifier feedback supplies information. Each retained quotient is certified by the relevant verifier: partition equality in $"GF"(2)$, the CHSH criterion in the quantum projection, and kernel acceptance in Lean. None of these steps is assumed by the store.

This is the geometric form of the thesis: learning is movement away from the zero-information origin by truth-verified displacement, with $cal(M)$ recording the Consumptor's certified position on the information manifold.

= Discussion and Limitations

== Limitations

First, the scope of automation is bounded by human-supplied structure. The initial grammar $G_0$, verifier $V$, and operator set $O_0$ are not discovered by the system. What the system extends is its vocabulary inside the grammar class generated by $O_0$: retained quotients may become new typed atoms, but the operator family and admissibility criterion remain externally specified. The architecture therefore does not autonomously form goals, invent new verifier regimes, or conduct open-ended scientific discovery.

Second, the algorithmic guarantees are intentionally shallow in several respects. Fiber dedup is syntactic rather than algebraic: two expressions that denote the same quotient are merged only when the canonicalizer recognizes the same fiber representation, not because the system has proved a full equational theory. Termination is guaranteed only in finite domains; in unbounded domains such as Lean proof states, coverage is operationally bounded by `max_rounds`. The quantum self-extension saturates at depth 1: the accepted reduction $alpha - beta$ is promoted and reused, but the experiment does not establish an unbounded hierarchy of new quantum abstractions.

Third, the evaluation scope is deliberately narrow. The real-corpus formal result replays one pinned theorem against a real Lake build with provenance, forbidden-token checks, and falsifier rejection; it is not a corpus-wide theorem-discovery result. The cross-domain manifold store demonstrates retention, indexing, and same-fiber alias merging under frozen receipts, but it is not compared against state-of-the-art retrieval, theorem proving, scientific discovery, or representation-learning benchmarks.

Fourth, the verifier is the trust boundary. The retained set is only as sound as the verifier that accepts it. In the formal domain, this boundary is unusually sharp because $V$ is the Lean kernel under the stated build assumptions. In empirical domains, the verifier encodes a domain criterion such as partition equality, CHSH thresholding, held-out agreement, or other externally specified tests. A bad verifier yields a bad retained set; the store records accepted structure, but it does not make acceptance true.

== Extensions and Applications

The extensions below are research directions licensed by the architecture, not results established in this paper.

One direction is to replace exhaustive enumeration with richer proposer mechanisms. A proposer could be an LLM, a neural policy, a Monte Carlo tree search controller, a random sampler, a symbolic heuristic, or a hybrid of these. This changes the order in which candidates are submitted to $V$, and may improve efficiency in large spaces, but it does not change the soundness boundary: retained structure remains sound only because the verifier accepts it, not because the proposer is trusted.

A second direction is to broaden verifier classes. Robotics and physics provide high-assurance application settings when the verifier is grounded in physical constraints, calibration, safety envelopes, or reproducible measurements, but such verifiers are not kernels and their retained sets must be interpreted accordingly. Learned verifiers, including JEPA-style or JEPA2-style predictive abstractions, would be probabilistic rather than sound in the theorem's sense; the relevant relaxation would be from sound retention to calibrated retention, with the soundness theorem replaced by a theorem about calibrated error, confidence, and verifier drift. The self-extending grammar is a candidate bridge for short-horizon abstractions in JEPA-like systems because retained short-range abstractions can become reusable atoms, but this is a research direction, not an established result.

A third direction is application to public, verifier-friendly domains. Seismology, public health, and formal methods are natural candidates because each can define claims that are checked against external evidence: earthquake-related public claims against geophysical data, respiratory or mortality claims against public-health streams, and proof claims against proof kernels or proof assistants. The claim in these settings would be verification, not prediction: the architecture would test whether a proposed quotient or claim survives the specified evidence contract. These domains are candidate future work, not deployed systems #cite(<github_repo>).

A fourth direction is architectural. Dataset-to-dataset traversal could be delegated to an external scout that proposes candidate evidence links while the verifier remains the retention gate. A language connector could translate natural-language claims into typed candidate quotients and verifier calls. Meta-level self-direction could choose which verifier-bounded task to attempt next without changing the rule that only verified structure is retained. More ambitiously, the self-extending grammar could serve as a bridge between short-horizon learned abstractions and longer compositional structure: a learned system proposes local structure; the verifier retains only calibrated or sound candidates; retained candidates become new atoms for later search. These are research directions, not results.

== The Path of Truth

The mechanism can be restated as traversal. The Consumptor hypothesizes a candidate from $G$, submits it to $V$, and retains it only when the verifier certifies admissibility. Learning is the consumption of truth-verified structure: each retained step is a certified displacement away from the zero-information origin.

Restated geometrically, the parameters of this traversal are the typings themselves — the verifier-accepted quotients — and the traversal is a dual projection carried out on coordinates earned by verification, not on a parametric family fixed in advance. In the smooth quantum case this is the Fisher-Rao dual projection; in the discrete cases it is the same projection pattern carried by counting and posterior structure, with no metric claimed.

The destiny of this traversal has a precise mathematical shape. The self-extending theorem says that, under soundness, completeness, fair enumeration, compositional resolution, and the stated syntactic dedup condition, the retained hierarchy approaches $"CC"(G_0, V)$: the compositional closure generated from $G_0$ under verifier-accepted operations. This is not metaphor. It is the theorem-level object toward which the retained set moves, bounded by the grammar, the verifier, and the admissible compositions they jointly permit.

This is where the architecture separates from statistical scaling. A statistical path may become more capable as data, parameters, and compute increase, but its retained internal structure is not generally certified step by step by an external admissibility verifier. Here the defining properties are soundness, certified retention, and verifier-bounded extension. The system is allowed to grow only by consuming what the verifier has accepted, and the retained manifold is therefore a record of certified structure rather than a record of optimized weights.

The honest claim is precise, not a slogan: a defensible candidate architecture whose growth rule has soundness, certified retention, and verifier-bounded self-extension, properties not guaranteed by parameter scaling alone. The path of truth, as we mean it here, is the path along which each step has been checked.

= Data and Code Availability

All code, test artifacts, and quantum data are available in the public repository #cite(<github_repo>). Quantum measurements were collected on ibm_marrakesh (156-qubit IBM Quantum processor) #cite(<ibmquantum2024>) at 4000 shots per circuit. The CHSH circuits are recorded under IBM job ID d8unl5propqc738b1m4g; the expanded circuits (angle sweep, entanglement ladder, resample ensemble) under d8usul0pknjs739vsua0. Backend calibration, timestamps, transpiled circuit definitions, and raw measurement counts are archived in the repository.

The correlator and CHSH formulas are:

$ E = (N_(00) + N_(11) - N_(01) - N_(10)) \/ N_("total") $

$ S = |E(a, b) - E(a, b') + E(a', b) + E(a', b')| $

where $N_("ij")$ are raw count frequencies and the four CHSH settings use angles $a = 0$, $a' = pi\/4$, $b = pi\/8$, $b' = 3pi\/8$.

#bibliography("refs.bib")
