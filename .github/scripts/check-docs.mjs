#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";

const API_URL =
  "https://soporte.pagopar.com/portal/api/kbArticles?portalId=edbsn090a928882b7e5dc61097ae8f267763b869c98670cc3d3f0899a42e01f005cf6&from=1&limit=100&categoryId=387583000001110307&locale=es";

const DOCS_DIR = path.resolve("docs");

async function main() {
  const response = await fetch(API_URL);

  if (!response.ok) {
    throw new Error(
      `Failed to fetch Pagopar documentation (${response.status})`
    );
  }

  const { data: articles = [] } = await response.json();

  // Local PDF documentation (without extension)
  const localDocs = new Set(
    (await fs.readdir(DOCS_DIR))
      .filter((file) => file.endsWith(".pdf"))
      .map((file) => path.basename(file, ".pdf"))
  );

  // Documentation published by Pagopar
  const remoteDocs = articles
    .filter((article) => article.locale === "es")
    .map((article) => ({
      title: article.title,
      permalink: article.permalink,
      modifiedTime: article.modifiedTime,
      url: article.webUrl,
    }));

  const missingDocs = remoteDocs.filter(
    (doc) => !localDocs.has(doc.permalink)
  );

  if (missingDocs.length === 0) {
    console.log("✅ Documentation is up to date.");
    return;
  }

  console.error("");
  console.error("❌ Missing documentation detected.");
  console.error("");
  console.error(
    "One or more documentation pages published by Pagopar are not present in the docs/ directory."
  );
  console.error("");
  console.error(
    "This likely means the API has introduced new features or changes that are not yet supported by this SDK."
  );
  console.error(
    "Please review the missing documentation and implement the corresponding functionality before merging."
  );
  console.error("");

  for (const doc of missingDocs) {
    console.error(`• ${doc.title}`);
    console.error(`  Permalink : ${doc.permalink}`);
    console.error(`  Modified  : ${doc.modifiedTime}`);
    console.error(`  URL       : ${doc.url}`);
    console.error("");
  }

  process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
