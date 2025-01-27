import { type NextPage } from "next";
import React, { useState } from "react";
import { API_URL, initialQuestions } from "../settings";
import type { Followup } from "../types";
import Page from "../components/page";
import { SearchBox } from "../components/searchbox";

const randomQuestion = () =>
  initialQuestions[Math.floor(Math.random() * initialQuestions.length)] || "";

const ignoreAbort = (error: Error) => {
  if (error.name !== "AbortError") {
    throw error;
  }
};

const Semantic: NextPage = () => {
  const [query, setQuery] = useState(() => randomQuestion());
  const [controller, setController] = useState(() => new AbortController());
  const [results, setResults] = useState<SemanticEntry[]>([]);

  const semantic_search = async (query: string) => {
    const controller = new AbortController();
    setController(controller);
    const res = await fetch(API_URL + "/semantic", {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
      body: JSON.stringify({ query: query }),
    }).catch(ignoreAbort);

    if (!res) {
      return;
    } else if (!res.ok) {
      console.error("load failure: " + res.status);
    }

    const data = await res.json();

    setResults(data);
  };

  return (
    <Page page="semantic">
      <h2>Retrieve relevant data sources from alignment research</h2>
      <SearchBox
        search={semantic_search}
        query={query}
        onQuery={setQuery}
        abortSearch={() => controller.abort()}
      />
      <ul>
        {results.map((entry, i) => (
          <li key={"entry" + i}>
            <ShowSemanticEntry entry={entry} />
          </li>
        ))}
      </ul>
    </Page>
  );
};

// Round trip test. If this works, our heavier usecase probably will (famous last words)
// The one real difference is we'll want to send back a series of results as we get
// them back from OpenAI - I think we can just do this with a websocket, which
// shouldn't be too much harder.

type SemanticEntry = {
  title: string;
  authors: string[];
  date: string;
  url: string;
  tags: string;
  text: string;
};

export const ShowSemanticEntry: React.FC<{ entry: SemanticEntry }> = ({ entry }) => {
  return (
    <div className="my-3">
      {/* horizontally split first row, title on left, authors on right */}
      <div className="flex">
        <h3 className="flex-1 text-xl">{entry.title}</h3>
        <p className="my-0 flex-1 text-right">
          {entry.authors.join(", ")} - {entry.date}
        </p>
      </div>
      {entry.text.split("\n").map((paragraph, i) => {
        const p = paragraph.trim();
        if (p === "") return <></>;
        if (p === ".....") return <hr key={"b" + i} />;
        return (
          <p className="text-sm" key={"p" + i}>
            {" "}
            {paragraph}{" "}
          </p>
        );
      })}

      <a href={entry.url}>Read more</a>
    </div>
  );
};

export default Semantic;
