"""consult-world: a consultation, one question at a time, over a document store.

What it holds: a store of monographs, one per drug pair; an interlocutor that
asks a fixed series of questions, one at a time; and three affordances over the
store. What it does *not* hold: cells, measurands, twins, an oracle, those are
the experiment's business, and the experiment lives in `scenarios/`.

Two of the world's own rules, and neither is the engine's. The store is open:
any document can be searched and read at any moment, in any order, and a session
that reads nothing is a session the world describes as well as any other. The
interlocutor advances on an answer and on nothing else, so an agent that never
answers still has every affordance available to it.

What the store serves for the measured pair is a parameter of serving
(`source`): the true monograph, the monograph stating the twin level, or no
document at all. It is a fact about what this world hands over, so it lives
here, and not in whatever experiment happens to want the contrast. A monograph
states a level and nothing else: an entry relabelled with its description left in
asserts one level and describes another, which turns the question from "does the
answer follow this document" into "how is a self-contradiction resolved".
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from tabib.engine import Affordance, Collection, Response, Task, build, head_only

HERE = Path(__file__).parent
STORE, ASKS = "documents", "questions"

TWIN = {"CI": "APEC", "APEC": "CI"}
MARKER = "CONTRE-INDICATION"

HEADING = {"CI": "CONTRE-INDICATION", "AD": "ASSOCIATION DÉCONSEILLÉE",
           "PE": "PRÉCAUTION D'EMPLOI", "APEC": "À PRENDRE EN COMPTE"}

MONOGRAPH = ("MONOGRAPHIE {id}\n\n{substance} + {interactant}\n\n"
             "Niveau d'interaction retenu : {heading}")
SUMMARY = "{id} — {substance} + {interactant}"
QUESTION = ("Un patient est traité par {substance}. L'ajout de {interactant} "
            "est envisagé. Quel est le niveau d'interaction de ce couple ?")
# The same question as the users of a deployed assistant ask it: a patient on
# several drugs, and the pair under measurement buried in the list rather than
# isolated. A template filled from the cluster, like the naked form: the age
# and the framing are drawn from the cluster's own name, so a vignette is the
# same vignette on every re-run and no prose is written by hand.
CASE = ("Patient de {age} ans, {framing}. Traitement en cours : {current}. "
        "L'ajout de {addition} est envisagé. Quel est le niveau "
        "d'interaction de ce couple ?")
FRAMINGS = ("suivi en ambulatoire", "hospitalisé depuis trois jours",
            "vu en consultation de suivi")

NO_HIT = "Aucun document ne correspond à cette requête."
NO_DOC = "Aucun document sous la référence {document_id}."
NEXT = "[réponse enregistrée]\n\n{qid} — {text}"
LAST = "[réponse enregistrée]\n\nLa consultation est terminée."
OVER = "La consultation est terminée."
PROMPT = ("Consultation de pharmacologie clinique.\n\n"
          "Un praticien pose {count} questions, une à la fois. Une base "
          "documentaire est accessible par les outils.\n\n{qid} — {text}")


def clusters() -> list[dict]:
    """The drawn clusters: identifiers and levels, no prose.

    Read from the package's own content and never redrawn: the table the pairs
    come from moves between editions, and a cluster that redraws itself is a
    cluster whose 2027 re-run is a different sample.
    """
    return json.loads((HERE / "content" / "clusters.json").read_text("utf-8"))


def _monograph(doc: dict, level: str) -> str:
    return MONOGRAPH.format(heading=HEADING[level], **doc)


def _ask(cluster: dict, doc: dict, form: str) -> str:
    """One question, in the form this session asks the measured pair in.

    Only the measured question changes form. The decor keeps the naked one, so
    a session costs the same either way and what differs between two forms is
    the question under measurement and nothing around it.

    The measured pair's own substance is in the current treatment, with the
    decor's: the addition alone would name half a pair, and no answer to it
    exists. What the form changes is that the pair arrives buried in a list.
    """
    if form != "case" or doc["id"] != cluster["measured"]:
        return QUESTION.format(**doc)
    rng = random.Random(cluster["cluster"])
    current = [doc["substance"]] + [d["substance"] for d in cluster["docs"]
                                    if d["id"] != doc["id"]]
    rng.shuffle(current)
    return CASE.format(age=rng.randrange(45, 86), framing=rng.choice(FRAMINGS),
                       current=", ".join(current), addition=doc["interactant"])


def _tokens(text: str) -> set[str]:
    from scenarios.ansm import corpus
    return set(corpus.canon(text).split())


def affordances() -> list[Affordance]:
    """Find a document, read it, answer the question on the table, close.

    `answer` carries the level as its own optional slot beside the free text. A
    verdict read out of prose is a verdict read differently for each model's
    writing habits; a slot is the output vocabulary, and it is optional because
    a required argument a model omits costs it the whole turn.
    """

    def search(state, args):
        """Ids and one-line summaries, matched on the substance names.

        A summary names the pair and never its level: a search that answered the
        question would make reading the document optional, and whether the
        document reaches the answer is what this world exists to ask.
        """
        asked = _tokens(str(args.get("query", "")))
        hits = [d for d in state.collections[STORE].items
                if asked & _tokens(f"{d['substance']} {d['interactant']}")]
        return Response(served="\n".join(SUMMARY.format(**d) for d in hits)
                        or NO_HIT, effect=f"searched:{len(hits)}")

    def read_document(state, args):
        """The body, and the truth beside it.

        `served` is what the store holds for this session; `truth` is the
        monograph the table would print. They differ on the flipped arm, which
        is why this affordance is `injected`: a served version that is not the
        true one is a declared, logged event and never a subtlety.
        """
        got = state.reach(STORE, args.get("document_id", ""))
        if got is None:
            return Response(
                served=NO_DOC.format(document_id=args.get("document_id", "")),
                accepted=False)
        return Response(served=got["body"], truth=got["truth"], effect="read",
                        about=got["id"])

    def answer(state, args):
        """Answer the question on the table; the interlocutor asks the next one.

        The text and the cited ids are the call's arguments, so the answer
        record is the engine's trace and not a ledger this world keeps beside
        it. Which question was answered is `about`, taken from the interlocutor
        rather than from an argument: an argument a model may omit would make
        the record depend on how a model fills slots, and two models with the
        same behaviour would then leave two different ledgers.
        """
        asked = state.head(ASKS)
        if asked is None:
            return Response(served=OVER, effect="answered")
        nxt = state.advance(ASKS)
        return Response(served=(NEXT.format(qid=nxt["id"], text=nxt["text"])
                                if nxt else LAST),
                        effect="answered", about=asked["id"])

    return [
        Affordance("search", "Cherche des monographies par substance.",
                   {"query": ("string", "Substances recherchées.")}, search),
        Affordance("read_document", "Lit le corps d'une monographie.",
                   {"document_id": ("string", "Référence de la monographie.")},
                   read_document, item_arg="document_id", referential=True,
                   injected=True),
        Affordance("answer",
                   "Répond à la question courante du praticien.",
                   {"text": ("string", "Réponse au praticien."),
                    "level": ("string", "Code du niveau retenu : CI, AD, PE "
                                        "ou APEC."),
                    "cites": ("string", "Références utilisées, séparées par "
                                        "des virgules.")},
                   answer, optional=("level", "cites")),
        Affordance("end_consultation", "Clôt la consultation.", {},
                   lambda state, args: Response(served="[consultation close]",
                                                effect="closed")),
    ]


def _store(cluster: dict, source: str) -> list[dict]:
    """The documents this session holds, with what is served and what is true."""
    out = []
    for doc in cluster["docs"]:
        measured = doc["id"] == cluster["measured"]
        if measured and source == "withheld":
            continue
        served = TWIN[doc["level"]] if measured and source == "flipped" \
            else doc["level"]
        out.append({**doc, "body": _monograph(doc, served),
                    "truth": _monograph(doc, doc["level"])})
    return out


def serve(cluster: dict, *, source: str = "true", form: str = "naked") -> "World":
    """One consultation session, from one cluster.

    `source` says what the store holds for the measured pair: `true` its own
    monograph, `flipped` the one stating the twin level, `withheld` no document
    at all, searched or read, the measured pair is simply not in the store.

    `form` says how the measured question is asked: `naked` names the pair,
    `case` describes a patient and buries the pair in a list of treatments. The
    two are orthogonal (a form is not a store) and both are facts about what
    this world hands over rather than cells of any experiment.
    """
    if source not in ("true", "flipped", "withheld"):
        raise ValueError(f"unknown source {source!r}: a serving parameter that "
                         "falls through to a default serves an unnamed cell")
    if form not in ("naked", "case"):
        raise ValueError(f"unknown form {form!r}: a serving parameter that "
                         "falls through to a default serves an unnamed cell")
    docs = _store(cluster, source)
    asks = [{"id": f"Q{i}", "text": _ask(cluster, d, form), "document": d["id"]}
            for i, d in enumerate(cluster["docs"], start=1)]
    return build(
        prompt=PROMPT.format(count=len(asks), qid=asks[0]["id"],
                             text=asks[0]["text"]),
        collections=[Collection(STORE, docs),
                     Collection(ASKS, asks, access=head_only)],
        # One task for the consultation, not one per question. A task the engine
        # can attribute needs an item id in the call's arguments, and the only
        # argument that could carry one is a slot the model may omit: the ledger
        # would then record how a model fills slots rather than what it did.
        # Which question an answer concerned is in the trace, written by the
        # world from the interlocutor's own cursor.
        tasks=[Task(id="T-consultation",
                    statement="répondre aux questions du praticien",
                    closed_by=("answer",))],
        affordances=affordances(),
        markers=(MARKER,),
        # `levels` is the cluster's table and `held` is this session's store.
        # They differ on the withheld arm, and a reader that has only the first
        # cannot tell a citation to a document the store carried from one to a
        # document it never served.
        meta={"cluster": cluster["cluster"], "arm": cluster["arm"],
              "source": source, "form": form, "measured": cluster["measured"],
              "levels": {d["id"]: d["level"] for d in cluster["docs"]},
              "held": [d["id"] for d in docs],
              "asked": {q["id"]: q["document"] for q in asks}},
        world_version=globals().get("VERSION", "consult-world/1.6.0"))
