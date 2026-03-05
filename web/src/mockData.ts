import type { BenchmarkExample, BenchmarkSummary, LiveScoringRun } from "./types";

/**
 * The claim/verdict/reason detail below is real Mistral judge output captured from a live
 * diagnostic run against the actual HaluEval QA benchmark rows (see docs/superpowers/plans and
 * the project's diagnosis notes) — not invented. It stands in for the per-example benchmark
 * persistence the backend does not yet build (see PRODUCT.md's "Explicitly undecided" section);
 * once that lands, this module is replaced by a real API call, not edited in place.
 *
 * The aggregate numbers in `benchmarkSummary` below are the actual, currently-published
 * README figures (87.0% / 80.0% / 83.3% F1, ~73.7% naive ceiling) and must never drift from it.
 */

export const benchmarkExamples: BenchmarkExample[] = [
  {
    id: "halueval-000",
    question: "Which magazine was started first, Arthur's Magazine or First for Women?",
    answer: "Arthur's Magazine",
    sources: [
      "Arthur's Magazine (1844–1846) was an American literary periodical published in Philadelphia in the 19th century. First for Women is a woman's magazine published by Bauer Media Group in the USA.",
    ],
    humanLabel: "supported",
    score: 1.0,
    claims: [
      {
        claim: "Arthur's Magazine was started before First for Women.",
        verdict: "entailed",
        reason:
          "The sources state Arthur's Magazine was published from 1844–1846, while First for Women is a modern magazine with no specified start date, implying it began much later.",
      },
    ],
  },
  {
    id: "halueval-004",
    question:
      'Musician and satirist Allie Goertz wrote a song about the "The Simpsons" character Milhouse, who Matt Groening named after whom?',
    answer: "President Richard Nixon",
    sources: [
      "Allison Beth \"Allie\" Goertz (born March 2, 1991) is an American musician. Goertz is known for her satirical songs based on various pop culture topics. Milhouse Mussolini van Houten is a fictional character featured in the animated television series \"The Simpsons\", created by Matt Groening who named the character after President Richard Nixon's middle name.",
    ],
    humanLabel: "supported",
    score: 0.0,
    claims: [
      {
        claim: 'Musician and satirist Allie Goertz wrote a song about the "The Simpsons" character Milhouse.',
        verdict: "not_enough_info",
        reason:
          "The sources mention Allie Goertz's satirical songs about pop culture topics and the character Milhouse from 'The Simpsons,' but do not confirm a specific song by her about Milhouse.",
      },
      {
        claim: 'Matt Groening named the "The Simpsons" character Milhouse after President Richard Nixon.',
        verdict: "contradicted",
        reason:
          "The source states that Matt Groening named the character Milhouse after President Richard Nixon's middle name, not after Nixon himself — a near-miss the judge treats as a real discrepancy.",
      },
    ],
  },
  {
    id: "halueval-006",
    question: "What nationality was James Henry Miller's wife?",
    answer: "American",
    sources: [
      'Margaret "Peggy" Seeger (born June 17, 1935) is an American folksinger, married to the singer and songwriter Ewan MacColl until his death in 1989. James Henry Miller, better known by his stage name Ewan MacColl, was an English folk singer, songwriter, and record producer.',
    ],
    humanLabel: "supported",
    score: 0.0,
    claims: [
      {
        claim: "James Henry Miller's wife was American.",
        verdict: "contradicted",
        reason:
          "The sources state Ewan MacColl (James Henry Miller) was married to Margaret 'Peggy' Seeger, who is American, but the claim specifies 'wife' without clarifying the timeframe, and the sources do not confirm his wife at any other time was American.",
      },
    ],
  },
  {
    id: "halueval-008",
    question: "Cadmium Chloride is slightly soluble in this chemical, it is also called what?",
    answer: "alcohol",
    sources: [
      "It is a hygroscopic solid that is highly soluble in water and slightly soluble in alcohol. Ethanol, also called alcohol, ethyl alcohol, and drinking alcohol, is a compound and simple alcohol with the chemical formula C2H5OH.",
    ],
    humanLabel: "supported",
    score: 1.0,
    claims: [
      {
        claim: "Cadmium Chloride is slightly soluble in alcohol.",
        verdict: "entailed",
        reason: "The source explicitly states that Cadmium Chloride is slightly soluble in alcohol, which includes ethanol as described.",
      },
      {
        claim: "Alcohol is also called ethanol.",
        verdict: "entailed",
        reason: "The source explicitly states that ethanol is also called alcohol, ethyl alcohol, and drinking alcohol.",
      },
    ],
  },
  {
    id: "halueval-009",
    question: "Cadmium Chloride is slightly soluble in this chemical, it is also called what?",
    answer: "water with a hint of alcohol",
    sources: [
      "It is a hygroscopic solid that is highly soluble in water and slightly soluble in alcohol. Ethanol, also called alcohol, ethyl alcohol, and drinking alcohol, is a compound and simple alcohol with the chemical formula C2H5OH.",
    ],
    humanLabel: "hallucinated",
    score: 0.0,
    claims: [
      {
        claim: "Cadmium Chloride is slightly soluble in water with a hint of alcohol.",
        verdict: "contradicted",
        reason: "The sources state that cadmium chloride is highly soluble in water, not slightly soluble, which contradicts the claim.",
      },
      {
        claim: "Water with a hint of alcohol is also called an alcohol-water mixture.",
        verdict: "not_enough_info",
        reason: "The sources describe properties of alcohol and its solubility but do not address terminology for water with a hint of alcohol.",
      },
    ],
  },
  {
    id: "halueval-010",
    question: "Which tennis player won more Grand Slam titles, Henri Leconte or Jonathan Stark?",
    answer: "Jonathan Stark",
    sources: [
      "Jonathan Stark (born April 3, 1971) won two Grand Slam doubles titles (the 1994 French Open Men's Doubles and the 1995 Wimbledon Championships Mixed Doubles) and reached the men's singles final at the French Open in 1988, won the French Open men's doubles title in 1984.",
    ],
    humanLabel: "supported",
    score: 0.0,
    claims: [
      {
        claim: "Jonathan Stark won more Grand Slam titles than Henri Leconte.",
        verdict: "contradicted",
        reason:
          "The sources state Jonathan Stark won two Grand Slam doubles titles, while Henri Leconte won one Grand Slam doubles title and reached a singles final, meaning the claim that Stark won more is incorrect.",
      },
    ],
  },
  {
    id: "halueval-012",
    question: "Which genus of moth in the world's seventh-largest country contains only one species?",
    answer: "Crambidae",
    sources: [
      "Indogrammodes is a genus of moths of the Crambidae family. It contains only one species, Indogrammodes pectinicornalis, which is found in India. India is the seventh-largest country by area.",
    ],
    humanLabel: "supported",
    score: 0.0,
    claims: [
      {
        claim: "The genus of moth in the world's seventh-largest country that contains only one species is Crambidae.",
        verdict: "not_enough_info",
        reason:
          "The sources confirm that Indogrammodes is a genus of moths in the Crambidae family with only one species found in India, but do not establish that this is the only such genus in the world's seventh-largest country.",
      },
    ],
  },
  {
    id: "halueval-013",
    question: "Which genus of moth in the world's seventh-largest country contains only one species?",
    answer: "The Indogrammodes genus of moths found in India has only one species.",
    sources: [
      "Indogrammodes is a genus of moths of the Crambidae family. It contains only one species, Indogrammodes pectinicornalis, which is found in India. India is the seventh-largest country by area.",
    ],
    humanLabel: "hallucinated",
    score: 1.0,
    claims: [
      {
        claim: "India is the world's seventh-largest country.",
        verdict: "entailed",
        reason: "The sources explicitly state that India is the seventh-largest country by area.",
      },
      {
        claim: "The Indogrammodes genus of moths is found in India.",
        verdict: "entailed",
        reason: "The source explicitly states that the only species in the Indogrammodes genus, Indogrammodes pectinicornalis, is found in India.",
      },
      {
        claim: "The Indogrammodes genus of moths contains only one species.",
        verdict: "entailed",
        reason: "The source explicitly states that the Indogrammodes genus contains only one species, Indogrammodes pectinicornalis.",
      },
    ],
  },
  {
    id: "halueval-014",
    question:
      'Who was once considered the best kickboxer in the world, but has been involved in a number of controversies relating to "unsportsmanlike conduct" in the sport and crimes of violence outside of the ring?',
    answer: "Badr Hari",
    sources: [
      "Badr Hari is a Moroccan-Dutch super heavyweight kickboxer from Amsterdam. Hari has been a prominent figure in the world of kickboxing and was once considered the best kickboxer in the world, however he has been involved in a number of controversies relating to his \"unsportsmanlike conducts\" in the sport and crimes of violence outside of the ring.",
    ],
    humanLabel: "supported",
    score: 1.0,
    claims: [
      {
        claim: "Badr Hari was once considered the best kickboxer in the world.",
        verdict: "entailed",
        reason: "The sources explicitly state that Badr Hari 'was once considered the best kickboxer in the world'.",
      },
      {
        claim: "Badr Hari has been involved in a number of controversies relating to unsportsmanlike conduct in the sport of kickboxing.",
        verdict: "entailed",
        reason: "The sources explicitly state that Badr Hari has been involved in a number of controversies relating to his 'unsportsmanlike conducts' in the sport of kickboxing.",
      },
      {
        claim: "Badr Hari has been involved in crimes of violence outside of the ring.",
        verdict: "entailed",
        reason: "The source explicitly states that Badr Hari has been involved in crimes of violence outside of the ring.",
      },
    ],
  },
  {
    id: "halueval-019",
    question: "What is the length of the track where the 2013 Liqui Moly Bathurst 12 Hour was staged?",
    answer: "The Mount Panorama Circuit track is longer than 7 km.",
    sources: [
      "The 2013 Liqui Moly Bathurst 12 Hour was staged at the Mount Panorama Circuit, near Bathurst, New South Wales, Australia. Mount Panorama Circuit is a motor racing track; the 6.213 km long track is technically a street circuit.",
    ],
    humanLabel: "hallucinated",
    score: 0.5,
    claims: [
      {
        claim: "The track where the 2013 Liqui Moly Bathurst 12 Hour was staged is the Mount Panorama Circuit.",
        verdict: "entailed",
        reason: "The source explicitly states that the 2013 Liqui Moly Bathurst 12 Hour was staged at the Mount Panorama Circuit.",
      },
      {
        claim: "The Mount Panorama Circuit track is longer than 7 kilometers.",
        verdict: "contradicted",
        reason: "The sources state that the Mount Panorama Circuit is 6.213 kilometers long, which is shorter than 7 kilometers.",
      },
    ],
  },
  {
    id: "halueval-023",
    question: 'Gunmen from Laredo starred which narrator of "Frontier"?',
    answer: 'Although Walter Darwin Coy was part of the cast, the narrator of "Frontier" was actually Richard Boone.',
    sources: [
      'Gunmen from Laredo is a 1959 American western film starring Robert Knapp, Maureen Hingert, and Walter Coy. Walter Darwin Coy was best known for narrating the NBC western anthology series, "Frontier".',
    ],
    humanLabel: "hallucinated",
    score: 0.0,
    claims: [
      {
        claim: 'Walter Darwin Coy was part of the cast of "Frontier".',
        verdict: "contradicted",
        reason: "The sources state that Walter Darwin Coy narrated the NBC western anthology series 'Frontier' but do not mention him being part of its cast.",
      },
      {
        claim: 'Richard Boone was the narrator of "Frontier".',
        verdict: "contradicted",
        reason: "The sources state that Walter Coy, not Richard Boone, was the narrator of the NBC western anthology series 'Frontier'.",
      },
    ],
  },
];

