const puppeteer = require("puppeteer");
const path = require("path");

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  const filePath = "file:///" + path.resolve("civicrecords-ai-manual.html").replace(/\\/g, "/");
  console.log("Loading:", filePath);
  await page.goto(filePath, { waitUntil: "networkidle0" });
  await page.pdf({
    path: "civicrecords-ai-manual.pdf",
    format: "Letter",
    printBackground: true,
    margin: { top: "0.75in", bottom: "0.75in", left: "0.75in", right: "0.75in" },
  });
  await browser.close();
  console.log("PDF generated: civicrecords-ai-manual.pdf");
})();
