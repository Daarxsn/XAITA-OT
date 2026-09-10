# XAITA-OT Architecture

```text
OT Observations
      |
      v
Preprocessing / Semantic Harmonization
      |
      v
CNN-LSTM Detector ----> Detection Evidence (DC)
      |
      v
BTAE Event Correlation ----> Attack Episode (EC)
      |                         |
      +----> BSS --------------+
      |                         |
      +----> ECS / ATT&CK ------+
      |                         |
      +----> MAS ---------------+
                                v
                         ACFM Evidence Fusion
                     / supporting / conflicting / unresolved /
                                |
                                v
                   Belief / Plausibility Attribution
                                |
                 +--------------+--------------+
                 |              |              |
                 v              v              v
               XAI            Risk            CTI
                 |              |              |
                 +--------------+--------------+
                                v
                     Evidence-linked output
                                |
                                v
                       Human Analyst Review
```

The implementation keeps detection confidence and attribution confidence separate. ATT&CK mappings are contextual evidence, not actor identity proof. CTI contains provenance IDs pointing back to source events.
