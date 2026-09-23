---
status: draft
---

# Choose a question by the decision you need

Status: **draft**. All numbers on this page are synthetic illustrations.
They are not service observations or accuracy measurements.

Suppose a support ticket says: “I was charged twice. Please help today.”
That text is the **state**. You could ask whether it concerns billing, which
team should handle it, or how urgent it is. Those are different questions,
even though they use the same text. Choosing the type defines what the
answer can mean; it does not choose your application's action.

## A proposition: Noul

“Is this about billing?” asks whether a proposition is true. A Noul answer
of `0.85` expresses the model's probability of yes. It is not a boolean and
does not mean that 85% of the ticket is about billing. A value near zero
supports no; a value near one supports yes. A middle value leaves more
uncertainty between those outcomes. Noul has no separate confidence field.
These are the semantics of [TypeSafe's Noul primitive](https://docs.typesafe.ai/primitives/noul).

Your application still needs a decision rule. Sending a ticket to a review
queue may tolerate more false positives than taking an irreversible action.
The probability alone cannot choose that tradeoff. A [local policy](policies.md)
expresses the application's acceptance rule.

## Unordered alternatives: Choice

“Which team should handle this?” selects between labels such as `billing`
and `technical`. Choice supplies the selected label, each option's probability,
and confidence. The label with the highest probability is selected. Confidence
summarizes the distribution's concentration; it is not simply another name
for the selected probability. See [TypeSafe's Choice definition](https://docs.typesafe.ai/primitives/choice).

For example, synthetic probabilities of `0.6` for billing and `0.4` for
technical select billing, but still leave substantial probability on technical.
There is no ordering between these labels: technical is not “more” than
billing. Replacing them with numbers would hide that distinction.

The label set also defines what can be selected. If a ticket fits neither
team, a forced choice between only those teams does not establish a good fit.
Your application must decide whether its categories cover the task and how to
handle uncertain cases. A high confidence value does not prove the categories
or the resulting route are correct.

## Ordered levels: Score

“How urgent is this?” asks for a position on a rubric. Use descriptions such
as “Can wait,” “This week” and “Today.” Their positions define levels zero,
one and two. The answer includes `legend`, which maps levels to descriptions,
and `probabilities`, which describes the model's distribution over levels.
The numeric `score` is the probability-weighted mean. It can fall between levels.
See [TypeSafe's Score definition](https://docs.typesafe.ai/primitives/score).

| Level | Description | Synthetic probability | Contribution |
|---|---|---|---|
| 0 | Can wait | 0.1 | 0.0 |
| 1 | This week | 0.2 | 0.2 |
| 2 | Today | 0.7 | 1.4 |

The probabilities sum to one. Their weighted mean is `1.6`. That value is a
position on this rubric, not a probability and not confidence. It does not
mean 1.6 days or 80% urgency. Changing the rubric changes its interpretation.

A score also loses information. Equal probability on levels zero and two
has mean one, just like all probability on level one. The first distribution
splits between extremes; the second concentrates in the middle. Read the
probabilities and confidence alongside the score before deciding how to act.
TypeSafe describes this distinction in its [Score interpretation guidance](https://docs.typesafe.ai/primitives/score).

## Valid structure is not a correct judgment

A typed answer lets your code access known fields without parsing generated
prose. A structurally valid answer can still misunderstand a ticket. Neither
reported probability nor confidence establishes measured accuracy on your data.
judgevet has not validated statistical calibration. Confidence `0.7` does not
prove that 70% of comparable judgments are correct.

Use deterministic checks for facts you can compute exactly, such as whether
an invoice identifier exists in your database. Use review by a person when
missing context or the cost of error makes an automated decision unsuitable.
Those review and routing actions belong to your application; judgevet does
not supply a review queue or execute refunds.

Next, read [how policies turn answers into decisions](policies.md) and
[what verification establishes](verification.md). For code, use the
[library quick start](../../README.md#use-the-typed-library) and
[Python policy guide](../how-to/use-policy-library.md).
The [glossary](../reference/glossary.md) and [API reference](../reference/api.md)
provide lookup definitions and fields.

Practice with the [first-judgment tutorial](../tutorials/first-judgment.md).
