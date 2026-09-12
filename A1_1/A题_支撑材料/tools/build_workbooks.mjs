import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";


const root = path.resolve(import.meta.dirname, "..");
const inputDir = path.join(root, "tmp", "numerical");
const outputDir = path.join(root, "outputs", "results");
const previewDir = path.join(root, "tmp", "xlsx_previews");


async function readNumericCsv(fileName) {
  const text = (await fs.readFile(path.join(inputDir, fileName), "utf8")).replace(/^\uFEFF/, "");
  return text.trimEnd().split(/\r?\n/).map((line, rowIndex) =>
    line.split(",").map((field, columnIndex) => {
      if (rowIndex === 0) return field;
      if (field === "" || field.toLowerCase() === "nan") return null;
      const value = Number(field);
      if (!Number.isFinite(value)) return field;
      return columnIndex === 0 ? Math.round(value) : Math.round(value * 1.0e4) / 1.0e4;
    }),
  );
}


function columnName(index) {
  let value = index + 1;
  let name = "";
  while (value > 0) {
    value -= 1;
    name = String.fromCharCode(65 + (value % 26)) + name;
    value = Math.floor(value / 26);
  }
  return name;
}


async function addDataSheet(workbook, sheetName, csvName, previewStem) {
  const matrix = await readNumericCsv(csvName);
  const rowCount = matrix.length;
  const columnCount = matrix[0].length;
  const lastColumn = columnName(columnCount - 1);
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  sheet.getRange("A1").write(matrix);

  const used = sheet.getRange(`A1:${lastColumn}${rowCount}`);
  used.format.font = { name: "Arial", size: 10, color: "#1F2937" };
  used.format.verticalAlignment = "center";
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: "#1F4E78",
    font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    rowHeight: 28,
    borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
  };
  sheet.getRange(`A2:A${rowCount}`).format.numberFormat = "0";
  sheet.getRange(`B2:${lastColumn}${rowCount}`).format.numberFormat = "0.0000";
  sheet.getRange(`A1:A${rowCount}`).format.columnWidth = 18;
  sheet.getRange(`B1:${lastColumn}${rowCount}`).format.columnWidth = 10;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);

  const preview = await workbook.render({
    sheetName,
    range: `A1:${lastColumn}${Math.min(rowCount, 18)}`,
    scale: 1.3,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, `${previewStem}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
  return { sheetName, rowCount, columnCount, lastColumn };
}


async function buildWorkbook(fileName, sheetSpecs) {
  const workbook = Workbook.create();
  const metadata = [];
  for (const spec of sheetSpecs) {
    metadata.push(await addDataSheet(workbook, ...spec));
  }
  workbook.recalculate();
  const inspection = await workbook.inspect({
    kind: "sheet,region",
    maxChars: 5000,
    tableMaxRows: 4,
    tableMaxCols: 8,
  });
  console.log(fileName, inspection.ndjson);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(path.join(outputDir, fileName));
  return metadata;
}


await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const manifest = {};
manifest["result1.xlsx"] = await buildWorkbook("result1.xlsx", [
  ["温度", "result1_temperature.csv", "result1_temperature"],
  ["水分浓度", "result1_moisture.csv", "result1_moisture"],
]);
manifest["result2.xlsx"] = await buildWorkbook("result2.xlsx", [
  ["温度", "result2_temperature.csv", "result2_temperature"],
  ["水分浓度", "result2_moisture.csv", "result2_moisture"],
]);
manifest["result3.xlsx"] = await buildWorkbook("result3.xlsx", [
  ["Sheet1", "result3_moisture.csv", "result3_moisture"],
]);
manifest["result4.xlsx"] = await buildWorkbook("result4.xlsx", [
  ["Sheet1", "result4_moisture.csv", "result4_moisture"],
]);

await fs.writeFile(
  path.join(outputDir, "manifest.json"),
  JSON.stringify(manifest, null, 2),
  "utf8",
);
