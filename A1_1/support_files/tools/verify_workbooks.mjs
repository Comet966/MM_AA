// Read-only verification for the four exported result workbooks.

import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const dir = path.join(root, "outputs", "results");
for (const name of ["result1.xlsx", "result2.xlsx", "result3.xlsx", "result4.xlsx"]) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(dir, name)));
  const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 3000 });
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 50 },
    summary: "final formula error scan",
  });
  console.log(JSON.stringify({ name, sheets: sheets.ndjson, errors: errors.ndjson }));
}
