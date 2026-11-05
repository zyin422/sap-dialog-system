// Typst Academic Research Poster: "Beyond WER"
// Trick or Research 2026 — Siebel School of Computing and Data Science, UIUC
// Dimensions: 48 inches wide x 36 inches tall (Landscape)

#import "@preview/peace-of-posters:0.6.0": *

#set page(
  width: 48in,
  height: 36in,
  margin: (top: 0.8in, bottom: 0.8in, left: 1.2in, right: 1.2in),
  fill: rgb("#FFFFFF"),
)

#set text(
  font: "Liberation Sans",
  size: 15.5pt,
  fill: rgb("#1F2937"),
)

#let uiuc-navy = rgb("#13294B")
#let uiuc-orange = rgb("#E84A27")

// -------------------------------------------------------------
// POSTER HEADER
// -------------------------------------------------------------
#block(
  fill: uiuc-navy,
  inset: (x: 1.2in, y: 0.6in),
  radius: 4pt,
  stroke: (bottom: 8pt + uiuc-orange),
  width: 100%,
)[
  #grid(
    columns: (1fr, auto),
    gutter: 1in,
    [
      #text(fill: rgb("#FDBA74"), size: 16pt, weight: "bold")[TRICK OR RESEARCH 2026 · CS STARS SYMPOSIUM · THOMAS M. SIEBEL CENTER]\
      #v(0.2em)
      #text(fill: white, size: 38pt, weight: "black")[
        Beyond WER: Quantifying ASR Error Propagation in Spoken Language Understanding for Dysarthric Speech
      ]\
      #v(0.3em)
      #text(fill: rgb("#F3F4F6"), size: 21pt, weight: "bold")[
        #underline[Zixuan Yin]#super("1"), Xiuwen Zheng#super("1"), Haolong Zheng#super("1"), Kush Bhardwaj#super("1"), Mark Hasegawa-Johnson#super("1")
      ]\
      #v(0.1em)
      #text(fill: rgb("#D1D5DB"), size: 15pt)[
        #super("1")Department of Electrical & Computer Engineering and Siebel School of Computing & Data Science, UIUC\
        Speech Accessibility Project (SAP) · Beckman Institute for Advanced Science and Technology
      ]
    ],
    align(right + horizon)[
      #block(
        fill: uiuc-orange,
        inset: 16pt,
        radius: 4pt,
        stroke: 3pt + white,
      )[
        #text(fill: white, size: 44pt, weight: "black", font: "Liberation Serif")[I]
      ]
      #v(0.4em)
      #text(fill: rgb("#E5E7EB"), size: 12pt, weight: "bold")[ACCESS CIS250149\ NCSA Delta GPU]
    ]
  )
]

#v(0.5in)