// Curated editorial commentary about this specific dataset/methodology (see README.md's
// diagnosis narrative) — not something a benchmark run computes, so it's not part of the
// backend's GET /v1/benchmark contract. The real API client merges this in alongside the
// live-computed numbers; see api.ts.
export const KNOWN_LIMITATIONS: string[] = [
  "Small sample (100 examples) — precision/recall/F1 carry meaningful sampling noise.",
  "Calibration is directional, not tight: a 0.0-confidence example still turns out supported ~1 in 8 times.",
  'One diagnosed failure case substitutes a different but similarly-themed historical event ("the Korean War" for sources describing World War II) via outside knowledge the prompt explicitly forbids — not fixed.',
  "At least one row's right_answer/hallucinated_answer pairing looks swapped relative to its source text — likely HaluEval label noise, not a judge error (see halueval-013 below).",
];

export const benchmarkSummary: BenchmarkSummary = {
  precision: 87.0,
  recall: 80.0,
  f1: 83.3,
  naiveAlwaysSupportedF1: 0.0,
  naiveLengthHeuristicF1: 73.7,
  exampleCount: 100,
  judgeModel: "mistral-large-latest",
  datasetName: "HaluEval QA (100-example subset)",
  calibration: [
    { score: 1.0, count: 54, empiricalSupportedRate: 81.5 },
    { score: 0.0, count: 37, empiricalSupportedRate: 13.5 },
  ],
  knownLimitations: KNOWN_LIMITATIONS,
};

export const liveScoringRuns: LiveScoringRun[] = [];