// -------------------------------------------------------------
// 3-COLUMN ACADEMIC GRID
// -------------------------------------------------------------
#columns(3, gutter: 0.5in)[

  // -----------------------------------------------------------
  // COLUMN 1
  // -----------------------------------------------------------
  #block(
    fill: white,
    inset: 20pt,
    radius: 4pt,
    stroke: 1.5pt + rgb("#D1D5DB"),
    width: 100%,
  )[
    #text(fill: uiuc-navy, size: 19pt, weight: "bold")[1. Introduction & Clinical Motivation]
    #v(0.4em)
    Motor speech disorders (dysarthria) affect over *100 million individuals globally* resulting from Cerebral Palsy (CP), ALS, Parkinson's disease (PD), and stroke. Hands-free voice interfaces provide essential independence, but commercial systems fail drastically.

    #v(0.3em)
    - *Acoustic Degradation:* Hypernasality, prolonged phonemes, atypical pitch contours, and irregular rates yield commercial *Word Error Rates (WER) of 30%–50%+*.
    - *Turn-Taking Truncation:* Involuntary mid-sentence pauses trigger standard Voice Activity Detection (VAD) energy cutoffs, prematurely terminating commands.
  ]

  #v(0.35in)

  #block(
    fill: white,
    inset: 20pt,
    radius: 4pt,
    stroke: 1.5pt + rgb("#D1D5DB"),
    width: 100%,
  )[
    #text(fill: uiuc-navy, size: 19pt, weight: "bold")[2. The "Beyond WER" Problem]
    #v(0.4em)
    Conventional speech benchmarks evaluate models solely by minimizing transcription WER. However, downstream task completion demonstrates starkly non-linear sensitivity:

    #v(0.3em)
    - *Benign Disfluencies:* Dropped function words ("the", "a"), repetitions, and fillers ("uh", "um") are absorbed by LLM contextual priors.
    - *Catastrophic Entity Corruptions:* Phonetic mutations in *action slots and named entities* ("call mom" $arrow$ "call tom", "5mg" $arrow$ "50mg") cause unrecoverable task failure or hazardous actions.

    #v(0.4em)
    #block(fill: rgb("#F9FAFB"), inset: 10pt, stroke: (left: 4pt + uiuc-navy))[
      *Research Question (RQ):* _What quantitative gains does dysarthria-specific acoustic adaptation yield at the level of downstream spoken language understanding (SLU) and tool invocation, beyond transcript WER?_
    ]
  ]

  #v(0.35in)

  #block(
    fill: white,
    inset: 20pt,
    radius: 4pt,
    stroke: 1.5pt + rgb("#D1D5DB"),
    width: 100%,
  )[
    #text(fill: uiuc-navy, size: 19pt, weight: "bold")[3. Audited SLU Benchmark (Schema v1.3)]
    #v(0.4em)
    Audio is sourced from the *Speech Accessibility Project (SAP)* at UIUC Beckman Institute. To quantify downstream task execution, we formulated an audited benchmark grounded in OpenAPI 3.0 schemas:

    - *1,274 Canonical Gold Commands:* Multi-model consensus (Claude 3.5 Sonnet & GPT-4o) with human verification. 100% compliant with strict typing and slot validation rules.
    - *35 Out-of-Domain (OOD) Items:* Partitioned out wake phrases, OS system utility launches, and dictation fragments to prevent metric distortion.
    - *10 Real-World Domains (29 Tools):* Health, Communication, Calendar/Alarm, Smart Home, Media, Places, QA, Notes, Accessibility, and Transport.
    - *Speaker-Disjoint Protocol:* Evaluation audio is strictly disjoint from acoustic training splits to measure true generalized adaptation.
  ]

  #colbreak()

  // -----------------------------------------------------------
  // COLUMN 2
  // -----------------------------------------------------------
  #block(
    fill: white,
    inset: 20pt,
    radius: 4pt,
    stroke: 1.5pt + rgb("#D1D5DB"),
    width: 100%,
  )[
    #text(fill: uiuc-navy, size: 19pt, weight: "bold")[4. Decoupled System Architecture]
    #v(0.4em)
    Rather than an uninspectable end-to-end black box, we implement a *strictly decoupled cascaded pipeline* that isolates acoustic recognition errors from LLM reasoning failures:

    #v(0.3em)
    #align(center)[
      #block(fill: rgb("#F9FAFB"), inset: 12pt, radius: 4pt, stroke: 1pt + rgb("#D1D5DB"))[
        *SAP Dysarthric Audio* (16 kHz Waveform)\
        $arrow.b$\
        *Turn Segmentation* (Push-to-Talk / Zero Pause Truncation)\
        $arrow.b$\
        *Streaming ASR: Parakeet-TDT 0.6B* (12.5 Hz, 80ms chunks)\
        _Condition 2: Zero-Shot Base | Condition 3: Fine-Tuned SAP_\
        $arrow.b$\
        *Frozen Downstream Agent: Qwen 2.5 72B-Instruct* ($T=0.0$)\
        _OpenAPI 3.0 Function-Calling Engine & Strict Slot Validation_
      ]
    ]
  ]

  #v(0.35in)

  #block(
    fill: white,
    inset: 20pt,
    radius: 4pt,
    stroke: 1.5pt + rgb("#D1D5DB"),
    width: 100%,
  )[
    #text(fill: uiuc-navy, size: 19pt, weight: "bold")[5. Controlled Evaluation Protocol]
    #v(0.4em)
    The downstream LLM agent prompt, OpenAPI tool definitions, and temperature ($T=0.0$) are held *100% constant* across three experimental conditions:

    - *Condition 1 (Oracle Ceiling):* Pristine human ground-truth transcripts. Measures the LLM's semantic reasoning capacity.
    - *Condition 2 (Base ASR Baseline):* Unadapted zero-shot NVIDIA Parakeet-TDT (Acoustic WER: *28.15%*).
    - *Condition 3 (Fine-Tuned ASR):* Parakeet-TDT fine-tuned on speaker-disjoint SAP audio (Acoustic WER: *10.70%*).

    #v(0.3em)
    *Key Metrics:*
    - *Tool Selection (TS):* Exact target API match.
    - *Parameter Filling (PF):* Exact slot keys and argument values.
    - *Command Frame Acc:* $\text{TS} = 1 \land \text{PF} = 1$.
    - *Adaptation Recovery Rate (ARR):*
      $ "ARR" = ("Acc"("FT") - "Acc"("Base")) / ("Acc"("Oracle") - "Acc"("Base")) times 100% $
  ]

  #colbreak()

  // -----------------------------------------------------------
  // COLUMN 3
  // -----------------------------------------------------------
  #block(
    fill: white,
    inset: 20pt,
    radius: 4pt,
    stroke: 1.5pt + rgb("#D1D5DB"),
    width: 100%,
  )[
    #text(fill: uiuc-navy, size: 19pt, weight: "bold")[6. Empirical Evaluation (Pilot Dev N=291)]
    #v(0.4em)
    Evaluation across 291 benchmark dev utterances on NCSA Delta GPUs:

    #v(0.2em)
    #table(
      columns: (1.5fr, 0.8fr, 0.8fr, 0.8fr, 1fr),
      inset: 7pt,
      stroke: (x, y) => if y == 0 { (bottom: 2pt + uiuc-navy, top: 2pt + uiuc-navy) } else if y == 4 { (bottom: 2pt + uiuc-navy) } else { 0.5pt + rgb("#E5E7EB") },
      fill: (x, y) => if y == 3 { rgb("#FEF9C3") } else { none },
      [*Condition*], [*WER*], [*TS*], [*PF*], [*Frame Acc*],
      [1. Oracle Ceiling], [0.0%], [88.3%], [66.7%], [*59.45%*],
      [2. Base Parakeet], [28.2%], [74.2%], [40.3%], [28.18%],
      [*3. Fine-Tuned ASR*], [*10.7%*], [*86.6%*], [*58.7%*], [*50.52%*],
      [*Net Gain*], [*-17.5%*], [*+12.4%*], [*+18.4%*], [*+22.3%*],
    )
    #text(size: 11pt, style: "italic")[*Table 1:* End-to-end SLU performance. Acoustic adaptation recovers *71.44%* of the downstream task failure gap.]

    #v(0.3em)
    *Disproportionate Gain in High-Stakes Assistive Domains:*
    - *Health & Medication (N=42):* Base 14.3% $arrow$ Fine-Tuned *81.0%* (*+66.7% gain*). Preserves critical dosages and symptom entities.
    - *Communication (N=33):* Base 24.2% $arrow$ Fine-Tuned *72.7%* (*+48.5% gain*). Recovers recipient contact names.
    - *General QA (N=90):* Base 35.6% $arrow$ Fine-Tuned *48.9%* (*+13.3% gain*). Search queries tolerate noisy keywords.
  ]

  #v(0.35in)

  #block(
    fill: white,
    inset: 20pt,
    radius: 4pt,
    stroke: 1.5pt + rgb("#D1D5DB"),
    width: 100%,
  )[
    #text(fill: uiuc-navy, size: 19pt, weight: "bold")[7. Error Analysis & Next Steps]
    #v(0.4em)
    *Slot Mutation vs. Recovery:*
    - *Base ASR:* "set alarm for _several thirty_" $arrow$ `time="several:30"` (Type Error / Crash).
    - *Fine-Tuned:* "set alarm for _7:30 a.m._" $arrow$ `alarm_create(time="07:30")` (*Task Success*).
    - *SECR:* In *35.07%* of corrupted slots, the LLM inferred gold slots from phonetic context (e.g. "call dr house agar" $arrow$ "Dr. Hasegawa").

    #v(0.3em)
    *Immediate Research Roadmap:*
    1. *Corpus Scaling:* Expand inference across all 1,274 gold utterances on NCSA Delta GPUs.
    2. *Phonetic Tolerance:* Integrate Double Metaphone metrics into parameter grading.
    3. *Full-Duplex Dialogue:* Develop pause-tolerant atypical VAD models to replace push-to-talk.
    4. *Edge Deployment:* Quantize fine-tuned streaming ASR for on-device assistive hardware.
  ]

]

#v(0.4in)

// -------------------------------------------------------------
// POSTER FOOTER
// -------------------------------------------------------------
#block(
  fill: rgb("#F3F4F6"),
  inset: (x: 1.2in, y: 0.3in),
  radius: 4pt,
  stroke: (top: 1.5pt + rgb("#D1D5DB")),
  width: 100%,
)[
  #grid(
    columns: (1fr, auto),
    align: (left + horizon, right + horizon),
    [
      #text(size: 13pt, weight: "bold")[Speech Accessibility Project (SAP) · Beckman Institute · University of Illinois Urbana-Champaign]\
      #text(size: 11pt, fill: rgb("#4B5563"))[Supported by the SAP Consortium and ACCESS Project Allocation CIS250149 on NCSA Delta GPU cluster.]
    ],
    [
      #text(size: 12pt, weight: "bold")[Code & Benchmark Explorer:]
      #text(size: 11pt, fill: rgb("#4B5563"))[ github.com/zyin422/sap-dialog-system]
    ]
  )
]
